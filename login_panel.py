import io
import os
import sys
import time
import psutil  # 用于进程监控
from datetime import datetime
from log_config import setup_logger
from selenium.webdriver.common.by import By
from config_handler import load_config, save_config
from selenium.webdriver.support.ui import WebDriverWait
from browser_driver import setup_driver, update_geckodriver
from selenium.webdriver.support import expected_conditions as EC
from PyQt5.QtWidgets import (QApplication, QWidget, QVBoxLayout, QHBoxLayout, QLabel,
                             QPushButton, QFrame, QTextEdit, QMessageBox, QTableWidget,
                             QTableWidgetItem)
from PyQt5.QtCore import Qt, QTimer, QPropertyAnimation, QEasingCurve, QPointF, pyqtSignal, QRectF, pyqtProperty  # 导入 pyqtProperty
from PyQt5.QtGui import QPainter, QBrush, QColor, QPen, QFont
from sign_handler import perform_sign
from work_handler import perform_work
from login_handler import show_login_browser

# 配置日志
logger = setup_logger('tsdm_sign_tools.log')

LOGIN_URL = 'https://www.tsdm39.com/member.php?mod=logging&action=login'

class ToggleSwitch(QWidget):
    def __init__(self, parent=None, width=150, height=30, checked_color="#66BB6A",
                 unchecked_color="#E0E0E0", handle_color="#FAFAFA"):
        super().__init__(parent)
        self.setFixedSize(width, height)
        self.checked = False
        self.checked_color = QColor(checked_color)
        self.unchecked_color = QColor(unchecked_color)
        self.handle_color = QColor(handle_color)
        self._offset = 0  # 初始化 _offset
        self.animation = QPropertyAnimation(self, b"offset")
        self.animation.setEasingCurve(QEasingCurve.InOutQuad)
        self.animation.setDuration(200)

    # 使用 pyqtProperty 定义 offset 属性
    @pyqtProperty(float)
    def offset(self):
        return self._offset

    @offset.setter
    def offset(self, offset):
        self._offset = offset
        self.update()

    def sizeHint(self):
        return self.size()

    def hitButton(self, pos):
        return self.contentsRect().contains(pos)

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)

        rect = QRectF(0, 0, self.width(), self.height())
        background_color = self.checked_color if self.checked else self.unchecked_color
        painter.setBrush(QBrush(background_color))
        painter.setPen(Qt.NoPen)
        painter.drawRoundedRect(rect, self.height() / 2, self.height() / 2)

        handle_radius = (self.height() - 4) / 2
        handle_x = 2 + self.offset  # 直接访问属性
        handle_y = (self.height() - (handle_radius * 2)) / 2
        painter.setBrush(QBrush(self.handle_color))
        painter.drawEllipse(QPointF(handle_x + handle_radius, self.height() / 2),
                            handle_radius, handle_radius)

        # 设置文字字体和颜色
        font = QFont()
        font.setPointSize(10)
        painter.setFont(font)

        # 根据开关状态设置文字颜色
        if self.checked:
            text_color = QColor(255, 255, 255)  # 白色文字
        else:
            text_color = QColor(0, 0, 0)  # 黑色文字
        painter.setPen(text_color)

        # 根据开关状态绘制文字
        if self.checked:
            text = "运行中"
            text_x = self.width() / 2 - painter.fontMetrics().width(text) / 2
        else:
            text = "自动运行"
            text_x = self.width() / 2 - painter.fontMetrics().width(text) / 2

        text_y = self.height() / 2 + painter.fontMetrics().ascent() / 2
        painter.drawText(int(text_x), int(text_y), text)

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            self.checked = not self.checked
            self.animation.stop()
            if self.checked:
                self.animation.setStartValue(0)
                self.animation.setEndValue(self.width() - self.height())
            else:
                self.animation.setStartValue(self.width() - self.height())
                self.animation.setEndValue(0)
            self.animation.start()
            self.clicked.emit()

    clicked = pyqtSignal()  # 使用导入的 pyqtSignal

class LoginTool(QWidget):
    def __init__(self):
        super().__init__()
        self.resize(1200, 800)  # 初始窗口大小
        self.log_file_path = 'tsdm_sign_tools.log'
        self.last_log_size = 0  # 新增属性，记录上一次读取的文件大小
        self.logged_accounts = load_config().get('account_categories', {})
        # 初始化 sign_process 属性
        self.sign_process = None

        self.initUI()
        # 初始化时加载配置并刷新面板
        self.load_and_refresh()
        # 设置定时器，每秒更新一次日志
        self.timer = QTimer(self)
        self.timer.timeout.connect(self.update_log_display)
        self.timer.start(1000)

    def load_and_refresh(self):
        """加载配置文件并刷新面板显示"""
        self.load_configuration()
        self.display_logged_accounts()
        self.display_admin_scheduled_tasks()
        self.update_browser_version_display()

    def initUI(self):
        self.setWindowTitle("天使动漫论坛登录工具")

        # 软件标题
        title_label = QLabel("天使动漫论坛签到工具")
        title_label.setAlignment(Qt.AlignCenter)
        title_label.setStyleSheet("font-size: 24px; font-weight: bold;")

        # 用户信息表格
        self.user_table = QTableWidget()
        self.user_table.setColumnCount(8)  # 增加一列
        self.user_table.setHorizontalHeaderLabels(["用户", "cookie状态", "签到情况", "打工冷却", "功能", "功能", "功能", "删除"])
        self.user_table.horizontalHeader().setStretchLastSection(True)

        # 管理员身份计划任务部分
        admin_tasks_frame = QFrame()
        admin_tasks_layout = QVBoxLayout(admin_tasks_frame)
        admin_title_label = QLabel("管理员身份计划任务:")
        admin_title_label.setStyleSheet("font-weight: bold;")
        admin_tasks_layout.addWidget(admin_title_label)
        self.admin_tasks_list = QLabel()
        admin_tasks_layout.addWidget(self.admin_tasks_list)

        # 浏览器信息及按钮部分
        browser_info_frame = QFrame()
        browser_info_layout = QHBoxLayout(browser_info_frame)
        self.browser_version_label = QLabel()
        browser_info_layout.addWidget(self.browser_version_label)
        update_driver_button = QPushButton("更新驱动")
        update_driver_button.clicked.connect(self.update_driver)
        browser_info_layout.addWidget(update_driver_button)

        # 滑动式开关
        self.toggle_switch = ToggleSwitch()
        self.toggle_switch.clicked.connect(self.on_toggle_switch_clicked)
        browser_info_layout.addWidget(self.toggle_switch)

        # 初始化添加账号按钮为禁用状态
        self.add_account_button = QPushButton("添加账号")
        self.add_account_button.clicked.connect(self.show_login_browser)
        self.add_account_button.setEnabled(False)
        browser_info_layout.addWidget(self.add_account_button)

        clear_log_button = QPushButton("清空日志")
        clear_log_button.clicked.connect(self.clear_log)
        browser_info_layout.addWidget(clear_log_button)

        # 日志信息
        self.log_text_edit = QTextEdit()
        self.log_text_edit.setReadOnly(True)

        # 主布局
        main_layout = QVBoxLayout()
        main_layout.addWidget(title_label)
        main_layout.addWidget(self.user_table)
        main_layout.addWidget(admin_tasks_frame)
        main_layout.addWidget(browser_info_frame)
        main_layout.addWidget(self.log_text_edit)

        self.setLayout(main_layout)

    def load_configuration(self):
        self.config = load_config()
        self.logged_accounts = self.config.get("account_categories", {})
        self.browser_info = self.config.get("browser_info", {})
        self.admin_scheduled_tasks = self.config.get("scheduled_tasks", [])

        # 检查是否有账号信息，若没有则强制关闭开关
        if not self.logged_accounts:
            self.toggle_switch.checked = False
            self.toggle_switch._offset = 0
            self.toggle_switch.update()
        else:
            # 有账号信息时正常加载开关状态
            self.toggle_switch.checked = self.config.get("toggle_switch_state", False)
            if self.toggle_switch.checked:
                self.toggle_switch._offset = self.toggle_switch.width() - self.toggle_switch.height()
                self.toggle_switch.update()

        # 添加日志输出检测是否读取成功
        logger.info(f"浏览器信息: {self.browser_info}")  # 浏览器信息
        logger.info(f"账号信息: {self.logged_accounts}")  # 账号信息
        logger.info(f"计划任务信息: {self.admin_scheduled_tasks}")  # 管理员计划任务信息

        # 根据浏览器驱动信息启用或禁用添加账号按钮
        if self.browser_info.get('path') and self.browser_info.get('version'):
            self.add_account_button.setEnabled(True)
        else:
            self.add_account_button.setEnabled(False)

    def on_toggle_switch_clicked(self):
        if not self.logged_accounts:
            # 没有账号信息，强制关闭开关
            self.toggle_switch.checked = False
            self.toggle_switch._offset = 0
            self.toggle_switch.animation.stop()
            self.toggle_switch.animation.setStartValue(self.toggle_switch.width() - self.toggle_switch.height())
            self.toggle_switch.animation.setEndValue(0)
            self.toggle_switch.animation.start()
            QMessageBox.warning(self, "警告", "没有可用账号，无法开启自动功能。")
            logger.warning("没有可用账号，自动功能开启失败。")
        else:
            if self.toggle_switch.checked:
                logger.info("自动功能已开启")
                # 这里添加开启自动功能的逻辑
            else:
                logger.info("自动功能已关闭")
                # 这里添加关闭自动功能的逻辑

        # 保存滑动开关状态
        self.config["toggle_switch_state"] = self.toggle_switch.checked
        save_config(self.config)

    def update_browser_version_display(self):
        version = self.browser_info.get('version', '未知，请先更新驱动')
        self.browser_version_label.setText(f"驱动版本: {version}")

    def display_logged_accounts(self):
        self.user_table.setRowCount(0)
        current_hour = datetime.now().hour  # 获取当前小时
        row = 0
        for username, account_info in self.logged_accounts.items():
            self.user_table.insertRow(row)
            # 用户
            self.user_table.setItem(row, 0, QTableWidgetItem(username))
            # cookie 状态
            is_valid = account_info["is_cookie_valid"]
            status_text = "有效" if is_valid else "过期"
            self.user_table.setItem(row, 1, QTableWidgetItem(status_text))
            # 签到情况（这里先假设为固定值，可根据实际情况修改）
            self.user_table.setItem(row, 2, QTableWidgetItem("已签到"))
            # 打工冷却（这里先假设为固定值，可根据实际情况修改）
            self.user_table.setItem(row, 3, QTableWidgetItem("05:59:58"))
            # 签到按钮
            sign_button = QPushButton("签到")
            sign_button.clicked.connect(lambda _, u=username: self.start_sign_for_user(u))
            sign_button.setEnabled(is_valid and not (0 <= current_hour < 1))
            self.user_table.setCellWidget(row, 4, sign_button)
            # 打工按钮
            work_button = QPushButton("打工")
            work_button.clicked.connect(lambda _, u=username: self.start_work_for_user(u))
            work_button.setEnabled(is_valid)
            self.user_table.setCellWidget(row, 5, work_button)
            # 重登按钮
            re_login_button = QPushButton("重登")
            re_login_button.clicked.connect(lambda _, u=username: self.re_login(u))
            self.user_table.setCellWidget(row, 6, re_login_button)
            # 删除按钮
            delete_button = QPushButton("删除")
            delete_button.clicked.connect(lambda _, u=username: self.delete_account(u))
            self.user_table.setCellWidget(row, 7, delete_button)
            row += 1

    def delete_account(self, username):
        if username in self.logged_accounts:
            del self.logged_accounts[username]
            self.save_config_changes()
            self.load_and_refresh()
            logger.info(f"账号 {username} 已删除")

    def display_admin_scheduled_tasks(self):
        tasks_text = '\n'.join(self.admin_scheduled_tasks)
        self.admin_tasks_list.setText(tasks_text)

    def show_login_browser(self):
        show_login_browser(self)
        self.load_and_refresh()

    def add_account(self, username, cookies):
        self.logged_accounts[username] = {
            "cookies": cookies,
            "is_cookie_valid": True
        }

    def re_login(self, username):
        self.show_login_browser()

    def update_driver(self):
        update_result = update_geckodriver()
        if update_result is True:
            # 操作完成后加载配置并刷新面板
            self.load_and_refresh()
            QMessageBox.information(self, "更新成功", "浏览器驱动已成功更新。")
        elif update_result is False:
            QMessageBox.critical(self, "更新失败", "浏览器驱动更新失败，请查看日志。")

    def save_config_changes(self):
        self.config["account_categories"] = self.logged_accounts
        save_config(self.config)

    def start_sign_for_user(self, username):
        try:
            logger.info(f"为用户 {username} 启动签到")
            account_info = self.logged_accounts[username]
            cookies = account_info["cookie"]
            perform_sign(username, cookies)
        finally:
            pass

        self.load_and_refresh()

    def start_work_for_user(self, username):
        try:
            logger.info(f"为用户 {username} 启动打工")
            account_info = self.logged_accounts[username]
            cookies = account_info["cookie"]
            perform_work(username, cookies)
        finally:
            pass

        self.load_and_refresh()

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
            # 重置 last_log_size 为 0
            self.last_log_size = 0


if __name__ == "__main__":
    app = QApplication(sys.argv)
    login_tool = LoginTool()
    login_tool.show()
    sys.exit(app.exec_())