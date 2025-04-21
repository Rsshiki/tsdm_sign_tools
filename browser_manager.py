from browser_driver import setup_driver
from log_config import setup_logger
from selenium.webdriver.remote.webdriver import WebDriver
from PyQt5.QtCore import QTimer
from selenium.common.exceptions import WebDriverException

# 配置日志
logger = setup_logger('tsdm_sign_tools.log')

# 全局浏览器驱动实例
global_driver = None
idle_timer = None

MAIN_URL = 'https://www.tsdm39.com'

# 记录功能是否在运行的标志
is_function_running = False

def get_browser_driver(headless=True):
    global global_driver, is_function_running, idle_timer
    if not check_driver_validity():
        try:
            global_driver, _ = setup_driver(headless=headless)
            if not global_driver:
                logger.error("无法启动浏览器")
                return None
            # 第一次打开浏览器时访问指定页面
            try:
                global_driver.set_page_load_timeout(30)
                global_driver.get(MAIN_URL)
                logger.info(f"成功访问页面: {MAIN_URL}")
            except Exception as e:
                logger.error(f"访问页面 {MAIN_URL} 时出错: {e}")
        except Exception as e:
            logger.error(f"启动浏览器时出错: {e}")

    # 有功能开始运行，停止空闲定时器
    if idle_timer and idle_timer.isActive():
        idle_timer.stop()
    is_function_running = True
    return global_driver


def start_idle_timer():
    global idle_timer, global_driver
    if idle_timer is None:
        idle_timer = QTimer()
        idle_timer.timeout.connect(close_browser_driver)
        logger.info("空闲定时器已创建")

    # 若浏览器驱动存在且没有功能在运行，启动 10 秒定时器
    if global_driver and not is_function_running:
        logger.info("尝试启动空闲定时器")
        idle_timer.start(10000)
        logger.info("空闲定时器已启动，10 秒后尝试关闭浏览器")
    else:
        logger.info("不满足启动空闲定时器的条件：浏览器驱动不存在或有功能正在运行")

def function_finished():
    global is_function_running
    logger.info("功能已完成，将 is_function_running 标志设置为 False")
    is_function_running = False
    start_idle_timer()

def close_browser_driver():
    global global_driver, idle_timer
    if global_driver:
        try:
            global_driver.quit()
            global_driver = None
            logger.info("浏览器已关闭")
        except Exception as e:
            logger.error(f"关闭浏览器时出错: {e}")
    if idle_timer and idle_timer.isActive():
        idle_timer.stop()
        logger.info("空闲定时器已停止")

def check_driver_validity():
    global global_driver
    if global_driver:
        try:
            # 简单检查 driver 是否有效，例如获取当前页面的 URL
            global_driver.current_url
            return True
        except WebDriverException:
            logger.error("浏览器驱动已失效，将重置驱动")
            global_driver = None
    return False

