import tkinter as tk
from tkinter import messagebox
from selenium import webdriver
from selenium.webdriver.firefox.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
import logging
from config_handler import load_config, save_config

# 配置日志
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

class LoginTool:
    def __init__(self, root):
        self.root = root
        self.root.title("TSDM 登录工具")
        self.logged_accounts = load_config()

        # 展示面板
        self.account_frame = tk.Frame(root)
        self.account_frame.pack(pady=10)

        # 底部添加按钮
        self.add_button = tk.Button(root, text="添加新账号", command=self.show_login_browser)
        self.add_button.pack(pady=10)

        self.display_logged_accounts()

    def display_logged_accounts(self):
        # 清空现有展示
        for widget in self.account_frame.winfo_children():
            widget.destroy()

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

    def show_login_browser(self):
        firefox_options = Options()
        driver = webdriver.Firefox(options=firefox_options)
        try:
            driver.get("https://www.tsdm39.com/member.php?mod=logging&action=login")
            logging.info("已打开登录页面")

            try:
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
                save_config(self.logged_accounts)
                self.display_logged_accounts()
            except Exception as e:
                logging.error(f"等待 title 为 '访问我的空间' 的元素时出错: {e}")
                messagebox.showerror("错误", f"登录检测失败，请检查是否完成登录。错误信息: {e}")

        except Exception as e:
            logging.error(f"打开浏览器或操作过程中出错: {e}")
            messagebox.showerror("错误", str(e))
        finally:
            driver.quit()

    def add_account(self, username, cookies):
        self.logged_accounts[username] = {
            "cookies": cookies,
            "is_cookie_valid": True
        }

    def re_login(self, username):
        # 这里可实现重新登录逻辑，登录成功后更新 cookie 和状态
        pass

    def delete_account(self, username, frame):
        if username in self.logged_accounts:
            del self.logged_accounts[username]
            frame.destroy()
            save_config(self.logged_accounts)


if __name__ == "__main__":
    root = tk.Tk()
    app = LoginTool(root)
    root.mainloop()
