---
name: serial-assistant-mcp
description: Operate the Cordis Serial Port Assistant (Serial_Port_Assistant) through its MCP Streamable HTTP interface at http://127.0.0.1:8765/mcp. Use when connecting to a running instance, renaming JustFloat channels, sending FireWater temperature-PID commands, recording float data to CSV, or tuning temp_kp/temp_ki/temp_kd for the temperature PID simulation. Covers debug-mode AI constraints (command-only sending, CSV-only data viewing, no DSH context injection) and hard-won PID tuning lessons (temp_kd is an actuator damping, not a derivative term; integral windup causes massive overshoot; the recommended parameter set is kp=12, ki=0, kd=2).
---

# Serial Port Assistant — MCP 操作指南（温度 PID 场景）

通过 MCP 接口远程操作串口助手（Cordis 插件框架 + PyQt6）。本项目源码即 `Serial_Port_Assistant` 工程本身，
配置在 `~/.serial_assistant/config.yaml`（YAML，兼容旧 config.json），指令依据 `docs/串口指令文档.md`。

## 1. 连接与工具

- **MCP 端点**：`POST http://127.0.0.1:8765/mcp`，请求头必须带 `Accept: application/json, text/event-stream`，
  Content-Type `application/json; charset=utf-8`；body 为 JSON-RPC（`{"jsonrpc":"2.0","id":N,"method":"tools/call","params":{"name":"...","arguments":{...}}}`）。
  响应为 SSE 格式，取 `data:` 行的 JSON 的 `result.content[].text`。
- **中文编码**：用 PowerShell 发中文/参数时，把 JSON body 写成无 BOM UTF-8 文件再 `-InFile` 发送，
  避免控制台编码把内容弄乱（曾出现 bytes_sent 与预期不符的乱码问题）。
- **先查状态再操作**：`get_status`（连接/端口/波特率/debug_mode）→ `justfloat_status`（解析统计/通道名/最新值）。
- **工具集**（调试模式 32 个；正常模式 10 个）：
  - 串口：`list_ports` `open_port` `close_port` `get_status`
  - 配置：`config_status` `config_save` `config_load` `config_set`
  - 指令（调试模式）：`list_commands` `send_command` `set_params` `send_preset`
  - JustFloat：`justfloat_status` `justfloat_enable` `justfloat_reset` `justfloat_frames`
    `justfloat_latest` `justfloat_rename` `justfloat_reset_names` `justfloat_apply_doc_channels`
  - 录制：`float_recorder_start/pause/resume/stop/status/list/set_dir/set_duration/set_sample_hz`
  - TCP 转发：`tcp_forward_start/stop/status`

## 2. 调试模式下 AI 的能力边界（必须遵守）

- **发送**：只能用 `send_command`（指令文本，如 `temp_sw:1;temp_tar:37;`）、`set_params`（参数 dict）
  或 `send_preset`（预设名）。**没有通用 `send`**——AI 不能发任意字节。
- **查看数据**：没有 `read_received`。实时看 `justfloat_latest`（当前帧数值），历史数据只能看
  `float_recorder_*` 录制的 CSV（`csv_floder/log_YYYYMMDD_HHMMSS.csv`）。
- **不注入 DSH 上下文**：AI 联动推送在调试模式被禁用，JustFloat 数据流不会进入 Agent 会话。
- 指令会被校验（参数名 + 取值范围，如 `temp_sw` 只能 0/1、`temp_tar` 0~100），非法会被拒绝。

## 3. 标准操作流程（温度 PID 场景）

1. **确认状态**：`get_status` + `justfloat_status`（注意通道当前是 Ch0.. 还是已命名）。
2. **通道命名**：`justfloat_apply_doc_channels` 一键按文档命名 8 通道
   （temp_kp/temp_ki/temp_kd/temp_sw/temp_tar/temp_value/temp_current/timestamp）；
   或 `justfloat_rename({"0": "PumpRPM"})` 自定义。
3. **发指令**：`set_params({"temp_sw": 1, "temp_tar": 37})` 或 `send_command("temp_sw:1;temp_tar:37;")`
   或 `send_preset("闭环控制默认")`。发送后下一帧（10ms）即可在 `justfloat_latest` 看到回显确认。
4. **观察波形**：`justfloat_latest` 高频采样，或开录制：
   `float_recorder_set_sample_hz({"hz": 50})` → `float_recorder_start({"duration": 6})` →
   到点自动停止（`reason: timeout`）→ 用 `float_recorder_list` 找文件 → 读取 `csv_floder/*.csv` 分析。
   录制表头自动使用重命名后的通道名（`Time(s),temp_kp,...,timestamp`），20Hz/50Hz 足够看清阶跃响应。
5. **阶跃测试要诀**：先切开环（`set_params({"temp_sw": 0})`）让温度回落到低位 → 下发目标
   （`temp_tar = 当前温度 + 20`，温差 20）→ 开始录制 → 150ms 后开闭环（`set_params({"temp_sw": 1})`）触发阶跃。

## 4. 温度 PID 调参经验（实测总结，20°C 温差阶跃）

### 参数含义（务必读文档，不要想当然）

| 参数 | 含义 | 陷阱 |
|---|---|---|
| `temp_kp` | 温度环比例系数 | 大 → 电流饱和升温快，但接近目标时撤流猛 |
| `temp_ki` | 温度环积分系数 | **大 → 积分 windup → 严重超调且不收敛** |
| `temp_kd` | **电流执行器一阶惯性阻尼**（不是 PID 微分项！） | **大 → 电流变钝、刹车慢 → 超调更大** |

### 实测对比（温差 20°C 阶跃，目标温度 73.2°C 等）

| 参数 (kp/ki/kd) | 首次到达 | 峰值超调 | 结论 |
|---|---|---|---|
| 60 / 20 / 5 | 0.48s | +21°C | ki 积分饱和 → 冲过头 |
| 20 / 3 / 25 | 1.32s | +31°C | kd 钝 + ki windup → 更糟 |
| 15 / 0 / 35 | 1.68s | +8.5°C | 无积分了，但 kd 大刹车慢 |
| 10 / 0 / 60 | ~1.5s | +19°C | kd 越大概率越糟（钝） |
| **12 / 0 / 2** | **0.68s** | **+1.8°C** | ✅ 最优：kp 适中 + ki=0 + kd 小（电流灵敏） |

**推荐参数**：`temp_kp=12, temp_ki=0, temp_kd=2` → 温差 20°C 阶跃 0.68s 到达、超调仅 1.8°C、2s 内收敛、稳态误差 ~0.2°C（纯比例固有）。

### 规律与物理

- 电流 ≈ `kp × 误差`（ki=0 时纯比例，可用 `justfloat_latest` 的 temp_current/temp_value 反验，如 12×0.81≈9.7A）。
- 升温斜率可达 15-20°C/s（电流饱和 ~57-90A，固件限幅与文档 5A 不同——以实测为准）。
- 超调主因：① 积分 windup（ki>0 在升温期累积）；② 电流执行器太钝（kd 大）导致接近目标时撤流慢。
- ki=0 有稳态残差（维持温度需散热电流 → 误差 = 维持电流/kp）；要零误差需小 ki + 限幅，但 2s 快速响应场景优先 ki=0。

### 常见坑（都踩过）

1. **忘了发 `temp_sw:1`** → 数据是开环降温（电流恒 0），阶跃没触发——每次阶跃前确认 sw=1。
2. **CSV 首行 tar 是旧值**：分析时取第一行 `temp_tar` 会误读（录制 start 时目标可能还没改）；
   应以本次设置的值为准，或逐行打印确认。
3. **`temp_kd` 当微分项调** → 方向完全反了（越大越糟）。文档写的是"电流响应阻尼"。
4. **参数越界被拒**：`temp_sw:2`、`temp_tar:150` 会被 `send_command`/`set_params` 拒绝（范围校验），
   先 `list_commands` 看元数据。
5. **10ms 高频帧**：JustFloat 100Hz 数据流只在后台解析/录制，UI 表格按 250ms 节流刷新；
   不要用 `read_received`/DSH 注入看原始字节（调试模式已禁用，且无意义）。

## 5. 配置文件（YAML 按需加载/保存）

- 默认 `~/.serial_assistant/config.yaml`（兼容旧 config.json，BOM 健壮）。
- `config_status` / `config_save(path)` / `config_load(path)` / `config_set(key, value)` 支持 AI 按需管理。
- 关键键：`debug_mode`（调试开关，勾选即热切换无需重启）、`justfloat_channel_names`（通道重命名映射）、
  `csv_dir` / `csv_duration_s`（默认 300s）/ `csv_sample_hz`（默认 1.0）。
