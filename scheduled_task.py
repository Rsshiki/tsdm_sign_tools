import re
import sys
import ctypes
import subprocess
from datetime import timedelta
from config_handler import load_config, update_scheduled_tasks

def is_admin():
    try:
        return ctypes.windll.shell32.IsUserAnAdmin()
    except:
        return False

def create_scheduled_task(next_work_time):
    """创建Windows计划任务"""
    # 如果秒数大于 0，将时间向上进位到下一分钟
    if next_work_time.second > 0 or next_work_time.microsecond > 0:
        next_work_time = next_work_time + timedelta(minutes=1)
    next_work_time = next_work_time.replace(second=0, microsecond=0)

    # 生成任务名称（基于下次执行时间）
    task_name = f"TS_DmWork_{next_work_time.strftime('%Y%m%d%H%M00')}"
    # 转义路径中的特殊字符
    exe_path = sys.executable.replace("\\", "\\\\")
    # 构建schtasks命令，时间格式精确到秒
    st_time = next_work_time.strftime("%H:%M:00")
    sd_date = next_work_time.strftime("%Y-%m-%d")
    command = f'schtasks /Create /TN "{task_name}" /TR "{exe_path}" /SC ONCE /ST {st_time} /SD {sd_date}'

    try:
        # 清除之前创建的单次任务
        clear_previous_scheduled_tasks()
        
        # 直接执行命令创建任务，不额外指定管理员权限
        result = subprocess.run(
            command,
            shell=True,
            check=True,
            stdin=subprocess.DEVNULL,
            stdout=subprocess.PIPE,  # 捕获标准输出
            stderr=subprocess.PIPE   # 捕获标准错误
        )
        # print(f"任务 {task_name} 创建成功，输出信息: {result.stdout.decode('gbk', errors='ignore')}")

        if is_admin():
            config = load_config()
            scheduled_tasks = config["scheduled_tasks"]
            if task_name not in scheduled_tasks:
                scheduled_tasks.append(task_name)
            update_scheduled_tasks(scheduled_tasks)
        
        try:
            # 验证任务是否创建成功
            verify_result = subprocess.run(
                ['schtasks', '/Query', '/TN', task_name],
                shell=True,
                check=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE
            )
            print(f"{verify_result.stdout.decode('gbk', errors='ignore')}")
        except subprocess.CalledProcessError as e:
            print(f"验证任务 {task_name} 存在时出错: {e.stderr.decode('gbk', errors='ignore')}")
    except subprocess.CalledProcessError as e:
        print(f"创建计划任务失败，命令: {command}")
        print(f"错误输出: {e.stderr.decode('gbk', errors='ignore')}")  # 打印错误信息
        return None

def clear_previous_scheduled_tasks():
    """清除之前创建的以 'TS_DmWork_' 开头的单次计划任务，跳过管理员身份创建的任务"""
    config = load_config()
    admin_tasks = config["scheduled_tasks"]
    valid_admin_tasks = []
    failed_tasks = []  # 用于记录无法删除的任务

    try:
        # 查询所有计划任务
        result = subprocess.run(
            ['schtasks', '/Query', '/FO', 'LIST', '/V'],
            shell=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE
        )
        if result.returncode != 0:
            print(f"执行 schtasks /Query 命令出错: {result.stderr.decode('gbk', errors='ignore')}")
            return
        # 使用 gbk 解码并去除多余空白字符
        output = result.stdout.decode('gbk', errors='ignore')
        output = ' '.join(output.split())  # 将多个空白字符替换为一个空格

        # 正则表达式匹配任务名
        task_pattern = re.compile(r'任务名: \\(TS_DmWork_[^ ]+)')
        matches = task_pattern.findall(output)

        existing_tasks = set(matches)

        for task in admin_tasks:
            if task in existing_tasks:
                valid_admin_tasks.append(task)

        update_scheduled_tasks(valid_admin_tasks)

        for task in matches:
            if task in valid_admin_tasks:
                continue
            # 删除任务，注意任务名需要加上反斜杠
            full_task_name = f'\\{task}'
            # 修正删除命令，去掉多余的引号
            delete_command = f'schtasks /Delete /TN "{full_task_name}" /F'
            try:
                subprocess.run(
                    delete_command,
                    shell=True,
                    check=True,
                    stdin=subprocess.DEVNULL,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE
                )
            except subprocess.CalledProcessError as e:
                # print(f"删除任务 {full_task_name} 时出错: {e.stderr.decode('gbk', errors='ignore')}")
                if task not in admin_tasks:
                    failed_tasks.append(task)

        # 将无法删除且不在配置文件中的任务添加到配置文件
        if failed_tasks:
            new_scheduled_tasks = valid_admin_tasks + failed_tasks
            update_scheduled_tasks(new_scheduled_tasks)

    except Exception as e:
        print(f"清除计划任务时发生未知错误: {e}")

def create_login_startup_task():
    """检查是否有用户登录后自动启动的计划任务，没有则创建"""
    task_name = "TS_DmWork_LoginStartup"
    exe_path = sys.executable.replace("\\", "\\\\")
    command = f'schtasks /Create /TN "{task_name}" /TR "{exe_path}" /SC ONLOGON'

    try:
        # 检查任务是否已经存在
        result = subprocess.run(
            ['schtasks', '/Query', '/TN', task_name],
            shell=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE
        )
        if result.returncode == 0:
            print(f"开机启动任务已存在。")
            return task_name

        # 以管理员权限执行命令创建任务
        subprocess.run(
            command,
            shell=True,
            check=True,
            stdin=subprocess.DEVNULL,
            stdout=subprocess.PIPE,  # 捕获标准输出
            stderr=subprocess.PIPE   # 捕获标准错误
        )
        print(f"创建开机自动启动任务 {task_name} 创建成功。")

        if is_admin():
            config = load_config()
            scheduled_tasks = config["scheduled_tasks"]
            if task_name not in scheduled_tasks:
                scheduled_tasks.append(task_name)
            update_scheduled_tasks(scheduled_tasks)

        return task_name
    except subprocess.CalledProcessError as e:
        print(f"创建开机自动启动任务失败，需要管理员身份运行")
        print(f"错误输出: {e.stderr.decode('gbk', errors='ignore')}")