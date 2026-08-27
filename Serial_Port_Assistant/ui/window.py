"""主窗口外壳：左右分栏布局 + 状态栏。

布局：
  - 左列：参数设置（串口设置 / TCP 转发 / JustFloat 解析 / 浮点录制，调试面板按模式显隐）
  - 右列：上方数据接收（拉伸）、下方数据发送
左右宽度可通过分隔条拖动调整。
"""

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import (
    QHBoxLayout, QLabel, QMainWindow, QMessageBox, QPushButton, QSplitter,
    QVBoxLayout, QWidget,
)

from ui.panels.float_recorder import FloatRecorderPanel
from ui.panels.justfloat import JustFloatPanel
from ui.panels.receive import ReceivePanel
from ui.panels.rtt import RttPanel
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
        self.rtt = RttPanel()

        # ---- 左列：参数设置（可折叠） ----
        left = QWidget()
        self.config_panel = left
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
        right_box.addWidget(self.rtt, stretch=1)

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
        layout.setSpacing(8)

        # 顶部工具条：配置栏折叠开关
        top_bar = QHBoxLayout()
        self.config_toggle = QPushButton("☰ 配置")
        self.config_toggle.setCheckable(True)
        self.config_toggle.setChecked(False)
        self.config_toggle.setToolTip("点击展开/收起左侧配置栏")
        self.config_toggle.toggled.connect(self._toggle_config)
        top_bar.addWidget(self.config_toggle)
        top_bar.addStretch(1)
        layout.addLayout(top_bar)

        layout.addWidget(self.splitter)
        self.setCentralWidget(central)

        # 默认收起配置栏（右列占满）
        self.config_panel.setVisible(False)

        self.state_label = QLabel("未连接")
        self.statusBar().addWidget(self.state_label, 1)

        self.set_mode("serial")
        self.resize(1180, 820)
        self.setMinimumSize(980, 640)

    def _toggle_config(self, checked: bool) -> None:
        self.config_panel.setVisible(checked)

    def set_mode(self, mode: str) -> None:
        """按四态模式显隐面板。

        serial/serial_vofa → 串口控制台（接收+发送）；
        rtt_shell/rtt_vofa  → RTT 控制台；
        serial_vofa/rtt_vofa → 波形调试面板（TCP 转发 / justfloat / 录制）。
        """
        is_rtt = mode in ("rtt_shell", "rtt_vofa")
        is_wave = mode in ("serial_vofa", "rtt_vofa")
        self.receive.setVisible(not is_rtt)
        self.send.setVisible(not is_rtt)
        self.rtt.setVisible(is_rtt)
        self.tcp.setVisible(is_wave)
        self.justfloat.setVisible(is_wave)
        self.recorder.setVisible(is_wave)

    def set_state(self, text: str) -> None:
        self.state_label.setText(text)

    def show_error(self, text: str) -> None:
        self.statusBar().showMessage(text, 5000)
        QMessageBox.warning(self, "提示", text)

    def show_message(self, text: str) -> None:
        self.statusBar().showMessage(text, 4000)
