import os
import shutil
import logging
import tempfile
from selenium import webdriver
from selenium.webdriver.firefox.options import Options
from selenium.webdriver.firefox.service import Service
from webdriver_manager.firefox import GeckoDriverManager

# 配置 Python 日志，方便调试
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

def setup_driver(headless=True): #True为无头模式，False为有头模式
    """设置浏览器驱动"""
    firefox_options = Options()
    if headless:
        firefox_options.add_argument('-headless')
    firefox_options.set_preference("general.log.level", "fatal")
    user_data_dir = None
    driver = None
    try:
        user_data_dir = tempfile.mkdtemp()
        firefox_options.add_argument(f'-profile')
        firefox_options.add_argument(user_data_dir)
        service = Service(GeckoDriverManager().install())
        driver = webdriver.Firefox(service=service, options=firefox_options)
    except Exception as e:
        logging.error(f"启动浏览器时出错: {e}")
        if user_data_dir and os.path.exists(user_data_dir):
            try:
                shutil.rmtree(user_data_dir)
            except Exception as rm_error:
                logging.error(f"删除临时用户数据目录时出错: {rm_error}")
    return driver, user_data_dir

def login(driver, login_url):
    if driver is None:
        print("浏览器驱动未正确初始化，无法执行登录操作")
        return None
    try:
        # 添加日志，确认是否执行到跳转步骤
        logging.info(f"尝试跳转到登录页面: {login_url}")
        driver.get(login_url)
        # 等待用户手动登录
        input("请在浏览器中完成登录，登录完成后按回车键继续...")
        # 获取 cookies
        cookies = driver.get_cookies()
        return cookies
    except Exception as e:
        logging.error(f"登录时出错: {e}")
        return None