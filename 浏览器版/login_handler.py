import os
import shutil
from log_config import setup_logger
from browser_driver import setup_driver
from selenium.webdriver.common.by import By
from config_handler import load_config, save_config
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

# 配置日志
logger = setup_logger('tsdm_sign_tools.log')

LOGIN_URL = 'https://www.tsdm39.com/member.php?mod=logging&action=login'

def show_login_browser(login_tool_instance):
    driver, user_data_dir = setup_driver(headless=False)  # 通常添加账号时不需要无头模式
    if not driver:
        return

    try:
        driver.get(LOGIN_URL)
        logger.info("已打开登录页面")

        # 等待 title 属性包含 "访问我的空间" 的 a 标签出现
        space_link_element = WebDriverWait(driver, 300).until(
            EC.presence_of_element_located((By.XPATH, '//a[@title="访问我的空间"]'))
        )
        # 获取用户名，即 <a> 标签内的文本
        username = space_link_element.text.strip()
        logger.info(f"成功获取用户名: {username}")

        # 获取 cookies
        cookies = driver.get_cookies()
        logger.info("成功获取 cookies")

        # 加载配置文件
        config = load_config()

        # 初始化用户信息
        config['account_categories'][username] = {
            'cookie': cookies,
            'is_cookie_valid': True,
            'last_sign_time': None,
            'last_work_time': None
        }
        # 保存配置文件
        save_config(config)

    except Exception as e:
        error_message = str(e)
        if "Browsing context has been discarded" in error_message:
            # 处理用户手动关闭浏览器的情况，不报错
            logger.info("用户手动关闭了浏览器，操作已取消。")
        else:
            logger.error(f"等待 title 为 '访问我的空间' 的元素时出错: {e}")
            from PyQt5.QtWidgets import QMessageBox
            QMessageBox.critical(login_tool_instance, "错误", f"登录检测失败，请检查是否完成登录。错误信息: {e}")
    finally:
        if driver:
            driver.quit()
        if user_data_dir and os.path.exists(user_data_dir):
            shutil.rmtree(user_data_dir)

