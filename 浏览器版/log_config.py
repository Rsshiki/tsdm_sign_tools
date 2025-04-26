# -*- coding: utf-8 -*-
import os
import sys
import logging

def setup_logger(log_file_name):
    # 判断程序是否被打包
    if getattr(sys, 'frozen', False):
        # 如果是打包后的程序，使用 sys._MEIPASS 所在目录
        base_path = os.path.dirname(sys.executable)
    else:
        # 如果是未打包的程序，使用当前脚本所在目录
        base_path = os.path.dirname(os.path.abspath(__file__))
    # 构建日志文件的完整路径
    log_file_path = os.path.join(base_path, log_file_name)
    # 创建日志记录器，使用固定名称避免不同模块获取不同实例
    logger = logging.getLogger('tsdm_sign_logger')
    # 禁用日志传播
    logger.propagate = False
    logger.setLevel(logging.INFO)

    # 定义日志格式
    formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')

    has_stream_handler = any(isinstance(handler, logging.StreamHandler) for handler in logger.handlers)
    if not has_stream_handler:
        stream_handler = logging.StreamHandler()
        stream_handler.setFormatter(formatter)
        logger.addHandler(stream_handler)
    has_file_handler = any(isinstance(handler, logging.FileHandler) for handler in logger.handlers)
    if not has_file_handler:
        # 使用新构建的日志文件路径
        file_handler = logging.FileHandler(log_file_path, mode='a', encoding='utf-8')
        file_handler.setFormatter(formatter)
        logger.addHandler(file_handler)
    return logger