import io
import os
import sys
import time
import psutil  # 用于进程监控
from log_config import setup_logger
from selenium.webdriver.common.by import By
from config_handler import load_config, save_config
from selenium.webdriver.support.ui import WebDriverWait
from browser_driver import setup_driver, update_geckodriver
from selenium.webdriver.support import expected_conditions as EC
from PyQt5.QtWidgets import (QApplication, QWidget, QVBoxLayout, QHBoxLayout, QLabel,
                             QPushButton, QFrame, QTextEdit, QMessageBox)
from PyQt5.QtCore import Qt, QTimer

# 配置日志
logger = setup_logger('tsdm_sign_tools.log')

LOGIN_URL = 'https://www.tsdm39.com/member.php?mod=logging&action=login'


class LoginTool(QWidget):
    def __init__(self):
        super().__init__()
        self.resize(600, 400) # 初始窗口大小
        self.log_file_path = 'tsdm_sign_tools.log'
        self.last_log_size = 0  # 新增属性，记录上一次读取的文件大小
        self.sign_process = None  # 存储签到进程
        self.initUI()
        # 设置定时器，每秒更新一次日志
        self.timer = QTimer(self)
        self.timer.timeout.connect(self.update_log_display)
        self.timer.start(1000)

    def get_executable_path_info(self):
        # 判断是否打包成 EXE
        if getattr(sys, 'frozen', False):
            # 如果是打包后的 EXE，获取 EXE 所在目录
            base_path = os.path.dirname(sys.executable)
            file_name = 'tsdm_sign_tools.exe'
        else:
            # 如果是未打包的 Python 脚本，获取脚本所在目录
            base_path = os.path.dirname(os.path.abspath(__file__))
            file_name = 'tsdm_sign_tools.py'
        return base_path, file_name
    
    def initUI(self):
        self.setWindowTitle("天使动漫论坛登录工具")

        # 创建开始签到按钮并设置点击事件
        self.start_sign_button = QPushButton("开始签到")
        base_path, file_name = self.get_executable_path_info()
        exe_path = os.path.join(base_path, file_name)
        self.start_sign_button.clicked.connect(lambda: os.startfile(exe_path))
        self.start_sign_button.setEnabled(False)  # 初始设置为不可点击
        self.start_sign_button.hide()  # 初始设置为隐藏
        
        self.load_configuration()  # 调用加载配置的方法

        # 主布局
        main_layout = QVBoxLayout()

        # 展示面板
        self.account_frame = QFrame()
        self.account_layout = QVBoxLayout(self.account_frame)
        main_layout.addWidget(self.account_frame)

        self.admin_tasks_frame = QFrame()
        self.admin_tasks_layout = QVBoxLayout(self.admin_tasks_frame)
        main_layout.addWidget(self.admin_tasks_frame)
        self.display_admin_scheduled_tasks()

        # 底部水平布局
        bottom_layout = QHBoxLayout()

        # 显示浏览器版本信息的标签，放到底部左下角
        self.browser_version_label = QLabel(f"驱动版本: {self.browser_info.get('version', '未知，请先更新驱动')}") 
        bottom_layout.addWidget(self.browser_version_label, alignment=Qt.AlignLeft | Qt.AlignVCenter)

        # 添加伸缩项，将后续按钮推到右侧
        bottom_layout.addStretch()

        # 开始签到按钮
        bottom_layout.addWidget(self.start_sign_button)

        # 底部添加按钮
        self.add_button = QPushButton("添加账号")
        self.add_button.clicked.connect(self.show_login_browser)
        bottom_layout.addWidget(self.add_button)

        # 添加更新 geckodriver 按钮
        self.update_button = QPushButton("更新驱动")
        self.update_button.clicked.connect(self.update_driver)
        bottom_layout.addWidget(self.update_button)

        # 将底部布局添加到主布局
        main_layout.addLayout(bottom_layout)

        self.display_logged_accounts()

        # 添加运行日志框
        self.log_text_edit = QTextEdit()
        self.log_text_edit.setReadOnly(True)
        main_layout.addWidget(self.log_text_edit)

        # 添加清空日志按钮
        clear_log_button = QPushButton("清空日志")
        clear_log_button.clicked.connect(self.clear_log)
        main_layout.addWidget(clear_log_button)

        self.setLayout(main_layout)
        self.update_start_sign_button()

    def load_configuration(self):
        self.config = load_config()
        self.logged_accounts = self.config.get("accounts", {})
        self.browser_info = self.config.get("browser_info", {})
        self.admin_scheduled_tasks = self.config.get("scheduled_tasks", [])
        logger.info("读取配置文件")

    def update_start_sign_button(self):
        # 判断是否打包成 EXE
        base_path, file_name = self.get_executable_path_info()
        exe_path = os.path.join(base_path, file_name)
        is_file_exist = os.path.isfile(exe_path)

        if is_file_exist and self.logged_accounts:
            self.start_sign_button.setEnabled(True)  # 设置为可点击
            self.start_sign_button.show()  # 显示按钮
        else:
            self.start_sign_button.setEnabled(False)  # 设置为不可点击
            self.start_sign_button.hide()  # 隐藏按钮

    def show_login_browser(self):
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

            self.add_account(username, cookies)
            self.save_config_changes()
            self.load_configuration()
            self.display_logged_accounts()
            self.display_admin_scheduled_tasks()
            # 确保添加账号后更新按钮状态
            self.update_start_sign_button()
        except Exception as e:
            error_message = str(e)
            if "Browsing context has been discarded" in error_message:
                # 处理用户手动关闭浏览器的情况，不报错
                logger.info("用户手动关闭了浏览器，操作已取消。")
            else:
                logger.error(f"等待 title 为 '访问我的空间' 的元素时出错: {e}")
                from PyQt5.QtWidgets import QMessageBox
                QMessageBox.critical(self, "错误", f"登录检测失败，请检查是否完成登录。错误信息: {e}")
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
        while self.account_layout.count():
            item = self.account_layout.takeAt(0)
            widget = item.widget()
            if widget:
                widget.deleteLater()

        if not self.logged_accounts:
            no_account_label = QLabel("无账号信息")
            self.account_layout.addWidget(no_account_label, alignment=Qt.AlignCenter)
            return

        # 添加标题标签
        title_label = QLabel("已记录账号信息")
        title_label.setStyleSheet("font-weight: bold; font-size: 24px;")  # 设置标题样式
        self.account_layout.addWidget(title_label, alignment=Qt.AlignCenter)

        logger.info("面板加载")
        for username in self.logged_accounts:
            # 创建一个垂直布局来包含标题和账号信息
            account_main_layout = QVBoxLayout()

            # 用户名标题
            username_title_label = QLabel("用户名")
            username_title_label.setStyleSheet("font-weight: bold")
            account_main_layout.addWidget(username_title_label)

            # 展示用户名
            username_label = QLabel(username)
            account_main_layout.addWidget(username_label)

            # Cookie 状态标题
            cookie_status_title_label = QLabel("Cookie 状态")
            cookie_status_title_label.setStyleSheet("font-weight: bold")
            account_main_layout.addWidget(cookie_status_title_label)

            # 展示 cookie 状态
            is_valid = self.logged_accounts[username]["is_cookie_valid"]
            status_text = "Cookie有效" if is_valid else "Cookie过期"
            status_label = QLabel(status_text)
            status_label.setStyleSheet(f"color: {'green' if is_valid else 'red'}")
            account_main_layout.addWidget(status_label)

            # 创建一个水平布局来放置按钮
            button_layout = QHBoxLayout()

            # 重新登录按钮
            re_login_btn = QPushButton("重新登录")
            re_login_btn.clicked.connect(lambda _, u=username: self.re_login(u))
            button_layout.addWidget(re_login_btn)

            # 删除账号按钮
            delete_btn = QPushButton("删除账号")

            # 创建一个框架并设置布局
            account_frame = QFrame()
            account_frame.setLayout(account_main_layout)

            # 现在 account_frame 已经创建，可以安全地连接事件
            delete_btn.clicked.connect(lambda _, u=username, f=account_frame: self.delete_account(u, f))
            button_layout.addWidget(delete_btn)

            # 将按钮布局添加到主布局
            account_main_layout.addLayout(button_layout)

            self.account_layout.addWidget(account_frame)

        # 更新浏览器版本信息
        self.browser_info = self.config.get("browser_info", {})
        self.browser_version_label.setText(f"驱动版本: {self.browser_info.get('version', '未知，请先更新驱动')}")
        logger.info("面板加载完成")
    def re_login(self, username):
        self.show_login_browser()

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
            from PyQt5.QtWidgets import QMessageBox
            QMessageBox.information(self, "更新成功", "浏览器驱动已成功更新。")
        else:
            from PyQt5.QtWidgets import QMessageBox
            QMessageBox.critical(self, "更新失败", "浏览器驱动更新失败，请查看日志。")

    def save_config_changes(self):
        self.config["accounts"] = self.logged_accounts
        save_config(self.config)

    def display_admin_scheduled_tasks(self):
        while self.admin_tasks_layout.count():
            item = self.admin_tasks_layout.takeAt(0)
            widget = item.widget()
            if widget:
                widget.deleteLater()

        if self.admin_scheduled_tasks:
            title_label = QLabel("管理员身份计划任务：")
            self.admin_tasks_layout.addWidget(title_label)
            for task_name in self.admin_scheduled_tasks:
                task_label = QLabel(task_name)
                self.admin_tasks_layout.addWidget(task_label)
        else:
            no_task_label = QLabel("无管理员身份计划任务。")
            self.admin_tasks_layout.addWidget(no_task_label, alignment=Qt.AlignCenter)

    def start_sign(self, exe_path):
        try:
            os.startfile(exe_path)
            # 查找 tsdm_sign_tools.exe 进程
            for proc in psutil.process_iter(['name']):
                if proc.info['name'] == 'tsdm_sign_tools.exe':
                    self.sign_process = proc
                    break
        except Exception as e:
            QMessageBox.critical(self, "错误", f"启动签到程序失败: {e}")

    def update_log_display(self):
        if os.path.exists(self.log_file_path):
            is_sign_running = self.is_sign_process_running()
            max_retries = 3
            retries = 0
            while retries < max_retries:
                try:
                    if is_sign_running:
                        # 签到进程运行时，只读模式读取
                        with io.open(self.log_file_path, 'r', encoding='utf-8', errors='ignore') as f:
                            f.seek(0, os.SEEK_END)
                            current_size = f.tell()
                            if current_size > self.last_log_size:
                                f.seek(self.last_log_size)
                                new_log_content = ''.join([line.strip() + '\n' for line in f.readlines()])
                                self.log_text_edit.insertPlainText(new_log_content)
                                self.last_log_size = current_size
                    else:
                        # 签到进程结束后，可进行读写操作（这里主要是读取显示）
                        with open(self.log_file_path, 'r', encoding='utf-8') as f:
                            f.seek(0, os.SEEK_END)
                            current_size = f.tell()
                            if current_size > self.last_log_size:
                                f.seek(self.last_log_size)
                                new_log_content = ''.join([line.strip() + '\n' for line in f.readlines()])
                                self.log_text_edit.insertPlainText(new_log_content)
                                self.last_log_size = current_size
                    self.log_text_edit.moveCursor(self.log_text_edit.textCursor().End)
                    break
                except Exception as e:
                    retries += 1
                    time.sleep(0.1)
                    if retries == max_retries:
                        QMessageBox.warning(self, "警告", f"读取日志文件时出错: {e}")

    def is_sign_process_running(self):
        if self.sign_process:
            try:
                return self.sign_process.is_running()
            except psutil.NoSuchProcess:
                self.sign_process = None
        return False

    def clear_log(self):
        if os.path.exists(self.log_file_path):
            with open(self.log_file_path, 'w') as f:
                f.truncate(0)
            self.log_text_edit.clear()

if __name__ == "__main__":
    app = QApplication(sys.argv)
    login_tool = LoginTool()
    login_tool.show()
    sys.exit(app.exec_())