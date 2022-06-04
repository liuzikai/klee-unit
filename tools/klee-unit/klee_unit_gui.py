import sys
import os
from typing import Optional, List

from klee_unit_core import DriverGenerator, ArgumentDriverType

from PyQt6 import QtGui, QtWidgets, QtCore
from PyQt6.QtWidgets import *
from option_group import OptionGroup
from mainwindow import Ui_MainWindow


class MainWindow(QMainWindow, Ui_MainWindow):
    ARGUMENT_OPTION_TEXT = {
        ArgumentDriverType.NONE: "None",
        ArgumentDriverType.SYMBOLIC: "Symbolic",
        ArgumentDriverType.SYMBOLIC_ARRAY: "Symbolic Array",
        ArgumentDriverType.EXPANDED_ARRAY: "Expanded Array",
        ArgumentDriverType.EXPANDED_STRUCT: "Expanded Struct",
        ArgumentDriverType.PTR_OUT: "Output Variable",
        ArgumentDriverType.PTR_IN_OUT: "In/Out Variable"
    }

    def __init__(self, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent=parent)
        self.setupUi(self)
        self.setWindowTitle('KLEE Unit GUI')
        # self.setWindowIcon(QtGui.QIcon('res/meta_logo.jpeg'))

        try:
            self.session = DriverGenerator()
        except Exception as e:
            # Show error message in a dialog
            msg = QMessageBox()
            msg.setIcon(QtWidgets.QMessageBox.Icon.Critical)
            msg.setText("Error: {}".format(e))
            msg.setWindowTitle("Error")
            msg.exec()
            sys.exit(1)

        self.boxCMake.setVisible(False)
        self.radioSingle.clicked.connect(lambda: self.boxCMake.setVisible(False))
        self.radioCMake.clicked.connect(lambda: self.boxCMake.setVisible(True))
        self.splitter.setSizes([2147483647, 2147483647])

        self.btnAnalyzeSrc.clicked.connect(self.analyze_src)
        self.btnAnalyzeFunc.clicked.connect(self.analyze_selected_func)
        self.btnGenerateDriver.clicked.connect(self.generate_driver)
        self.btnGenerateKLEE.clicked.connect(self.generate_klee)

        self.editTestFile.textChanged.connect(lambda: self.session.set_test_file(self.editTestFile.text()))
        self.ignore_next_code_change = False
        self.session.set_test_file(self.editTestFile.text())
        self.btnReloadTestFile.clicked.connect(self.on_reload_test_file_click)
        self.lblAutoSave.setVisible(False)
        self.setFocusPolicy(QtCore.Qt.FocusPolicy.StrongFocus)

        self.ret_option_group = OptionGroup(self.groupRet)
        self.ret_option_group.selection_changed.connect(self.on_ret_option_changed)
        self.verticalRet.addWidget(self.ret_option_group)

        # Timer to add some delay before saving the test file
        self.auto_save_timer = QtCore.QTimer()
        self.auto_save_timer.setInterval(1000)
        self.auto_save_timer.timeout.connect(self.on_save_timer_timeout)
        self.auto_save_timer.setSingleShot(True)
        self.auto_save_timer.stop()

    # Helper function to show a message in a dialog
    @staticmethod
    def show_message(msg: str, title: str = "Message") -> None:
        msg_box = QMessageBox()
        msg_box.setIcon(QtWidgets.QMessageBox.Icon.Information)
        msg_box.setText(msg)
        msg_box.setWindowTitle(title)
        msg_box.exec()

    def reload_test_file(self) -> None:
        self.ignore_next_code_change = True
        with open(self.editTestFile.text(), 'r', encoding="utf-8") as f:
            self.testEditor.set_code(f.read())

    def on_reload_test_file_click(self) -> None:
        self.reload_test_file()
        self.start_auto_saving()

    def focusInEvent(self, event: QtGui.QFocusEvent) -> None:
        if self.lblAutoSave.isVisible():
            # Reload the test file when the window gets focus if auto saving is enabled
            self.reload_test_file()

    @QtCore.pyqtSlot()
    def on_save_timer_timeout(self) -> None:
        # Save the file
        with open(self.editTestFile.text(), 'w', encoding="utf-8") as f:
            f.write(self.testEditor.get_code())
        self.statusbar.showMessage("Test file saved", 1000)

    # Start the delay timer when editor code is changed
    def on_code_changed(self) -> None:
        if self.ignore_next_code_change:
            self.ignore_next_code_change = False
        else:
            self.auto_save_timer.start()

    @QtCore.pyqtSlot()
    def analyze_src(self):
        try:
            self.session.set_src_file(self.editSrcFile.text())
            self.comboFunc.clear()
            for key, signature in self.session.analyze_src().items():
                self.comboFunc.addItem(signature, key)
        except Exception as e:
            self.statusbar.showMessage("Fail to analysis source file: {}".format(e))
        else:
            self.statusbar.showMessage("Successfully analyzed source file")

    @QtCore.pyqtSlot()
    def analyze_selected_func(self):
        if self.session is None:
            self.statusbar.showMessage("Analyze source first")

        # Delete all widgets in groupArgs
        for i in reversed(range(self.groupArgs.layout().count())):
            self.groupArgs.layout().itemAt(i).widget().setParent(None)

        # Analyze function
        try:
            args, has_ret = self.session.analyze_func(self.comboFunc.currentData())
        except Exception as e:
            self.statusbar.showMessage(str(e))
            return

        # Add widgets for each argument
        for arg in args:

            type_label = QLabel(self.groupArgs)
            type_label.setText(arg.type_str)
            type_label.setAlignment(QtCore.Qt.AlignmentFlag.AlignRight | QtCore.Qt.AlignmentFlag.AlignVCenter)
            self.gridArgs.addWidget(type_label, self.gridArgs.rowCount(), 0)

            name_label = QLabel(self.groupArgs)
            name_label.setText(arg.name)
            name_label.setStyleSheet("font-weight: bold")
            self.gridArgs.addWidget(name_label, self.gridArgs.rowCount() - 1, 1)

            widget = QWidget()
            layout = QHBoxLayout(widget)
            layout.setContentsMargins(0, 0, 0, 0)
            layout.setSpacing(0)

            option_group = OptionGroup(widget)
            option_group.selection_changed.connect(self.on_arg_option_changed)  # connect first so default applies
            for option in arg.options:
                option_group.add_button(self.ARGUMENT_OPTION_TEXT[option], (arg.name, option))
            layout.addWidget(option_group)

            hspacer = QSpacerItem(20, 20, QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Minimum)
            layout.addItem(hspacer)

            self.gridArgs.addWidget(widget, self.gridArgs.rowCount() - 1, 2)

        # Setup return option group
        self.ret_option_group.clear()
        if has_ret:
            self.ret_option_group.add_button("Watch", True)  # default option
            self.ret_option_group.add_button("Discard", False)
        else:
            self.ret_option_group.add_button("None", False)  # default option

    @QtCore.pyqtSlot(int, object)
    def on_arg_option_changed(self, index: int, data: object):
        name, option = data
        try:
            self.session.set_arg_option(name, option)
        except Exception as e:
            self.statusbar.showMessage(str(e))

    @QtCore.pyqtSlot(int, object)
    def on_ret_option_changed(self, index: int, data: bool):
        try:
            self.session.set_watch_ret(data)
        except Exception as e:
            self.statusbar.showMessage(str(e))

    @QtCore.pyqtSlot()
    def generate_driver(self):
        try:
            self.session.generate_test_driver()
        except Exception as e:
            self.statusbar.showMessage(str(e))
        else:
            self.statusbar.showMessage("Successfully generated test driver")

        self.reload_test_file()
        self.start_auto_saving()

    def start_auto_saving(self):
        self.testEditor.code_changed.connect(self.on_code_changed)
        self.lblAutoSave.setVisible(True)

    def add_test_case(self, index, vals):
        self.tableTests.setRowCount(self.tableTests.rowCount() + 1)
        # index_item = QTableWidgetItem(str(index))
        # self.tableTests.setItem(self.tableTests.rowCount() - 1, 0, index_item)
        for i, val in enumerate(vals):
            val_item = QTableWidgetItem(str(val))
            self.tableTests.setItem(self.tableTests.rowCount() - 1, i, val_item)

    @QtCore.pyqtSlot()
    def generate_klee(self):
        # Generate KLEE driver
        try:
            var_names = self.session.generate_klee_driver()
        except Exception as e:
            self.statusbar.showMessage("Fail to generate KLEE driver: {}".format(e))
            return
        else:
            self.statusbar.showMessage("Successfully generated KLEE driver")

        # Clear the test case table
        self.tableTests.setColumnCount(len(var_names))
        self.tableTests.setHorizontalHeaderLabels(var_names)
        self.tableTests.setRowCount(0)

        # Run KLEE
        try:
            self.session.run_klee(self.add_test_case)
        except Exception as e:
            self.statusbar.showMessage("Fail to run KLEE: {}".format(e))



if __name__ == '__main__':
    app = QApplication(sys.argv)
    w = MainWindow()
    w.showMaximized()
    sys.exit(app.exec())
