from flask import request, jsonify
import json
import traceback
from ..db_utils import get_db, get_album_table_name, get_current_user_id
from ..decorators import login_required
import pymysql


def register_score_routes(app):
    """注册专辑评分相关路由（评分保存+评分读取）"""

    # ========== 评分计算 ==========
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

        # 4. 计算有效单曲的平均分
        avg_track_score = 0.0
        if len(valid_track_scores) > 0:
            avg_track_score = sum(valid_track_scores) / len(valid_track_scores)

        # 5. 核心加权计算：专辑分60%权重 + 有效单曲平均分40%权重 (最优权重比)
        total_score = album_score * 0.6 + avg_track_score * 0.4

        # 6. 严格限制分数区间在 0~100 之间，杜绝溢出
        total_score = max(0.0, min(total_score, 100.0))

        # 7. 保留1位小数，评分展示更整洁，也可以根据需求改保留2位/取整
        return round(total_score, 1)

    # ✅ 1. 保存评分接口 - 全局个人评分 + 所有单曲评分 存入 my_score 列
    @app.route('/api/album/score/save/<int:album_id>', methods=['PUT', 'OPTIONS'])
    @login_required
    def save_album_my_score(album_id):
        try:
            current_user_id = get_current_user_id()
            if current_user_id is None:
                return jsonify({"code": 401, "msg": "用户未登录！"}), 200

            data = request.get_json()
            score_list = data.get('score_list', [])
            # 容错：必须是数组，不是则赋值空数组
            if not isinstance(score_list, list):
                score_list = []

            # 数组转JSON字符串存入数据库 my_score 字段
            score_json = json.dumps(score_list, ensure_ascii=False)
            table_name = get_album_table_name(current_user_id)
            db = get_db()
            cursor = db.cursor()

            # 更新专辑的my_score字段
            cursor.execute(f'''
                UPDATE `{table_name}` 
                SET my_score = %s 
                WHERE id = %s
            ''', (score_json, album_id))
            db.commit()
            cursor.close()

            return jsonify({
                "code": 200,
                "msg": "专辑评分保存成功！",
                "data": {"score_list": score_list}
            })
        except Exception as e:
            print(f"❌ 保存专辑评分出错：{str(e)}")
            print(traceback.format_exc())
            return jsonify({"code": 500, "msg": f"保存评分失败：{str(e)}"}), 200

    # ✅ 2. 读取评分接口 - 从 my_score 列读取并解析成评分数组
    @app.route('/api/album/score/get/<int:album_id>', methods=['GET', 'OPTIONS'])
    @login_required
    def get_album_my_score(album_id):
        try:
            current_user_id = get_current_user_id()
            if current_user_id is None:
                return jsonify({"code": 401, "msg": "用户未登录！"}), 200

            table_name = get_album_table_name(current_user_id)
            db = get_db()
            cursor = db.cursor(cursor=pymysql.cursors.DictCursor)

            # 查询当前专辑的my_score字段
            cursor.execute(f'''
                SELECT my_score FROM `{table_name}` 
                WHERE id = %s LIMIT 1
            ''', (album_id,))
            album_info = cursor.fetchone()
            cursor.close()

            score_list = []
            if album_info and album_info.get('my_score'):
                try:
                    # 解析JSON字符串为数组，容错解析失败
                    score_list = json.loads(album_info['my_score'])
                    if not isinstance(score_list, list):
                        score_list = []
                except json.JSONDecodeError:
                    score_list = []

            return jsonify({
                "code": 200,
                "msg": "获取专辑评分成功！",
                "data": {"score_list": score_list}
            })
        except Exception as e:
            print(f"❌ 获取专辑评分出错：{str(e)}")
            print(traceback.format_exc())
            return jsonify({"code": 500, "msg": f"获取评分失败：{str(e)}"}), 200