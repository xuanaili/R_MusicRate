def calculate_album_total_score(score_list: list) -> float:
    """
    通用专辑综合评分计算函数
    :param score_list: 评分列表 [专辑整体评分, 单曲1评分, 单曲2评分, ...] 例: [50,100,20,30,0,0]
    :return: 0-100之间的综合评分(保留1位小数，美观实用)
    """
    # 1. 基础容错处理：空列表/非列表 直接返回0
    if not isinstance(score_list, list) or len(score_list) == 0:
        return 0.0

    # 2. 解构数据：第一个值固定是专辑整体评分，剩余是单曲评分
    album_score = score_list[0] if score_list[0] is not None else 0
    track_scores = score_list[1:] if len(score_list) > 1 else []

    # 3. 过滤掉 单曲评分为0的项（核心需求：0分不参与计算）
    valid_track_scores = [s for s in track_scores if isinstance(s, (int, float)) and s > 0]

    # 4. 核心逻辑修改：如果所有单曲评分都是0（有效单曲列表为空），直接返回专辑整体评分
    if len(valid_track_scores) == 0:
        total_score = album_score
    else:
        # 有有效单曲评分时，按原权重计算
        avg_track_score = sum(valid_track_scores) / len(valid_track_scores)
        total_score = album_score * 0.6 + avg_track_score * 0.4

    # 5. 严格限制分数区间在 0~100 之间，杜绝溢出
    total_score = max(0.0, min(total_score, 100.0))

    # 6. 保留1位小数，评分展示更整洁
    return round(total_score, 1)


def normalize_score_list(score_list) -> list:
    """
    评分变化判定归一化：去掉末尾连续 0（含 '0'/'' 等字符串形态）。

    用于评分保存接口判断「评分是否实际变化」——前端在离开评分板块 / 切换子页面 /
    退出专辑时都会自动保存一次，老逻辑每次保存都发经验。末位 0 代表「未评分的单曲」，
    数组长度会随曲目数变化，故剥掉末尾 0 后比较，避免曲目增删 / 自动保存造成误判。
    首位是专辑整体分，即使为 0 也保留结构。
    :param score_list: 评分列表 [专辑整体评分, 单曲1评分, ...]
    :return: 去掉末尾连续 0 的新列表；非列表输入返回 []
    """
    if not isinstance(score_list, list):
        return []
    result = list(score_list)
    while result and result[-1] in (0, 0.0, '0', ''):
        result.pop()
    return result