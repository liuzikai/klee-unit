from typing import Optional, Any
from PyQt6.QtCore import pyqtSignal, pyqtSlot
from PyQt6.QtWidgets import QWidget, QToolButton, QHBoxLayout


class OptionGroup(QWidget):
    button_toggled = pyqtSignal(int, bool, object)
    selection_changed = pyqtSignal(int, object)

    def __init__(self, parent: Optional['QWidget'] = None) -> None:
        super().__init__(parent=parent)
        self._layout = QHBoxLayout(self)
        self._layout.setContentsMargins(0, 0, 0, 0)
        self._layout.setSpacing(-1)
        self._current_index = None
        self._buttons: list[QToolButton] = []

    def add_button(self, text: str, data: Any):
        button = QToolButton(parent=self)
        button.setText(text)
        button.setCheckable(True)
        button.setAutoExclusive(True)
        button.setProperty("index", len(self._buttons))
        button.setProperty("data", data)
        button.toggled.connect(self.handle_button_toggled)
        self._layout.addWidget(button)
        self._buttons.append(button)
        if len(self._buttons) == 1:
            button.click()

    def set_current_index(self, index: int):
        self._buttons[index].click()

    def get_current_index(self) -> int:
        return self._current_index

    def button(self, index: int) -> QToolButton:
        return self._buttons[index]

    def get_current_data(self) -> Any:
        return self._buttons[self._current_index].property("data")

    def clear(self):
        while len(self._buttons) > 0:
            button: QToolButton = self._buttons.pop()
            button.deleteLater()
        self._current_index = None

    @pyqtSlot(bool)
    def handle_button_toggled(self, checked: bool):
        sender = self.sender()
        index = sender.property("index")
        if checked:
            self._current_index = index
            self.selection_changed.emit(index, sender.property("data"))
        self.button_toggled.emit(index, checked, sender.property("data"))
