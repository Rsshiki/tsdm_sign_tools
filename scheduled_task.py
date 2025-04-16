import re
import sys
import subprocess
from datetime import timedelta

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
        
        # 以管理员权限执行命令创建任务
        subprocess.run(
            command,
            shell=True,
            check=True,
            stdin=subprocess.DEVNULL,
            stdout=subprocess.PIPE,  # 捕获标准输出
            stderr=subprocess.PIPE   # 捕获标准错误
        )
        try:        
            if task_name:
                print(f"任务 {task_name}已创建")
                try:
                    subprocess.run(
                        ['schtasks', '/Query', '/TN', task_name],
                        shell=True,
                        check=True
                    )
                except subprocess.CalledProcessError:
                    print(f"验证任务 {task_name} 存在时出错")
                
        except subprocess.CalledProcessError as e:
            print(f"验证任务时出错: {e.stderr}")
            return None
    except subprocess.CalledProcessError as e:
        print(f"创建计划任务失败，命令: {command}")
        print(f"错误输出: {e.stderr.decode('gbk', errors='ignore')}")  # 打印错误信息
        return None

def clear_previous_scheduled_tasks():
    """清除之前创建的以 'TS_DmWork_' 开头的单次计划任务"""
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

        for task in matches:
            # 删除任务，注意任务名需要加上反斜杠
            full_task_name = f'\\{task}'
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
                print(f"删除任务 {full_task_name} 时出错: {e.stderr.decode('gbk', errors='ignore')}")
    except Exception as e:
        print(f"清除计划任务时发生未知错误: {e}")

def create_login_startup_task():
    """检查是否有用户登录后自动启动的计划任务，没有则创建"""
    task_name = "TSDM_Work_LoginStartup"
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
            print(f"开机启动任务 {task_name} 已创建。")
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
        print(f"用户登录后自动启动的计划任务 {task_name} 创建成功。")
        return task_name
    except subprocess.CalledProcessError as e:
        print(f"创建用户登录后自动启动的计划任务失败，需要管理员身份启动exe，命令: {command}")
        print(f"错误输出: {e.stderr.decode('gbk', errors='ignore')}")