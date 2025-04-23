import io
import os
import sys
import time
import winreg
import multiprocessing
from datetime import datetime, timedelta
from log_config import setup_logger
from config_handler import load_config, save_config
from browser_driver import update_geckodriver
from PyQt5.QtWidgets import (QApplication, QWidget, QVBoxLayout, QHBoxLayout, QLabel,
                             QPushButton, QFrame, QTextEdit, QMessageBox, QTableWidget,
                             QTableWidgetItem, QSystemTrayIcon, QMenu, QAction)
from PyQt5.QtCore import Qt, QTimer, QPropertyAnimation, QEasingCurve, QPointF, pyqtSignal, QRectF, QThread, QObject, pyqtProperty  # 导入 pyqtProperty
from PyQt5.QtGui import QPainter, QBrush, QColor, QFont, QIcon
from sign_handler import perform_sign
from work_handler import perform_work
from login_handler import show_login_browser
from browser_manager import close_browser_driver

# 配置日志
logger = setup_logger('tsdm_sign_tools.log')

LOGIN_URL = 'https://www.tsdm39.com/member.php?mod=logging&action=login'

class UpdateDriverThread(QThread):
    result_signal = pyqtSignal(int)  # 定义信号，用于发送更新结果

    def run(self):
        try:
            update_result = update_geckodriver()
            if update_result is None:  # 假设无需更新时返回 None
                self.result_signal.emit(0)
            elif update_result is True:
                self.result_signal.emit(1)
            else:
                self.result_signal.emit(-1)
        except Exception as e:
            # 可以记录异常日志
            self.result_signal.emit(-1)

class LogReaderThread(QThread):
    new_log_signal = pyqtSignal(str)  # 定义信号，用于发送新的日志内容

    def __init__(self, log_file_path, last_log_size):
        super().__init__()
        self.log_file_path = log_file_path
        self.last_log_size = last_log_size

    def run(self):
        if os.path.exists(self.log_file_path):
            try:
                with io.open(self.log_file_path, 'r', encoding='utf-8', errors='ignore') as f:
                    f.seek(0, os.SEEK_END)
                    current_size = f.tell()
                    if current_size > self.last_log_size:
                        f.seek(self.last_log_size)
                        new_log_content = ''.join([line.strip() + '\n' for line in f.readlines()])
                        self.new_log_signal.emit(new_log_content)  # 发送新日志内容
                        self.last_log_size = current_size
            except Exception as e:
                # 这里可以记录异常日志
                pass

class SignThread(QThread):
    # 定义信号，任务完成时发出
    finished = pyqtSignal(str)

    def __init__(self, username, cookies):
        super().__init__()
        self.username = username
        self.cookies = cookies

    def run(self):
        try:
            perform_sign(self.username, self.cookies)
            self.finished.emit(self.username)
        except Exception as e:
            # 可以在这里添加错误处理的日志
            pass

class AddAccountThread(QThread):
    finished = pyqtSignal()

    def __init__(self, parent):
        super().__init__()
        self.parent = parent

    def run(self):
        try:
            show_login_browser(self.parent)
            self.finished.emit()
        except Exception as e:
            # 可以在这里添加错误处理的日志
            pass

class WorkThread(QThread):
    finished = pyqtSignal(str)

    def __init__(self, username, cookies):
        super().__init__()
        self.username = username
        self.cookies = cookies

    def run(self):
        try:
            perform_work(self.username, self.cookies)
            self.finished.emit(self.username)
        except Exception as e:
            # 可以在这里添加错误处理的日志
            pass


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

    # 属性定义
    @pyqtProperty(float)
    def offset(self):
        return self._offset

    @offset.setter
    def offset(self, offset):
        self._offset = offset
        self.update()

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

    # UI 绘制
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
        text_color = QColor(255, 255, 255) if self.checked else QColor(0, 0, 0)
        painter.setPen(text_color)

        # 根据开关状态绘制文字
        text = "运行中" if self.checked else "自动运行"
        text_x = self.width() / 2 - painter.fontMetrics().width(text) / 2
        text_y = self.height() / 2 + painter.fontMetrics().ascent() / 2
        painter.drawText(int(text_x), int(text_y), text)

# 定义一个信号类，用于在子进程和主进程间通信
class RegistrySignal(QObject):
    result_signal = pyqtSignal(bool)

def add_startup_registry_worker(signal):
    try:
        app_path = sys.executable if getattr(sys, 'frozen', False) else __file__
        key = winreg.OpenKey(winreg.HKEY_CURRENT_USER,
                             r"Software\Microsoft\Windows\CurrentVersion\Run",
                             0, winreg.KEY_SET_VALUE)
        winreg.SetValueEx(key, "TSDM_Sign_Tools", 0, winreg.REG_SZ, app_path)
        winreg.CloseKey(key)
        signal.result_signal.emit(True)
    except Exception as e:
        print(f"添加开机启动项失败: {e}")
        signal.result_signal.emit(False)

def remove_startup_registry_worker(signal):
    try:
        key = winreg.OpenKey(winreg.HKEY_CURRENT_USER,
                             r"Software\Microsoft\Windows\CurrentVersion\Run",
                             0, winreg.KEY_ALL_ACCESS)
        winreg.DeleteValue(key, "TSDM_Sign_Tools")
        winreg.CloseKey(key)
        signal.result_signal.emit(True)
    except Exception as e:
        print(f"删除开机启动项失败: {e}")
        signal.result_signal.emit(False)

def is_startup_enabled():
    try:
        key = winreg.OpenKey(winreg.HKEY_CURRENT_USER,
                             r"Software\Microsoft\Windows\CurrentVersion\Run",
                             0, winreg.KEY_READ)
        try:
            winreg.QueryValueEx(key, "TSDM_Sign_Tools")
            winreg.CloseKey(key)
            return True
        except OSError:
            winreg.CloseKey(key)
            return False
    except Exception as e:
        print(f"检查开机启动项状态失败: {e}")
        return False

class LoginTool(QWidget):
    def __init__(self):
        super().__init__()
        self._init_config()
        self.setFixedWidth(937)
        self._init_timers()
        self.init_startup_switch()
        self._init_ui()
        self.is_automation_running = False
        self.task_queue = []  # 任务队列
        self.is_task_running = False  # 任务锁
        self.log_reader_thread = None  # 日志读取线程
        self.current_task_index = -1  # 新增：当前任务的索引
        self.registry_signal = RegistrySignal()
        self.registry_signal.result_signal.connect(self.handle_registry_result)
        self.load_and_refresh() # 初始化开机启动开关按钮
        self.init_tray_icon()   # 初始化系统托盘


    def init_startup_switch(self):
        self.startup_button = QPushButton(self)
        self.update_startup_button_text()
        self.startup_button.clicked.connect(self.toggle_startup)
        
    def update_startup_button_text(self):
        if is_startup_enabled():
            self.startup_button.setText("开机启动: 开启")
        else:
            self.startup_button.setText("开机启动: 关闭")

    # 初始化相关
    def init_tray_icon(self):
        # 获取图标路径
        icon_path = self.get_icon_path('app_icon.ico')
        # 创建系统托盘图标
        self.tray_icon = QSystemTrayIcon(self)
        # 替换为你的图标路径
        self.tray_icon.setIcon(QIcon(icon_path))

        # 创建菜单
        tray_menu = QMenu(self)

        # 创建显示窗口的动作
        show_action = QAction("显示窗口", self)
        show_action.triggered.connect(self.showNormal)
        tray_menu.addAction(show_action)

        # 创建退出程序的动作
        quit_action = QAction("退出", self)
        quit_action.triggered.connect(self.quit_app)
        tray_menu.addAction(quit_action)

        # 将菜单设置给系统托盘图标
        self.tray_icon.setContextMenu(tray_menu)

        # 显示系统托盘图标
        self.tray_icon.show()

    def get_icon_path(self, filename):
        if getattr(sys, 'frozen', False):
            # 如果是打包后的程序
            base_path = sys._MEIPASS
        else:
            # 如果是未打包的程序
            base_path = os.path.dirname(os.path.abspath(__file__))
        return os.path.join(base_path, filename)

    def quit_app(self):
        # 确保程序完全退出
        self.tray_icon.hide()
        QApplication.quit()

    def closeEvent(self, event):
        # 重写关闭事件，最小化到系统托盘而不是关闭程序
        event.ignore()
        self.hide()
        self.tray_icon.showMessage(
            "程序已最小化",
            "程序已最小化到系统托盘，右键点击图标进行操作。",
            QSystemTrayIcon.Information,
            2000
        )

    def changeEvent(self, event):
        # 处理窗口状态变化事件
        if event.type() == event.WindowStateChange:
            if self.isMinimized():
                event.ignore()
                self.hide()
                self.tray_icon.showMessage(
                    "程序已最小化",
                    "程序已最小化到系统托盘，右键点击图标进行操作。",
                    QSystemTrayIcon.Information,
                    2000
                )
        super().changeEvent(event)

    def _init_config(self):
        self.resize(937, 800)  # 初始窗口大小，长度比下面表格所有列加起来多57，就刚好能显示所有列
        self.log_file_path = 'tsdm_sign_tools.log'
        self.last_log_size = 0  # 新增属性，记录上一次读取的文件大小
        self.config = load_config()
        self.logged_accounts = self.config.get('account_categories', {})
        self.browser_info = self.config.get("browser_info", {})
        self.admin_scheduled_tasks = self.config.get("scheduled_tasks", [])
        self.current_time = datetime.now()

    def _init_timers(self):
        # 合并时间获取逻辑到一个定时器中
        self.time_update_timer = QTimer(self)
        self.time_update_timer.timeout.connect(self.update_all_time_dependent_info)
        self.time_update_timer.start(1000)

        # 日志定时器
        self.timer = QTimer(self)
        self.timer.timeout.connect(self.update_log_display)
        self.timer.start(1000)

    def start_log_reader(self):
        if self.log_reader_thread and self.log_reader_thread.isRunning():
            return
        self.log_reader_thread = LogReaderThread(self.log_file_path, self.last_log_size)
        self.log_reader_thread.new_log_signal.connect(self.update_log_display_ui)
        self.log_reader_thread.start()

    def update_log_display_ui(self, new_log_content):
        self.log_text_edit.insertPlainText(new_log_content)
        self.last_log_size += len(new_log_content.encode('utf-8'))
        self.log_text_edit.moveCursor(self.log_text_edit.textCursor().End)

    def _init_ui(self):
        self.setWindowTitle("天使动漫论坛登录工具")
        main_layout = QVBoxLayout()

        self.user_table = self._create_user_table()
        main_layout.addWidget(self.user_table)
        main_layout.addWidget(self._create_admin_tasks_frame())
        browser_info_frame = self._create_browser_info_frame()
        main_layout.addWidget(browser_info_frame)

        # 将开机启动开关按钮添加到浏览器信息框架布局中
        browser_info_frame.layout().addWidget(self.startup_button)

        self.log_text_edit = QTextEdit()
        self.log_text_edit.setReadOnly(True)
        main_layout.addWidget(self.log_text_edit)

        self.setLayout(main_layout)

    def toggle_startup(self):
        if is_startup_enabled():
            process = multiprocessing.Process(target=remove_startup_registry_worker, args=(self.registry_signal,))
            process.start()
        else:
            process = multiprocessing.Process(target=add_startup_registry_worker, args=(self.registry_signal,))
            process.start()

    def handle_registry_result(self, success):
        if success:
            self.update_startup_button_text()
        else:
            QMessageBox.critical(self, "错误", "注册表操作失败，请检查权限或稍后重试。")

    # UI 创建工具方法
    def _create_user_table(self):
        table = QTableWidget()
        table.setColumnCount(8)
        table.setHorizontalHeaderLabels(["用户", "cookie状态", "签到情况", "打工冷却", "功能", "功能", "功能", "删除"])
        # 隐藏表格线
        table.setShowGrid(False)
        table.horizontalHeader().setStretchLastSection(True)
        # 设置每列的固定宽度
        column_widths = [120, 120, 120, 120, 100, 100, 100, 100]
        for col, width in enumerate(column_widths):
            table.setColumnWidth(col, width)
        # 设置选择行为为无选择，禁止选中表格项
        table.setSelectionMode(QTableWidget.NoSelection)
        table.setEditTriggers(QTableWidget.NoEditTriggers)

        return table

    def _create_admin_tasks_frame(self):
        frame = QFrame()
        layout = QVBoxLayout(frame)
        title_label = QLabel("管理员身份计划任务:")
        title_label.setStyleSheet("font-weight: bold;")
        layout.addWidget(title_label)
        self.admin_tasks_list = QLabel()
        layout.addWidget(self.admin_tasks_list)
        return frame

    def _create_browser_info_frame(self):
        frame = QFrame()
        layout = QHBoxLayout(frame)
        self.browser_version_label = QLabel()
        layout.addWidget(self.browser_version_label)

        update_driver_button = QPushButton("更新驱动")
        update_driver_button.clicked.connect(self.update_driver)
        layout.addWidget(update_driver_button)
        
        self.toggle_switch = ToggleSwitch()
        self.toggle_switch.clicked.connect(self.on_toggle_switch_clicked)
        layout.addWidget(self.toggle_switch)

        self.add_account_button = QPushButton("添加账号")
        self.add_account_button.clicked.connect(self.show_login_browser)
        self._update_add_account_button_state()
        layout.addWidget(self.add_account_button)

        clear_log_button = QPushButton("清空日志")
        clear_log_button.clicked.connect(self.clear_log)
        layout.addWidget(clear_log_button)

        self.clock_label = QLabel()
        self.clock_label.setAlignment(Qt.AlignCenter)
        self.clock_label.setStyleSheet("font-size: 18px;")
        layout.addWidget(self.clock_label)

        return frame

    def load_and_refresh(self):
        """加载配置文件并刷新面板显示"""
        self.load_configuration()
        self.display_logged_accounts()
        self.display_admin_scheduled_tasks()
        self.update_browser_version_display()

        # 检查开关状态并触发自动功能
        if self.toggle_switch.checked:
            self.is_automation_running = True
            # 触发一次任务检查，确保自动任务开始执行
            self.update_all_time_dependent_info()

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

        # 添加日志输出检测是否读取成功(可以作为开场）

        self._update_add_account_button_state()

    def _update_add_account_button_state(self):
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
                self.is_automation_running = True
            else:
                logger.info("自动功能已关闭")
                self.is_automation_running = False

        # 保存滑动开关状态
        self.config["toggle_switch_state"] = self.toggle_switch.checked
        save_config(self.config)

    def update_driver(self):
        self.update_driver_thread = UpdateDriverThread()
        self.update_driver_thread.result_signal.connect(self.handle_update_result)
        self.update_driver_thread.start()

    def handle_update_result(self, result_code):
        if result_code == 1:
            # 操作完成后加载配置并刷新面板
            self.load_and_refresh()
            QMessageBox.information(self, "更新成功", "浏览器驱动已成功更新。")
        elif result_code == 0:
            QMessageBox.information(self, "无需更新", "当前 geckodriver 已经是最新版本，无需更新。")
        elif result_code == -1:
            QMessageBox.critical(self, "更新失败", "浏览器驱动更新失败，请查看日志。")

    def show_login_browser(self):
        self.add_account_thread = AddAccountThread(self)
        self.add_account_thread.finished.connect(self.load_and_refresh)
        self.add_account_thread.start()

    def delete_account(self, username):
        if username in self.logged_accounts:
            del self.logged_accounts[username]
            self.save_config_changes()
            self.load_and_refresh()
            logger.info(f"账号 {username} 已删除")

    def start_sign_for_user(self, username, callback=None):
        logger.info(f"为用户 {username} 启动签到")
        account_info = self.logged_accounts[username]
        cookies = account_info["cookie"]
        self.sign_thread = SignThread(username, cookies)
        if callback:
            self.sign_thread.finished.connect(lambda: (callback(), self.load_and_refresh()))
        else:
            self.sign_thread.finished.connect(self.load_and_refresh)
        self.sign_thread.start()

    def start_work_for_user(self, username, callback=None):
        logger.info(f"为用户 {username} 启动打工")
        account_info = self.logged_accounts[username]
        cookies = account_info["cookie"]
        self.work_thread = WorkThread(username, cookies)
        if callback:
            self.work_thread.finished.connect(lambda: (callback(), self.load_and_refresh()))
        else:
            self.work_thread.finished.connect(self.load_and_refresh)
        self.work_thread.start()


    def task_complete(self):
        self.is_task_running = False  # 任务完成，解锁
        unique_tasks = []
        seen = set()
        for task in self.task_queue:
            if task not in seen:
                unique_tasks.append(task)
                seen.add(task)
        self.task_queue = unique_tasks

        # 检查任务队列是否为空，如果为空则关闭浏览器
        if not self.task_queue:
            logger.info("任务队列已清空，关闭浏览器进程")
            close_browser_driver()
    def clear_log(self):
        if os.path.exists(self.log_file_path):
            with open(self.log_file_path, 'w') as f:
                f.truncate(0)
            self.log_text_edit.clear()
            # 重置 last_log_size 为 0
            self.last_log_size = 0

    # 数据更新
    def update_browser_version_display(self):
        version = self.browser_info.get('version', '未知，请先更新驱动')
        self.browser_version_label.setText(f"驱动版本: {version}")

    def display_logged_accounts(self):
        self.user_table.setRowCount(0)
        current_date = self.current_time.strftime("%Y-%m-%d") 
        for row, (username, account_info) in enumerate(self.logged_accounts.items()):
            self.user_table.insertRow(row)
            # 用户
            self.user_table.setItem(row, 0, QTableWidgetItem(username))

            # cookie 状态
            is_valid = account_info["is_cookie_valid"]
            status_text = "有效" if is_valid else "过期"
            self.user_table.setItem(row, 1, QTableWidgetItem(status_text))

            # 签到情况
            last_sign_date = account_info.get("last_sign_date", "")
            sign_status = "今日已签到" if last_sign_date == current_date else "未签到"
            self.user_table.setItem(row, 2, QTableWidgetItem(sign_status))

            # 打工冷却
            cool_down_text = self.calculate_work_cool_down(account_info)
            self.user_table.setItem(row, 3, QTableWidgetItem(cool_down_text))

            # 签到按钮
            current_hour = self.current_time.hour
            sign_button = QPushButton("签到")
            sign_button.clicked.connect(lambda _, u=username: self.add_task_to_queue('sign', u))
            sign_button.setEnabled(is_valid and not (0 <= current_hour < 1))
            self.user_table.setCellWidget(row, 4, sign_button)

            # 打工按钮
            work_button = QPushButton("打工")
            work_button.clicked.connect(lambda _, u=username: self.add_task_to_queue('work', u))
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

    def add_task_to_queue(self, task_type, username):
        task = (task_type, username)
        if task not in self.task_queue:
            logger.info(f"添加 {username} 的 {task_type} 任务")
            self.task_queue.append(task)
            logger.info(f"更新任务队列: {self.task_queue}")
            self.execute_task_if_available()
    def update_all_time_dependent_info(self):
        # 每秒获取一次当前时间
        current_time = datetime.now()
        self.current_time = current_time
        current_time_str = current_time.strftime("%Y-%m-%d %H:%M:%S")

        # 更新时钟显示
        self.clock_label.setText(current_time_str)

        # 更新打工冷却时间
        for row in range(self.user_table.rowCount()):
            username_item = self.user_table.item(row, 0)
            if username_item:
                username = username_item.text()
                account_info = self.logged_accounts.get(username, {})
                new_cool_down_text = self.calculate_work_cool_down(account_info)
                cool_down_item = self.user_table.item(row, 3)
                if cool_down_item:
                    cool_down_item.setText(new_cool_down_text)
                else:
                    self.user_table.setItem(row, 3, QTableWidgetItem(new_cool_down_text))

                work_button = self.user_table.cellWidget(row, 5)
                if work_button:
                    is_valid = account_info.get("is_cookie_valid", False)
                    work_button.setEnabled(is_valid)

        self.user_table.viewport().update()

        # 自动化功能逻辑
        if self.is_automation_running:
            for username, account_info in self.logged_accounts.items():
                is_valid = account_info["is_cookie_valid"]
                current_date = self.current_time.strftime("%Y-%m-%d")
                last_sign_date = account_info.get("last_sign_date", "")
                sign_status = last_sign_date == current_date
                current_hour = self.current_time.hour
                cool_down_text = self.calculate_work_cool_down(account_info)

                # 输出日志，检查判断条件
                # logger.info(f"账号: {username}, 签到状态: {sign_status}, 当前小时: {current_hour}, 冷却时间: {cool_down_text}")

                # 自动签到逻辑
                if is_valid and not sign_status and not (0 <= current_hour < 1):
                    sign_task = ('sign', username)
                    if sign_task not in self.task_queue:
                        self.task_queue.append(sign_task)

                # 自动打工逻辑
                if is_valid and cool_down_text == "00:00:00":
                    work_task = ('work', username)
                    if work_task not in self.task_queue:
                        self.task_queue.append(work_task)

        # logger.info(f"更新任务队列: {self.task_queue}")
        self.execute_task_if_available()
        
    def execute_task_if_available(self):
        if self.task_queue and not self.is_task_running:
            # 不立即从队列中移除任务，只记录当前任务索引
            self.current_task_index += 1
            if self.current_task_index < len(self.task_queue):
                task_type, username = self.task_queue[self.current_task_index]
                logger.info(f"即将执行任务 {task_type} - {username}，当前任务队列: {self.task_queue}")
                self.is_task_running = True
                if task_type == 'sign':
                    logger.info(f"自动为用户 {username} 启动签到")
                    self.start_sign_for_user(username, callback=self.task_complete)
                elif task_type == 'work':
                    logger.info(f"自动为用户 {username} 启动打工")
                    self.start_work_for_user(username, callback=self.task_complete)
            else:
                # 若索引超出队列长度，重置索引
                self.current_task_index = -1

    def task_complete(self):
        self.is_task_running = False  # 任务完成，解锁
        if self.current_task_index >= 0 and self.current_task_index < len(self.task_queue):
            # 任务完成后，从队列中移除当前任务
            completed_task = self.task_queue.pop(self.current_task_index)
            logger.info(f"任务 {completed_task} 已完成，从队列中移除，当前任务队列: {self.task_queue}")
            # 由于移除了任务，需要调整当前索引
            self.current_task_index -= 1

        unique_tasks = []
        seen = set()
        for task in self.task_queue:
            if task not in seen:
                unique_tasks.append(task)
                seen.add(task)
        self.task_queue = unique_tasks

        # 检查任务队列是否为空，如果为空则关闭浏览器
        if not self.task_queue:
            logger.info("任务队列已清空，关闭浏览器进程")
            close_browser_driver()
            self.current_task_index = -1  # 队列清空，重置索引

        # 任务完成后，尝试执行下一个任务
        self.execute_task_if_available()

    def update_log_display(self): # 更新日志显示
        if os.path.exists(self.log_file_path):
            max_retries = 3
            retries = 0
            while retries < max_retries:
                try:
                    # 统一使用只读模式读取日志文件
                    with io.open(self.log_file_path, 'r', encoding='utf-8', errors='ignore') as f:
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

 # 其他工具方法
    def calculate_work_cool_down(self, account_info): # 计算打工冷却时间
        last_work_time_str = account_info.get("last_work_time", "")
        if last_work_time_str:
            try:
                last_work_time = datetime.strptime(last_work_time_str, "%Y-%m-%d %H:%M:%S")
                cool_down_end_time = last_work_time + timedelta(hours=6)
                remaining_time = cool_down_end_time - self.current_time
                if remaining_time.total_seconds() > 0:
                    total_seconds = int(remaining_time.total_seconds()) + (1 if remaining_time.microseconds > 0 else 0)
                    hours = total_seconds // 3600
                    minutes = (total_seconds % 3600) // 60
                    seconds = total_seconds % 60
                    return f"{hours:02d}:{minutes:02d}:{seconds:02d}"
            except ValueError:
                logger.error(f"解析 last_work_time {last_work_time_str} 时出错，格式可能不正确")
        return "00:00:00"

    def display_admin_scheduled_tasks(self):
        tasks_text = '\n'.join(self.admin_scheduled_tasks)
        self.admin_tasks_list.setText(tasks_text)

    def add_account(self, username, cookies):
        self.logged_accounts[username] = {
            "cookies": cookies,
            "is_cookie_valid": True
        }

    def re_login(self, username):
        self.show_login_browser()

    def save_config_changes(self):
        self.config["account_categories"] = self.logged_accounts
        save_config(self.config)


    def closeEvent(self, event):
        """
        重写关闭事件方法，在主窗口关闭时关闭浏览器
        """
        try:
            logger.info("主程序即将关闭，尝试关闭浏览器进程")
            close_browser_driver()
            logger.info("浏览器进程已成功关闭")
        except Exception as e:
            logger.error(f"主程序关闭时，关闭浏览器进程出错: {e}")
        
        # 接受关闭事件，让主窗口正常关闭
        event.accept()

if __name__ == "__main__":
    app = QApplication(sys.argv)
    login_tool = LoginTool()
    login_tool.show()
    sys.exit(app.exec_())