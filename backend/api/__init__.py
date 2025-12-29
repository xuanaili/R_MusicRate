# MusicRate\backend\api\__init__.py 接口模块初始化 - 统一注册所有业务接口
from . import auth, album, album_pool, review, comment, audio_resource, playlist,listening  # 新增：导入音频接口


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
    # 新增：注册音频资源接口 (最后加)
    audio_resource.register_audio_routes(app)

    # ✅ 新增：注册播放列表接口 (最后一行加这个即可)
    playlist.register_playlist_routes(app)

    # ✅ ✅ ✅ 新增：注册播放计时接口 (最后加这一行) ✅ ✅ ✅
    listening.register_listening_routes(app)