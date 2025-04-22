import os
import sys
import shutil
import tempfile
import requests
import re
from selenium import webdriver
from log_config import setup_logger
from selenium.webdriver.firefox.options import Options
from selenium.webdriver.firefox.service import Service
from webdriver_manager.firefox import GeckoDriverManager
from config_handler import load_config, update_browser_info
from selenium.webdriver.common.desired_capabilities import DesiredCapabilities

# 配置日志
logger = setup_logger('tsdm_sign_tools.log')

# 判断是脚本运行还是 exe 运行，获取对应目录
if getattr(sys, 'frozen', False):
    base_path = os.path.dirname(sys.executable)
else:
    base_path = os.path.dirname(os.path.abspath(__file__))
browser_dir = os.path.join(base_path, 'browserdriver')


def extract_version_from_path(driver_path):
    """从驱动路径中提取版本号"""
    parts = driver_path.split(os.sep)
    for i in range(len(parts) - 1, -1, -1):
        if parts[i].startswith('v') and parts[i + 1] == 'geckodriver.exe':
            return parts[i].lstrip('v')
    return None


def extract_version_from_url(url):
    """从下载地址中提取版本号"""
    pattern = r'v(\d+\.\d+\.\d+)'
    match = re.search(pattern, url)
    if match:
        return match.group(1)
    return None


class CustomGeckoDriverManager(GeckoDriverManager):
    def __init__(self):
        super().__init__()
        self.download_url = None

    def _get_driver_download_url(self, driver, os_type):
        self.download_url = super()._get_driver_download_url(driver, os_type)
        return self.download_url


def get_geckodriver_download_info():
    """获取 geckodriver 下载地址和版本号"""
    custom_manager = CustomGeckoDriverManager()
    # 触发获取下载地址逻辑
    try:
        custom_manager.driver = custom_manager._get_driver_to_download()
        custom_manager._get_driver_download_url(custom_manager.driver, custom_manager.os_type)
    except Exception as e:
        logger.error(f"获取下载地址时出错: {e}")
        return None, None
    download_url = custom_manager.download_url
    version = extract_version_from_url(download_url)
    return download_url, version


def setup_driver(headless=True):
    """设置浏览器驱动"""
    firefox_options = Options()
    if headless:
        firefox_options.add_argument('-headless')
    # 设置页面加载策略为 eager
    caps = DesiredCapabilities.FIREFOX
    caps["pageLoadStrategy"] = "eager"
    # 设置页面加载策略为 eager，迁移自 capabilities
    firefox_options.set_preference("pageLoadStrategy", "eager")
    # 设置日志级别
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
            pass
        else:
            download_url, version = get_geckodriver_download_info()
            logger.info(f"geckodriver 下载地址: {download_url}")
            if version:
                logger.info(f"从下载地址获取到的 geckodriver 版本号: {version}")
            else:
                logger.warning("未能从下载地址中提取到版本号")

            # 让 webdriver_manager 正常下载
            default_driver_path = GeckoDriverManager().install()
            # 获取驱动所在的文件夹
            default_driver_folder = os.path.dirname(default_driver_path)

            # 确保自定义目录存在
            if not os.path.exists(browser_dir):
                os.makedirs(browser_dir)

            # 生成移动后的目标文件夹路径
            folder_name = os.path.basename(default_driver_folder)
            target_folder = os.path.join(browser_dir, folder_name)

            # 移动整个文件夹
            shutil.move(default_driver_folder, target_folder)
            # 更新驱动路径
            geckodriver_path = os.path.join(target_folder, os.path.basename(default_driver_path))
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
        logger.error(f"启动浏览器时出错: {e}")
        if user_data_dir and os.path.exists(user_data_dir):
            try:
                os.rmdir(user_data_dir)
            except Exception as rm_error:
                logger.error(f"删除用户数据目录时出错: {rm_error}")
    return driver, user_data_dir


def is_driver_active(driver):
    """检查浏览器驱动是否处于活动状态"""
    try:
        driver.current_url
        return True
    except:
        return False


def update_geckodriver():
    """更新 geckodriver 并更新配置文件"""
    try:
        # 获取 GitHub 上的最新版本
        response = requests.get("https://api.github.com/repos/mozilla/geckodriver/releases/latest")
        response.raise_for_status()
        latest_version = response.json()["tag_name"].lstrip('v')

        config = load_config()
        browser_info = config.get("browser_info", {})
        current_version = browser_info.get('version', '0.0.0')

        if latest_version > current_version:
            logger.info(f"检测到新版本 {latest_version}，当前版本 {current_version}，开始更新...")
            download_url, version = get_geckodriver_download_info()
            logger.info(f"geckodriver 下载地址: {download_url}")
            if version:
                logger.info(f"从下载地址获取到的 geckodriver 版本号: {version}")
            else:
                logger.warning("未能从下载地址中提取到版本号")

            # 让 webdriver_manager 正常下载
            default_driver_path = GeckoDriverManager().install()
            # 获取驱动所在的文件夹
            default_driver_folder = os.path.dirname(default_driver_path)

            # 确保自定义目录存在
            if not os.path.exists(browser_dir):
                os.makedirs(browser_dir)

            # 生成移动后的目标文件夹路径
            folder_name = os.path.basename(default_driver_folder)
            target_folder = os.path.join(browser_dir, folder_name)

            # 检查目标文件夹是否已存在，如果存在则先删除
            if os.path.exists(target_folder):
                shutil.rmtree(target_folder)

            # 移动整个文件夹
            shutil.move(default_driver_folder, target_folder)
            # 更新驱动路径
            geckodriver_path = os.path.join(target_folder, os.path.basename(default_driver_path))
            geckodriver_version = extract_version_from_path(geckodriver_path)

            browser_info = {
                'path': geckodriver_path,
                'version': geckodriver_version
            }
            update_browser_info(browser_info)
            logger.info(f"成功更新 geckodriver 到版本 {geckodriver_version}，保存路径: {geckodriver_path}")
            return True
        else:
            logger.info(f"当前 geckodriver 已经是最新版本 {current_version}，无需更新。")
            return None
    except requests.RequestException as e:
        logger.error(f"获取 GitHub 最新版本信息时出错: {e}")
        return False
    except Exception as e:
        logger.error(f"更新 geckodriver 时出错: {e}")
        return False