# MusicRate\backend\api\review.py 听后感相关接口 - 添加、删除、编辑、清空
from datetime import datetime

from flask import request, jsonify
import json
import uuid
import traceback
from ..db_utils import get_db, get_album_table_name, get_current_user_id  # 导入get_current_user_id
from ..decorators import login_required


def register_review_routes(app):
    """注册听后感相关路由（需传入Flask app实例）"""

    # 1. 添加单条听后感
    @app.route('/api/album/review/add/<int:album_id>', methods=['POST'])
    @login_required
    def add_single_review(album_id):
        try:
            # 获取当前登录用户ID（从g对象中获取）
            current_user_id = get_current_user_id()
            if current_user_id is None:
                return jsonify({"code": 401, "msg": "用户未登录！"}), 401
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
                "create_time": data.get('create_time', ''),
                "listening_duration":data.get('listening_duration'),
                "my_score": data.get('my_score'),
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
            # 获取当前登录用户ID（从g对象中获取）
            current_user_id = get_current_user_id()
            if current_user_id is None:
                return jsonify({"code": 401, "msg": "用户未登录！"}), 401
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
            # 获取当前登录用户ID（从g对象中获取）
            current_user_id = get_current_user_id()
            if current_user_id is None:
                return jsonify({"code": 401, "msg": "用户未登录！"}), 401
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
            # 获取当前登录用户ID（从g对象中获取）
            current_user_id = get_current_user_id()
            if current_user_id is None:
                return jsonify({"code": 401, "msg": "用户未登录！"}), 401
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

        # ============ ✅ 新增核心接口：日历听后感统计数据查询 ============

        # ============ ✅ 核心接口：日历听后感统计数据查询【最优版，适配初始化review】 ============

    @app.route('/api/album/review/calendar', methods=['GET'])
    @login_required
    def get_calendar_review_data():
        try:
            current_user_id = get_current_user_id()
            if current_user_id is None:
                return jsonify({"code": 401, "msg": "用户未登录！"}), 401

            table_name = get_album_table_name(current_user_id)
            db = get_db()
            cursor = db.cursor()

            # ✅ 精准查询：review不为空 + 是有效的JSON（数据库已初始化，一定满足）
            cursor.execute(f'''
                   SELECT album_name, singer, tags, review FROM `{table_name}` 
                   WHERE review IS NOT NULL AND review != ''
               ''')
            album_list = cursor.fetchall()
            cursor.close()

            calendar_data = []

            # 秒数转 分:秒 格式化方法
            def format_duration(seconds):
                if not seconds or seconds < 0:
                    return "00:00"
                m = int(seconds // 60)
                s = int(seconds % 60)
                return f"{m:02d}:{s:02d}"

            for album in album_list:
                album_name = album.get('album_name', '未知专辑')
                singer = album.get('singer', '未知歌手')
                tags = album.get('tags', '')
                review_str = album.get('review', '')

                try:
                    review = json.loads(review_str)
                    feelings = review.get('feelings', [])
                    # 只处理有听后感的记录
                    if len(feelings) == 0:
                        continue

                    # 遍历每一条听后感，组装日历需要的结构
                    for feeling in feelings:
                        create_time = feeling.get('create_time', '')
                        if not create_time:
                            continue
                        # 解析时间：2026-01-01 16:32:27 → 年/月/日
                        dt = datetime.strptime(create_time, "%Y-%m-%d %H:%M:%S")
                        calendar_data.append({
                            "year": dt.year,
                            "month": dt.month,
                            "day": dt.day,
                            "albumName": album_name,
                            "singer": singer,
                            "tags": tags,
                            "score": round(feeling.get('my_score', 0.0), 1),  # 评分保留1位小数
                            "content": feeling.get('content', ''),
                            "listening_duration": format_duration(feeling.get('listening_duration', 0)),  # 格式化时长
                            "feeling_id": feeling.get('id', '')
                        })
                except Exception as e:
                    print(f"解析专辑[{album_name}]的review数据出错: {str(e)}")
                    continue


            print(calendar_data)
            return jsonify({
                "code": 200,
                "msg": "数据获取成功！",
                "data": calendar_data
            })
        except Exception as e:
            print(f"❌ 获取日历听后感数据出错：{str(e)}")
            print(traceback.format_exc())
            return jsonify({"code": 500, "msg": f"数据获取失败：{str(e)}"}), 500