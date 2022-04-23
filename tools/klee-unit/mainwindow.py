# Form implementation generated from reading ui file 'mainwindow.ui'
#
# Created by: PyQt6 UI code generator 6.2.1
#
# WARNING: Any manual changes made to this file will be lost when pyuic6 is
# run again.  Do not edit this file unless you know what you are doing.


from PyQt6 import QtCore, QtGui, QtWidgets


class Ui_MainWindow(object):
    def setupUi(self, MainWindow):
        MainWindow.setObjectName("MainWindow")
        MainWindow.resize(887, 737)
        self.centralwidget = QtWidgets.QWidget(MainWindow)
        self.centralwidget.setObjectName("centralwidget")
        self.gridLayout = QtWidgets.QGridLayout(self.centralwidget)
        self.gridLayout.setObjectName("gridLayout")
        self.labelSrcFile = QtWidgets.QLabel(self.centralwidget)
        self.labelSrcFile.setObjectName("labelSrcFile")
        self.gridLayout.addWidget(self.labelSrcFile, 1, 0, 1, 1)
        self.btnAnalyzeSrc = QtWidgets.QPushButton(self.centralwidget)
        self.btnAnalyzeSrc.setObjectName("btnAnalyzeSrc")
        self.gridLayout.addWidget(self.btnAnalyzeSrc, 1, 2, 1, 1)
        self.labelTestFile = QtWidgets.QLabel(self.centralwidget)
        self.labelTestFile.setObjectName("labelTestFile")
        self.gridLayout.addWidget(self.labelTestFile, 0, 0, 1, 1)
        self.groupRet = QtWidgets.QGroupBox(self.centralwidget)
        self.groupRet.setObjectName("groupRet")
        self.verticalRet = QtWidgets.QVBoxLayout(self.groupRet)
        self.verticalRet.setObjectName("verticalRet")
        self.gridLayout.addWidget(self.groupRet, 3, 2, 1, 1)
        self.comboFunc = QtWidgets.QComboBox(self.centralwidget)
        self.comboFunc.setObjectName("comboFunc")
        self.gridLayout.addWidget(self.comboFunc, 2, 1, 1, 1)
        self.editTestFile = QtWidgets.QLineEdit(self.centralwidget)
        self.editTestFile.setObjectName("editTestFile")
        self.gridLayout.addWidget(self.editTestFile, 0, 1, 1, 1)
        self.groupTestCases = QtWidgets.QGroupBox(self.centralwidget)
        sizePolicy = QtWidgets.QSizePolicy(QtWidgets.QSizePolicy.Policy.Preferred, QtWidgets.QSizePolicy.Policy.Expanding)
        sizePolicy.setHorizontalStretch(0)
        sizePolicy.setVerticalStretch(0)
        sizePolicy.setHeightForWidth(self.groupTestCases.sizePolicy().hasHeightForWidth())
        self.groupTestCases.setSizePolicy(sizePolicy)
        self.groupTestCases.setObjectName("groupTestCases")
        self.tableWidget = QtWidgets.QTableWidget(self.groupTestCases)
        self.tableWidget.setGeometry(QtCore.QRect(90, 60, 256, 192))
        self.tableWidget.setObjectName("tableWidget")
        self.tableWidget.setColumnCount(0)
        self.tableWidget.setRowCount(0)
        self.gridLayout.addWidget(self.groupTestCases, 9, 0, 1, 3)
        self.groupArgs = QtWidgets.QGroupBox(self.centralwidget)
        sizePolicy = QtWidgets.QSizePolicy(QtWidgets.QSizePolicy.Policy.Preferred, QtWidgets.QSizePolicy.Policy.Maximum)
        sizePolicy.setHorizontalStretch(0)
        sizePolicy.setVerticalStretch(0)
        sizePolicy.setHeightForWidth(self.groupArgs.sizePolicy().hasHeightForWidth())
        self.groupArgs.setSizePolicy(sizePolicy)
        self.groupArgs.setObjectName("groupArgs")
        self.gridArgs = QtWidgets.QGridLayout(self.groupArgs)
        self.gridArgs.setObjectName("gridArgs")
        self.gridLayout.addWidget(self.groupArgs, 3, 0, 1, 2)
        self.btnAnalyzeFunc = QtWidgets.QPushButton(self.centralwidget)
        self.btnAnalyzeFunc.setObjectName("btnAnalyzeFunc")
        self.gridLayout.addWidget(self.btnAnalyzeFunc, 2, 2, 1, 1)
        self.labelFunc = QtWidgets.QLabel(self.centralwidget)
        self.labelFunc.setObjectName("labelFunc")
        self.gridLayout.addWidget(self.labelFunc, 2, 0, 1, 1)
        self.editSrcFile = QtWidgets.QLineEdit(self.centralwidget)
        self.editSrcFile.setObjectName("editSrcFile")
        self.gridLayout.addWidget(self.editSrcFile, 1, 1, 1, 1)
        self.checkInline = QtWidgets.QCheckBox(self.centralwidget)
        self.checkInline.setObjectName("checkInline")
        self.gridLayout.addWidget(self.checkInline, 4, 0, 1, 1)
        self.btnGenerateDriver = QtWidgets.QPushButton(self.centralwidget)
        self.btnGenerateDriver.setObjectName("btnGenerateDriver")
        self.gridLayout.addWidget(self.btnGenerateDriver, 5, 2, 1, 1)
        MainWindow.setCentralWidget(self.centralwidget)
        self.menubar = QtWidgets.QMenuBar(MainWindow)
        self.menubar.setGeometry(QtCore.QRect(0, 0, 887, 21))
        self.menubar.setObjectName("menubar")
        MainWindow.setMenuBar(self.menubar)
        self.statusbar = QtWidgets.QStatusBar(MainWindow)
        self.statusbar.setObjectName("statusbar")
        MainWindow.setStatusBar(self.statusbar)

        self.retranslateUi(MainWindow)
        QtCore.QMetaObject.connectSlotsByName(MainWindow)

    def retranslateUi(self, MainWindow):
        _translate = QtCore.QCoreApplication.translate
        MainWindow.setWindowTitle(_translate("MainWindow", "MainWindow"))
        self.labelSrcFile.setText(_translate("MainWindow", "Source File"))
        self.btnAnalyzeSrc.setText(_translate("MainWindow", "Analysis File"))
        self.labelTestFile.setText(_translate("MainWindow", "Working Test File"))
        self.groupRet.setTitle(_translate("MainWindow", "Return Value"))
        self.editTestFile.setText(_translate("MainWindow", "/Users/liuzikai/Documents/Courses/AST/AST-Project/ast-klee/examples/klee-unit/foo_test.c"))
        self.groupTestCases.setTitle(_translate("MainWindow", "Test Cases"))
        self.groupArgs.setTitle(_translate("MainWindow", "Arguments"))
        self.btnAnalyzeFunc.setText(_translate("MainWindow", "Analysis Function"))
        self.labelFunc.setText(_translate("MainWindow", "Test Function"))
        self.editSrcFile.setText(_translate("MainWindow", "/Users/liuzikai/Documents/Courses/AST/AST-Project/ast-klee/examples/klee-unit/foo.c"))
        self.checkInline.setText(_translate("MainWindow", "Inline Argument"))
        self.btnGenerateDriver.setText(_translate("MainWindow", "Generate Test Driver"))
