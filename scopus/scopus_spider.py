import json
import os
import pickle
import time
import math
import traceback

import requests
from selenium.common.exceptions import TimeoutException
from selenium.webdriver.chrome.options import Options
from selenium import webdriver
from bs4 import BeautifulSoup as BS
import scopus.scopus_utils as su


class ScopusSpider(object):
    def __init__(self, work_path, search, username, password):
        self.option = Options()
        self.work_path = work_path
        self.search = search
        self.username = username
        self.password = password
        if os.path.exists(os.path.join(self.work_path, "finish")):
            return
        if not os.path.exists(self.work_path):
            os.mkdir(self.work_path)
        self.download_path = os.path.join(self.work_path, "tmp")
        self.pickle_save_path = os.path.join(self.download_path, "pickles")
        if not os.path.exists(self.download_path):
            os.mkdir(self.download_path)
        prefs = {
            "download.default_directory": self.download_path,
            "download.prompt_for_download": False,
        }
        self.option.add_argument("start-maximized")
        self.option.add_argument("disable-gpu")
        self.option.add_experimental_option("prefs", prefs)
        self.chrome_path = os.path.join(os.path.dirname(os.path.realpath(__file__)), "chromedriver.exe")


        self.url = "https://www.scopus.com/home.uri"
        self.perpage = 50
        self.go = True

    def resolve_data_clicked(self):
        self.read_pick(self.pickle_save_path)

    def run(self):
        self.driver = webdriver.Chrome(executable_path=self.chrome_path, chrome_options=self.option)
        self.driver.set_page_load_timeout(120)
        while self.go:
            try:
                self.driver.get(self.url)
                break
            except TimeoutException:
                time.sleep(1)
                continue
        self.driver.find_element_by_id("signin_link_move").click()

        self.driver.find_element_by_id("bdd-email").send_keys(self.username)
        self.driver.find_element_by_id("bdd-elsPrimaryBtn").click()
        self.driver.find_element_by_id("bdd-password").send_keys(self.password)
        self.driver.find_element_by_id("bdd-elsPrimaryBtn").click()
        # self.driver.get("https://www.scopus.com/search/form.uri?display=advanced")
        self.driver.find_element_by_id("searchfield").send_keys(self.search)
        self.driver.find_element_by_id("advSearch").click()

        # 全选并下载
        if not os.path.exists(os.path.join(self.download_path, "scopus.csv")):
            checkbox = self.driver.find_element_by_id("mainResults-selectAllTop")
            self.driver.execute_script("arguments[0].click()", checkbox)
            self.driver.find_element_by_id("directExport").click()

        # 计算并翻页
        total_str = self.driver.find_element_by_class_name("resultsCount").text
        print("总条数：" + total_str)
        total_str = total_str.replace(",", "")
        total = int(total_str)
        total_pages = math.ceil(total / self.perpage)
        print("总页数:" + str(total_pages))

        cur_page = 0

        while cur_page < total_pages:
            c = self.driver.get_cookies()
            cookies = dict()
            for cookie in c:
                cookies[cookie["name"]] = cookie["value"]

            if not os.path.exists(self.pickle_save_path):
                os.mkdir(self.pickle_save_path)
            if cur_page != total_pages - 1:
                page_detail = self.resolve_html(self.driver.page_source, cur_page, total, self.perpage, cookies, self.pickle_save_path)
                self.driver.execute_script("setSelectedLink('NextPageButton');")  # 翻页
            else:
                page_detail = self.resolve_html(self.driver.page_source, cur_page, total, total % self.perpage, cookies,
                                           self.pickle_save_path)
            cur_page += 1
        self.driver.close()
        os.mkdir(os.path.join(self.download_path, "finish"))
        self.read_pick(pickle_save_path)

    def stop(self):
        self.go = False
        self.driver.quit()

    def resolve_html(self, html, page, total, rest=50, cookies="", save_path=""):
        soup = BS(html, "html.parser")
        PlumXdetails = list()
        for i in range(0, rest):
            html_id = "resultDataRow" + str(i)
            print("html_id=" + html_id)
            title_bs = soup.find("tr", id=html_id)
            try:
                row_data_bs = title_bs.find("td", attrs={"data-type": "docTitle"})
            except:
                traceback.print_exc()
                continue
            paper_info_url = row_data_bs.a["href"]
            paper_title = str(row_data_bs.a.string)
            if os.path.exists(os.path.join(save_path, str(self.perpage * (page) + i) + ".pickle")):
                continue
            # print(paper_title + ":" + paper_info_url)
            url_params = paper_info_url.split("?")[1].split("&")
            eid = ""
            for p in url_params:
                if "eid" in p:
                    eid = p.split("=")[1]
            pre_url = "https://api.scopus.com/documentsfacade/documents/" + eid + "/metrics"
            try:
                r_json = self.get_html_by_requests(pre_url, cookies)
                pre_json = json.loads(r_json)
            except:
                print(r_json)
                traceback.print_exc()
                continue
            try:
                PlumXdetail_url = "https://plu.mx/api/v1/artifact/id/" + pre_json["plumXMetrics"]["link"].split("/")[-1]
            except:
                print(pre_json)
                traceback.print_exc()
                continue

            PlumXdetail_json_str = self.get_html_by_requests(PlumXdetail_url, cookies)
            try:
                PlumXdetail = su.resolve_json(PlumXdetail_json_str)
            except:
                print(PlumXdetail_json_str)
                traceback.print_exc()
                continue
            PlumXdetail["paper_title"] = paper_title
            with open(os.path.join(save_path, str(self.perpage * (page) + i) + ".pickle"), "wb") as f:
                pickle.dump(PlumXdetail, f)
            print(PlumXdetail)
            PlumXdetails.append(PlumXdetail)
            print("正在爬取第" + str(page + 1) + "页, 第" + str(self.perpage * (page) + i) + "条, 完成度:" + str(
                math.ceil((self.perpage * (page) + i + 1) / total * 100)) + "%...")
        return PlumXdetails

    def get_html_by_requests(self, url, cookies=dict()):
        header = {
            "user-agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/92.0.4515.131 Safari/537.36",
        }
        h = ""
        while True:
            try:
                proxies_click = False
                print("开始请求:" + url)
                if proxies_click:
                    proxies = {"http": "http://127.0.0.1:7890", "https": "http://127.0.0.1:7890"}
                    r = requests.get(url, headers=header, cookies=cookies, proxies=proxies, verify=False, timeout=5)
                else:
                    r = requests.get(url, headers=header, cookies=cookies, verify=False, timeout=5)
                print("请求成功")
                break
            except:
                print("请求失败, 继续")
                traceback.print_exc()
                time.sleep(1)
                continue

        h = r.content.decode("utf-8")
        return h

    def read_pick(self, file_dir):
        pickles = os.listdir(file_dir)

        objs = list()
        for p in pickles:
            if "pickle" in p:
                pickle_path = os.path.join(file_dir, p)
                f = open(pickle_path, "rb")
                obj = pickle.load(f)
                if "doi" in obj.keys():
                    objs.append(obj)
        is_dup = self.check_duplicate(objs)
        su.reset_dict(objs, os.path.join(self.download_path, "plumx.csv"))

    def check_duplicate(self, objs):
        origin_len = len(objs)
        tmp = set()
        ttmp = list()
        for p in objs:
            if p["doi"] == "10.1038/473277a":
                print(p)
            tmp.add(p["doi"])
            ttmp.append(p["doi"])
        ttmp = sorted(ttmp)
        i = 1
        while i < len(ttmp):
            if ttmp[i - 1] == ttmp[i]:
                print("i=" + str(i) + ", doi=" + ttmp[i])
            i += 1

        print("总共有doi=" + str(len(tmp)) + ", 但总共有数据=" + str(origin_len))
        lines = list()
        with open("./temp.txt", "w", encoding="utf-8") as f:
            i = 1
            for o in objs:
                lines.append(str(i) + "\t" + o["doi"] + "\t" + o["paper_title"] + "\n")
                i += 1
            f.writelines(lines)
        if len(tmp) == origin_len:
            return False
        return True