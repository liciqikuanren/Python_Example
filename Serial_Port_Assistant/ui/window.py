"""主窗口外壳：左右分栏布局 + 状态栏。

布局：
  - 左列：参数设置（串口设置 / TCP 转发 / JustFloat 解析 / 浮点录制，调试面板按模式显隐）
  - 右列：上方数据接收（拉伸）、下方数据发送
左右宽度可通过分隔条拖动调整。
"""

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import (
    QLabel, QMainWindow, QMessageBox, QSplitter, QVBoxLayout, QWidget,
)

from ui.panels.float_recorder import FloatRecorderPanel
from ui.panels.justfloat import JustFloatPanel
from ui.panels.receive import ReceivePanel
from ui.panels.send import SendPanel
from ui.panels.settings import SettingsPanel
from ui.panels.tcp_forward import TcpForwardPanel


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Cordis 串口助手")

        self.settings = SettingsPanel()
        self.tcp = TcpForwardPanel()
        self.justfloat = JustFloatPanel()
        self.recorder = FloatRecorderPanel()
        self.receive = ReceivePanel()
        self.send = SendPanel()

        # ---- 左列：参数设置 ----
        left = QWidget()
        left_box = QVBoxLayout(left)
        left_box.setContentsMargins(0, 0, 0, 0)
        left_box.setSpacing(8)
        left_box.addWidget(self.settings)
        left_box.addWidget(self.tcp)
        left_box.addWidget(self.justfloat)
        left_box.addWidget(self.recorder)
        left_box.addStretch(1)

        # ---- 右列：接收（上）+ 发送（下） ----
        right = QWidget()
        right_box = QVBoxLayout(right)
        right_box.setContentsMargins(0, 0, 0, 0)
        right_box.setSpacing(8)
        right_box.addWidget(self.receive, stretch=1)
        right_box.addWidget(self.send)

        # ---- 左右分栏 ----
        self.splitter = QSplitter(Qt.Orientation.Horizontal)
        self.splitter.addWidget(left)
        self.splitter.addWidget(right)
        self.splitter.setStretchFactor(0, 0)
        self.splitter.setStretchFactor(1, 1)
        self.splitter.setSizes([440, 720])
        self.splitter.setCollapsible(0, False)
        self.splitter.setCollapsible(1, False)

        central = QWidget()
        layout = QVBoxLayout(central)
        layout.setContentsMargins(8, 8, 8, 8)
        layout.addWidget(self.splitter)
        self.setCentralWidget(central)

        self.state_label = QLabel("未连接")
        self.statusBar().addWidget(self.state_label, 1)

        self.resize(1180, 820)
        self.setMinimumSize(980, 640)

    def set_debug_visible(self, visible: bool) -> None:
        """调试模式显隐 TCP 转发 / justfloat / 录制面板（正常模式仅 AI 功能）。"""
        self.tcp.setVisible(visible)
        self.justfloat.setVisible(visible)
        self.recorder.setVisible(visible)

    def set_state(self, text: str) -> None:
        self.state_label.setText(text)

    def show_error(self, text: str) -> None:
        self.statusBar().showMessage(text, 5000)
        QMessageBox.warning(self, "提示", text)

    def show_message(self, text: str) -> None:
        self.statusBar().showMessage(text, 4000)
