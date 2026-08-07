# MusicRate\backend\run.py 项目启动入口 - 替代原app.py的启动逻辑
import subprocess
import sys
import os
import time
import socket

# Windows终端UTF-8输出，防止emoji(✅❌)等字符GBK编码报错
if sys.platform == 'win32':
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')
    sys.stderr.reconfigure(encoding='utf-8', errors='replace')

# 添加这一行：自动设置正确的导入路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from backend import create_app
from backend.utils.db import init_base_tables

# 创建Flask应用实例
app = create_app()


def is_mysql_port_ready():
    """检查MySQL 3306端口是否可连接"""
    try:
        sock = socket.create_connection(('localhost', 3306), timeout=1)
        sock.close()
        return True
    except (ConnectionRefusedError, socket.timeout, OSError):
        return False


def wait_mysql_ready(max_wait=60):
    """等待MySQL端口就绪，最多等max_wait秒"""
    for i in range(max_wait // 2):
        time.sleep(2)
        if is_mysql_port_ready():
            print(f"MySQL服务已就绪（等待了{(i+1)*2}秒）")
            return True
    print(f"⚠️ MySQL服务启动超时（{max_wait}秒），尝试继续启动...")
    return False


def start_mysql_via_service():
    """尝试通过Windows服务启动MySQL"""
    try:
        result = subprocess.run(
            ['sc', 'query', 'MySQL80'],
            capture_output=True, text=True, encoding='gbk'
        )
        if "STATE" in result.stdout and "RUNNING" in result.stdout:
            print("MySQL服务已启动")
            return True
        # 尝试通过sc start启动
        ps_cmd = 'powershell -Command "Start-Process cmd -ArgumentList \'/c sc start MySQL80\' -Verb RunAs"'
        subprocess.run(ps_cmd, shell=True, capture_output=True, text=True)
        print("尝试通过MySQL80服务启动...")
        return wait_mysql_ready()
    except Exception as e:
        print(f"通过服务启动失败：{e}")
        return False


def start_mysql_via_mysqld():
    """直接启动mysqld进程（适用于移动硬盘等非系统安装的MySQL）"""
    # 根据项目所在盘符推算MySQL路径
    project_drive = os.path.splitdrive(os.path.abspath(__file__))[0]  # 如 U:
    mysqld_path = os.path.join(project_drive, os.sep, '__',
                                'app', 'MySQL', 'MySQL Server 8.0', 'bin', 'mysqld.exe')
    ini_path = os.path.join(project_drive, os.sep, '__',
                             'app', 'MySQL', 'MySQL Server 8.0', 'my.ini')

    if not os.path.exists(mysqld_path):
        print(f"⚠️ 未找到mysqld：{mysqld_path}")
        return False

    print(f"尝试直接启动mysqld：{mysqld_path}")
    try:
        # 以管理员权限启动mysqld，使用--defaults-file指定配置
        cmd = f'powershell -Command "Start-Process cmd -ArgumentList \'/c \\"{mysqld_path}\\" --defaults-file=\\"{ini_path}\\"\' -Verb RunAs"'
        subprocess.run(cmd, shell=True, capture_output=True, text=True)
        return wait_mysql_ready()
    except Exception as e:
        print(f"直接启动mysqld失败：{e}")
        return False


# ========== 启动MySQL & 初始化 ==========
try:
    if is_mysql_port_ready():
        print("MySQL服务已就绪")
    else:
        # 优先尝试Windows服务，失败则直接启动mysqld
        if not start_mysql_via_service():
            start_mysql_via_mysqld()
except Exception as e:
    print(f"启动MySQL失败：{e}")

# 启动初始化（创建基础表、默认管理员）
with app.app_context():
    init_base_tables()

# 启动服务
if __name__ == '__main__':
    print("✅ MySQL版音乐评分系统后端启动！")
    print(f"🌐 服务地址：http://0.0.0.0:5000")
    # use_reloader=False：关闭Flask自动重载，避免reloader重启子进程导致所有输出打印两遍
    # debug=True仍保留：错误页面、调试器等开发功能正常可用
    app.run(debug=True, host='0.0.0.0', port=5000, use_reloader=False)
