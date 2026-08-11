# MusicRate\backend\utils\xp.py 经验来源常量（v0.7.2）
# 经验来源枚举 + 加分来源集合 + 中文 label（前端弹窗 / 明细流展示用）
# 规则（README v0.7.1/v0.7.2 已定决策）：
# - 收听（listening）：1 秒 = 1 XP，无上限
# - 评分（rating）保存成功 +5、听后感（review）新增 +20、评论（comment）新增 +10
# - 评分/听后感/评论为「加分来源」，合计受每日上限 100 约束（users.bonus_xp_today）
# 明细落表 user_xp_log.xp_type 存这些常量值，与 users 累计列同事务写入

XP_LISTENING = 'listening'  # 听歌（1秒=1XP，无上限）
XP_RATING = 'rating'        # 评分保存成功 +5
XP_REVIEW = 'review'        # 听后感新增 +20
XP_COMMENT = 'comment'      # 评论新增 +10

# 加分来源（受每日上限 100 约束）；不含 listening（收听无上限）
BONUS_SOURCES = (XP_RATING, XP_REVIEW, XP_COMMENT)

# 来源中文 label（前端弹窗 / 明细流展示）
SOURCE_LABELS = {
    XP_LISTENING: '听歌',
    XP_RATING: '评分',
    XP_REVIEW: '听后感',
    XP_COMMENT: '评论',
}
