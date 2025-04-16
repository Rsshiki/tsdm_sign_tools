import os
import time
import shutil
from browser_driver import setup_driver
from config_handler import load_config
from sign_work import perform_sign, perform_work, calculate_work_time
from scheduled_task import create_login_startup_task, create_scheduled_task

LOGIN_URL = 'https://www.tsdm39.com/member.php?mod=logging&action=login'
SIGN_URL = 'https://www.tsdm39.com/plugin.php?id=dsu_paulsign:sign'
WORK_URL = 'https://www.tsdm39.com/plugin.php?id=np_cliworkdz:work'

def main():
    config = load_config()
    expired_accounts = []  # 用于记录 cookie 过期的账号
    last_next_work_time = None # 初始化 last_next_work_time
    for username, account_info in config.items():
        if not account_info.get("is_cookie_valid", False):
            expired_accounts.append(username)
            continue

        driver = None
        user_data_dir = None
        try:
            driver, user_data_dir = setup_driver(headless=True)
            # 直接执行签到和打工操作，由浏览器判断是否需要执行
            if driver:
                print(f"开始处理账号 {username} 的签到和打工任务")
                driver.get('https://www.tsdm39.com')
                for cookie in account_info["cookies"]:
                    driver.add_cookie(cookie)
                print(f"查看账号 {username} 的签到情况")
                perform_sign(driver, username, SIGN_URL)
                print(f"查看账号 {username} 的打工情况")
                perform_work(driver, username, WORK_URL)
                
                # 获取下次打工时间并创建计划任务
                driver.get(WORK_URL)
                _, next_work_time = calculate_work_time(driver)

                if next_work_time:
                    last_next_work_time = next_work_time
        except Exception as e:
            print(f"处理账号 {username} 时发生错误: {e}")
        finally:
            # 关闭浏览器
            if driver:
                try:
                    driver.quit()
                    # print("浏览器已成功关闭")
                except Exception as close_error:
                    print(f"关闭浏览器时发生错误: {close_error}")
            if user_data_dir and os.path.exists(user_data_dir):
                try:
                    shutil.rmtree(user_data_dir)
                except Exception as rm_error:
                    print(f"删除用户数据目录时出错: {rm_error}")

    # 提示 cookie 过期的账号
    if expired_accounts:
        print("以下账号的 cookie 已过期，请重新登录获取新的 cookie:")
        for account in expired_accounts:
            print(account)

    # 按最后一个账号的时间创建计划任务
    if last_next_work_time:
        print(f"创建下次打工计划任务，预计在 {last_next_work_time.strftime('%H:%M:%S')} 后执行")
        create_scheduled_task(last_next_work_time)

    print("尝试创建开机自动启动任务")
    create_login_startup_task()
    print("创建计划任务可在任务计划程序中查看")
    print("所有任务完成，程序将在 5 秒后自动退出...")
    time.sleep(5)  # 等待 5 秒自动退出

if __name__ == "__main__":
    main()