# MusicRate\backend\api\comment.py 评论相关接口 - 提交、添加
from flask import request, jsonify
import json
import traceback
from ..db_utils import get_db, get_album_table_name, get_current_user_id  # 导入get_current_user_id
from ..decorators import login_required


def register_comment_routes(app):
    """注册评论相关路由（需传入Flask app实例）"""

    # 1. 提交评论（带评分，兼容旧接口）
    @app.route('/api/music/comment', methods=['POST'])
    @login_required
    def submit_comment():
        try:
            # 获取当前登录用户ID（从g对象中获取）
            current_user_id = get_current_user_id()
            if current_user_id is None:
                return jsonify({"code": 401, "msg": "用户未登录！"}), 401
            data = request.get_json()
            music_id = data.get('musicId')
            comment = data.get('comment')
            score = data.get('score', 0)

            # 校验必填字段
            if not music_id or not comment:
                return jsonify({"code": 400, "msg": "音乐ID和评论不能为空"}), 400

            table_name = get_album_table_name(current_user_id)
            db = get_db()
            cursor = db.cursor()

            # 查询原有数据
            cursor.execute(f'SELECT score, comments FROM `{table_name}` WHERE id = %s', (music_id,))
            album = cursor.fetchone()
            if not album:
                cursor.close()
                return jsonify({"code": 404, "msg": f"未找到ID为{music_id}的专辑！"}), 404

            # 更新评论和评分
            comments = json.loads(album["comments"]) if album["comments"] else []
            comments.append(comment)
            new_score = album["score"]
            if score > 0:
                new_score = round((album["score"] + score) / 2, 1)

            # 保存更新
            cursor.execute(f'''
                UPDATE `{table_name}` SET score = %s, comments = %s WHERE id = %s
            ''', (new_score, json.dumps(comments), music_id))
            db.commit()

            # 返回更新后的专辑列表
            cursor.execute(f'SELECT * FROM `{table_name}`')
            albums = cursor.fetchall()
            cursor.close()

            # 解析专辑列表JSON字段
            album_list = []
            for a in albums:
                a_dict = {
                    "id": a["id"],
                    "album_name": a["album_name"],
                    "cover_img": a["cover_img"],
                    "singer": a["singer"],
                    "release_year": a["release_year"],
                    "start_time": a["start_time"],
                    "track_count": a["track_count"],
                    "track_duration": a["track_duration"],
                    "my_score": a["my_score"],
                    "burn_class": a["burn_class"],
                    "duration_type": a["duration_type"],
                    "tags": json.loads(a["tags"]) if a["tags"] else [],
                    "main_type": json.loads(a["main_type"]) if a["main_type"] else [],
                    "code": a["code"],
                    "video_shared": a["video_shared"],
                    "mandopop_code": a["mandopop_code"],
                    "tracks": json.loads(a["tracks"]) if a["tracks"] else [],
                    "review": json.loads(a["review"]) if a["review"] else {},
                    "score": a["score"],
                    "comments": json.loads(a["comments"]) if a["comments"] else []
                }
                album_list.append(a_dict)

            return jsonify({"code": 200, "msg": "提交成功", "data": album_list})
        except Exception as e:
            print(f"❌ 提交评论出错：{str(e)}")
            print(traceback.format_exc())
            return jsonify({"code": 500, "msg": f"提交评论出错：{str(e)}"}), 500

    # 2. 兼容的专辑评论添加接口（仅添加评论，不修改评分）
    @app.route('/api/album/comment/add/<int:album_id>', methods=['POST'])
    @login_required
    def add_album_comment(album_id):
        try:
            # 获取当前登录用户ID（从g对象中获取）
            current_user_id = get_current_user_id()
            if current_user_id is None:
                return jsonify({"code": 401, "msg": "用户未登录！"}), 401
            data = request.get_json()
            comment = data.get('comment')

            # 校验必填字段
            if not comment:
                return jsonify({"code": 400, "msg": "评论内容不能为空！"}), 400

            table_name = get_album_table_name(current_user_id)
            db = get_db()
            cursor = db.cursor()

            # 查询原有数据
            cursor.execute(f'SELECT score, comments FROM `{table_name}` WHERE id = %s', (album_id,))
            album = cursor.fetchone()
            if not album:
                cursor.close()
                return jsonify({"code": 404, "msg": f"未找到ID为{album_id}的专辑！"}), 404

            # 更新评论
            comments = json.loads(album["comments"]) if album["comments"] else []
            comments.append(comment)

            # 保存更新（评分保持不变）
            cursor.execute(f'''
                UPDATE `{table_name}` SET comments = %s WHERE id = %s
            ''', (json.dumps(comments), album_id))
            db.commit()
            cursor.close()

            return jsonify({
                "code": 200,
                "msg": "评论提交成功！",
                "data": {"comments": comments}
            })
        except Exception as e:
            print(f"❌ 添加专辑评论出错：{str(e)}")
            print(traceback.format_exc())
            return jsonify({"code": 500, "msg": f"添加评论失败：{str(e)}"}), 500