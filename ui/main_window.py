# -*- coding: utf-8 -*-

################################################################################
## Form generated from reading UI file 'main_window.ui'
##
## Created by: Qt User Interface Compiler version 6.2.2
##
## WARNING! All changes made in this file will be lost when recompiling UI file!
################################################################################

from PySide6.QtCore import (QCoreApplication, QDate, QDateTime, QLocale,
    QMetaObject, QObject, QPoint, QRect,
    QSize, QTime, QUrl, Qt)
from PySide6.QtGui import (QBrush, QColor, QConicalGradient, QCursor,
    QFont, QFontDatabase, QGradient, QIcon,
    QImage, QKeySequence, QLinearGradient, QPainter,
    QPalette, QPixmap, QRadialGradient, QTransform)
from PySide6.QtWidgets import (QApplication, QLabel, QLineEdit, QPlainTextEdit,
    QPushButton, QSizePolicy, QTextBrowser, QWidget)

class Ui_Form(object):
    def setupUi(self, Form):
        if not Form.objectName():
            Form.setObjectName(u"Form")
        Form.resize(611, 475)
        self.label_4 = QLabel(Form)
        self.label_4.setObjectName(u"label_4")
        self.label_4.setGeometry(QRect(30, 100, 61, 21))
        self.label_5 = QLabel(Form)
        self.label_5.setObjectName(u"label_5")
        self.label_5.setGeometry(QRect(50, 240, 54, 16))
        self.password = QLineEdit(Form)
        self.password.setObjectName(u"password")
        self.password.setGeometry(QRect(90, 60, 171, 20))
        self.label_3 = QLabel(Form)
        self.label_3.setObjectName(u"label_3")
        self.label_3.setGeometry(QRect(30, 160, 54, 16))
        self.work_path = QLineEdit(Form)
        self.work_path.setObjectName(u"work_path")
        self.work_path.setGeometry(QRect(90, 100, 451, 21))
        self.scrap_log = QTextBrowser(Form)
        self.scrap_log.setObjectName(u"scrap_log")
        self.scrap_log.setGeometry(QRect(90, 240, 451, 192))
        self.label_2 = QLabel(Form)
        self.label_2.setObjectName(u"label_2")
        self.label_2.setGeometry(QRect(50, 60, 54, 16))
        self.username = QLineEdit(Form)
        self.username.setObjectName(u"username")
        self.username.setGeometry(QRect(90, 20, 171, 20))
        self.start_btn = QPushButton(Form)
        self.start_btn.setObjectName(u"start_btn")
        self.start_btn.setGeometry(QRect(460, 10, 75, 24))
        self.label = QLabel(Form)
        self.label.setObjectName(u"label")
        self.label.setGeometry(QRect(50, 20, 54, 16))
        self.search = QPlainTextEdit(Form)
        self.search.setObjectName(u"search")
        self.search.setGeometry(QRect(90, 160, 451, 61))
        self.resolve_data_btn = QPushButton(Form)
        self.resolve_data_btn.setObjectName(u"resolve_data_btn")
        self.resolve_data_btn.setGeometry(QRect(460, 50, 75, 24))

        self.retranslateUi(Form)

        QMetaObject.connectSlotsByName(Form)
    # setupUi

    def retranslateUi(self, Form):
        Form.setWindowTitle(QCoreApplication.translate("Form", u"Scopus Plumx\u6570\u636e\u722c\u866b\u7cfb\u7edf", None))
        self.label_4.setText(QCoreApplication.translate("Form", u"\u5de5\u4f5c\u8def\u5f84", None))
        self.label_5.setText(QCoreApplication.translate("Form", u"\u65e5\u5fd7", None))
        self.label_3.setText(QCoreApplication.translate("Form", u"\u67e5\u8be2\u8bed\u53e5", None))
        self.label_2.setText(QCoreApplication.translate("Form", u"\u5bc6\u7801", None))
        self.start_btn.setText(QCoreApplication.translate("Form", u"\u5f00\u59cb", None))
        self.label.setText(QCoreApplication.translate("Form", u"\u8d26\u53f7", None))
        self.resolve_data_btn.setText(QCoreApplication.translate("Form", u"\u5904\u7406\u6570\u636e", None))
    # retranslateUi

