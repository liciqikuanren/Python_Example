"""浮点录制面板：时长/采样率设置 + 开始/暂停/恢复/停止 + 状态与文件列表。"""

from PyQt6.QtCore import pyqtSignal
from PyQt6.QtWidgets import (
    QComboBox, QDoubleSpinBox, QGroupBox, QHBoxLayout, QLabel, QPushButton,
    QSpinBox, QVBoxLayout, QWidget,
)

DEFAULT_DURATION = 300  # 默认 5 分钟


class FloatRecorderPanel(QWidget):
    start_clicked = pyqtSignal(int, float)   # (时长秒, 采样率Hz)
    pause_clicked = pyqtSignal()
    resume_clicked = pyqtSignal()
    stop_clicked = pyqtSignal()
    refresh_clicked = pyqtSignal()
    settings_changed = pyqtSignal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self._applying = False
        self._build()

    def _build(self):
        group = QGroupBox("浮点通道录制")
        row = QHBoxLayout(group)
        row.setSpacing(8)

        self.start_btn = QPushButton("开始录制")
        self.pause_btn = QPushButton("暂停")
        self.resume_btn = QPushButton("继续")
        self.stop_btn = QPushButton("结束")
        self.pause_btn.setEnabled(False)
        self.resume_btn.setEnabled(False)
        self.stop_btn.setEnabled(False)

        self.duration_spin = QSpinBox()
        self.duration_spin.setRange(1, 24 * 3600)
        self.duration_spin.setValue(DEFAULT_DURATION)
        self.duration_spin.setSuffix(" 秒")
        self.duration_spin.setMinimumWidth(100)

        self.hz_spin = QDoubleSpinBox()
        self.hz_spin.setRange(0.1, 1000.0)
        self.hz_spin.setValue(1.0)
        self.hz_spin.setDecimals(1)
        self.hz_spin.setSuffix(" Hz")
        self.hz_spin.setMinimumWidth(90)

        self.status_label = QLabel("空闲")
        self.status_label.setStyleSheet("color: #888;")
        self.file_label = QLabel("")
        self.file_label.setStyleSheet("color: #9aa3ad;")
        self.file_combo = QComboBox()
        self.file_combo.setMinimumWidth(180)
        self.refresh_btn = QPushButton("刷新")

        row.addWidget(self.start_btn)
        row.addWidget(self.pause_btn)
        row.addWidget(self.resume_btn)
        row.addWidget(self.stop_btn)
        row.addSpacing(10)
        row.addWidget(QLabel("时长"))
        row.addWidget(self.duration_spin)
        row.addWidget(QLabel("采样"))
        row.addWidget(self.hz_spin)
        row.addSpacing(10)
        row.addWidget(self.status_label)
        row.addStretch(1)

        row2 = QHBoxLayout()
        row2.addWidget(QLabel("已录文件"))
        row2.addWidget(self.file_combo, 1)
        row2.addWidget(self.refresh_btn)
        row2.addWidget(self.file_label)

        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.addWidget(group)
        outer.addLayout(row2)

        self.start_btn.clicked.connect(self._on_start)
        self.pause_btn.clicked.connect(self.pause_clicked.emit)
        self.resume_btn.clicked.connect(self.resume_clicked.emit)
        self.stop_btn.clicked.connect(self.stop_clicked.emit)
        self.refresh_btn.clicked.connect(self.refresh_clicked.emit)
        self.duration_spin.valueChanged.connect(self._on_param_changed)
        self.hz_spin.valueChanged.connect(self._on_param_changed)

    def _on_start(self):
        self.start_clicked.emit(self.duration_spin.value(), self.hz_spin.value())

    def _on_param_changed(self, *args):
        if not self._applying:
            self.settings_changed.emit()

    # ---------------- 对外接口 ----------------
    def set_status(self, status: dict) -> None:
        status = status or {}
        state = status.get("state", "idle")
        path = status.get("path", "") or ""
        rows = status.get("rows", 0)
        remaining = status.get("remaining", 0)
        if state == "recording":
            self.status_label.setText(
                f"录制中 {rows} 行 | 剩余 {remaining:.0f}s"
            )
            self.status_label.setStyleSheet("color: #4caf50;")
        elif state == "paused":
            self.status_label.setText(f"已暂停 {rows} 行 | 剩余 {remaining:.0f}s")
            self.status_label.setStyleSheet("color: #ff9800;")
        else:
            self.status_label.setText("空闲")
            self.status_label.setStyleSheet("color: #888;")
        self.start_btn.setEnabled(state == "idle")
        self.pause_btn.setEnabled(state == "recording")
        self.resume_btn.setEnabled(state == "paused")
        self.stop_btn.setEnabled(state in ("recording", "paused"))
        if path:
            from pathlib import Path
            self.file_label.setText(str(Path(path)))
            self.file_label.setToolTip(str(Path(path)))
        else:
            self.file_label.setText("")
            self.file_label.setToolTip("")

    def set_files(self, files: list) -> None:
        from PyQt6.QtCore import Qt
        self.file_combo.blockSignals(True)
        self.file_combo.clear()
        for f in (files or []):
            name = f.get("name", "")
            path = f.get("path", "")
            self.file_combo.addItem(
                f"{name}  ({f.get('size', 0)} B)", name
            )
            idx = self.file_combo.count() - 1
            tip = path or name
            self.file_combo.setItemData(idx, tip, Qt.ItemDataRole.ToolTipRole)
        self.file_combo.blockSignals(False)

    def apply_config(self, cfg: dict) -> None:
        self._applying = True
        try:
            self.duration_spin.setValue(int(cfg.get("csv_duration_s", DEFAULT_DURATION)))
            self.hz_spin.setValue(float(cfg.get("csv_sample_hz", 1.0)))
        finally:
            self._applying = False

    def settings_dict(self) -> dict:
        return {
            "csv_duration_s": self.duration_spin.value(),
            "csv_sample_hz": self.hz_spin.value(),
        }
