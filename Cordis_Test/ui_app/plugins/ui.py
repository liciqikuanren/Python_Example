"""UI 插件（叶子）：Qt 桥接 + 窗口视图，订阅各事件（无业务依赖）"""

from PyQt6.QtCore import QObject, pyqtSignal
from PyQt6.QtWidgets import QLabel, QMainWindow, QTextEdit, QVBoxLayout, QWidget


class UIBridge(QObject):
    line = pyqtSignal(str)

    def push(self, text: str):
        self.line.emit(text)  # 后台线程调用，跨线程排队到主线程


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


class Plugin:
    name = "ui"
    inject = []

    def apply(self, ctx):
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
        ctx.effect(lambda: None, window.close)
        window.show()