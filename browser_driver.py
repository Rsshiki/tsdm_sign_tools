import os
import logging
import tempfile
from selenium import webdriver
from selenium.webdriver.firefox.options import Options
from selenium.webdriver.firefox.service import Service
from webdriver_manager.firefox import GeckoDriverManager
from config_handler import load_config, update_browser_info

# 配置 Python 日志，方便调试
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

def extract_version_from_path(driver_path):
    """从驱动路径中提取版本号"""
    parts = driver_path.split(os.sep)
    for i in range(len(parts) - 1, -1, -1):
        if parts[i].startswith('v') and parts[i + 1] == 'geckodriver.exe':
            return parts[i].lstrip('v')
    return None

def setup_driver(headless=False): #True为无头模式，False为有头模式
    """设置浏览器驱动"""
    firefox_options = Options()
    # if headless:
    #     firefox_options.add_argument('-headless')
    firefox_options.set_preference("general.log.level", "fatal")
    user_data_dir = None
    driver = None
    config = load_config()
    browser_info = config.get("browser_info", {})
    geckodriver_path = browser_info.get('path')
    geckodriver_version = browser_info.get('version')
    
    try:
        if geckodriver_path and os.path.exists(geckodriver_path):
            # 如果配置文件中有浏览器驱动路径且文件存在，直接使用该路径
            # logging.info(f"使用已存在的浏览器驱动: {geckodriver_path}")
            pass     
        else:
            manager = GeckoDriverManager()
            geckodriver_path = manager.install()
            geckodriver_version = extract_version_from_path(geckodriver_path)

            browser_info = {
                'path': geckodriver_path,
                'version': geckodriver_version
            }
            update_browser_info(browser_info)

        user_data_dir = tempfile.mkdtemp()
        firefox_options.add_argument(f'-profile')
        firefox_options.add_argument(user_data_dir)
        service = Service(executable_path=geckodriver_path)
        driver = webdriver.Firefox(service=service, options=firefox_options)
    except Exception as e:
        logging.error(f"启动浏览器时出错: {e}")
        if user_data_dir and os.path.exists(user_data_dir):
            try:
                os.rmdir(user_data_dir)
            except Exception as rm_error:
                logging.error(f"删除用户数据目录时出错: {rm_error}")
    return driver, user_data_dir

def update_geckodriver():
    """更新 geckodriver 并更新配置文件"""
    try:
        manager = GeckoDriverManager()
        geckodriver_path = manager.install()
        geckodriver_version = extract_version_from_path(geckodriver_path)
        browser_info = {
            'path': geckodriver_path,
            'version': geckodriver_version
        }
        update_browser_info(browser_info)
        logging.info(f"成功更新 geckodriver 到版本 {geckodriver_version}，保存路径: {geckodriver_path}")
        return True
    except Exception as e:
        logging.error(f"更新 geckodriver 时出错: {e}")
        return False