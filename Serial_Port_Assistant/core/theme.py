"""应用级深色主题：QSS + 自定义复选框绘制（带白色对勾，替代纯色方块）。"""

from PyQt6.QtCore import QPointF, QRect, Qt
from PyQt6.QtGui import QColor, QPainter, QPainterPath, QPen, QPolygonF
from PyQt6.QtWidgets import QProxyStyle, QStyle, QStyleFactory

RX_COLOR = QColor("#d8dde5")
TX_COLOR = QColor("#5ee6a8")      # 人发送
AI_COLOR = QColor("#c084fc")      # AI 发送
TCP_COLOR = QColor("#fbbf24")     # TCP 转发来源（客户端 → 串口）
TS_COLOR = QColor("#8a8f98")

ACCENT = QColor("#4f8ef7")
ACCENT_HOVER = QColor("#6ba0f9")


class CheckBoxStyle(QProxyStyle):
    """在深色主题下绘制带白色对勾的复选框。"""

    def __init__(self):
        super().__init__(QStyleFactory.create("Fusion"))

    def drawPrimitive(self, element, option, painter, widget=None):
        if element == QStyle.PrimitiveElement.PE_IndicatorCheckBox:
            self._draw_checkbox(option, painter)
        elif element in (QStyle.PrimitiveElement.PE_IndicatorSpinUp,
                         QStyle.PrimitiveElement.PE_IndicatorSpinDown):
            self._draw_spin_arrow(
                option, painter,
                up=element == QStyle.PrimitiveElement.PE_IndicatorSpinUp,
            )
        else:
            super().drawPrimitive(element, option, painter, widget)

    def _draw_checkbox(self, option, painter):
        rect = option.rect
        size = min(rect.width(), rect.height()) - 2
        box = QRect(rect.center().x() - size // 2,
                    rect.center().y() - size // 2, size, size)

        checked = bool(option.state & QStyle.StateFlag.State_On)
        enabled = bool(option.state & QStyle.StateFlag.State_Enabled)
        hover = bool(option.state & QStyle.StateFlag.State_MouseOver)

        painter.save()
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        if not enabled:
            border = QColor("#33373d")
            fill = QColor("#222529")
        elif checked:
            border = ACCENT
            fill = ACCENT
        else:
            border = ACCENT_HOVER if hover else QColor("#4a4f57")
            fill = QColor("#23252a")

        painter.setPen(QPen(border, 1))
        painter.setBrush(fill)
        painter.drawRoundedRect(box, 3, 3)

        if checked:
            pen = QPen(QColor("#ffffff"), 1.8)
            pen.setCapStyle(Qt.PenCapStyle.RoundCap)
            pen.setJoinStyle(Qt.PenJoinStyle.RoundJoin)
            painter.setPen(pen)
            painter.setBrush(Qt.BrushStyle.NoBrush)

            w, h = box.width(), box.height()
            path = QPainterPath()
            path.moveTo(QPointF(box.x() + w * 0.25, box.y() + h * 0.54))
            path.lineTo(QPointF(box.x() + w * 0.44, box.y() + h * 0.72))
            path.lineTo(QPointF(box.x() + w * 0.76, box.y() + h * 0.30))
            painter.drawPath(path)

        painter.restore()

    def _draw_spin_arrow(self, option, painter, up: bool):
        """绘制上下微调三角箭头（浅色，避免深色背景下看不清）。"""
        rect = option.rect
        enabled = bool(option.state & QStyle.StateFlag.State_Enabled)
        color = QColor("#d6dae0") if enabled else QColor("#5c626b")

        painter.save()
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(color)

        w = 8.0
        h = 5.0
        cx = rect.center().x()
        cy = rect.center().y()
        if up:
            points = [
                QPointF(cx - w / 2, cy + h * 0.6),
                QPointF(cx + w / 2, cy + h * 0.6),
                QPointF(cx, cy - h * 0.4),
            ]
        else:
            points = [
                QPointF(cx - w / 2, cy - h * 0.6),
                QPointF(cx + w / 2, cy - h * 0.6),
                QPointF(cx, cy + h * 0.4),
            ]
        painter.drawPolygon(QPolygonF(points))
        painter.restore()


STYLESHEET = """
QMainWindow, QWidget {
    background-color: #1b1d21;
    color: #d6dae0;
    font-family: "Microsoft YaHei UI", "Segoe UI", sans-serif;
    font-size: 13px;
}

QGroupBox {
    border: 1px solid #2f333a;
    border-radius: 8px;
    margin-top: 12px;
    padding: 10px 8px 8px 8px;
    background-color: #222529;
    font-weight: 600;
}
QGroupBox::title {
    subcontrol-origin: margin;
    left: 12px;
    padding: 0 6px;
    color: #8ab4ff;
}

QLabel { background: transparent; }

QPushButton {
    background-color: #2c3036;
    border: 1px solid #3a3f47;
    border-radius: 6px;
    padding: 6px 14px;
    color: #e6e9ee;
}
QPushButton:hover { background-color: #343941; border-color: #4a505a; }
QPushButton:pressed { background-color: #262a30; }
QPushButton:disabled { color: #5c626b; background-color: #222529; border-color: #2f333a; }

QPushButton#OpenButton[connected="true"] {
    background-color: #1e7a4d;
    border-color: #2ca05f;
    color: #eafff2;
}
QPushButton#OpenButton[connected="true"]:hover { background-color: #24885a; }

QPushButton#SendButton, QPushButton#OpenButton {
    background-color: #2f5da8;
    border-color: #3a6fca;
    color: #f0f5ff;
}
QPushButton#SendButton:hover, QPushButton#OpenButton:hover { background-color: #3768bd; }

QComboBox, QSpinBox {
    background-color: #282b30;
    border: 1px solid #3a3f47;
    border-radius: 6px;
    padding: 4px 8px;
    color: #e6e9ee;
    min-height: 18px;
}
QComboBox:hover, QSpinBox:hover { border-color: #4a505a; }
QComboBox:focus, QSpinBox:focus { border-color: #4f8ef7; }
QSpinBox::up-button, QSpinBox::down-button {
    background-color: #33383f;
    border: 1px solid #4a505a;
    width: 18px;
}
QSpinBox::up-button:hover, QSpinBox::down-button:hover {
    background-color: #3e444d;
    border-color: #5a6270;
}
QSpinBox::up-button:pressed, QSpinBox::down-button:pressed {
    background-color: #262a30;
}
QComboBox::drop-down { border: none; width: 22px; }
QComboBox QAbstractItemView {
    background-color: #282b30;
    border: 1px solid #3a3f47;
    border-radius: 4px;
    selection-background-color: #2f5da8;
    selection-color: #f0f5ff;
    color: #e6e9ee;
    padding: 2px;
}

QCheckBox { background: transparent; spacing: 7px; color: #d6dae0; }
QCheckBox:disabled { color: #5c626b; }

QPlainTextEdit, QTextEdit {
    background-color: #17191d;
    border: 1px solid #2f333a;
    border-radius: 6px;
    color: #d8dde5;
    selection-background-color: #2f5da8;
    padding: 5px;
}
QPlainTextEdit:focus, QTextEdit:focus { border-color: #4f8ef7; }

QStatusBar {
    background-color: #222529;
    color: #8a8f98;
    border-top: 1px solid #2f333a;
}

QScrollBar:vertical { background: #222529; width: 12px; margin: 0; border: none; }
QScrollBar::handle:vertical { background: #3a3f47; border-radius: 6px; min-height: 26px; }
QScrollBar::handle:vertical:hover { background: #4a505a; }
QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical { height: 0; }
QScrollBar:horizontal { background: #222529; height: 12px; margin: 0; }
QScrollBar::handle:horizontal { background: #3a3f47; border-radius: 6px; min-width: 26px; }
QScrollBar::add-line:horizontal, QScrollBar::sub-line:horizontal { width: 0; }

QToolTip {
    background-color: #2c3036; color: #e6e9ee;
    border: 1px solid #3a3f47; padding: 4px;
}
"""
