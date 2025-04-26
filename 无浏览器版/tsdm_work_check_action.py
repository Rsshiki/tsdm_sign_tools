import requests
import json
import re
from datetime import datetime, timedelta
import time
import random
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

def check_work_status(username):
    url = 'https://www.tsdm39.com/plugin.php?id=np_cliworkdz:work'

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
                logger.error(f"未找到 {username} 的登录信息，请检查。")
                return None
        else:
            logger.error("login_info.json 格式错误，应为列表。")
            return None

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
        invalid_cookie_msg = "请先登录再进行点击任务"
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
            return None

        # 提取等待时间
        pattern = r"您需要等待(\d+)小时(\d+)分钟(\d+)秒后即可进行。"
        match = re.search(pattern, response.text)
        if match:
            hours = int(match.group(1))
            minutes = int(match.group(2))
            seconds = int(match.group(3))
            wait_time = timedelta(hours=hours, minutes=minutes, seconds=seconds)

            # 先减去 6 小时，再加上等待时间得到上次打工时间
            now = datetime.now()
            six_hours_ago = now - timedelta(hours=6)
            last_work_time = six_hours_ago + wait_time

            # 转换为字符串格式
            last_work_time_str = last_work_time.strftime("%Y-%m-%d %H:%M:%S")

            # 更新 login_info.json 中对应用户名的 last_work_time
            for info in all_login_info:
                if info["username"] == username:
                    info["last_work_time"] = last_work_time_str
                    break

            # 保存更新后的登录信息到 login_info.json
            with open('login_info.json', 'w') as file:
                config_data['accounts'] = all_login_info
                json.dump(config_data, file, indent=4)

            logger.info(f"{username} 已打过工，正在冷却状态。")
            return None

        # 获取新的 cookie
        new_cookies = session.cookies.get_dict()
        # logger.info("新的 Cookie:", new_cookies)
        # 合并新旧 cookies
        merged_cookies = cookies_dict.copy()
        merged_cookies.update(new_cookies)

        # 将合并后的 cookies 转换为符合 Cookie 请求头格式的字符串
        cookie_header_str = "; ".join([f"{key}={value}" for key, value in merged_cookies.items()])

        # logger.info(f"{username} 的 Cookie 已更新。")
        return cookie_header_str

    except FileNotFoundError:
        logger.info("未找到 login_info.json 文件。")
        return None
    except requests.RequestException as e:
        logger.error(f"请求出错: {e}")
        return None

def perform_work(username):
    # 调用补全cookie函数获取合并后的Cookie字符串
    cookie_header_str = check_work_status(username)
    if cookie_header_str is None:
        return
    if not cookie_header_str:
        logger.error("未获取到有效的Cookie字符串，无法继续操作。")
        return

    # 定义点广告的 URL
    ad_url = 'https://www.tsdm39.com/plugin.php?id=np_cliworkdz:work'

    # 定义点广告的请求头
    ad_headers = {
        'Accept': '*/*',
        'Accept-Encoding': 'gzip, deflate, br, zstd',
        'Accept-Language': 'zh-CN,zh;q=0.9,en;q=0.8,en-GB;q=0.7,en-US;q=0.6',
        'Connection': 'keep-alive',
        'Content-Type': 'application/x-www-form-urlencoded',
        'Cookie': cookie_header_str,
        'Host': 'www.tsdm39.com',
        'Origin': 'https://www.tsdm39.com',
        'Referer': 'https://www.tsdm39.com/plugin.php?id=np_cliworkdz:work',
        'Sec-Fetch-Dest': 'empty',
        'Sec-Fetch-Mode': 'cors',
        'Sec-Fetch-Site': 'same-origin',
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/135.0.0.0 Safari/537.36 Edg/135.0.0.0',
        'X-Requested-With': 'XMLHttpRequest',
        'sec-ch-ua': '"Microsoft Edge";v="135", "Not-A.Brand";v="8", "Chromium";v="135"',
        'sec-ch-ua-mobile': '?0',
        'sec-ch-ua-platform': 'Windows'
    }

    # 定义点广告的查询字符串参数
    ad_params = {
        'id': 'np_cliworkdz:work'
    }

    # 定义点广告的表单数据
    ad_data = {
        'act': 'clickad'
    }

    while True:
        # 每次请求前更新 s_gkr8_682f_lastact
        cookie_header_str = update_lastact(cookie_header_str)
        ad_headers['Cookie'] = cookie_header_str

        try:
            # 发送点广告请求
            ad_session = requests.Session()
            ad_response = ad_session.post(ad_url, headers=ad_headers, params=ad_params, data=ad_data)
            ad_response.raise_for_status()

            logger.info("点广告请求成功，响应状态码: %d", ad_response.status_code)
            # 打印响应内容
            ad_response_text = ad_response.text.strip()
            logger.info("点广告响应内容:", ad_response_text)

            if ad_response_text == "6":
                logger.info("点广告获得返回值 6，开始打工请求。")
                break
            elif ad_response_text in ["1", "2", "3", "4", "5"]:
                # 生成 1 - 2 秒之间的随机间隔时间
                sleep_time = random.uniform(1, 2)
                logger.info(f"点广告返回值为 {ad_response_text}，等待 {sleep_time:.3f} 秒后继续请求。")
                time.sleep(sleep_time)
            else:
                logger.error(f"点广告收到意外返回值 {ad_response_text}，停止操作。")
                return

        except requests.RequestException as e:
            logger.error(f"点广告请求出错: {e}")
            return

    # 定义打工的 URL
    work_url = 'https://www.tsdm39.com/plugin.php?id=np_cliworkdz:work'

    # 定义打工的请求头
    work_headers = {
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7',
        'Accept-Encoding': 'gzip, deflate, br, zstd',
        'Accept-Language': 'zh-CN,zh;q=0.9,en;q=0.8,en-GB;q=0.7,en-US;q=0.6',
        'Cache-Control': 'max-age=0',
        'Connection': 'keep-alive',
        'Content-Type': 'application/x-www-form-urlencoded',
        'Cookie': cookie_header_str,
        'Host': 'www.tsdm39.com',
        'Origin': 'https://www.tsdm39.com',
        'Referer': 'https://www.tsdm39.com/plugin.php?id=np_cliworkdz:work',
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

    # 打工请求前更新 s_gkr8_682f_lastact
    cookie_header_str = update_lastact(cookie_header_str)
    work_headers['Cookie'] = cookie_header_str

    # 定义打工的查询字符串参数
    work_params = {
        'id': 'np_cliworkdz:work'
    }

    # 定义打工的表单数据
    work_data = {
        'act': 'getcre'
    }

    try:
        # 发送打工请求
        work_session = requests.Session()
        work_response = work_session.post(work_url, headers=work_headers, params=work_params, data=work_data)
        work_response.raise_for_status()

        logger.info("打工请求成功，响应状态码: %d", work_response.status_code)

        target_content = '恭喜，您已经成功领取了奖励天使币'
        if target_content in work_response.text:
            # 再次检查签到状态
            recheck, _, _ = check_work_status(username)
            if recheck:
                logger.info("打工完成。")
            else:
                logger.info("打工出错。")

    except requests.RequestException as e:
        logger.error(f"打工请求出错: {e}")
        return False

if __name__ == "__main__":
    # 示例调用，可替换为实际的用户名
    username = "sscvex"
    result = check_work_status(username)
    if result:
        print("合并后的 Cookie 请求头字符串:", result)