# import os
# import json
# from cryptography.fernet import Fernet
# import sys

# def get_file_path(file_name):
#     if getattr(sys, 'frozen', False):
#         # 获取 exe 所在目录
#         base_path = os.path.dirname(sys.executable)
#     else:
#         base_path = os.path.dirname(os.path.abspath(__file__))
#     return os.path.join(base_path, file_name)

# # 密钥文件路径
# KEY_FILE = get_file_path('encryption_key.key')

# # 配置文件路径
# CONFIG_FILE = get_file_path('tsdm502.json')

# # 检查密钥文件是否存在，如果不存在则生成并保存
# if not os.path.exists(KEY_FILE):
#     KEY = Fernet.generate_key()
#     with open(KEY_FILE, 'wb') as key_file:
#         key_file.write(KEY)
# else:
#     with open(KEY_FILE, 'rb') as key_file:
#         KEY = key_file.read()

# cipher_suite = Fernet(KEY)

# def encrypt_config(data):
#     """加密数据"""
#     return cipher_suite.encrypt(json.dumps(data).encode()).decode()

# def decrypt_config(encrypted_data):
#     """解密数据"""
#     return json.loads(cipher_suite.decrypt(encrypted_data.encode()).decode())

