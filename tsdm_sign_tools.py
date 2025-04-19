import os
import time
import shutil
import logging
from browser_driver import setup_driver
from config_handler import load_config
from sign_work import perform_sign, perform_work, calculate_work_time
from scheduled_task import create_login_startup_task, create_scheduled_task

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    filename='tsdm_sign_tools.log',  # 日志文件路径
    filemode='a'  # 追加模式，如果需要覆盖，请使用 'w'
)

SIGN_URL = 'https://www.tsdm39.com/plugin.php?id=dsu_paulsign:sign'
WORK_URL = 'https://www.tsdm39.com/plugin.php?id=np_cliworkdz:work'

def main():
    config = load_config()
    expired_accounts = [] # 存储过期的账号
    account_time_list = [] # 存储账号的 next_work_time 和 last_work_time

    # 从 accounts 字段获取账号信息
    accounts = config.get('accounts', {})
    for username, account_info in accounts.items():
        # 检查 cookie 是否有效
        if not account_info.get("is_cookie_valid", False):
            expired_accounts.append(username)
            continue

        driver = None
        user_data_dir = None
        account_time_info = {
            "username": username,
            "next_work_time": None,
            "last_work_time": None
        }

        try:
            logging.info(f"开始处理账号 {username} 的任务")
            driver, user_data_dir = setup_driver(headless=True)
            if driver:
                logging.info(f"浏览器已启动，开始访问主页面")
                driver.get('https://www.tsdm39.com')
                logging.info(f"开始为账号 {username} 添加 cookie")
                for cookie in account_info["cookies"]:
                    driver.add_cookie(cookie)
                logging.info(f"cookie 添加完成，准备查看账号 {username} 的签到情况")
                perform_sign(driver, username, SIGN_URL)

                # 执行打工操作
                perform_work(driver, username, WORK_URL)
                # 确保获取到 next_work_time 和 last_work_time
                while account_time_info["next_work_time"] is None or account_time_info["last_work_time"] is None:
                    driver.get(WORK_URL)
                    driver.execute_script("window.setTimeout = function() {};")
                    last_work_time, next_work_time = calculate_work_time(driver)

                    if last_work_time:
                        account_time_info["last_work_time"] = last_work_time
                    if next_work_time:
                        account_time_info["next_work_time"] = next_work_time

                account_time_list.append(account_time_info)


        except Exception as e:
            logging.error(f"处理账号 {username} 时发生错误: {e}")
        finally:
            # 关闭浏览器
            if driver:
                try:
                    driver.quit()
                    # logging.info("浏览器已成功关闭")
                except Exception as close_error:
                    logging.error(f"关闭浏览器时发生错误: {close_error}")
            if user_data_dir and os.path.exists(user_data_dir):
                try:
                    shutil.rmtree(user_data_dir)
                    # logging.info("用户数据目录已删除")
                except Exception as rm_error:
                    logging.error(f"删除用户数据目录时出错: {rm_error}")

    # 提示 cookie 过期的账号
    if expired_accounts:
        logging.info("以下账号的 cookie 已过期，请重新登录获取新的 cookie:")
        for account in expired_accounts:
            logging.info(account)

    # 输出每个账号的打工时间信息
    for info in account_time_list:
        username = info["username"]
        last_work_time = info["last_work_time"].strftime('%H:%M:%S')
        next_work_time = info["next_work_time"].strftime('%H:%M:%S')
        logging.info(f"账号 {username} 在 {last_work_time} 打工完成，下次可打工时间 {next_work_time}")

    # 找出最迟的 next_work_time
    latest_next_work_time = None
    for info in account_time_list:
        if info["next_work_time"]:
            if latest_next_work_time is None or info["next_work_time"] > latest_next_work_time:
                latest_next_work_time = info["next_work_time"]

    # 按最迟的时间创建计划任务
    if latest_next_work_time:
        logging.info(f"创建下次打工计划任务，预计在 {latest_next_work_time.strftime('%H:%M:%S')} 后执行")
        create_scheduled_task(latest_next_work_time)

    logging.info("尝试创建开机自动启动任务")
    create_login_startup_task()
    logging.info("创建计划任务可在任务计划程序中查看")
    logging.info("所有任务完成，程序将在 5 秒后自动退出...")
    time.sleep(5)  # 等待 5 秒自动退出

if __name__ == "__main__":
    main()