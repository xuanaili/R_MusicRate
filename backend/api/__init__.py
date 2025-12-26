# 接口模块初始化 - 统一注册所有业务接口
from . import auth, album, album_pool, review, comment


def register_all_api_routes(app):
    """注册所有业务接口路由（需传入Flask app实例）"""
    # 注册登录/注册接口
    auth.register_auth_routes(app)
    # 注册专辑基础操作接口
    album.register_album_routes(app)
    # 注册专辑搜索池接口
    album_pool.register_album_pool_routes(app)
    # 注册听后感接口
    review.register_review_routes(app)
    # 注册评论接口
    comment.register_comment_routes(app)