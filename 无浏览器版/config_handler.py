import os
import sys
import json
import logging

# 配置日志
logger = logging.getLogger('tsdm_sign_tools')


# 动态获取基础路径
if getattr(sys, 'frozen', False):
    # 如果是打包后的程序，获取 exe 所在目录
    base_path = os.path.dirname(sys.executable)
else:
    # 如果是未打包的程序，使用当前脚本所在目录
    base_path = os.path.dirname(os.path.abspath(__file__))

# 构建配置文件的完整路径
CONFIG_FILE = os.path.join(base_path, 'login_info.json')

def load_config():
    """
    加载配置文件，若文件不存在，返回包含 toggle_switch_state 的默认配置。
    """
    try:
        if os.path.exists(CONFIG_FILE):
            with open(CONFIG_FILE, 'r', encoding='utf-8') as f:
                config = json.load(f)
            # 确保 toggle_switch_state 字段存在
            if isinstance(config, list):
                # 如果配置是列表，将其转换为包含 accounts 和 toggle_switch_state 的字典
                new_config = {
                    "accounts": config,
                    "toggle_switch_state": False
                }
                config = new_config
            elif isinstance(config, dict):
                config.setdefault("toggle_switch_state", False)
            return config
        else:
            logger.info(f"{CONFIG_FILE} 文件不存在，将使用默认配置。")
            return {
                "accounts": [],
                "toggle_switch_state": False
            }
    except Exception as e:
        logger.error(f"加载配置文件 {CONFIG_FILE} 时出错: {e}")
        return {
            "accounts": [],
            "toggle_switch_state": False
        }

def save_config(config):
    """
    保存配置文件。
    """
    try:
        with open(CONFIG_FILE, 'w', encoding='utf-8') as f:
            json.dump(config, f, ensure_ascii=False, indent=4)
        logger.info("配置文件保存成功")
    except Exception as e:
        logger.error(f"保存配置文件 {CONFIG_FILE} 时出错: {e}")

def update_account_info(username, cookies, is_valid=True, last_sign_date="", last_work_time=""):
    """
    更新用户账户信息。
    """
    config = load_config()
    accounts = config.get("accounts", [])
    account_found = False
    for account in accounts:
        if account["username"] == username:
            account["cookies"] = cookies
            account["is_valid"] = is_valid
            account["last_sign_date"] = last_sign_date
            account["last_work_time"] = last_work_time
            account_found = True
            break
    if not account_found:
        new_account = {
            "base_url": "https://www.tsdm39.com/",
            "username": username,
            "password": "",  # 若没有密码更新，可保持为空
            "last_sign_date": last_sign_date,
            "last_work_time": last_work_time,
            "is_valid": is_valid,
            "cookies": cookies
        }
        accounts.append(new_account)
    config["accounts"] = accounts
    save_config(config)