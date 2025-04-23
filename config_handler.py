import os
import json
import logging

# 配置日志
logger = logging.getLogger('tsdm_sign_tools')
CONFIG_FILE = 'config.json'

def load_config():
    """
    加载配置文件，若文件不存在，返回默认配置。
    """
    try:
        if os.path.exists(CONFIG_FILE):
            with open(CONFIG_FILE, 'r', encoding='utf-8') as f:
                config = json.load(f)
                # 确保必要字段存在
                if "account_categories" not in config:
                    config["account_categories"] = {}
                if "browser_info" not in config:
                    config["browser_info"] = {}
                if "scheduled_tasks" not in config:
                    config["scheduled_tasks"] = []
                return config
        else:
            logger.info(f"{CONFIG_FILE} 文件不存在，将使用默认配置。")
            return {
                "account_categories": {},
                "browser_info": {},
                "scheduled_tasks": []
            }
    except Exception as e:
        logger.error(f"加载配置文件 {CONFIG_FILE} 时出错: {e}")
        return {
            "account_categories": {},
            "browser_info": {},
            "scheduled_tasks": []
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

def update_browser_info(browser_info):
    """
    更新浏览器信息。
    """
    config = load_config()
    config["browser_info"] = browser_info
    save_config(config)

def update_scheduled_tasks(scheduled_tasks):
    """
    更新计划任务信息。
    """
    config = load_config()
    config["scheduled_tasks"] = scheduled_tasks
    save_config(config)

def update_account_info(username, cookies, is_valid=True, last_sign_date="", last_work_time=""):
    """
    更新用户账户信息。
    """
    config = load_config()
    account_categories = config.get("account_categories", {})
    account_categories[username] = {
        "cookies": cookies,
        "is_cookie_valid": is_valid,
        "last_sign_date": last_sign_date,
        "last_work_time": last_work_time
    }
    config["account_categories"] = account_categories
    save_config(config)