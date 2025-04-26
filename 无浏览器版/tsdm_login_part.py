import requests
from bs4 import BeautifulSoup
import time
from PyQt5.QtWidgets import QApplication, QWidget, QVBoxLayout, QLabel, QLineEdit, QPushButton
from PyQt5.QtGui import QPixmap, QImage
from PyQt5.QtCore import QByteArray, Qt
import sys
from log_config import setup_logger
from config_handler import update_account_info

logger = setup_logger('tsdm_sign_tools.log')

class LoginWindow(QWidget):
    def __init__(self, session, username=None, password=None):
        super().__init__()
        self.session = session
        self.username = username
        self.password = password
        self.verification_code = ""
        self.img_label = None
        self.error_label = None
        self.initUI()

    def initUI(self):
        layout = QVBoxLayout()
        self.setLayout(layout)
        self.update_verification_code()

        # 用户名输入框
        self.username_label = QLabel('用户名:')
        self.username_input = QLineEdit()
        if self.username:
            self.username_input.setText(self.username)
        layout.addWidget(self.username_label)
        layout.addWidget(self.username_input)

        # 密码输入框
        self.password_label = QLabel('密码:')
        self.password_input = QLineEdit()
        self.password_input.setEchoMode(QLineEdit.Password)
        if self.password:
            self.password_input.setText(self.password)
        layout.addWidget(self.password_label)
        layout.addWidget(self.password_input)

        # 验证码输入框
        self.verification_label = QLabel('验证码:')
        self.verification_input = QLineEdit()
        layout.addWidget(self.verification_label)
        layout.addWidget(self.verification_input)

        # 错误提示标签
        self.error_label = QLabel('')
        self.error_label.setStyleSheet("color: red")
        layout.addWidget(self.error_label)

        # 提交按钮
        self.submit_button = QPushButton('提交')
        self.submit_button.clicked.connect(self.submit)
        layout.addWidget(self.submit_button)

        self.setWindowTitle('登录信息输入')
        self.show()

    def update_verification_code(self):
        login_url = 'https://www.tsdm39.com/member.php?mod=logging&action=login'
        base_url = 'https://www.tsdm39.com/'
        headers1 = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/135.0.0.0 Safari/537.36 Edg/135.0.0.0',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7',
            'Accept-Language': 'zh-CN,zh;q=0.9,en;q=0.8,en-GB;q=0.7,en-US;q=0.6',
        }
        try:
            response = self.session.get(login_url, headers=headers1)
            response.raise_for_status()
            soup = BeautifulSoup(response.text, 'html.parser')
            verify_img = soup.find('img', class_='tsdm_verify')
            if verify_img:
                verify_img_url = verify_img.get('src')
                if verify_img_url:
                    full_verify_img_url = base_url + verify_img_url if not verify_img_url.startswith('http') else verify_img_url
                    img_response = self.session.get(full_verify_img_url, headers=headers1)
                    img_response.raise_for_status()
                    img_data = img_response.content
                    qimage = QImage()
                    qimage.loadFromData(QByteArray(img_data))
                    pixmap = QPixmap.fromImage(qimage)
                    if self.img_label is None:
                        self.img_label = QLabel(self)
                        self.img_label.setPixmap(pixmap)
                        self.layout().insertWidget(0, self.img_label)
                        self.img_label.mousePressEvent = self.on_img_click
                    else:
                        self.img_label.setPixmap(pixmap)
        except requests.RequestException as e:
            logger.error(f"请求出错: {e}")

    def on_img_click(self, event):
        if event.button() == Qt.LeftButton:
            self.update_verification_code()

    def submit(self):
        login_url = 'https://www.tsdm39.com/member.php?mod=logging&action=login'
        base_url = 'https://www.tsdm39.com/'
        headers1 = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/135.0.0.0 Safari/537.36 Edg/135.0.0.0',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7',
            'Accept-Language': 'zh-CN,zh;q=0.9,en;q=0.8,en-GB;q=0.7,en-US;q=0.6',
        }
        self.username = self.username_input.text()
        self.password = self.password_input.text()
        self.verification_code = self.verification_input.text()
        try:
            response = self.session.get(login_url, headers=headers1)
            response.raise_for_status()
            soup = BeautifulSoup(response.text, 'html.parser')
            formhash_input = soup.find('input', {'name': 'formhash'})
            formhash = formhash_input.get('value') if formhash_input else ''
            main_message_div = soup.find('div', id=lambda x: x and x.startswith('main_messaqge_'))
            loginhash = main_message_div.get('id').split('main_messaqge_')[-1] if main_message_div else ''
            a1cookies = self.session.cookies.get_dict()
            if "s_gkr8_682f_lastact" in a1cookies:
                current_timestamp = str(int(time.time()))
                parts = a1cookies["s_gkr8_682f_lastact"].split("%09", 1)
                if len(parts) > 1:
                    new_lastact = current_timestamp + "%09" + parts[1]
                    a1cookies["s_gkr8_682f_lastact"] = new_lastact
            self.session.cookies.update(a1cookies)
            new_cookie = "; ".join([f"{key}={value}" for key, value in a1cookies.items()])
            headers2 = {
                'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7',
                'Accept-Encoding': 'gzip, deflate, br, zstd',
                'Accept-Language': 'zh-CN,zh;q=0.9,en;q=0.8,en-GB;q=0.7,en-US;q=0.6',
                'Cache-Control': 'max-age=0',
                'Connection': 'keep-alive',
                'Content-Type': 'application/x-www-form-urlencoded',
                'Cookie': new_cookie,
                'Host': 'www.tsdm39.com',
                'Origin': 'https://www.tsdm39.com',
                'Referer': 'https://www.tsdm39.com/member.php?mod=logging&action=login',
                'Sec-Fetch-Dest': 'document',
                'Sec-Fetch-Mode': 'navigate',
                'Sec-Fetch-Site': 'same-origin',
                'Sec-Fetch-User': '?1',
                'Upgrade-Insecure-Requests': '1',
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/135.0.0.0 Safari/537.36 Edg/135.0.0.0',
                'sec-ch-ua': '"Microsoft Edge";v="135", "Not-A.Brand";v="8", "Chromium";v="135"',
                'sec-ch-ua-mobile': '?0',
                'sec-ch-ua-platform': '"Windows"'
            }
            params = {
                'mod': 'logging',
                'action': 'login',
                'loginsubmit': 'yes',
                'handlekey': 'ls',
                'loginhash': loginhash
            }
            data = {
                'formhash': formhash,
                'referer': 'https://www.tsdm39.com/./',
                'loginfield': 'username',
                'username': self.username,
                'password': self.password,
                'tsdm_verify': self.verification_code,
                'questionid': 0,
                'answer': '',
                'loginsubmit': 'true'
            }
            cur_login_url = f'{base_url}/member.php?mod=logging&action=login&loginsubmit=yes&loginhash={loginhash}'
            login_response = self.session.post(cur_login_url, headers=headers2, params=params, data=data)
            login_response.raise_for_status()
            logger.info("登录请求已发送，响应状态码:", login_response.status_code)

            if "欢迎您回来" in login_response.text:
                logger.info("登录成功！")
                # with open('page_after_login.html', 'w', encoding='utf-8') as html_file:
                #     html_file.write(login_response.text)
                # logger.info("登录后的页面 HTML 已保存到 page_after_login.html")

                cookies_after_login = self.session.cookies.get_dict()
                cookies_list = []
                for key, value in cookies_after_login.items():
                    cookies_list.append({
                        "name": key,
                        "value": value
                    })

                # 调用 config_handler 中的方法更新账户信息
                update_account_info(
                    username=self.username,
                    cookies=cookies_list,
                    is_valid=True,
                    last_sign_date="",
                    last_work_time=""
                )

                logger.info("登录信息已更新到配置文件")
                self.close()
            else:
                logger.info("登录失败，请检查用户名、密码和验证码。")
                self.error_label.setText("登录失败，请检查用户名、密码和验证码。")
        except requests.RequestException as e:
            logger.error(f"请求出错: {e}")
            self.error_label.setText(f"请求出错: {e}")


if __name__ == "__main__":
    try:
        session = requests.Session()
        app = QApplication(sys.argv)
        login_window = LoginWindow(session)  # 确保传入 session
        sys.exit(app.exec_())
    except Exception as e:
        logger.error(f"发生未知错误: {e}")