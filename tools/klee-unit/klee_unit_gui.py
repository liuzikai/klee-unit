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

        self.session: Optional[DriverGenerator] = None

        self.btnAnalyzeSrc.clicked.connect(self.analyze_src)
        self.btnAnalyzeFunc.clicked.connect(self.analyze_selected_func)
        self.btnGenerateDriver.clicked.connect(self.generate_driver)
        self.btnGenerateKLEE.clicked.connect(self.generate_klee)

        self.ret_option_group = OptionGroup(self.groupRet)
        self.ret_option_group.selection_changed.connect(self.on_ret_option_changed)
        self.verticalRet.addWidget(self.ret_option_group)

    @QtCore.pyqtSlot()
    def analyze_src(self):
        self.session = DriverGenerator(self.editSrcFile.text(), self.editTestFile.text())
        self.comboFunc.clear()
        for key, signature in self.session.analyze_src().items():
            self.comboFunc.addItem(signature, key)

    @QtCore.pyqtSlot()
    def analyze_selected_func(self):
        if self.session is None:
            self.statusbar.showMessage("Analyze source first")

        # Delete all widgets in groupArgs
        for i in reversed(range(self.groupArgs.layout().count())):
            self.groupArgs.layout().itemAt(i).widget().setParent(None)

        args, has_ret = self.session.analyze_func(self.comboFunc.currentData())

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
        self.session.set_arg_option(name, option)

    @QtCore.pyqtSlot(int, object)
    def on_ret_option_changed(self, index: int, data: bool):
        self.session.set_watch_ret(data)

    @QtCore.pyqtSlot()
    def generate_driver(self):
        self.session.generate_test_driver()

    def add_test_case(self, index, vals):
        self.tableTests.setRowCount(self.tableTests.rowCount() + 1)
        # index_item = QTableWidgetItem(str(index))
        # self.tableTests.setItem(self.tableTests.rowCount() - 1, 0, index_item)
        for i, val in enumerate(vals):
            val_item = QTableWidgetItem(str(val))
            self.tableTests.setItem(self.tableTests.rowCount() - 1, i, val_item)

    @QtCore.pyqtSlot()
    def generate_klee(self):
        var_names = self.session.generate_klee_driver()
        self.tableTests.setColumnCount(len(var_names))
        self.tableTests.setHorizontalHeaderLabels(var_names)
        self.tableTests.setRowCount(0)

        self.session.run_klee(self.add_test_case)


if __name__ == '__main__':
    app = QApplication(sys.argv)
    w = MainWindow()
    w.show()
    sys.exit(app.exec())
