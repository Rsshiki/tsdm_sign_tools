import time
import random
from log_config import setup_logger
from datetime import datetime, timedelta
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from config_handler import load_config, save_config
from selenium.webdriver.support import expected_conditions as EC

# 配置日志
logger = setup_logger('tsdm_sign_tools.log')

# 签到页面选择器
NEED_LOGIN_SIGN_CSS = '#messagetext.alert_info p'
ALREADY_SIGNED_CSS = 'h1.mt'
SMILE_BUTTON_CSS_TEMPLATE = 'ul.qdsmile {}'
RADIO_BUTTON_CSS = '#qiandao > table.tfm > tbody > tr:nth-child(1) > td > label:nth-child(2) > input[type=radio]'
SUBMIT_BUTTON_CSS = '#qiandao > table:nth-child(11) > tbody > tr > td > div > a:nth-child(2)'

# 打工页面选择器
NEED_LOGIN_WORK_CSS = '#messagetext.alert_info p'
NEED_WAIT_WORK_CSS = '#messagetext.alert_info p'
STOP_AD_BUTTON_CSS = '#stopad a'

# 选择器文本
wait_work_time = "必须与上一次间隔6小时0分钟0秒才可再次进行"
sign_cookie_wrong = "您需要先登录才能继续本操作"
work_cookie_wrong = "请先登录再进行点击任务"

def calculate_work_time(driver):
    """
    从页面获取等待信息，计算上次和下次打工时间
    :param driver: 浏览器驱动
    :return: 上次打工时间和下次打工时间，如果未获取到等待信息则返回 None, None
    """
    wait_elements = driver.find_elements(By.CSS_SELECTOR, NEED_WAIT_WORK_CSS)
    for element in wait_elements:
        if wait_work_time in element.text:
            wait_text = element.text.split('您需要等待')[1].split('后即可进行。')[0]
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
    # 判断当前时间是否在 0 点到 1 点之间
    current_hour = datetime.now().hour
    if 0 <= current_hour < 1:
        logger.info("当前时间在 0 点到 1 点之间，不允许签到，跳过签到操作")
        return

    driver.get(SIGN_URL)
    # 检查cookie是否有效
    login_elements = driver.find_elements(By.CSS_SELECTOR, NEED_LOGIN_SIGN_CSS)
    for element in login_elements:
        if sign_cookie_wrong in element.text:
            logger.info("Cookie过期，标记状态...")
            config = load_config()
            if username in config.get('accounts', {}):
                config['accounts'][username]["is_cookie_valid"] = False
                save_config(config)
            return

    try:
        # 显式等待检查是否已经签到的元素加载完成
        WebDriverWait(driver, 2).until(
            EC.presence_of_element_located((By.CSS_SELECTOR, ALREADY_SIGNED_CSS))
        )
        logger.info("检查是否已经签到")
        signed_elements = driver.find_elements(By.CSS_SELECTOR, ALREADY_SIGNED_CSS)
        target_text = "您今天已经签到过了或者签到时间还未开始"
        for element in signed_elements:
            if target_text in element.text:
                logger.info("今日已签到")
                return
    except Exception as e:
        logger.error(f"检查是否已经签到时出错: {e}")

    # 执行签到动作
    logger.info("还未签到，开始执行签到动作...")
    smile_buttons = ['#kx', '#ng', '#ym', '#wl', '#nu', '#ch', '#fd', '#yl', '#shuai']
    random_smile = random.choice(smile_buttons)
    try:
        logger.info(f"尝试点击表情按钮: {random_smile}")
        WebDriverWait(driver, 10).until(
            EC.element_to_be_clickable((By.CSS_SELECTOR, SMILE_BUTTON_CSS_TEMPLATE.format(random_smile)))).click()
        logger.info("表情按钮点击成功")
    except Exception as e:
        logger.error(f"点击表情按钮时出错: {e}")
        return

    try:
        logger.info("尝试点击单选按钮")
        WebDriverWait(driver, 10).until(EC.element_to_be_clickable((By.CSS_SELECTOR, RADIO_BUTTON_CSS))).click()
        logger.info("单选按钮点击成功")
    except Exception as e:
        logger.error(f"点击单选按钮时出错: {e}")
        return

    try:
        logger.info("尝试点击提交按钮")
        WebDriverWait(driver, 10).until(EC.element_to_be_clickable((By.CSS_SELECTOR, SUBMIT_BUTTON_CSS))).click()
        logger.info("提交按钮点击成功，签到完成")
    except Exception as e:
        logger.error(f"点击提交按钮时出错: {e}")
        return


def perform_work(driver, username, WORK_URL):
    """执行打工操作"""
    logger.info(f"开始执行账号 {username} 的打工操作")
    driver.get(WORK_URL)

    # 检查cookies是否过期
    login_elements = driver.find_elements(By.CSS_SELECTOR, NEED_LOGIN_WORK_CSS)
    for element in login_elements:
        if work_cookie_wrong in element.text:
            logger.info("Cookie过期，标记状态...")
            config = load_config()
            if username in config.get('accounts', {}):
                config['accounts'][username]["is_cookie_valid"] = False
                save_config(config)
            return

    try:
        # 检查是否有以 np_advid 开头的按钮
        work_buttons = WebDriverWait(driver, 1).until(
            EC.presence_of_all_elements_located((By.CSS_SELECTOR, '[id^="np_advid"]'))) #没有按钮就表示
        if work_buttons:
            logger.info("找到打工按钮，开始执行打工动作")
            work_buttons_ids = [button.get_attribute('id') for button in work_buttons]
            random.shuffle(work_buttons_ids)  # 随机打乱按钮顺序
            logger.info(f"找到的所有打工按钮: {work_buttons_ids}")

            all_clicked_success = True
            for button_id in work_buttons_ids:
                try:
                    button = WebDriverWait(driver, 10).until(EC.element_to_be_clickable((By.ID, button_id)))

                    original_window = driver.current_window_handle
                    button.click()
                    time.sleep(random.uniform(1, 2))
                    driver.switch_to.window(original_window) # 切换回原始窗口
                    a_element = WebDriverWait(driver, 10).until(
                        EC.presence_of_element_located((By.CSS_SELECTOR, f'#{button_id} a')))
                    style_value = a_element.get_attribute('style')
                    if style_value and 'display: none;' in ' '.join(style_value.split()).strip():
                        logger.info(f"按钮 {button_id} 点击成功")
                    else:
                        logger.info(f"按钮 {button_id} 点击可能未成功")
                        all_clicked_success = False

                except Exception as e:
                    logger.error(f"定位、点击或检查打工按钮 {button_id} 时出错: {e}")
                    all_clicked_success = False

            if not all_clicked_success:
                logger.info("部分广告按钮未成功点击")
                choice = input("部分广告按钮未成功点击，是否重新进行打工？(输入 y 重新打工，其他任意键退出): ")
                if choice.lower() == 'y':
                    perform_work(driver, username, WORK_URL)
                return

            if all_clicked_success:
                try:
                    stop_ad_button = WebDriverWait(driver, 10).until(
                        EC.element_to_be_clickable((By.CSS_SELECTOR, STOP_AD_BUTTON_CSS)))
                    logger.info("点击停止广告按钮")
                    stop_ad_button.click()

                    # 检查是否出现失败提示
                    try:
                        logger.info("检查是否出现打工失败提示")
                        possible_elements = WebDriverWait(driver, 10).until(
                            EC.presence_of_element_located((By.CSS_SELECTOR, '#messagetext.alert_info p'))
                        )
                        target_text = "不要作弊哦，重新进行游戏吧！"
                        failure_element = None
                        if isinstance(possible_elements, list):
                            for element in possible_elements:
                                if target_text in element.text:
                                    failure_element = element
                                    break
                        elif target_text in possible_elements.text:
                            failure_element = possible_elements

                        if failure_element:
                            logger.info("打工失败，页面提示需要重新进行游戏。")
                            choice = input("打工失败，是否重新进行打工？(输入 y 重新打工，其他任意键退出): ")
                            if choice.lower() == 'y':
                                perform_work(driver, username, WORK_URL)
                    except Exception as e:
                        logger.info("打工成功")

                except Exception as e:
                    logger.error(f"定位或点击停止广告按钮时出错: {e}")
                    choice = input("点击停止广告按钮失败，是否重新进行打工？(输入 y 重新打工，其他任意键退出): ")
                    if choice.lower() == 'y':
                        perform_work(driver, username, WORK_URL)

    except Exception as e:
        # 没有找到打工按钮，可能处于冷却期
        logger.info("未找到打工按钮，可能处于冷却期")