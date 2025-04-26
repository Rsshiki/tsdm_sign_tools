import requests
import json
from datetime import datetime
import random
import time
import re
from log_config import setup_logger
logger = setup_logger('tsdm_sign_tools.log')

def update_lastact(cookie_header_str):
    if "s_gkr8_682f_lastact" in cookie_header_str:
        current_timestamp = str(int(time.time()))
        start_index = cookie_header_str.find("s_gkr8_682f_lastact=")
        end_index = cookie_header_str.find(";", start_index)
        if end_index == -1:
            end_index = len(cookie_header_str)
        parts = cookie_header_str[start_index:end_index].split("%09", 1)
        if len(parts) > 1:
            new_lastact = "s_gkr8_682f_lastact=" + current_timestamp + "%09" + parts[1]
            cookie_header_str = cookie_header_str[:start_index] + new_lastact + cookie_header_str[end_index:]
    return cookie_header_str

def check_sign_status(username):
    url = 'https://www.tsdm39.com/plugin.php?id=dsu_paulsign:sign'
    try:
        # 从 login_info.json 中读取数据，注意读取 accounts 字段
        with open('login_info.json', 'r') as file:
            config_data = json.load(file)
            all_login_info = config_data.get('accounts', [])

        # 找到对应用户名的登录信息
        if isinstance(all_login_info, list):
            target_info = None
            for info in all_login_info:
                if info["username"] == username:
                    # 将 cookie 列表转换为字典
                    cookies_dict = {cookie["name"]: cookie["value"] for cookie in info["cookies"]}
                    target_info = info
                    break
            if target_info is None:
                logger.info(f"未找到 {username} 的登录信息，请检查。")
                return None, None, None
        else:
            logger.info("login_info.json 格式错误，应为列表。")
            return None, None, None

        # 定义请求头
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/135.0.0.0 Safari/537.36 Edg/135.0.0.0',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7',
            'Accept-Language': 'zh-CN,zh;q=0.9,en;q=0.8,en-GB;q=0.7,en-US;q=0.6',
            'Accept-Encoding': 'gzip, deflate, br, zstd',
            'Connection': 'keep-alive',
            'Host': 'www.tsdm39.com',
            'Referer': 'https://www.tsdm39.com/',
            'Sec-Fetch-Dest': 'document',
            'Sec-Fetch-Mode': 'navigate',
            'Sec-Fetch-Site': 'same-origin',
            'Sec-Fetch-User': '?1',
            'Upgrade-Insecure-Requests': '1',
            'sec-ch-ua': '"Microsoft Edge";v="135", "Not-A.Brand";v="8", "Chromium";v="135"',
            'sec-ch-ua-mobile': '?0',
            'sec-ch-ua-platform': '"Windows"'
        }

        # 创建会话对象并发送请求
        session = requests.Session()
        response = session.get(url, headers=headers, cookies=cookies_dict)
        response.raise_for_status()

        logger.info("请求成功，响应状态码: %d", response.status_code)

        # 检查 cookie 是否失效
        invalid_cookie_msg = "您需要先登录才能继续本操作"
        if invalid_cookie_msg in response.text:
            logger.info(f"{username} 的 cookie 已失效，更新登录信息。")
            for info in all_login_info:
                if info["username"] == username:
                    # 假设添加一个 'is_valid' 字段来表示 cookie 状态
                    info["is_valid"] = False
                    break
            # 保存更新后的登录信息到 login_info.json
            with open('login_info.json', 'w') as file:
                config_data['accounts'] = all_login_info
                json.dump(config_data, file, indent=4)
            return None, None, None

        # 获取当前时间
        now = datetime.now()
        hour = now.hour

        # 检查返回页面是否包含指定文本且当前时间不在 0 点 - 1 点
        target_text = "您今天已经签到过了或者签到时间还未开始"
        if target_text in response.text and not (0 <= hour < 1):
            logger.info("今日已签到")
            # 获取今日日期
            today_date = now.strftime("%Y-%m-%d")
            # 更新 login_info.json 中对应用户名的 last_sign_date
            for info in all_login_info:
                if info["username"] == username:
                    info["last_sign_date"] = today_date
                    break
            # 将更新后的信息写回 login_info.json
            with open('login_info.json', 'w') as file:
                config_data['accounts'] = all_login_info
                json.dump(config_data, file, indent=4)
            return True, None, None

        # 更灵活的正则表达式来搜索 formhash 的值
        formhash_pattern = r'<input\s+[^>]*name="formhash"\s+[^>]*value="([a-f0-9]+)"'
        match = re.search(formhash_pattern, response.text)
        formhash = None
        if match:
            formhash = match.group(1)
            logger.info(f"找到 formhash: {formhash}")
        else:
            logger.info("未找到 formhash")

        # 获取新的 cookie
        new_cookies = session.cookies.get_dict()
        # logger.info("新的 Cookie:", new_cookies)
        # 合并新旧 cookies
        merged_cookies = cookies_dict.copy()
        merged_cookies.update(new_cookies)

        # 将合并后的 cookies 转换为符合 Cookie 请求头格式的字符串
        cookie_header_str = "; ".join([f"{key}={value}" for key, value in merged_cookies.items()])

        return False, cookie_header_str, formhash

    except FileNotFoundError:
        logger.info("未找到 login_info.json 文件。")
        return None, None, None
    except requests.RequestException as e:
        logger.error(f"请求出错: {e}")
        return None, None, None


def perform_sign(username):
    sign_url = 'https://www.tsdm39.com/plugin.php?id=dsu_paulsign:sign&operation=qiandao&infloat=1&inajax=1'

    checked, cookie_header_str, formhash = check_sign_status(username)
    if checked is None:
        return
    if checked is True:
        return

    # 定义签到请求头
    sign_headers = {
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7',
        'Accept-Encoding': 'gzip, deflate, br, zstd',
        'Accept-Language': 'zh-CN,zh;q=0.9,en;q=0.8,en-GB;q=0.7,en-US;q=0.6',
        'Cache-Control': 'max-age=0',
        'Connection': 'keep-alive',
        'Content-Type': 'application/x-www-form-urlencoded',
        'Cookie': cookie_header_str,
        'Host': 'www.tsdm39.com',
        'Origin': 'https://www.tsdm39.com',
        'Referer': 'https://www.tsdm39.com/plugin.php?id=dsu_paulsign:sign',
        'Sec-Fetch-Dest': 'iframe',
        'Sec-Fetch-Mode': 'navigate',
        'Sec-Fetch-Site': 'same-origin',
        'Sec-Fetch-User': '?1',
        'Upgrade-Insecure-Requests': '1',
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/135.0.0.0 Safari/537.36 Edg/135.0.0.0',
        'sec-ch-ua': '"Microsoft Edge";v="135", "Not-A.Brand";v="8", "Chromium";v="135"',
        'sec-ch-ua-mobile': '?0',
        'sec-ch-ua-platform': '"Windows"'
    }

    # 打工请求前更新 s_gkr8_682f_lastact
    cookie_header_str = update_lastact(cookie_header_str)
    sign_headers['Cookie'] = cookie_header_str

    # 定义签到的查询字符串参数
    sign_params = {
        'id': 'dsu_paulsign:sign',
        'operation': 'qiandao',
        'infloat': '1',
        'inajax': '1',
    }

    # 可供选择的 qdxq 值列表
    qdxq_options = ['kx', 'ng', 'ym', 'wl', 'nu', 'ch', 'fd', 'yl', 'shuai']
    # 随机选择一个 qdxq 值
    random_qdxq = random.choice(qdxq_options)

    # 定义签到的表单数据
    sign_data = {
        'formhash': formhash,
        'qdxq': random_qdxq,
        'qdmode': '3',
        'todaysay': '',
        'fastreply': '1'
    }

    try:
        # 发送签到请求
        sign_session = requests.Session()
        sign_response = sign_session.post(sign_url, headers=sign_headers, params=sign_params, data=sign_data)
        sign_response.raise_for_status()

        logger.info("签到请求成功，响应状态码: %d", sign_response.status_code)

        # 再次检查签到状态
        recheck, _, _ = check_sign_status(username)
        if recheck:
            logger.info("签到成功。")
        else:
            logger.info("签到出错。")

    except requests.RequestException as e:
        logger.error(f"签到请求出错: {e}")


if __name__ == "__main__":
    # 示例调用，可替换为实际的用户名
    username = "vuiyu"
    perform_sign(username)