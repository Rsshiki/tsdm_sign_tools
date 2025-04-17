import json
import os

CONFIG_FILE = "config.json"

def load_config():
    """
    加载配置文件，确保配置文件结构正确，包含 accounts 和 browser_info 字段。
    若文件不存在，返回默认配置。
    """
    try:
        if os.path.exists(CONFIG_FILE):
            with open(CONFIG_FILE, "r", encoding="utf-8") as f:
                config = json.load(f)
                # 确保 accounts 字段存在
                if "accounts" not in config:
                    config["accounts"] = {}
                # 确保 browser_info 字段存在
                if "browser_info" not in config:
                    config["browser_info"] = {}
                if "scheduled_tasks" not in config:
                    config["scheduled_tasks"] = []
                # 确保每个账号都有 is_cookie_valid 字段
                for account_info in config["accounts"].values():
                    if "is_cookie_valid" not in account_info:
                        account_info["is_cookie_valid"] = True
                return config
        else:
            print(f"{CONFIG_FILE} 文件不存在，将使用默认配置。")
            return {"accounts": {}, "browser_info": {}, "scheduled_tasks": []}
    except Exception as e:
        print(f"加载配置文件 {CONFIG_FILE} 时出错: {e}")
        return {"accounts": {}, "browser_info": {}, "scheduled_tasks": []}

def save_config(config):
    """
    将配置保存到文件，确保格式正确。
    """
    try:
        with open(CONFIG_FILE, "w", encoding="utf-8") as f:
            json.dump(config, f, ensure_ascii=False, indent=4)
    except Exception as e:
        print(f"保存配置文件 {CONFIG_FILE} 时出错: {e}")

def update_browser_info(browser_info):
    """
    更新配置文件中的浏览器信息。
    """
    config = load_config()
    config["browser_info"] = browser_info
    save_config(config)

def update_scheduled_tasks(task_names):
    """
    更新配置文件中的计划任务信息。
    """
    config = load_config()
    config["scheduled_tasks"] = task_names
    save_config(config)