from log_config import setup_logger
from browser_driver import setup_driver
from PyQt5.QtCore import QObject, pyqtSignal
from selenium.common.exceptions import WebDriverException

# 配置日志
logger = setup_logger('tsdm_sign_tools.log')

# 全局浏览器驱动实例
global_driver = None

MAIN_URL = 'https://www.tsdm39.com'

class TimerManager(QObject):
    start_timer_signal = pyqtSignal()
    stop_timer_signal = pyqtSignal()

def get_browser_driver(headless=True):
    global global_driver
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
    return global_driver

def close_browser_driver():
    global global_driver
    if global_driver:
        try:
            global_driver.quit()
            global_driver = None
        except Exception as e:
            # 详细记录异常信息，方便排查问题
            logger.error(f"关闭浏览器时出错: {e}", exc_info=True)

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

