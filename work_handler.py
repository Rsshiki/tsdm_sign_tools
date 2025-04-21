import time
import random
from log_config import setup_logger
from datetime import datetime, timedelta
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from config_handler import load_config, save_config
from selenium.webdriver.support import expected_conditions as EC
from browser_manager import get_browser_driver, function_finished, check_driver_validity

# 配置日志
logger = setup_logger('tsdm_sign_tools.log')

# 打工页面选择器
NEED_LOGIN_WORK_CSS = '#messagetext.alert_info p'
STOP_AD_BUTTON_CSS = '#stopad a'
NEED_WAIT_WORK_CSS = '#messagetext.alert_info p'

# 选择器文本
work_cookie_wrong = "请先登录再进行点击任务"
wait_work_time = "必须与上一次间隔6小时0分钟0秒才可再次进行"

WORK_URL = 'https://www.tsdm39.com/plugin.php?id=np_cliworkdz:work'

def ensure_browser_started():
    driver = get_browser_driver()
    return driver

def check_cookie_validity(driver, username, cookies):
    """
    检查 cookie 的有效性
    :param driver: 浏览器驱动实例
    :param username: 用户名
    :param cookies: 要检查的 cookie 列表
    :return: 如果 cookie 有效返回 True，否则返回 False
    """
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
    except Exception as e:
        logger.error(f"检查 {username} 的 cookie 有效性时出错: {e}")

    # 标记 cookie 无效
    config = load_config()
    if username in config.get('account_categories', {}):
        config['account_categories'][username]["is_cookie_valid"] = False
        save_config(config)
    return False

def calculate_work_time(driver):
    """
    从页面获取等待信息，计算上次打工时间
    :param driver: 浏览器驱动
    :return: 上次打工时间，如果未获取到等待信息则返回 None
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
            return last_work_time
    return None

def perform_work(username, cookies):
    # 确保浏览器已启动（并附加cookie）
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
    driver.get(WORK_URL)

    try:
        # 检查是否有以 np_advid 开头的按钮
        work_buttons = WebDriverWait(driver, 1).until(
            EC.presence_of_all_elements_located((By.CSS_SELECTOR, '[id^="np_advid"]')))
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
                    driver.switch_to.window(original_window)
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
                    perform_work(username, cookies)
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
                                perform_work(username, cookies)
                    except Exception as e:
                        logger.info("打工成功")
                        # 未找到打工按钮，记录 last_work_time
                        record_last_work_time(driver, username)
                    finally:
                        logger.info("打工操作结束，调用 function_finished")
                        function_finished()
                except Exception as e:
                    logger.error(f"定位或点击停止广告按钮时出错: {e}")
                    choice = input("点击停止广告按钮失败，是否重新进行打工？(输入 y 重新打工，其他任意键退出): ")
                    if choice.lower() == 'y':
                        perform_work(username, cookies)

    except Exception as e:
        # 没有找到打工按钮，可能处于冷却期
        logger.info("未找到打工按钮，可能处于冷却期")
        # 未找到打工按钮，记录 last_work_time
        record_last_work_time(driver, username)
    finally:
        logger.info("签到操作结束，调用 function_finished")
        function_finished()

def record_last_work_time(driver, username):
    last_work_time = None
    max_retries = 3
    retry_count = 0
    while retry_count < max_retries and last_work_time is None:
        try:
            # 每次尝试前访问 work_url 页面
            driver.get(WORK_URL)
            last_work_time = calculate_work_time(driver)
            if last_work_time is None:
                logger.info(f"第 {retry_count + 1} 次尝试未获取到用户 {username} 的上次打工时间，将进行下一次尝试")
        except Exception as e:
            logger.error(f"第 {retry_count + 1} 次尝试获取用户 {username} 的上次打工时间时出错: {e}")
        retry_count += 1

    if last_work_time:
        config = load_config()
        if username in config.get('account_categories', {}):
            config['account_categories'][username]["last_work_time"] = last_work_time.strftime("%Y-%m-%d %H:%M:%S")
            save_config(config)
            logger.info(f"已记录用户 {username} 的上次打工时间: {last_work_time}")
    else:
        logger.info(f"尝试 {max_retries} 次后仍未获取到用户 {username} 的上次打工时间")
