from flask import request, jsonify
import json
import traceback
from backend.utils.db import get_db, get_album_table_name, get_current_user_id
from backend.utils.decorators import login_required
from backend.utils.user import add_bonus_xp
from backend.utils.score import normalize_score_list
import pymysql




def register_score_routes(app):
    """注册专辑评分相关路由（评分保存+评分读取）"""

    # ========== 评分计算 ==========


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

            # 先读已存评分，用于判断「评分是否实际变化」。
            # 历史遗留：前端在离开评分板块/切换子页面/退出专辑时都会自动保存一次，
            # 老逻辑每次保存都 +5，导致未评分也发经验。这里比较归一化后的评分，
            # 实际变化才加分，未变化返回 xp_gained=0（前端已有 xp_gained>0 才 toast 的守卫）。
            old_list = []
            cursor.execute(f'SELECT my_score FROM `{table_name}` WHERE id = %s LIMIT 1', (album_id,))
            old_row = cursor.fetchone()
            if old_row and old_row.get('my_score'):
                try:
                    parsed = json.loads(old_row['my_score'])
                    if isinstance(parsed, list):
                        old_list = parsed
                except (json.JSONDecodeError, TypeError):
                    old_list = []
            score_changed = normalize_score_list(old_list) != normalize_score_list(score_list)

            # 更新专辑的my_score字段
            cursor.execute(f'''
                UPDATE `{table_name}`
                SET my_score = %s
                WHERE id = %s
            ''', (score_json, album_id))
            db.commit()
            cursor.close()

            # v0.7.1 P0：评分保存成功 +5 经验（仅评分实际变化时发放，受每日上限约束），返回本次实际加分供 toast
            xp_gained = 0.0
            if score_changed:
                xp_gained, _, _, _ = add_bonus_xp(current_user_id, 5)

            return jsonify({
                "code": 200,
                "msg": "专辑评分保存成功！",
                "data": {"score_list": score_list, "xp_gained": xp_gained}
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