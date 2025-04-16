import json
import os

CONFIG_FILE = "accounts.json"

def load_config():
    if os.path.exists(CONFIG_FILE):
        with open(CONFIG_FILE, "r", encoding="utf-8") as f:
            try:
                accounts = json.load(f)
                # 确保每个账号都有 is_cookie_valid 字段
                for account_info in accounts.values():
                    if "is_cookie_valid" not in account_info:
                        account_info["is_cookie_valid"] = True
                return accounts
            except json.JSONDecodeError:
                return {}
    return {}

def save_config(config):
    with open(CONFIG_FILE, "w", encoding="utf-8") as f:
        json.dump(config, f, ensure_ascii=False, indent=4)