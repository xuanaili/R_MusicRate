# 项目启动入口 - 替代原app.py的启动逻辑
from backend import create_app  # 从backend包导入create_app
from backend.db_utils import init_base_tables

# 创建Flask应用实例
app = create_app()

# 启动初始化（创建基础表、默认管理员）
with app.app_context():
    init_base_tables()

# 启动服务
if __name__ == '__main__':
    print("✅ MySQL版音乐评分系统后端启动！")
    print(f"🌐 服务地址：http://0.0.0.0:5000")
    app.run(debug=True, host='0.0.0.0', port=5000)