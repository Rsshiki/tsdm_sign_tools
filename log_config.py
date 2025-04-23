# -*- coding: utf-8 -*-
import logging

def setup_logger(log_file_name):
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
        file_handler = logging.FileHandler(log_file_name, mode='a', encoding='utf-8')
        file_handler.setFormatter(formatter)
        logger.addHandler(file_handler)
    return logger