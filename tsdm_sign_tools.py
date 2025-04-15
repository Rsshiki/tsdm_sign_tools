from config_handler import load_config, save_config
from browser_driver import setup_driver, login
from sign_work import perform_sign, perform_work, calculate_work_time
from scheduled_task import create_login_startup_task, create_scheduled_task
import os
import shutil

LOGIN_URL = 'https://www.tsdm39.com/member.php?mod=logging&action=login'
SIGN_URL = 'https://www.tsdm39.com/plugin.php?id=dsu_paulsign:sign'
WORK_URL = 'https://www.tsdm39.com/plugin.php?id=np_cliworkdz:work'

def main():
    config = load_config()
    driver = None
    user_data_dir = None
    try:
        driver, user_data_dir = setup_driver(headless='cookies' in config)
        if 'cookies' not in config:
            print("没有cookie，网页登录获取...")
            cookies = login(driver, LOGIN_URL)
            if cookies is not None:
                print("成功获取 cookies")
                config['cookies'] = cookies
                save_config(config)
                print("配置文件已更新")
        else:
            if driver:
                driver.get('https://www.tsdm39.com')
                for cookie in config['cookies']:
                    driver.add_cookie(cookie)


        # 直接执行签到和打工操作，由浏览器判断是否需要执行
        if driver:
            print("查看签到情况")
            perform_sign(driver, config, SIGN_URL, LOGIN_URL)
            print("查看打工情况")
            perform_work(driver, config, WORK_URL, LOGIN_URL)
            
            # 获取下次打工时间并创建计划任务
            driver.get(WORK_URL)
            last_work_time, next_work_time = calculate_work_time(driver)
            create_scheduled_task(next_work_time)
            print(f"上次打工时间为{last_work_time.strftime('%H:%M:%S')}")
    except Exception as e:
        print(f"发生错误: {e}")
    finally:
        if driver:
            try:
                driver.quit()
                print("浏览器已成功关闭")
            except Exception as close_error:
                print(f"关闭浏览器时发生错误: {close_error}")
        if user_data_dir and os.path.exists(user_data_dir):
            try:
                shutil.rmtree(user_data_dir)
            except Exception as rm_error:
                print(f"删除用户数据目录时出错: {rm_error}")
    
    create_login_startup_task()
    input("请按回车键退出...")

if __name__ == "__main__":
    main()