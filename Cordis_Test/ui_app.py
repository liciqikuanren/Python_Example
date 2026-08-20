"""
ui_app.py - 案例：多插件仪器上位机仿真（PyQt6 + asyncio 双线程）

插件拓扑（依赖方向）：
    config ──┐
    logger ──┼──▶ serial ──▶ temp、psu
             └────────────────▶ psu 提供 "psu" 服务 ──▶ alarm

事件流（一对多广播）：
    temp_reading ──▶ recorder + alarm + UI
    power_status  ──▶ recorder + UI
    alarm         ──▶ UI

演示的 Cordis 特性：
    1. 依赖注入 + load_all 自动排序（乱序传入也能正确加载）
    2. 反向依赖感知（serial 用 on_depend 知道谁接入了总线）
    3. 事件总线一对多（temp 事件同时被 recorder/alarm/UI 消费）
    4. 服务注入（alarm 注入 psu 服务并调用它断电）
    5. 级联卸载（拔出 serial 自动逆序卸载 alarm/psu/temp）
    6. UI 作为叶子插件，可插拔

线程模型：主线程跑 Qt（UI），后台线程跑 asyncio（业务），Qt 信号桥接。
"""

import asyncio
import math
import os
import sys
import threading
import time

# 让控制台按 UTF-8 输出，避免 Windows GBK 控制台打印 emoji 报错
try:
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:
    pass

from PyQt6.QtCore import QObject, QTimer, pyqtSignal
from PyQt6.QtWidgets import (
    QApplication, QLabel, QMainWindow, QTextEdit, QVBoxLayout, QWidget,
)

from mini_cordis import Cordis, Context


# ================= 基础服务插件 =================

class ConfigPlugin:
    name = "config"
    inject = []

    def apply(self, ctx: Context):
        ctx.provide("config", {
            "port": "COM3",
            "temp_threshold": 70,
            "temp_interval": 2,
            "power_interval": 3,
        })


class LoggerPlugin:
    name = "logger"
    inject = []

    def apply(self, ctx: Context):
        def log(msg: str):
            print(f"[LOG] {msg}")

        ctx.provide("log", log)


# ================= 串口总线（被设备依赖的服务）=================

class SerialBusPlugin:
    name = "serial"
    inject = ["config", "log"]

    def apply(self, ctx: Context):
        cfg = ctx.get("config")
        log = ctx.get("log")

        ctx.provide("serial", {"port": cfg["port"]})

        # 反向依赖感知：每当有插件开始依赖 "serial" 就触发
        def on_new_user(plugin_name: str):
            log(f"🔌 {plugin_name} 接入了串口总线")

        ctx.on_depend("serial", on_new_user)

        ctx.effect("serial", lambda: None, lambda: log("🔌 串口总线已移除"))
        log(f"🟢 串口总线就绪 (端口 {cfg['port']})")


# ================= 设备插件 =================

class TempSensorPlugin:
    name = "temp"
    inject = ["serial", "config", "log"]

    def apply(self, ctx: Context):
        cfg = ctx.get("config")
        log = ctx.get("log")
        loop = asyncio.get_running_loop()
        running = True
        task = None

        async def read():
            nonlocal running
            while running:
                value = round(45 + 45 * math.sin(time.time() / 2), 1)
                await ctx.emit("temp_reading", {"source": "temp", "value": value})
                await asyncio.sleep(cfg["temp_interval"])

        def setup():
            nonlocal task
            task = loop.create_task(read())

        def teardown():
            nonlocal running, task
            running = False
            if task is not None:
                task.cancel()
            log("🌡️ 温度传感器已移除")

        ctx.effect("temp", setup, teardown)


class PowerSupplyPlugin:
    name = "psu"
    inject = ["serial", "log"]

    def apply(self, ctx: Context):
        log = ctx.get("log")
        loop = asyncio.get_running_loop()
        running = True
        task = None
        state = {"voltage": 12.0}

        def set_voltage(v: float) -> float:
            state["voltage"] = float(v)
            return state["voltage"]

        ctx.provide("psu", set_voltage)   # 提供服务，供 alarm 注入调用

        async def status():
            nonlocal running
            while running:
                await ctx.emit("power_status", {"source": "psu", "voltage": state["voltage"]})
                await asyncio.sleep(3)

        def setup():
            nonlocal task
            task = loop.create_task(status())

        def teardown():
            nonlocal running, task
            running = False
            if task is not None:
                task.cancel()
            log("🔋 电源已移除")

        ctx.effect("psu", setup, teardown)


# ================= 跨插件业务：告警（注入 psu 服务 + 监听 temp 事件）=================

class AlarmPlugin:
    name = "alarm"
    inject = ["psu", "config", "log"]

    def apply(self, ctx: Context):
        psu = ctx.get("psu")          # 注入电源服务
        cfg = ctx.get("config")
        log = ctx.get("log")

        async def on_temp(data):
            if data["value"] > cfg["temp_threshold"]:
                log(f"🚨 温度 {data['value']}°C 超阈值，紧急断电")
                psu(0.0)              # 调用别的插件的服务
                await ctx.emit("alarm", {
                    "source": "alarm",
                    "msg": f"温度过高 {data['value']}°C，已断电",
                })

        ctx.on("temp_reading", on_temp)
        ctx.effect("alarm", lambda: None, lambda: log("🚨 告警插件已移除"))


# ================= 记录器：非 UI 消费者（展示一对多广播）=================

class RecorderPlugin:
    name = "recorder"
    inject = ["log"]

    def apply(self, ctx: Context):
        log = ctx.get("log")

        async def on_temp(data):
            log(f"📝 记录温度: {data['value']}°C")

        async def on_power(data):
            log(f"📝 记录电压: {data['voltage']}V")

        ctx.on("temp_reading", on_temp)
        ctx.on("power_status", on_power)


# ================= UI 桥接 + 视图 + UI 插件（叶子）=================

class UIBridge(QObject):
    line = pyqtSignal(str)

    def push(self, text: str):
        self.line.emit(text)   # 后台线程调用，跨线程排队到主线程


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Mini Cordis 上位机 — 多设备演示")
        self._title = QLabel("已连接：温度传感器 · 电源 · 告警 · 记录器")
        self._log = QTextEdit()
        self._log.setReadOnly(True)

        central = QWidget()
        layout = QVBoxLayout(central)
        layout.addWidget(self._title)
        layout.addWidget(self._log, stretch=1)
        self.setCentralWidget(central)
        self.resize(560, 420)

    def append(self, text: str):
        self._log.append(text)


class UIPlugin:
    name = "ui"
    inject = []

    def apply(self, ctx: Context):
        bridge = UIBridge()
        window = MainWindow()

        async def on_temp(d):
            bridge.push(f"🌡️ 温度: {d['value']}°C")

        async def on_power(d):
            bridge.push(f"🔋 电压: {d['voltage']}V")

        async def on_alarm(d):
            bridge.push(f"🚨 {d['msg']}")

        async def on_system(d):
            bridge.push(d)

        ctx.on("temp_reading", on_temp)
        ctx.on("power_status", on_power)
        ctx.on("alarm", on_alarm)
        ctx.on("system", on_system)

        bridge.line.connect(window.append)
        ctx.effect("ui", lambda: None, window.close)
        window.show()


# ================= 后台线程 + 主程序 =================

def run_backend(cordis: Cordis, stop: threading.Event):
    async def main_async():
        # 故意乱序传入，load_all 会自动按依赖排序加载
        cordis.load_all([
            AlarmPlugin(),
            PowerSupplyPlugin(),
            TempSensorPlugin(),
            RecorderPlugin(),
            ConfigPlugin(),
            LoggerPlugin(),
            SerialBusPlugin(),
        ])

        # 运行 12 秒，观察数据流与告警
        await asyncio.sleep(12)

        # 拔出串口：级联卸载 alarm -> psu -> temp
        print("\n--- 拔出串口总线（级联卸载）---")
        await cordis.ctx.emit("system", "🔌 拔出串口总线，级联卸载温度/电源/告警插件")
        cordis.unload_plugin("serial")

        while not stop.is_set():
            await asyncio.sleep(0.1)

    asyncio.run(main_async())


def main():
    app = QApplication(sys.argv)
    cordis = Cordis()

    # 1. 主线程先加载 UI 插件（叶子，先订阅事件）
    cordis.load_plugin(UIPlugin())

    # 2. 后台线程跑业务插件
    stop = threading.Event()
    backend = threading.Thread(target=run_backend, args=(cordis, stop), daemon=True)
    backend.start()

    # 无头冒烟测试钩子：AUTO_QUIT_MS 可自动退出
    auto_quit = os.environ.get("AUTO_QUIT_MS")
    if auto_quit:
        QTimer.singleShot(int(auto_quit), app.quit)

    # 3. Qt 主循环
    app.aboutToQuit.connect(stop.set)
    code = app.exec()
    backend.join(timeout=2)
    return code


if __name__ == "__main__":
    raise SystemExit(main())
