# MusicRate\backend\run.py 项目启动入口 - 替代原app.py的启动逻辑
import subprocess
import sys
import os
import time

# 添加这一行：自动设置正确的导入路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from backend import create_app
from backend.utils.db import init_base_tables

# 创建Flask应用实例
app = create_app()


try:
        # 执行sc query命令查询服务状态
    result = subprocess.run(
            ['sc', 'query', 'MySQL80'],
            capture_output=True,
            text=True,
            encoding='gbk'  # 解决中文乱码
        )
        # 判断服务是否运行中（STATE : 4 RUNNING）
    if not ("STATE" in result.stdout and "RUNNING" in result.stdout):
        ps_cmd = 'powershell -Command "Start-Process cmd -ArgumentList \'/c sc start MySQL80\' -Verb RunAs"'
        result = subprocess.run(ps_cmd, shell=True, capture_output=True, text=True)
        print("MySQL服务启动中，等待就绪...")
        # 等待MySQL真正就绪（端口可连接），最多等60秒
        import socket
        mysql_ready = False
        for i in range(30):
            time.sleep(2)
            try:
                sock = socket.create_connection(('localhost', 3306), timeout=1)
                sock.close()
                print(f"MySQL服务已就绪（等待了{(i+1)*2}秒）")
                mysql_ready = True
                break
            except (ConnectionRefusedError, socket.timeout):
                if i == 29:
                    print("⚠️ MySQL服务启动超时（60秒），尝试继续启动...")
        if not mysql_ready:
            print("⚠️ MySQL可能未完全启动，后续数据库操作可能失败")
    else:
        print(f"MySQL服务已启动")
except Exception as e:
        print(f"查询MySQL状态失败：{e}")

# 启动初始化（创建基础表、默认管理员）
with app.app_context():
    init_base_tables()

# 启动服务
if __name__ == '__main__':
    print("✅ MySQL版音乐评分系统后端启动！")
    print(f"🌐 服务地址：http://0.0.0.0:5000")
    app.run(debug=True, host='0.0.0.0', port=5000)