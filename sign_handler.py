import time
import random
from browser_driver import setup_driver, is_driver_active
from log_config import setup_logger
from datetime import datetime, timedelta
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from config_handler import load_config, save_config
from selenium.webdriver.support import expected_conditions as EC
from browser_manager import get_browser_driver, function_finished, check_driver_validity

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
    logger.info("准备添加浏览器cookie")
    if not check_driver_validity():
        driver = get_browser_driver()
        if not driver:
            return False
    try:
        # 清除旧的 cookie
        driver.delete_all_cookies()
        # 添加当前账号的 cookie
        for cookie in cookies:
            driver.add_cookie(cookie)
        # 刷新页面
        driver.refresh()
        logger.info("浏览器cookie添加完成并完成刷新")
        space_link_element = WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.XPATH, '//a[@title="访问我的空间"]'))
        )
        actual_username = space_link_element.text.strip()
        if actual_username == username:
            return True
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
    finally:
        logger.info("签到操作结束，调用 function_finished")
        function_finished()

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
    finally:
        logger.info("签到操作结束，调用 function_finished")
        function_finished()
        
def update_sign_date(username):
    config = load_config()
    if username in config.get('account_categories', {}):
        today = datetime.now().strftime("%Y-%m-%d")
        config['account_categories'][username]["last_sign_date"] = today
        save_config(config)    