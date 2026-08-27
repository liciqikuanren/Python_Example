"""串口设置面板：常用项（端口/波特率/连接）暴露，高级项折叠在「高级设置」里。"""

from PyQt6.QtCore import pyqtSignal
from PyQt6.QtWidgets import (
    QCheckBox, QComboBox, QGridLayout, QGroupBox, QHBoxLayout, QLabel,
    QLineEdit, QPushButton, QVBoxLayout, QWidget,
)

from ui.constants import (
    BAUD_RATES, DATA_BITS, FLOW_CONTROL, PARITY, PARITY_BY_VALUE, STOP_BITS,
)

MODES = [
    ("串口交互", "serial"),
    ("串口 + TCP VoFA 转发", "serial_vofa"),
    ("RTT Shell 交互", "rtt_shell"),
    ("RTT Shell + 波形 + TCP VoFA", "rtt_vofa"),
]


class SettingsPanel(QWidget):
    open_clicked = pyqtSignal()
    refresh_clicked = pyqtSignal()
    auto_reconnect_toggled = pyqtSignal(bool)
    params_changed = pyqtSignal()
    load_config_clicked = pyqtSignal()
    save_config_clicked = pyqtSignal()
    mode_changed = pyqtSignal(str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self._applying = False
        self._build()

    def _build(self):
        group = QGroupBox("串口设置")
        grid = QGridLayout(group)
        grid.setHorizontalSpacing(8)
        grid.setVerticalSpacing(8)

        # ---- 常用项 ----
        self.port_combo = QComboBox()  # 下拉选择，自动扫描
        self.port_combo.setMinimumWidth(170)
        self.refresh_btn = QPushButton("刷新")

        self.baud_combo = QComboBox()  # 可编辑，支持自定义波特率
        self.baud_combo.setEditable(True)
        self.baud_combo.addItems(BAUD_RATES)
        self.baud_combo.setMinimumWidth(110)

        self.advanced_btn = QPushButton("高级设置 ▾")
        self.advanced_btn.setCheckable(True)
        self.advanced_btn.toggled.connect(self._on_advanced_toggled)

        self.open_btn = QPushButton("打开串口")
        self.open_btn.setObjectName("OpenButton")
        self.open_btn.setProperty("connected", False)
        self.open_btn.setEnabled(False)
        self.open_btn.clicked.connect(self.open_clicked.emit)
        self.refresh_btn.setEnabled(False)
        self.refresh_btn.clicked.connect(self.refresh_clicked.emit)

        port_row = QHBoxLayout()
        port_row.addWidget(self.port_combo, 1)
        port_row.addWidget(self.refresh_btn)

        grid.addWidget(QLabel("端口号"), 0, 0)
        grid.addLayout(port_row, 0, 1)
        grid.addWidget(QLabel("波特率"), 0, 2)
        grid.addWidget(self.baud_combo, 0, 3)
        grid.addWidget(self.advanced_btn, 0, 4)
        grid.addWidget(self.open_btn, 0, 5)
        grid.setColumnStretch(1, 1)

        # ---- 高级项（默认折叠）----
        self.data_combo = QComboBox()
        self.data_combo.addItems(DATA_BITS)
        self.stop_combo = QComboBox()
        self.stop_combo.addItems(STOP_BITS)
        self.parity_combo = QComboBox()
        self.parity_combo.addItems(list(PARITY.keys()))
        self.flow_combo = QComboBox()
        self.flow_combo.addItems(FLOW_CONTROL)
        self.reconnect_check = QCheckBox("断线自动重连")

        self.advanced_widget = QWidget()
        adv = QHBoxLayout(self.advanced_widget)
        adv.setContentsMargins(0, 0, 0, 0)
        adv.setSpacing(8)
        adv.addWidget(QLabel("数据位"))
        adv.addWidget(self.data_combo)
        adv.addWidget(QLabel("停止位"))
        adv.addWidget(self.stop_combo)
        adv.addWidget(QLabel("校验位"))
        adv.addWidget(self.parity_combo)
        adv.addWidget(QLabel("流控"))
        adv.addWidget(self.flow_combo)
        adv.addWidget(self.reconnect_check)
        adv.addStretch(1)
        self.advanced_widget.setVisible(False)
        grid.addWidget(self.advanced_widget, 1, 0, 1, 6)

        # ---- AI 联动（串口数据推送到 DSH Agent 会话）----
        self.ai_push_check = QCheckBox("AI 联动推送")
        self.ai_push_mode_combo = QComboBox()
        self.ai_push_mode_combo.addItem("聊天", "chat")
        self.ai_push_mode_combo.addItem("监听", "monitor")
        self.ai_push_mode_combo.setEnabled(False)
        self.ai_push_check.toggled.connect(self.ai_push_mode_combo.setEnabled)
        ai_row = QHBoxLayout()
        ai_row.addWidget(QLabel("AI 联动"))
        ai_row.addWidget(self.ai_push_check)
        ai_row.addWidget(QLabel("模式"))
        ai_row.addWidget(self.ai_push_mode_combo)
        # ---- MCP 服务状态标识 ----
        self.ai_status_label = QLabel("AI嵌入式工具：启动中...")
        self.ai_status_label.setStyleSheet("color: #888;")
        ai_row.addSpacing(16)
        ai_row.addWidget(self.ai_status_label)
        ai_row.addStretch(1)
        grid.addLayout(ai_row, 2, 0, 1, 6)

        # ---- 运行模式（四态）----
        mode_row = QHBoxLayout()
        self.mode_combo = QComboBox()
        for label, value in MODES:
            self.mode_combo.addItem(label, value)
        self.mode_combo.setToolTip("切换后立即生效（动态加载/卸载 RTT 与调试插件）")
        mode_row.addWidget(QLabel("运行模式"))
        mode_row.addWidget(self.mode_combo)
        mode_row.addStretch(1)
        grid.addLayout(mode_row, 3, 0, 1, 6)

        # ---- 配置文件（YAML 按需加载/保存）----
        cfg_row = QHBoxLayout()
        self.config_path_edit = QLineEdit()
        self.config_path_edit.setReadOnly(True)
        self.config_path_edit.setPlaceholderText("~/.serial_assistant/config.yaml")
        self.config_path_edit.setMinimumWidth(220)
        self.load_config_btn = QPushButton("加载配置")
        self.save_config_btn = QPushButton("保存配置")
        cfg_row.addWidget(QLabel("配置文件"))
        cfg_row.addWidget(self.config_path_edit, 1)
        cfg_row.addWidget(self.load_config_btn)
        cfg_row.addWidget(self.save_config_btn)
        grid.addLayout(cfg_row, 4, 0, 1, 6)

        # ---- RTT / J-Link 设置（折叠）----
        self.rtt_btn = QPushButton("RTT / J-Link 设置 ▾")
        self.rtt_btn.setCheckable(True)
        self.rtt_btn.toggled.connect(self._on_rtt_toggled)
        grid.addWidget(self.rtt_btn, 5, 0, 1, 6)

        self.rtt_chip_edit = QLineEdit("STM32H743XI")
        self.rtt_chip_edit.setPlaceholderText("芯片型号，如 STM32H743XI")
        self.rtt_iface_combo = QComboBox()
        self.rtt_iface_combo.addItems(["SWD", "JTAG"])
        self.rtt_speed_edit = QLineEdit("4000")
        self.rtt_speed_edit.setPlaceholderText("接口速度 kHz")
        self.rtt_serial_edit = QLineEdit("")
        self.rtt_serial_edit.setPlaceholderText("序列号（留空=自动）")

        self.rtt_widget = QWidget()
        rtt_grid = QGridLayout(self.rtt_widget)
        rtt_grid.setContentsMargins(0, 0, 0, 0)
        rtt_grid.setHorizontalSpacing(6)
        rtt_grid.setVerticalSpacing(6)
        rtt_grid.addWidget(QLabel("芯片"), 0, 0)
        rtt_grid.addWidget(self.rtt_chip_edit, 0, 1)
        rtt_grid.addWidget(QLabel("接口"), 0, 2)
        rtt_grid.addWidget(self.rtt_iface_combo, 0, 3)
        rtt_grid.addWidget(QLabel("速度(kHz)"), 1, 0)
        rtt_grid.addWidget(self.rtt_speed_edit, 1, 1)
        rtt_grid.addWidget(QLabel("序列号"), 1, 2)
        rtt_grid.addWidget(self.rtt_serial_edit, 1, 3)
        rtt_grid.setColumnStretch(1, 1)
        rtt_grid.setColumnStretch(3, 1)
        self.rtt_widget.setVisible(False)
        grid.addWidget(self.rtt_widget, 6, 0, 1, 6)

        # ---- 信号接线 ----
        self.reconnect_check.toggled.connect(self._on_reconnect_toggled)
        for combo in (self.baud_combo, self.data_combo, self.stop_combo,
                      self.parity_combo, self.flow_combo):
            combo.currentTextChanged.connect(self._on_param_changed)
        self.port_combo.currentTextChanged.connect(self._on_param_changed)
        self.ai_push_check.toggled.connect(self._on_ai_push_changed)
        self.ai_push_mode_combo.currentTextChanged.connect(self._on_ai_push_changed)
        self.mode_combo.currentIndexChanged.connect(self._on_mode_changed)
        self.rtt_chip_edit.textChanged.connect(self._on_param_changed)
        self.rtt_iface_combo.currentTextChanged.connect(self._on_param_changed)
        self.rtt_speed_edit.textChanged.connect(self._on_param_changed)
        self.rtt_serial_edit.textChanged.connect(self._on_param_changed)
        self.load_config_btn.clicked.connect(self.load_config_clicked.emit)
        self.save_config_btn.clicked.connect(self.save_config_clicked.emit)

        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.addWidget(group)

    def _on_advanced_toggled(self, checked: bool):
        self.advanced_widget.setVisible(checked)
        self.advanced_btn.setText("高级设置 ▴" if checked else "高级设置 ▾")

    def _on_rtt_toggled(self, checked: bool):
        self.rtt_widget.setVisible(checked)
        self.rtt_btn.setText("RTT / J-Link 设置 ▴" if checked else "RTT / J-Link 设置 ▾")

    def _on_reconnect_toggled(self, checked: bool):
        if not self._applying:
            self.auto_reconnect_toggled.emit(checked)
            self.params_changed.emit()

    def _on_param_changed(self, *args):
        if not self._applying:
            self.params_changed.emit()

    def _on_ai_push_changed(self, *args):
        if not self._applying:
            self.params_changed.emit()

    def _on_mode_changed(self, index: int):
        if not self._applying:
            self.params_changed.emit()
            self.mode_changed.emit(self.mode_combo.currentData() or "serial")

    # ---------------- 对外接口 ----------------
    def serial_params(self) -> dict:
        port = self.port_combo.currentData() or ""
        try:
            baudrate = int(self.baud_combo.currentText().strip() or "115200")
        except ValueError:
            baudrate = 115200
        flow = self.flow_combo.currentText()
        return {
            "port": port,
            "baudrate": baudrate,
            "bytesize": int(self.data_combo.currentText()),
            "stopbits": float(self.stop_combo.currentText()),
            "parity": PARITY[self.parity_combo.currentText()],
            "flow": flow,
            "rtscts": flow == "RTS/CTS",
            "xonxoff": flow == "XON/XOFF",
        }

    def reconnect_enabled(self) -> bool:
        return self.reconnect_check.isChecked()

    def set_ports(self, ports: list[dict]) -> None:
        current = self.port_combo.currentData()
        self.port_combo.blockSignals(True)
        self.port_combo.clear()
        if not ports:
            self.port_combo.addItem("（未检测到串口，请点击刷新）", None)
        else:
            for p in ports:
                desc = p.get("description", "").strip()
                label = f"{p['device']} - {desc}".strip(" -")
                self.port_combo.addItem(label, p["device"])
            if current:
                idx = self.port_combo.findData(current)
                if idx >= 0:
                    self.port_combo.setCurrentIndex(idx)
        self.port_combo.blockSignals(False)

    def set_connected(self, connected: bool, info: str = "") -> None:
        self.open_btn.setText("关闭串口" if connected else "打开串口")
        self.open_btn.setProperty("connected", connected)
        self.open_btn.style().unpolish(self.open_btn)
        self.open_btn.style().polish(self.open_btn)

    def set_enabled(self, enabled: bool) -> None:
        self.open_btn.setEnabled(enabled)
        self.refresh_btn.setEnabled(enabled)

    def apply_serial_params(self, params: dict) -> None:
        """AI 打开端口后，同步设置栏显示当前端口/参数。"""
        self._applying = True
        try:
            port = params.get("port", "")
            if port:
                idx = self.port_combo.findData(port)
                if idx < 0:
                    self.port_combo.addItem(port, port)
                    idx = self.port_combo.findData(port)
                if idx >= 0:
                    self.port_combo.setCurrentIndex(idx)
            self._set_combo_text(self.baud_combo, str(params.get("baudrate", 115200)))
            self._set_combo_index(self.data_combo, str(params.get("bytesize", 8)))
            stop = float(params.get("stopbits", 1))
            stop_str = "1" if stop == 1 else ("1.5" if stop == 1.5 else "2")
            self._set_combo_index(self.stop_combo, stop_str)
            parity_key = PARITY_BY_VALUE.get(params.get("parity", "N"), "None")
            self._set_combo_index(self.parity_combo, parity_key)
            flow = params.get("flow", "None")
            self._set_combo_index(self.flow_combo, flow if flow in FLOW_CONTROL else "None")
        finally:
            self._applying = False

    def apply_config(self, cfg: dict) -> None:
        self._applying = True
        try:
            self._set_combo_text(self.baud_combo, str(cfg.get("baudrate", 115200)))
            self._set_combo_index(self.data_combo, str(cfg.get("bytesize", 8)))
            self._set_combo_index(self.stop_combo, str(cfg.get("stopbits", 1)))
            parity_key = PARITY_BY_VALUE.get(cfg.get("parity", "N"), "None")
            self._set_combo_index(self.parity_combo, parity_key)
            flow = cfg.get("flow", "None")
            self._set_combo_index(self.flow_combo, flow if flow in FLOW_CONTROL else "None")
            self.reconnect_check.setChecked(bool(cfg.get("auto_reconnect", False)))
            self.ai_push_check.setChecked(bool(cfg.get("ai_push_enabled", False)))
            mode = cfg.get("ai_push_mode", "chat")
            idx = self.ai_push_mode_combo.findData(mode)
            if idx >= 0:
                self.ai_push_mode_combo.setCurrentIndex(idx)
            mode = cfg.get("mode", "serial")
            idx = self.mode_combo.findData(mode)
            if idx >= 0:
                self.mode_combo.setCurrentIndex(idx)
            self.rtt_chip_edit.setText(str(cfg.get("rtt_chip", "STM32H743XI")))
            iface = str(cfg.get("rtt_interface", "SWD"))
            idx = self.rtt_iface_combo.findText(iface)
            if idx >= 0:
                self.rtt_iface_combo.setCurrentIndex(idx)
            self.rtt_speed_edit.setText(str(cfg.get("rtt_speed", 4000)))
            self.rtt_serial_edit.setText(str(cfg.get("rtt_serial_no", "")))
        finally:
            self._applying = False

    def set_config_path(self, path: str) -> None:
        if path:
            self.config_path_edit.setText(path)

    def set_ai_status(self, ready: bool, host: str = "", port: int = 0) -> None:
        """显示内置 MCP（AI嵌入式工具）服务状态。"""
        if ready:
            self.ai_status_label.setText(
                f"AI嵌入式工具：运行中 http://{host}:{port}/mcp"
            )
            self.ai_status_label.setStyleSheet("color: #4caf50;")
        else:
            self.ai_status_label.setText("AI嵌入式工具：已停止")
            self.ai_status_label.setStyleSheet("color: #888;")

    def set_ai_push_enabled(self, enabled: bool, reason: str = "") -> None:
        """启用/禁用 AI 联动推送控件（调试模式下禁用：
        justfloat 数据流不得直接注入 DSH 上下文，只能通过录制 CSV 查看）。"""
        self.ai_push_check.setEnabled(enabled)
        self.ai_push_mode_combo.setEnabled(enabled and self.ai_push_check.isChecked())
        self.ai_push_check.setToolTip(reason or "把串口接收数据推送到 DSH Agent 会话")

    def settings_dict(self) -> dict:
        p = self.serial_params()
        return {
            "port": p["port"],
            "baudrate": p["baudrate"],
            "bytesize": p["bytesize"],
            "stopbits": p["stopbits"],
            "parity": p["parity"],
            "flow": p["flow"],
            "auto_reconnect": self.reconnect_enabled(),
            "ai_push_enabled": self.ai_push_check.isChecked(),
            "ai_push_mode": self.ai_push_mode_combo.currentData() or "chat",
            "mode": self.mode_combo.currentData() or "serial",
            "rtt_chip": self.rtt_chip_edit.text().strip() or "STM32H743XI",
            "rtt_interface": self.rtt_iface_combo.currentText(),
            "rtt_speed": self.rtt_speed_edit.text().strip() or "4000",
            "rtt_serial_no": self.rtt_serial_edit.text().strip(),
        }

    def current_mode(self) -> str:
        return self.mode_combo.currentData() or "serial"

    @staticmethod
    def _set_combo_text(combo: QComboBox, text: str) -> None:
        idx = combo.findText(text)
        if idx >= 0:
            combo.setCurrentIndex(idx)
        else:
            combo.setCurrentText(text)

    @staticmethod
    def _set_combo_index(combo: QComboBox, text: str) -> None:
        idx = combo.findText(text)
        if idx >= 0:
            combo.setCurrentIndex(idx)
