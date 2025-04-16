import time
import random
from config_handler import save_config, load_config
from datetime import datetime, timedelta
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

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

def perform_sign(driver, username, SIGN_URL):
    """执行签到操作"""
    config = load_config()
    driver.get(SIGN_URL)
    # 检查是否需要重新登录
    if driver.find_elements(By.XPATH, NEED_LOGIN_SIGN_XPATH):
        print("Cookie过期，标记状态...")
        if username in config:
            config[username]["is_cookie_valid"] = False
            save_config(config)
        return

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


def perform_work(driver, username, WORK_URL):
    """执行打工操作"""
    config = load_config()
    driver.get(WORK_URL)
    # 检查是否需要重新登录
    if driver.find_elements(By.XPATH, NEED_LOGIN_WORK_XPATH):
        print("Cookie过期，标记状态...")
        if username in config:
            config[username]["is_cookie_valid"] = False
            save_config(config)
        return

    # 检查是否需要等待
    last_work_time, _ = calculate_work_time(driver)  # 使用下划线忽略未使用的next_work_time
    if last_work_time is not None:
        print(f"在{last_work_time.strftime('%H:%M:%S')}已打过工")
        return

    while True:
        # 执行打工动作
        print("开始执行打工动作")
        # 从网页获取所有以 np_advid 开头的按钮 id
        work_buttons = WebDriverWait(driver, 10).until(EC.presence_of_all_elements_located((By.CSS_SELECTOR, '[id^="np_advid"]')))
        work_buttons_ids = [button.get_attribute('id') for button in work_buttons]
        random.shuffle(work_buttons_ids)  # 随机打乱按钮顺序
        print(f"找到的所有打工按钮: {work_buttons_ids}")

        all_clicked_success = True
        for button_id in work_buttons_ids:
            try:
                button = WebDriverWait(driver, 10).until(EC.element_to_be_clickable((By.ID, button_id)))
                print(f"成功定位到打工按钮: {button_id}")
                
                # 记录当前窗口句柄
                original_window = driver.current_window_handle
                
                button.click()
                time.sleep(random.uniform(1, 3))
                
                # 切换回原窗口
                driver.switch_to.window(original_window)
                
                # 检查按钮是否成功点击
                a_element = WebDriverWait(driver, 10).until(EC.presence_of_element_located((By.CSS_SELECTOR, f'#{button_id} a')))
                style_value = a_element.get_attribute('style')
                if style_value and 'display: none;' in ' '.join(style_value.split()).strip():
                    print(f"按钮 {button_id} 点击成功")
                else:
                    print(f"按钮 {button_id} 点击可能未成功")
                    all_clicked_success = False

            except Exception as e:
                print(f"定位、点击或检查打工按钮 {button_id} 时出错: {e}")
                all_clicked_success = False

        if not all_clicked_success:
            choice = input("部分广告按钮未成功点击，是否重新进行打工？(输入 y 重新打工，其他任意键退出): ")
            if choice.lower() != 'y':
                break
            continue

        if all_clicked_success:
            try:
                stop_ad_button = WebDriverWait(driver, 10).until(EC.element_to_be_clickable((By.CSS_SELECTOR, STOP_AD_BUTTON_CSS)))
                print("成功定位到停止广告按钮")
                stop_ad_button.click()

                # 检查是否出现失败提示
                try:
                    failure_element = WebDriverWait(driver, 10).until(
                        EC.presence_of_element_located((By.XPATH, '//div[@id="messagetext" and @class="alert_info"]//p[contains(text(), "不要作弊哦，重新进行游戏吧！")]'))
                    )
                    print("打工失败，页面提示需要重新进行游戏。")
                    choice = input("打工失败，是否重新进行打工？(输入 y 重新打工，其他任意键退出): ")
                    if choice.lower() != 'y':
                        break
                    else:
                        continue
                except:
                    print("打工可能成功，未检测到失败提示信息。")
                    print("打工动作执行完成")
                    break

            except Exception as e:
                print(f"定位或点击停止广告按钮时出错: {e}")
                all_clicked_success = False
                choice = input("点击停止广告按钮失败，是否重新进行打工？(输入 y 重新打工，其他任意键退出): ")
                if choice.lower() != 'y':
                    break