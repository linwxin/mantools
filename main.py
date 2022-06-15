import sys
from PySide6.QtWidgets import QMainWindow

from logic.main_view import MainView
from PySide6 import QtCore, QtWidgets, QtGui


if __name__ == '__main__':
    QtCore.QCoreApplication.setAttribute(QtCore.Qt.AA_EnableHighDpiScaling)
    app = QtWidgets.QApplication(sys.argv)
    view = MainView()

    view.show()
    sys.exit(app.exec())


