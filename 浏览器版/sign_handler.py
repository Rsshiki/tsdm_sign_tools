import random
from datetime import datetime
from log_config import setup_logger
from selenium.webdriver.common.by import By
from config_handler import load_config, save_config
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from browser_manager import get_browser_driver, check_driver_validity
import requests
from bs4 import BeautifulSoup

# 配置日志
logger = setup_logger('tsdm_sign_tools.log')

# 签到页面选择器
NEED_LOGIN_SIGN_CSS = '#messagetext.alert_info p'
ALREADY_SIGNED_CSS = 'h1.mt'
SMILE_BUTTON_CSS_TEMPLATE = 'ul.qdsmile {}'
RADIO_BUTTON_CSS = '#qiandao > table.tfm > tbody > tr:nth-child(1) > td > label:nth-child(2) > input[type=radio]'
SUBMIT_BUTTON_CSS = '#qiandao > table:nth-child(11) > tbody > tr > td > div > a:nth-child(2)'

# 选择器文本
sign_cookie_wrong = "您需要先登录才能继续本操作"
signed = "您今天已经签到过了或者签到时间还未开始"

SIGN_URL = 'https://www.tsdm39.com/plugin.php?id=dsu_paulsign:sign'


def ensure_browser_started():
    driver = get_browser_driver()
    return driver

def check_cookie_validity(driver, username, cookies):
    logger.info("准备使用 requests 检查 cookie 有效性")
    try:
        # 使用 requests 发送请求并附带 cookies
        response = requests.get(SIGN_URL, cookies=cookies)
        response.raise_for_status()
        
        # 使用 BeautifulSoup 解析 HTML 数据
        soup = BeautifulSoup(response.text, 'html.parser')
        
        # 查找访问我的空间链接元素
        space_link_element = soup.find('a', {'title': '访问我的空间'})
        if space_link_element:
            actual_username = space_link_element.get_text().strip()
            if actual_username == username:
                return True
    except Exception as e:
        logger.error(f"检查 {username} 的 cookie 有效性时出错: {e}")
        
        # 标记 cookie 无效
        config = load_config()
        if username in config.get('account_categories', {}):
            config['account_categories'][username]["is_cookie_valid"] = False
            save_config(config)
    
    return False

def perform_sign(username, cookies):
    # 确保浏览器已启动
    driver = ensure_browser_started()
    if not driver:
        logger.error("无法启动浏览器，签到操作终止")
        return
    
    # 检查 cookie 有效性
    if not check_cookie_validity(driver, username, cookies):
        logger.error(f"{username} 的 cookie 无效，签到操作终止")
        return
    logger.info("cookie检查有效")

    # 跳转到签到页面
    driver.get(SIGN_URL)

    try:
        # 显式等待检查是否已经签到的元素加载完成
        WebDriverWait(driver, 2).until(
            EC.presence_of_element_located((By.CSS_SELECTOR, ALREADY_SIGNED_CSS))
        )
        logger.info("检查是否已经签到")
        signed_elements = driver.find_elements(By.CSS_SELECTOR, ALREADY_SIGNED_CSS)
        for element in signed_elements:
            if signed in element.text:
                logger.info("今日已签到")
                update_sign_date(username)
                return
    except Exception as e:
        logger.error(f"检查是否已经签到时出错: {e}")

    original_window = driver.current_window_handle #记录原始窗口

    # 执行签到动作
    logger.info("还未签到，开始执行签到动作...")
    smile_buttons = ['#kx', '#ng', '#ym', '#wl', '#nu', '#ch', '#fd', '#yl', '#shuai']
    random_smile = random.choice(smile_buttons)
    try:
        WebDriverWait(driver, 10).until(
            EC.element_to_be_clickable((By.CSS_SELECTOR, SMILE_BUTTON_CSS_TEMPLATE.format(random_smile)))).click()
        logger.info("表情按钮点击")
    except Exception as e:
        logger.error(f"点击表情按钮时出错: {e}")
        return
    
    driver.switch_to.window(original_window) # 切换回原始窗口

    try:
        WebDriverWait(driver, 10).until(EC.element_to_be_clickable((By.CSS_SELECTOR, RADIO_BUTTON_CSS))).click()
        logger.info("单选按钮点击")
    except Exception as e:
        logger.error(f"点击单选按钮时出错: {e}")
        return

    try:
        WebDriverWait(driver, 10).until(EC.element_to_be_clickable((By.CSS_SELECTOR, SUBMIT_BUTTON_CSS))).click()
        logger.info("提交按钮点击")
    except Exception as e:
        logger.error(f"点击提交按钮时出错: {e}")
        return

    try:
        # 检查是否签到成功
        WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.CSS_SELECTOR, ALREADY_SIGNED_CSS))
        )
        signed_elements = driver.find_elements(By.CSS_SELECTOR, ALREADY_SIGNED_CSS)
        for element in signed_elements:
            if signed in element.text:
                logger.info("签到成功")
                update_sign_date(username)
                return
    except Exception as e:
        logger.error(f"检查是否已经签到时出错: {e}")
        
def update_sign_date(username):
    config = load_config()
    if username in config.get('account_categories', {}):
        today = datetime.now().strftime("%Y-%m-%d")
        config['account_categories'][username]["last_sign_date"] = today
        save_config(config)    