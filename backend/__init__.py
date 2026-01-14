from flask import Flask
from flask_cors import CORS
from .config import SECRET_KEY, HOST, PORT
from .db_utils import close_db
from .upload_utils import register_upload_routes
from .api import register_all_api_routes


def create_app():
    """创建并配置Flask应用实例"""
    # 1. 初始化Flask app
    app = Flask(__name__)
    app.secret_key = SECRET_KEY

    # 2. 优化CORS配置（解决OPTIONS预检请求404问题）
    # ✅✅✅ 【修复后完整版CORS配置】彻底解决所有跨域问题，包括OPTIONS预检和POST请求
    CORS(
        app,
        supports_credentials=True,  # 允许前端携带cookie/token（你的项目必须要这个，因为有登录）
        origins=["http://localhost:8080", "http://127.0.0.1:8080"],
        # 允许所有前端域名跨域（开发环境推荐，生产可改成你的前端域名如http://localhost:8081）
        methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],  # 显式放行所有请求方法
        allow_headers=["Content-Type", "Authorization", "X-Requested-With"], # 放行所有必要请求头
        expose_headers=["Content-Type", "Authorization"],     # 允许前端读取的响应头
        max_age=3600                # 预检请求缓存1小时，减少OPTIONS请求次数，提升性能
    )

    # 3. 注册数据库连接关闭回调
    app.teardown_appcontext(close_db)

    # 4. 注册图床相关路由
    register_upload_routes(app)

    # 5. 注册所有业务接口路由
    register_all_api_routes(app)

    return app