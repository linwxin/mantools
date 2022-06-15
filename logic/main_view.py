from PySide6 import QtWidgets, QtCore
from loguru import logger
from ui.main_window import Ui_Form
from scopus.scopus_spider import ScopusSpider
import os



class MainView(QtWidgets.QWidget, Ui_Form):
    def __init__(self):
        super().__init__()
        self.setupUi(self)
        self.log = ""
        self.username.setText("wyz123@mail.ustc.edu.cn")
        self.password.setText("WANGyezhu123")
        self.work_path.setText(os.path.dirname(os.path.realpath(__file__)))
        self.search.setPlainText("SOURCE-ID ( \"21121\" )  AND  ( LIMIT-TO ( DOCTYPE ,  \"ar\" ) )  AND  ( LIMIT-TO ( PUBYEAR ,  2015 ) )  AND  ( LIMIT-TO ( AFFILCOUNTRY ,  \"China\" ) ) ")
        self.spider = ScopusSpider(self.work_path.text(), self.search.toPlainText(), self.username.text(),
                                   self.password.text())
        # 信号-槽
        self.start_btn.clicked.connect(self.start)
        self.resolve_data_btn.clicked.connect(self.resolve_data_clicked)

    def start(self):
        if self.start_btn.text() == "开始":
            if self.check():
                self.log = "start\n" + self.log
                self.log = self.username.text() + "\n" + self.log
                self.log = self.password.text() + "\n" + self.log
                self.log = self.work_path.text() + "\n" + self.log
                self.scrap_log.setText(self.log)
                self.start_btn.setText("停止")

                self.spider.run()
            else:
                self.scrap_log.setText(self.log)
        else:
            self.spider.stop()
            self.start_btn.setText("开始")

    def resolve_data_clicked(self):
        self.spider.resolve_data_clicked()

    def check(self):
        if self.username.text().strip() == "":
            self.log = "ERROR: 用户名不能为空\n" + self.log
            logger.info("用户名不能为空")
            return False
        if self.password.text().strip() == "":
            self.log = "ERROR: 密码不能为空\n" + self.log
            logger.info("密码不能为空")
            return False
        if self.search.toPlainText().strip() == "":
            self.log = "ERROR: 搜索语句不能为空\n" + self.log
            logger.info("搜索语句不能为空")
            return False

        return True
