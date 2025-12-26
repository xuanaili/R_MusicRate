# MusicRate/backend/__init__.py Flask应用初始化入口 - 统一创建和配置app实例
from flask import Flask
from flask_cors import CORS
from .config import SECRET_KEY
from .db_utils import close_db
from .upload_utils import register_upload_routes
from .api import register_all_api_routes


def create_app():
    """创建并配置Flask应用实例"""
    # 1. 初始化Flask app
    app = Flask(__name__)
    app.secret_key = SECRET_KEY

    # 2. 配置CORS（跨域）
    CORS(app, supports_credentials=True)

    # 3. 注册数据库连接关闭回调
    app.teardown_appcontext(close_db)

    # 4. 注册图床相关路由
    register_upload_routes(app)

    # 5. 注册所有业务接口路由
    register_all_api_routes(app)

    return app