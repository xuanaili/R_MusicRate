# MusicRate/backend/api/review.py 听后感相关接口 - 添加、删除、编辑、清空
from flask import request, jsonify
import json
import uuid
import traceback
from ..db_utils import get_db, get_album_table_name, current_user_id
from ..decorators import login_required


def register_review_routes(app):
    """注册听后感相关路由（需传入Flask app实例）"""

    # 1. 添加单条听后感
    @app.route('/api/album/review/add/<int:album_id>', methods=['POST'])
    @login_required
    def add_single_review(album_id):
        try:
            data = request.get_json()
            content = data.get('content', '').strip()
            if not content:
                return jsonify({"code": 400, "msg": "听后感内容不能为空！"}), 400

            table_name = get_album_table_name(current_user_id)
            db = get_db()
            cursor = db.cursor()

            # 查询原有review
            cursor.execute(f'SELECT review FROM `{table_name}` WHERE id = %s', (album_id,))
            album = cursor.fetchone()
            if not album:
                cursor.close()
                return jsonify({"code": 404, "msg": f"未找到ID为{album_id}的专辑！"}), 404

            # 初始化review结构（兼容旧数据）
            review = json.loads(album["review"]) if album["review"] else {"feelings": []}
            if "feelings" not in review:
                review["feelings"] = []

            # 生成单条听后感记录
            new_feeling = {
                "id": str(uuid.uuid4()),
                "content": content,
                "create_time": data.get('create_time', '')
            }
            review["feelings"].append(new_feeling)

            # 保存更新
            new_review = json.dumps(review)
            cursor.execute(f'''
                UPDATE `{table_name}` SET review = %s WHERE id = %s
            ''', (new_review, album_id))
            db.commit()
            cursor.close()

            return jsonify({
                "code": 200,
                "msg": "听后感添加成功！",
                "data": new_feeling
            })
        except Exception as e:
            print(f"❌ 添加听后感出错：{str(e)}")
            print(traceback.format_exc())
            return jsonify({"code": 500, "msg": f"添加听后感失败：{str(e)}"}), 500

    # 2. 删除单条听后感
    @app.route('/api/album/review/delete/single/<int:album_id>', methods=['POST'])
    @login_required
    def delete_single_review(album_id):
        try:
            data = request.get_json()
            feeling_id = data.get('feeling_id')
            if not feeling_id:
                return jsonify({"code": 400, "msg": "请指定要删除的听后感！"}), 400

            table_name = get_album_table_name(current_user_id)
            db = get_db()
            cursor = db.cursor()

            # 查询原有review
            cursor.execute(f'SELECT review FROM `{table_name}` WHERE id = %s', (album_id,))
            album = cursor.fetchone()
            if not album:
                cursor.close()
                return jsonify({"code": 404, "msg": f"未找到ID为{album_id}的专辑！"}), 404

            # 过滤要删除的记录
            review = json.loads(album["review"]) if album["review"] else {"feelings": []}
            if "feelings" not in review:
                cursor.close()
                return jsonify({"code": 400, "msg": "暂无听后感记录！"}), 400

            # 保留不等于该ID的记录
            review["feelings"] = [f for f in review["feelings"] if f.get("id") != feeling_id]
            new_review = json.dumps(review)

            # 保存更新
            cursor.execute(f'''
                UPDATE `{table_name}` SET review = %s WHERE id = %s
            ''', (new_review, album_id))
            db.commit()
            cursor.close()

            return jsonify({
                "code": 200,
                "msg": "听后感删除成功！"
            })
        except Exception as e:
            print(f"❌ 删除单条听后感出错：{str(e)}")
            print(traceback.format_exc())
            return jsonify({"code": 500, "msg": f"删除听后感失败：{str(e)}"}), 500

    # 3. 清空所有听后感
    @app.route('/api/album/review/delete/<int:album_id>', methods=['DELETE'])
    @login_required
    def delete_all_review(album_id):
        try:
            table_name = get_album_table_name(current_user_id)
            db = get_db()
            cursor = db.cursor()

            # 查询原有review
            cursor.execute(f'SELECT review FROM `{table_name}` WHERE id = %s', (album_id,))
            album = cursor.fetchone()
            if not album:
                cursor.close()
                return jsonify({"code": 404, "msg": f"未找到ID为{album_id}的专辑！"}), 404

            # 清空所有听后感（兼容重构后的结构）
            review = json.loads(album["review"]) if album["review"] else {}
            review["feelings"] = []
            review["personal_feeling"] = ""
            new_review = json.dumps(review)

            # 保存更新
            cursor.execute(f'''
                UPDATE `{table_name}` SET review = %s WHERE id = %s
            ''', (new_review, album_id))
            db.commit()
            cursor.close()

            return jsonify({
                "code": 200,
                "msg": "所有听后感已清空！"
            })
        except Exception as e:
            print(f"❌ 清空听后感出错：{str(e)}")
            print(traceback.format_exc())
            return jsonify({"code": 500, "msg": f"清空听后感失败：{str(e)}"}), 500

    # 4. 编辑听后感（重构后的单条听后感）
    @app.route('/api/album/review/edit/<int:album_id>', methods=['POST'])
    @login_required
    def edit_review(album_id):
        try:
            data = request.get_json()
            if not data or not data.get('personal_feeling'):
                return jsonify({"code": 400, "msg": "听后感内容不能为空！"}), 400

            table_name = get_album_table_name(current_user_id)
            db = get_db()
            cursor = db.cursor()

            # 查询原有review
            cursor.execute(f'SELECT review FROM `{table_name}` WHERE id = %s', (album_id,))
            album = cursor.fetchone()
            if not album:
                cursor.close()
                return jsonify({"code": 404, "msg": f"未找到ID为{album_id}的专辑！"}), 404

            # 更新听后感
            review = json.loads(album["review"]) if album["review"] else {}
            review['personal_feeling'] = data.get('personal_feeling')
            review['update_time'] = data.get('update_time', '')
            new_review = json.dumps(review)

            # 保存更新
            cursor.execute(f'''
                UPDATE `{table_name}` SET review = %s WHERE id = %s
            ''', (new_review, album_id))
            db.commit()
            cursor.close()

            return jsonify({
                "code": 200,
                "msg": "听后感编辑成功！",
                "data": review
            })
        except Exception as e:
            print(f"❌ 编辑听后感出错：{str(e)}")
            print(traceback.format_exc())
            return jsonify({"code": 500, "msg": f"编辑听后感失败：{str(e)}"}), 500