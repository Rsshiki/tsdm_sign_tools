import time
import random
from datetime import datetime, timedelta
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from browser_driver import login
from config_handler import save_config

# 签到页面选择器
NEED_LOGIN_SIGN_XPATH = '//div[@id="messagetext" and contains(@class, "alert_info")]//p[contains(text(), "您需要先登录才能继续本操作")]'
ALREADY_SIGNED_XPATH = '//h1[@class="mt" and contains(text(), "您今天已经签到过了或者签到时间还未开始")]'
SMILE_BUTTON_CSS_TEMPLATE = 'ul.qdsmile {}'
RADIO_BUTTON_CSS = '#qiandao > table.tfm > tbody > tr:nth-child(1) > td > label:nth-child(2) > input[type=radio]'
SUBMIT_BUTTON_CSS = '#qiandao > table:nth-child(11) > tbody > tr > td > div > a:nth-child(2)'

# 打工页面选择器
NEED_LOGIN_WORK_XPATH = '//div[@id="messagetext" and contains(@class, "alert_info")]//p[contains(text(), "请先登录再进行点击任务")]'
NEED_WAIT_WORK_XPATH = '//div[@id="messagetext" and contains(@class, "alert_info")]//p[contains(text(), "必须与上一次间隔6小时0分钟0秒才可再次进行。")]'
STOP_AD_BUTTON_CSS = '#stopad a'

def calculate_work_time(driver):
    """
    从页面获取等待信息，计算上次和下次打工时间
    :param driver: 浏览器驱动
    :return: 上次打工时间和下次打工时间，如果未获取到等待信息则返回 None, None
    """
    wait_elements = driver.find_elements(By.XPATH, NEED_WAIT_WORK_XPATH)
    if wait_elements:
        wait_text = wait_elements[0].text.split('您需要等待')[1].split('后即可进行。')[0]
        time_parts = {'hours': 0, 'minutes': 0, 'seconds': 0}
        unit_mapping = {
            '小时': 'hours',
            '分钟': 'minutes',
            '秒': 'seconds'
        }
        for unit in unit_mapping:
            if unit in wait_text:
                value, wait_text = wait_text.split(unit, 1)
                time_parts[unit_mapping[unit]] = int(value)

        last_work_time = datetime.now() - timedelta(hours=6) + timedelta(**time_parts)
        next_work_time = last_work_time + timedelta(hours=6)
        return last_work_time, next_work_time
    return None, None

def perform_sign(driver, config, SIGN_URL, LOGIN_URL):
    """执行签到操作"""
    driver.get(SIGN_URL)
    # 检查是否需要重新登录
    if driver.find_elements(By.XPATH, NEED_LOGIN_SIGN_XPATH):
        print("Cookie过期，重新登录...")
        cookies = login(driver, LOGIN_URL)
        config['cookies'] = cookies
        save_config(config)
        driver.get(SIGN_URL)

    # 检查是否已经签到
    if driver.find_elements(By.XPATH, ALREADY_SIGNED_XPATH):
        print("今日已签到")
        return

    # 执行签到动作
    smile_buttons = ['#kx', '#ng', '#ym', '#wl', '#nu', '#ch', '#fd', '#yl', '#shuai']
    random_smile = random.choice(smile_buttons)
    WebDriverWait(driver, 10).until(EC.element_to_be_clickable((By.CSS_SELECTOR, SMILE_BUTTON_CSS_TEMPLATE.format(random_smile)))).click()
    WebDriverWait(driver, 10).until(EC.element_to_be_clickable((By.CSS_SELECTOR, RADIO_BUTTON_CSS))).click()
    WebDriverWait(driver, 10).until(EC.element_to_be_clickable((By.CSS_SELECTOR, SUBMIT_BUTTON_CSS))).click()
    print("签到成功")


def perform_work(driver, config, WORK_URL, LOGIN_URL):
    """执行打工操作"""
    driver.get(WORK_URL)
    # 检查是否需要重新登录
    if driver.find_elements(By.XPATH, NEED_LOGIN_WORK_XPATH):
        print("Cookie过期，重新登录...")
        cookies = login(driver, LOGIN_URL)
        config['cookies'] = cookies
        save_config(config)
        driver.get(WORK_URL)

    # 检查是否需要等待
    last_work_time, _ = calculate_work_time(driver)  # 使用下划线忽略未使用的next_work_time
    if last_work_time is not None:
        return

    # 执行打工动作
    print("开始执行打工动作")
    work_buttons = ['np_advid1', 'np_advid2', 'np_advid4', 'np_advid6', 'np_advid7', 'np_advid9']
    for button_id in work_buttons:
        try:
            button = WebDriverWait(driver, 10).until(EC.element_to_be_clickable((By.ID, button_id)))
            print(f"成功定位到打工按钮: {button_id}")
            button.click()
            time.sleep(random.uniform(2, 3))
        except Exception as e:
            print(f"定位或点击打工按钮 {button_id} 时出错: {e}")

    try:
        stop_ad_button = WebDriverWait(driver, 10).until(EC.element_to_be_clickable((By.CSS_SELECTOR, STOP_AD_BUTTON_CSS)))
        print("成功定位到停止广告按钮")
        stop_ad_button.click()
    except Exception as e:
        print(f"定位或点击停止广告按钮时出错: {e}")
        
    print("打工动作执行完成")