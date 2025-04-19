import os
import sys
import logging
import tkinter as tk
from tkinter import messagebox
from selenium.webdriver.common.by import By
from config_handler import load_config, save_config
from selenium.webdriver.support.ui import WebDriverWait
from browser_driver import setup_driver, update_geckodriver
from selenium.webdriver.support import expected_conditions as EC

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    filename='tsdm_sign_tools.log',  # 日志文件路径
    filemode='a'  # 追加模式，如果需要覆盖，请使用 'w'
)

LOGIN_URL = 'https://www.tsdm39.com/member.php?mod=logging&action=login'

class LoginTool:
    def __init__(self, root):
        self.root = root
        self.root.title("TSDM 登录工具")
        # 初始化开始签到按钮为 None
        self.start_sign_button = None
        self.load_configuration()  # 调用加载配置的方法

        # 使用 grid 布局
        self.root.columnconfigure(0, weight=1)

        # 显示浏览器版本信息的标签
        self.browser_version_label = tk.Label(root, text=f"浏览器驱动版本: {self.browser_info.get('version', '未知')}")
        self.browser_version_label.grid(row=0, column=0, pady=5)

        # 展示面板
        self.account_frame = tk.Frame(root)
        self.account_frame.grid(row=1, column=0, pady=10)

        self.admin_tasks_frame = tk.Frame(root)
        self.admin_tasks_frame.grid(row=2, column=0, pady=10)
        self.display_admin_scheduled_tasks()

        # 初始检查并更新按钮状态
        self.update_start_sign_button()

        # 底部添加按钮
        self.add_button = tk.Button(root, text="添加新账号", command=self.show_login_browser)
        self.add_button.grid(row=4, column=0, pady=10)

        # 添加更新 geckodriver 按钮
        self.update_button = tk.Button(root, text="更新浏览器驱动", command=self.update_driver)
        self.update_button.grid(row=5, column=0, pady=10)

        self.display_logged_accounts()

    def load_configuration(self):
        self.config = load_config()
        self.logged_accounts = self.config.get("accounts", {})
        self.browser_info = self.config.get("browser_info", {})
        self.admin_scheduled_tasks = self.config.get("scheduled_tasks", [])
        logging.info("已读取加载的账号信息")
        # 加载配置后更新按钮状态
        self.update_start_sign_button()

    def update_start_sign_button(self):
        # 判断是否打包成 EXE
        if getattr(sys, 'frozen', False):
            # 如果是打包后的 EXE，获取 EXE 所在目录
            base_path = os.path.dirname(sys.executable)
            file_name = 'tsdm_sign_tools.exe'
        else:
            # 如果是未打包的 Python 脚本，获取脚本所在目录
            base_path = os.path.dirname(os.path.abspath(__file__))
            file_name = 'tsdm_sign_tools.py'

        exe_path = os.path.join(base_path, file_name)
        is_file_exist = os.path.isfile(exe_path)

        if is_file_exist and self.logged_accounts:
            if self.start_sign_button is None:
                if getattr(sys, 'frozen', False):
                    self.start_sign_button = tk.Button(self.root, text="开始签到", command=lambda: os.startfile(exe_path))
                else:
                    import subprocess
                    self.start_sign_button = tk.Button(self.root, text="开始签到", command=lambda: subprocess.Popen(['python', exe_path]))
                # 调整按钮位置，将其放在添加新账号按钮之上
                self.start_sign_button.grid(row=3, column=0, pady=10)
        else:
            if self.start_sign_button:
                self.start_sign_button.grid_forget()
                self.start_sign_button = None

    def show_login_browser(self):
        driver, user_data_dir = setup_driver(headless=False)  # 通常添加账号时不需要无头模式
        if not driver:
            return

        try:
            driver.get(LOGIN_URL)
            logging.info("已打开登录页面")

            # 等待 title 属性包含 "访问我的空间" 的 a 标签出现
            space_link_element = WebDriverWait(driver, 300).until(
                EC.presence_of_element_located((By.XPATH, '//a[@title="访问我的空间"]'))
            )
            # 获取用户名，即 <a> 标签内的文本
            username = space_link_element.text.strip()
            logging.info(f"成功获取用户名: {username}")

            # 获取 cookies
            cookies = driver.get_cookies()
            logging.info("成功获取 cookies")

            self.add_account(username, cookies)
            self.save_config_changes()
            self.load_configuration()
            self.display_logged_accounts()
            self.display_admin_scheduled_tasks()
            # 确保添加账号后更新按钮状态
            self.update_start_sign_button()
        except Exception as e:
            logging.error(f"等待 title 为 '访问我的空间' 的元素时出错: {e}")
            messagebox.showerror("错误", f"登录检测失败，请检查是否完成登录。错误信息: {e}")
        finally:
            if driver:
                driver.quit()
            if user_data_dir and os.path.exists(user_data_dir):
                import shutil
                shutil.rmtree(user_data_dir)

    def add_account(self, username, cookies):
        self.logged_accounts[username] = {
            "cookies": cookies,
            "is_cookie_valid": True
        }

    def display_logged_accounts(self):
        # 清空现有展示
        for widget in self.account_frame.winfo_children():
            widget.destroy()

        # 更新浏览器版本信息
        self.browser_info = self.config.get("browser_info", {})
        self.browser_version_label.config(text=f"浏览器驱动版本: {self.browser_info.get('version', '未知')}")

        if not self.logged_accounts:
            no_account_label = tk.Label(self.account_frame, text="暂无已登录账号，请添加新账号。")
            no_account_label.pack()
            return

        logging.info("准备展示账号信息")
        for username in self.logged_accounts:
            account_frame = tk.Frame(self.account_frame)
            account_frame.pack(pady=5)

            # 展示用户名
            username_label = tk.Label(account_frame, text=username)
            username_label.pack(side=tk.LEFT)

            # 展示 cookie 状态
            is_valid = self.logged_accounts[username]["is_cookie_valid"]
            status_text = "Cookie有效" if is_valid else "Cookie过期"
            status_label = tk.Label(account_frame, text=status_text, fg="green" if is_valid else "red")
            status_label.pack(side=tk.LEFT, padx=5)

            # 重新登录按钮
            re_login_btn = tk.Button(account_frame, text="重新登录", command=lambda u=username: self.re_login(u))
            re_login_btn.pack(side=tk.LEFT, padx=5)

            # 删除账号按钮
            delete_btn = tk.Button(account_frame, text="删除", command=lambda u=username, f=account_frame: self.delete_account(u, f))
            delete_btn.pack(side=tk.LEFT, padx=5)

    def re_login(self, username):
        # 这里可实现重新登录逻辑，登录成功后更新 cookie 和状态
        pass

    def delete_account(self, username, frame):
        if username in self.logged_accounts:
            del self.logged_accounts[username]
            self.save_config_changes()
            self.load_configuration()
            self.display_logged_accounts()
            # 确保删除账号后更新按钮状态
            self.update_start_sign_button()

    def update_driver(self):
        if update_geckodriver():
            self.load_configuration()  # 重新加载配置
            self.display_logged_accounts()
            self.display_admin_scheduled_tasks()
            # 确保更新驱动后更新按钮状态
            self.update_start_sign_button()
            tk.messagebox.showinfo("更新成功", "浏览器驱动已成功更新。")
        else:
            tk.messagebox.showerror("更新失败", "浏览器驱动更新失败，请查看日志。")

    def save_config_changes(self):
        self.config["accounts"] = self.logged_accounts
        save_config(self.config)

    def display_admin_scheduled_tasks(self):
        for widget in self.admin_tasks_frame.winfo_children():
            widget.destroy()

        if self.admin_scheduled_tasks:
            title_label = tk.Label(self.admin_tasks_frame, text="管理员身份计划任务：")
            title_label.pack()
            for task_name in self.admin_scheduled_tasks:
                task_label = tk.Label(self.admin_tasks_frame, text=task_name)
                task_label.pack()
        else:
            no_task_label = tk.Label(self.admin_tasks_frame, text="暂无管理员身份计划任务。")
            no_task_label.pack()


if __name__ == "__main__":
    root = tk.Tk()
    app = LoginTool(root)
    root.mainloop()
