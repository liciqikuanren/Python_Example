"""AI 接口插件：内置 MCP Streamable HTTP 服务，让 AI 打开/配置串口并收发数据。

- 提供 6 个工具：list_ports / open_port / close_port / get_status / send / read_received；
- AI 的发送经 transmitter（source="ai"），会在接收区打 [AI] 标签；
- AI 读取接收数据走独立缓冲区，不影响人类接收显示。
- 传输用 streamable-http（兼容 @deepseek-ai/dsh-mcp-client 等客户端）。
"""

import asyncio
import json
import threading
import urllib.request
from collections import deque

from mcp.server.fastmcp import FastMCP

from core import codec
from core.codec import NEWLINE_BYTES, bytes_to_hex, bytes_to_text


class RxBuffer:
    """线程安全的接收数据缓冲（AI 专用）。"""

    def __init__(self):
        self._lock = threading.Lock()
        self._chunks: deque = deque()
        self._total = 0

    def push(self, data: bytes) -> None:
        with self._lock:
            self._chunks.append(bytes(data))
            self._total += len(data)

    def drain(self) -> bytes:
        with self._lock:
            data = b"".join(self._chunks)
            self._chunks.clear()
            return data

    def peek(self) -> bytes:
        with self._lock:
            return b"".join(self._chunks)

    @property
    def pending(self) -> int:
        with self._lock:
            return sum(len(c) for c in self._chunks)

    @property
    def total(self) -> int:
        return self._total


def build_server(serial, transmitter, config, log, rxbuf: RxBuffer,
                 extra: dict | None = None) -> FastMCP:
    """构造 FastMCP 实例并注册工具。

    extra：调试模式可选服务 {"tcp_forward":.., "justfloat":.., "float_recorder":..}；
    存在哪个服务就注册对应工具（正常模式不传 → 仅 6 个基础工具）。
    """
    extra = extra or {}
    host = config.get("ai_server_host", "127.0.0.1")
    port = int(config.get("ai_server_port", 8765))
    mcp = FastMCP("serial-assistant", host=host, port=port,
                  streamable_http_path="/mcp", log_level="WARNING",
                  stateless_http=True)

    @mcp.tool()
    def list_ports() -> list:
        """列出可用串口，返回 [{device, description}]。"""
        return serial.list_ports()

    @mcp.tool()
    def open_port(port: str, baudrate: int = 115200, bytesize: int = 8,
                  parity: str = "N", stopbits: float = 1,
                  flow: str = "None") -> dict:
        """打开串口（若已打开会先关闭再打开）。flow 取值 None/RTS-CTS/XON-XOFF。"""
        params = {
            "port": port,
            "baudrate": int(baudrate),
            "bytesize": int(bytesize),
            "parity": parity,
            "stopbits": float(stopbits),
            "flow": flow,
            "rtscts": flow == "RTS-CTS",
            "xonxoff": flow == "XON-XOFF",
        }
        if serial.is_open:
            serial.close()
        ok, err = serial.open(params)
        return {"ok": ok, "message": err or "已打开", "port": port,
                "baudrate": int(baudrate)}

    @mcp.tool()
    def close_port() -> dict:
        """关闭串口。"""
        was_open = serial.is_open
        serial.close()
        return {"ok": True, "message": "已关闭" if was_open else "串口本未打开"}

    @mcp.tool()
    def get_status() -> dict:
        """获取当前连接状态与 AI 缓冲统计。"""
        p = serial.current_params or {}
        return {
            "connected": serial.is_open,
            "port": p.get("port", ""),
            "baudrate": p.get("baudrate", 0),
            "pending_rx_bytes": rxbuf.pending,
            "ai_rx_total_bytes": rxbuf.total,
            "debug_mode": bool(config.get("debug_mode", False)),
        }

    debug_mode = bool(extra.get("justfloat"))
    if not debug_mode:
        # ---- 正常模式：通用收发（AI 可任意发送/读取原始字节）----

        @mcp.tool()
        def send(data: str, as_hex: bool = False, encoding: str = "UTF-8",
                 newline: str = "") -> dict:
            """发送数据。newline 可选 ""（不追加）/crlf/lf/cr；as_hex=True 时 data 为十六进制。"""
            newline = (newline or "").upper()
            add_newline = newline in NEWLINE_BYTES
            newline_kind = newline if add_newline else "CRLF"
            ok, err = transmitter.send(data, as_hex, encoding, add_newline,
                                       newline_kind, source="ai")
            bytes_sent = 0
            if ok:
                try:
                    payload = codec.parse_send_payload(data, as_hex, encoding)
                    if add_newline:
                        payload += NEWLINE_BYTES[newline_kind]
                    bytes_sent = len(payload)
                except Exception:
                    bytes_sent = 0
            return {"ok": ok, "message": err or "已发送", "bytes_sent": bytes_sent}

        @mcp.tool()
        def read_received(as_hex: bool = False, encoding: str = "UTF-8",
                          clear: bool = True) -> dict:
            """读取自上次读取以来接收到的数据（默认读取后清空缓冲）。"""
            data = rxbuf.drain() if clear else rxbuf.peek()
            text = bytes_to_hex(data) if as_hex else bytes_to_text(data, encoding)
            return {"data": text, "bytes": len(data)}

    else:
        # ---- 调试模式：AI 只能发送串口指令（FireWater），查看数据走录制 CSV ----
        from plugins import commands

        @mcp.tool()
        def list_commands() -> dict:
            """列出可下发的串口指令参数（FireWater 格式：关键字:数值;，一行一帧）。"""
            return commands.describe_commands()

        @mcp.tool()
        def send_command(command: str) -> dict:
            """发送一条 FireWater 串口指令（如 "temp_sw:1;temp_tar:37;"），校验参数与范围。"""
            try:
                commands.parse_command(command)
            except ValueError as e:
                return {"ok": False, "message": str(e)}
            ok, err = transmitter.send(command.strip(), False, "UTF-8",
                                       True, "CRLF", source="ai")
            return {"ok": ok, "message": err or "指令已发送", "command": command.strip()}

        @mcp.tool()
        def set_params(params: dict) -> dict:
            """按 {参数: 数值} 构造并发送串口指令（如 {"temp_sw": 1, "temp_tar": 37}）。"""
            try:
                command = commands.build_command(params)
            except ValueError as e:
                return {"ok": False, "message": str(e)}
            ok, err = transmitter.send(command, False, "UTF-8",
                                       True, "CRLF", source="ai")
            return {"ok": ok, "message": err or "指令已发送", "command": command}

        @mcp.tool()
        def send_preset(preset: str) -> dict:
            """发送温度 PID 场景预设指令（如 "闭环控制默认"/"调大比例系数"/"增大阻尼"/"切回开环"）。"""
            spec = commands.PRESETS.get(preset)
            if spec is None:
                return {"ok": False, "message": f"未知预设「{preset}」，可用：{', '.join(commands.PRESETS)}"}
            command = commands.build_command(spec["params"])
            ok, err = transmitter.send(command, False, "UTF-8",
                                       True, "CRLF", source="ai")
            return {"ok": ok, "message": err or "指令已发送", "preset": preset,
                    "command": command, "desc": spec["desc"]}

    # ---------------- 配置管理（YAML 按需加载/保存/修改） ----------------
    from plugins.config import DEFAULTS as _CONFIG_KEYS

    @mcp.tool()
    def config_status() -> dict:
        """查询当前配置文件路径与配置项数量。"""
        return {"path": config.path, "keys": len(_CONFIG_KEYS),
                "debug_mode": bool(config.get("debug_mode", False))}

    @mcp.tool()
    def config_save(path: str = "") -> dict:
        """按需保存：把当前全部配置写入指定 .yaml/.json（缺省保存到默认配置文件）。"""
        target = path or config.path
        config.save_to(target)
        return {"ok": True, "path": str(target)}

    @mcp.tool()
    def config_load(path: str = "") -> dict:
        """按需加载：从指定 .yaml/.json 读取配置（缺省重新加载默认配置）。"""
        if path:
            config.load_from(path)
        else:
            config.load()
        return {"ok": True, "path": config.path,
                "debug_mode": bool(config.get("debug_mode", False))}

    @mcp.tool()
    def config_set(key: str, value) -> dict:
        """按需修改：设置一项配置并立即保存（仅支持已定义的配置键）。"""
        if key not in _CONFIG_KEYS:
            return {"ok": False, "message": f"未知配置键：{key}（可用 config_status 查看键数）"}
        config.set(key, value)
        return {"ok": True, "key": key, "value": config.get(key)}

    # ---------------- 调试模式工具（按服务存在与否注册） ----------------
    tcp = extra.get("tcp_forward")
    if tcp is not None:

        @mcp.tool()
        def tcp_forward_start(host: str = "127.0.0.1", port: int = 9000) -> dict:
            """启动 TCP 转发服务端（串口 ↔ TCP 客户端双向透传）。"""
            tcp.start(host, port)
            return {"ok": True, "message": "已请求启动"}

        @mcp.tool()
        def tcp_forward_stop() -> dict:
            """停止 TCP 转发服务端并断开所有客户端。"""
            tcp.stop()
            return {"ok": True, "message": "已请求停止"}

        @mcp.tool()
        def tcp_forward_status() -> dict:
            """查询 TCP 转发运行状态。"""
            return tcp.status()

    jf = extra.get("justfloat")
    if jf is not None:

        @mcp.tool()
        def justfloat_status() -> dict:
            """查询 justfloat 解析统计（帧数/图片帧/丢弃字节/开关）。"""
            return jf.stats()

        @mcp.tool()
        def justfloat_enable(enabled: bool = True) -> dict:
            """启用/停用 justfloat 协议解析。"""
            jf.set_enabled(enabled)
            return {"ok": True, "enabled": bool(enabled)}

        @mcp.tool()
        def justfloat_reset() -> dict:
            """重置 justfloat 解析器（清空缓冲与统计）。"""
            jf.reset()
            return {"ok": True, "stats": jf.stats()}

        @mcp.tool()
        def justfloat_frames(limit: int = 100, clear: bool = True) -> dict:
            """读取累积的浮点帧列表（默认读后清空）。"""
            frames = jf.read_frames(limit, clear)
            return {"frames": frames, "count": len(frames)}

        @mcp.tool()
        def justfloat_latest() -> dict:
            """查询当前解析到的通道：{names, values, count}（重命名后的名字 + 最新数值）。"""
            return jf.latest()

        @mcp.tool()
        def justfloat_rename(mapping: dict) -> dict:
            """重命名解析通道。mapping 形如 {"0": "PumpRPM", "Ch1": "Flow_L_min"}；
            重命名后的名字会作为浮点录制（float_recorder）的表头与数据源。"""
            return jf.rename(mapping)

        @mcp.tool()
        def justfloat_reset_names() -> dict:
            """清除全部通道重命名（恢复 Ch0..）。"""
            return jf.reset_names()

        @mcp.tool()
        def justfloat_apply_doc_channels() -> dict:
            """一键按指令文档（串口指令文档.md）命名 8 个通道
            （temp_kp/temp_ki/temp_kd/temp_sw/temp_tar/temp_value/temp_current/timestamp）。"""
            from plugins import commands
            mapping = {str(i): name for i, (name, _unit) in enumerate(commands.CHANNELS)}
            return jf.rename(mapping)

    fr = extra.get("float_recorder")
    if fr is not None:

        @mcp.tool()
        def float_recorder_start(channels=None, duration: float | None = None) -> dict:
            """开始浮点通道录制。channels 可选表头通道名列表；duration 秒（缺省用默认 5 分钟）。"""
            return fr.start(channels, duration)

        @mcp.tool()
        def float_recorder_pause() -> dict:
            """暂停录制（不写行，时长照走）。"""
            return fr.pause()

        @mcp.tool()
        def float_recorder_resume() -> dict:
            """继续已暂停的录制。"""
            return fr.resume()

        @mcp.tool()
        def float_recorder_stop() -> dict:
            """结束录制并落盘 CSV。"""
            return fr.stop()

        @mcp.tool()
        def float_recorder_status() -> dict:
            """查询录制状态（state/rows/remaining/通道数）。"""
            return fr.status()

        @mcp.tool()
        def float_recorder_list() -> list:
            """列出录制目录下的 CSV 文件。"""
            return fr.list_files()

        @mcp.tool()
        def float_recorder_set_dir(path: str) -> dict:
            """设置录制保存目录。"""
            fr.set_dir(path)
            return {"ok": True, "dir": fr.status()["dir"]}

        @mcp.tool()
        def float_recorder_set_duration(seconds: float) -> dict:
            """设置录制默认时长（秒），下次 start 生效。"""
            fr.set_duration(seconds)
            return {"ok": True, "duration": fr.status()["duration"]}

        @mcp.tool()
        def float_recorder_set_sample_hz(hz: float) -> dict:
            """设置录制采样率（Hz），下次 start 生效。"""
            fr.set_sample_hz(hz)
            return {"ok": True, "sample_hz": fr.status()["sample_hz"]}

    return mcp


def _push_received(data: bytes, config) -> None:
    """把接收到的数据推送到 DSH 串口桥（fire-and-forget，失败静默）。"""
    if not config.get("ai_push_enabled", False):
        return
    url = config.get("ai_push_url", "")
    if not url:
        return
    payload = {
        "text": bytes_to_text(data, config.get("rx_encoding", "UTF-8")),
        "hex": bytes_to_hex(data),
        "mode": config.get("ai_push_mode", "chat"),
    }

    def _post():
        try:
            req = urllib.request.Request(
                url,
                data=json.dumps(payload).encode("utf-8"),
                headers={"Content-Type": "application/json"},
                method="POST",
            )
            urllib.request.urlopen(req, timeout=2)
        except Exception:
            pass  # 推送失败不影响串口主流程

    threading.Thread(target=_post, daemon=True).start()


class Plugin:
    name = "ai_server"
    inject = ["serial", "transmitter", "config", "log"]

    def apply(self, ctx):
        config = ctx.get("config")
        log = ctx.get("log")

        if not config.get("ai_server_enabled", True):
            log("AI 接口已禁用（ai_server_enabled=false）")
            return

        serial = ctx.get("serial")
        transmitter = ctx.get("transmitter")
        rxbuf = RxBuffer()

        # 懒获取调试模式服务（正常模式未加载 → None，不注册对应工具）
        extra = {}
        for name in ("tcp_forward", "justfloat", "float_recorder"):
            svc = ctx.get(name, strict=False)
            if svc is not None:
                extra[name] = svc
        debug_mode = bool(extra)

        async def on_rx(data):
            # 调试模式：justfloat 数据流不缓存、不注入 DSH 上下文（AI 查看数据走录制 CSV）
            if not debug_mode:
                rxbuf.push(data)
                _push_received(data, config)

        ctx.on("serial_data_received", on_rx)

        server = build_server(serial, transmitter, config, log, rxbuf, extra)
        ctx.provide("ai_server", server)

        # 在现有后台 asyncio 循环里作为任务运行（比另开线程更可靠）
        loop = asyncio.get_running_loop()

        async def _run_server():
            """包装运行：uvicorn 端口冲突时 sys.exit(1) 是 SystemExit，必须拦下，
            否则会杀死整个后台事件循环（热切换重启 AI 接口时尤其关键）。"""
            try:
                await server.run_streamable_http_async()
            except SystemExit:
                log("AI 接口退出（端口冲突或主动停止，不影响后台循环）")
            except Exception as e:
                log(f"AI 接口异常：{e}")

        task = loop.create_task(_run_server())

        def on_done(t):
            if t.cancelled():
                return
            exc = t.exception()
            if exc is not None:
                log(f"AI 接口启动失败：{exc}")

        task.add_done_callback(on_done)

        async def teardown():
            """停止 AI 接口：取消任务并等待 uvicorn 完全关闭（释放端口，
            否则热切换重启时新实例会因端口未释放而绑定失败）。"""
            task.cancel()
            try:
                await task
            except (asyncio.CancelledError, SystemExit):
                pass
            log("AI 接口已停止")

        ctx.effect(lambda: None, teardown)

        host = config.get("ai_server_host", "127.0.0.1")
        port = int(config.get("ai_server_port", 8765))
        log(f"AI 接口已启动：http://{host}:{port}/mcp")
        # 通知 UI：AI 接口已就绪（stateless_http 无 session，重启不失效）
        asyncio.run_coroutine_threadsafe(
            ctx.emit("ai_server_ready", {"host": host, "port": port}), loop
        )
