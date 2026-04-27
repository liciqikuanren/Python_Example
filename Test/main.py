import sys
import threading
import winsound
from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QGridLayout,
    QPushButton, QLineEdit
)
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QFont


def _play_click():
    winsound.Beep(1500, 50)


BUTTON_STYLES = {
    "operator": (
        "QPushButton{background-color:#ff9500;color:white;border-radius:8px;font-weight:bold;}"
        "QPushButton:pressed{background-color:#cc7700;}"
    ),
    "equals": (
        "QPushButton{background-color:#34c759;color:white;border-radius:8px;font-weight:bold;}"
        "QPushButton:pressed{background-color:#28a745;}"
    ),
    "function": (
        "QPushButton{background-color:#d4d4d2;color:black;border-radius:8px;}"
        "QPushButton:pressed{background-color:#a8a8a6;}"
    ),
    "number": (
        "QPushButton{background-color:#505050;color:white;border-radius:8px;}"
        "QPushButton:pressed{background-color:#3a3a3a;}"
    ),
}


class Calculator(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("计算器")
        self.resize(320, 450)

        self.expression = ""
        self.new_number = True

        self._setup_ui()

    def _setup_ui(self):
        central = QWidget()
        self.setCentralWidget(central)
        layout = QVBoxLayout(central)
        layout.setSpacing(8)

        # 显示屏
        self.display = QLineEdit()
        self.display.setAlignment(Qt.AlignmentFlag.AlignRight)
        self.display.setFont(QFont("Arial", 28))
        self.display.setReadOnly(True)
        self.display.setText("0")
        self.display.setMinimumHeight(60)
        layout.addWidget(self.display)

        # 按钮
        grid = QGridLayout()
        grid.setSpacing(6)

        buttons = [
            ("C", 0, 0), ("±", 0, 1), ("%", 0, 2), ("÷", 0, 3),
            ("7", 1, 0), ("8", 1, 1), ("9", 1, 2), ("×", 1, 3),
            ("4", 2, 0), ("5", 2, 1), ("6", 2, 2), ("−", 2, 3),
            ("1", 3, 0), ("2", 3, 1), ("3", 3, 2), ("+", 3, 3),
            ("0", 4, 0, 1, 2), (".", 4, 2), ("=", 4, 3),
        ]

        for btn in buttons:
            text, row, col = btn[0], btn[1], btn[2]
            colspan = btn[3] if len(btn) > 3 else 1
            button = QPushButton(text)
            button.setFont(QFont("Arial", 18))
            button.setMinimumHeight(55)
            # 按下时视觉反馈 + 提示音
            button.pressed.connect(self._play_click)
            button.clicked.connect(self._on_button(text))
            grid.addWidget(button, row, col, 1, colspan)

        # 样式
        self._apply_button_styles(grid)

        layout.addLayout(grid)

    def _apply_button_styles(self, grid):
        for i in range(grid.count()):
            item = grid.itemAt(i)
            if item and item.widget():
                btn = item.widget()
                text = btn.text()
                if text in ("÷", "×", "−", "+"):
                    btn.setStyleSheet(BUTTON_STYLES["operator"])
                elif text == "=":
                    btn.setStyleSheet(BUTTON_STYLES["equals"])
                elif text in ("C", "±", "%"):
                    btn.setStyleSheet(BUTTON_STYLES["function"])
                else:
                    btn.setStyleSheet(BUTTON_STYLES["number"])

    def _play_click(self):
        threading.Thread(target=_play_click, daemon=True).start()

    def _on_button(self, text):
        def handler():
            if text == "C":
                self.expression = ""
                self.new_number = True
                self.display.setText("0")
            elif text == "±":
                if self.display.text() != "0":
                    val = self.display.text()
                    if val.startswith("-"):
                        self.display.setText(val[1:])
                    else:
                        self.display.setText("-" + val)
            elif text == "%":
                try:
                    val = float(self.display.text()) / 100
                    self.display.setText(self._format_result(val))
                except ValueError:
                    self.display.setText("Error")
            elif text in ("÷", "×", "−", "+"):
                self.expression += self.display.text() + " " + text + " "
                self.new_number = True
            elif text == "=":
                self.expression += self.display.text()
                try:
                    expr = self.expression.replace("÷", "/").replace("×", "*").replace("−", "-")
                    result = eval(expr)
                    self.display.setText(self._format_result(result))
                except (ZeroDivisionError, SyntaxError, Exception):
                    self.display.setText("Error")
                self.expression = ""
                self.new_number = True
            elif text == ".":
                if self.new_number:
                    self.display.setText("0.")
                    self.new_number = False
                elif "." not in self.display.text():
                    self.display.setText(self.display.text() + ".")
            else:
                if self.new_number:
                    self.display.setText(text)
                    self.new_number = False
                else:
                    self.display.setText(self.display.text() + text)
        return handler

    def _format_result(self, value):
        if isinstance(value, float) and value == int(value):
            return str(int(value))
        return str(round(value, 10))


def main():
    app = QApplication(sys.argv)
    calc = Calculator()
    calc.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
