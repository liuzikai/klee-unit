import json
import os
import typing

from PyQt6 import QtCore, QtWidgets, QtWebEngineWidgets, QtWebChannel

RESOURCE_DIR = os.path.join(os.path.dirname(os.path.realpath(__file__)), "monoaco-editor")


class BaseBridge(QtCore.QObject):
    initialized = QtCore.pyqtSignal()
    sendDataChanged = QtCore.pyqtSignal(str, str)

    def send_to_js(self, name, value):
        data = json.dumps(value)
        self.sendDataChanged.emit(name, data)

    @QtCore.pyqtSlot(str, str)
    def receive_from_js(self, name, value):
        data = json.loads(value)
        self.setProperty(name, data)

    @QtCore.pyqtSlot()
    def init(self):
        self.initialized.emit()


class EditorBridge(BaseBridge):
    valueChanged = QtCore.pyqtSignal()
    languageChanged = QtCore.pyqtSignal()
    themeChanged = QtCore.pyqtSignal()

    def __init__(self, parent=None):
        super(EditorBridge, self).__init__(parent)
        self._value = ""
        self._language = ""
        self._theme = ""

    def getValue(self):
        return self._value

    def setValue(self, value):
        self._value = value
        self.valueChanged.emit()

    def getLanguage(self):
        return self._language

    def setLanguage(self, language):
        self._language = language
        self.languageChanged.emit()

    def getTheme(self):
        return self._theme

    def setTheme(self, theme):
        self._theme = theme
        self.themeChanged.emit()

    value = QtCore.pyqtProperty(str, fget=getValue, fset=setValue, notify=valueChanged)
    language = QtCore.pyqtProperty(
        str, fget=getLanguage, fset=setLanguage, notify=languageChanged
    )
    theme = QtCore.pyqtProperty(str, fget=getTheme, fset=setTheme, notify=themeChanged)


class MonacoEditorWidget(QtWebEngineWidgets.QWebEngineView):

    code_changed = QtCore.pyqtSignal(str)
    language_changed = QtCore.pyqtSignal(str)
    theme_changed = QtCore.pyqtSignal(str)

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self._has_initialized = False

        channel = QtWebChannel.QWebChannel(self)
        self.page().setWebChannel(channel)

        self._bridge = EditorBridge()
        channel.registerObject("bridge", self.bridge)

        filename = os.path.join(RESOURCE_DIR, "monaco-editor.html")
        self.load(QtCore.QUrl.fromLocalFile(filename))

        self.bridge.initialized.connect(self._initialized)
        self.bridge.valueChanged.connect(lambda: self.code_changed.emit(self.bridge.value))
        self.bridge.languageChanged.connect(lambda: self.language_changed.emit(self.bridge.language))
        self.bridge.themeChanged.connect(lambda: self.theme_changed.emit(self.bridge.theme))

        while not self._has_initialized:
            QtCore.QCoreApplication.processEvents()

    @QtCore.pyqtSlot()
    def _initialized(self) -> None:
        self._has_initialized = True

    @property
    def bridge(self):
        return self._bridge

    def set_language(self, language: str):
        self.bridge.send_to_js("language", language)  # do not use self.bridge.language

    def set_theme(self, theme: str):
        self.bridge.send_to_js("theme", theme)  # do not use self.bridge.theme

    def set_text(self, text: str):
        self.bridge.send_to_js("value", text)  # do not use self.bridge.value

    def get_language(self) -> str:
        return self.bridge.language

    def get_theme(self) -> str:
        return self.bridge.theme

    def get_text(self) -> str:
        return self.bridge.value


if __name__ == "__main__":
    import sys

    sys.argv.append("--remote-debugging-port=8000")

    app = QtWidgets.QApplication(sys.argv)


    @QtCore.pyqtSlot()
    def code_changed(code: str):
        print("code changed:", code)

    w = MonacoEditorWidget()
    w.code_changed.connect(code_changed)
    w.show()

    sys.exit(app.exec())
