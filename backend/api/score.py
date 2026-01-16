from flask import request, jsonify
import json
import traceback
from backend.utils.db import get_db, get_album_table_name, get_current_user_id
from backend.utils.decorators import login_required
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