# MusicRate\backend\api\__init__.py 接口模块初始化 - 统一注册所有业务接口
from . import auth, album, album_pool, review, comment, audio_resource, playlist, listening, score, recommend, \
    unlock, tags, lyric, share, user, lyric_ai, ai  # 新增：导入音频接口；v0.7 新增个人用户中心接口；v0.8.1 新增 AI 识别异步任务接口 + AI key 配置接口



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

    # 新增：注册播放列表接口 (最后一行加这个即可)
    playlist.register_playlist_routes(app)

    # 新增：注册播放计时接口
    listening.register_listening_routes(app)

    # 新增：评分读取保存计算接口
    score.register_score_routes(app)

    # 推荐接口
    recommend.register_recommend_routes(app)

    # 音频解密解析接口
    unlock.register_unlock_routes(app)



    # 音乐风格接口
    tags.register_tags_routes(app)

    # 歌词接口
    lyric.register_lyric_routes(app)

    # v0.8.1 歌词 AI 识别异步任务接口（recognize 触发 + status 轮询）
    lyric_ai.register_lyric_ai_routes(app)

    # 专题接口
    share.register_share_routes(app)

    # v0.7 个人用户中心接口
    user.register_user_routes(app)

    # v0.8.1 P3 AI 助手接口（个人 AI key 配置：key 保存 + status 查询）
    ai.register_ai_routes(app)