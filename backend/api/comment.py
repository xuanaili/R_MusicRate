# MusicRate\backend\api\comment.py 评论相关接口 - 私有评论（原有）+ 公共评论（新增）
from flask import request, jsonify
import json
import traceback
from datetime import datetime
from backend.utils.db import get_db, get_album_table_name, get_current_user_id
from backend.utils.decorators import login_required
from backend.utils.user import add_bonus_xp
import pymysql

def register_comment_routes(app):
    """注册评论相关路由（私有评论+公共评论）"""

    # ==================== 原有逻辑：用户专属私有评论（兼容旧接口） ====================
    # 1. 提交评论（带评分，兼容旧接口 /api/albumDetail/comment）
    @app.route('/api/music/comment', methods=['POST'])
    @login_required
    def submit_comment():
        try:
            # 获取当前登录用户ID
            current_user_id = get_current_user_id()
            if current_user_id is None:
                return jsonify({"code": 401, "msg": "用户未登录！"}), 401

            data = request.get_json()
            music_id = data.get('musicId')
            comment = data.get('comment')
            score = data.get('score', 0)
            # ============ 新增：获取前端传入的听取时长 ============
            listening_duration = data.get('listening_duration', 0)

            # 校验必填字段
            if not music_id or not comment:
                return jsonify({"code": 400, "msg": "音乐ID和评论不能为空"}), 400

            table_name = get_album_table_name(current_user_id)
            db = get_db()
            cursor = db.cursor(cursor=pymysql.cursors.DictCursor)  # 改为DictCursor，方便取值

            # 查询原有数据
            cursor.execute(f'SELECT score, comments FROM `{table_name}` WHERE id = %s', (music_id,))
            album = cursor.fetchone()
            if not album:
                cursor.close()
                return jsonify({"code": 404, "msg": f"未找到ID为{music_id}的专辑！"}), 404

            # 更新评论和评分
            comments = json.loads(album["comments"]) if album["comments"] else []
            # ============ 新增：评论改为对象格式，存入内容+听取时长 ============
            comments.append({
                "content": comment,
                "listening_duration": listening_duration
            })
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
                    # ============ 保持原解析逻辑，直接返回包含时长的评论对象 ============
                    "comments": json.loads(a["comments"]) if a["comments"] else []
                }
                album_list.append(a_dict)

            return jsonify({"code": 200, "msg": "提交成功", "data": album_list})
        except Exception as e:
            print(f"❌ 提交私有评论出错：{str(e)}")
            print(traceback.format_exc())
            return jsonify({"code": 500, "msg": f"提交评论出错：{str(e)}"}), 500

    # 2. 兼容的专辑评论添加接口（仅添加评论，不修改评分）
    @app.route('/api/album/comment/add/<int:album_id>', methods=['POST'])
    @login_required
    def add_album_comment(album_id):
        try:
            # 获取当前登录用户ID
            current_user_id = get_current_user_id()
            if current_user_id is None:
                return jsonify({"code": 401, "msg": "用户未登录！"}), 401

            data = request.get_json()
            comment = data.get('comment')
            # ============ 新增：获取前端传入的听取时长 ============
            listening_duration = data.get('listening_duration', 0)

            # 校验必填字段
            if not comment:
                return jsonify({"code": 400, "msg": "评论内容不能为空！"}), 400

            table_name = get_album_table_name(current_user_id)
            db = get_db()
            cursor = db.cursor(cursor=pymysql.cursors.DictCursor)

            # 查询原有数据
            cursor.execute(f'SELECT comments FROM `{table_name}` WHERE id = %s', (album_id,))
            album = cursor.fetchone()
            if not album:
                cursor.close()
                return jsonify({"code": 404, "msg": f"未找到ID为{album_id}的专辑！"}), 404

            # 更新评论
            comments = json.loads(album["comments"]) if album["comments"] else []
            # ============ 新增：评论改为对象格式，存入内容+听取时长 ============
            comments.append({
                "content": comment,
                "listening_duration": listening_duration
            })

            # 保存更新（评分保持不变）
            cursor.execute(f'''
                UPDATE `{table_name}` SET comments = %s WHERE id = %s
            ''', (json.dumps(comments), album_id))
            db.commit()
            cursor.close()

            # v0.7.1 P0：评论【新增】成功 +10 经验（受每日上限约束），只计新增不计编辑
            xp_gained, _, _, _ = add_bonus_xp(current_user_id, 10)

            return jsonify({
                "code": 200,
                "msg": "私有评论提交成功！",
                "data": {"comments": comments, "xp_gained": xp_gained}
            })
        except Exception as e:
            print(f"❌ 添加私有专辑评论出错：{str(e)}")
            print(traceback.format_exc())
            return jsonify({"code": 500, "msg": f"添加评论失败：{str(e)}"}), 500

    # 新增：检查用户是否已对该专辑发表评论
    @app.route('/api/album/pool/comment/check', methods=['GET'])
    @login_required
    def check_user_comment():
        try:
            current_user_id = get_current_user_id()
            if not current_user_id:
                return jsonify({"code": 401, "msg": "用户未登录！"}), 401

            # 获取专辑ID参数
            album_id = request.args.get('album_id')
            if not album_id:
                return jsonify({"code": 400, "msg": "专辑ID不能为空！"}), 400

            db = get_db()
            cursor = db.cursor(pymysql.cursors.DictCursor)
            # 查询该用户是否已对该专辑发表评论
            cursor.execute('''
                SELECT id FROM album_comments 
                WHERE album_id = %s AND user_id = %s
            ''', (album_id, current_user_id))
            comment = cursor.fetchone()
            cursor.close()

            return jsonify({
                "code": 200,
                "msg": "查询成功！",
                "data": {
                    "has_comment": comment is not None,
                    "comment_id": comment['id'] if comment else None
                }
            })
        except Exception as e:
            print(f"检查用户评论失败：{str(e)}")
            return jsonify({"code": 500, "msg": f"查询失败：{str(e)}"}), 500
    # ==================== 新增逻辑：多用户共享的公共评论 ====================
    # 3. 发布公共评论（关联album_pool）
    @app.route('/api/album/pool/comment/add', methods=['POST', 'OPTIONS'])
    @login_required
    def add_public_album_comment():
        try:
            if request.method == 'OPTIONS':
                return jsonify({"code": 200, "msg": "OPTIONS allowed"}), 200

            current_user_id = get_current_user_id()
            if not current_user_id:
                return jsonify({"code": 401, "msg": "用户未登录！"}), 401

            data = request.get_json()
            album_id = data.get('album_id')
            content = data.get('content', '').strip()
            # ============ 新增：获取前端传入的听取时长，核心修改 ============
            listening_duration = data.get('listening_duration', 0)

            # ===== 1. 基础参数校验 =====
            if not album_id or not content:
                return jsonify({"code": 400, "msg": "专辑ID和评论内容不能为空！"}), 400

            # ===== 2. 唯一性校验：同一用户同一专辑只能评论一次 =====
            db = get_db()
            cursor = db.cursor(pymysql.cursors.DictCursor)
            cursor.execute('''
                SELECT id FROM album_comments 
                WHERE album_id = %s AND user_id = %s
            ''', (album_id, current_user_id))
            existing_comment = cursor.fetchone()
            if existing_comment:
                cursor.close()
                return jsonify({
                    "code": 403,
                    "msg": "你已对该专辑发表过评论，无法重复发布！",
                    "data": {"comment_id": existing_comment['id']}
                })

            # ===== 3. 获取用户名（冗余存储） =====
            cursor.execute('SELECT username FROM users WHERE user_id = %s', (current_user_id,))
            user = cursor.fetchone()
            if not user:
                cursor.close()
                return jsonify({"code": 404, "msg": "用户不存在！"}), 404
            username = user['username']

            # ===== 4. 插入评论 核心修改：新增 listening_duration 字段入库 =====
            create_time = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            sql = '''
                INSERT INTO album_comments (
                    album_id, user_id, username, content, listening_duration, create_time
                ) VALUES (%s, %s, %s, %s, %s, %s)
            '''
            cursor.execute(sql, (album_id, current_user_id, username, content, listening_duration, create_time))
            db.commit()
            comment_id = cursor.lastrowid
            cursor.close()

            # v0.7.1 P0：公共评论【新增】成功 +10 经验（受每日上限约束；唯一性校验天然防刷）
            xp_gained, _, _, _ = add_bonus_xp(current_user_id, 10)

            return jsonify({
                "code": 200,
                "msg": "公共评论发布成功！",
                "data": {"comment_id": comment_id, "xp_gained": xp_gained}
            })
        except Exception as e:
            print(f"❌ 发布公共评论失败：{str(e)}")
            print(traceback.format_exc())
            return jsonify({"code": 500, "msg": f"发布评论失败：{str(e)}"}), 500

    #4. 获取专辑的所有公共评论 核心修改：查询结果中包含 listening_duration 并返回前端
    @app.route('/api/album/pool/comment/list/<int:album_id>', methods=['GET', 'OPTIONS'])
    @login_required
    def get_public_album_comments(album_id):
        try:
            if request.method == 'OPTIONS':
                return jsonify({"code": 200, "msg": "OPTIONS allowed"}), 200

            db = get_db()
            cursor = db.cursor(cursor=pymysql.cursors.DictCursor)

            # 查询评论（按时间倒序） 核心修改：SELECT 中新增 listening_duration 字段
            sql = '''
                SELECT id, album_id, user_id, username, content, listening_duration, create_time, like_count, like_user_ids
                FROM album_comments 
                WHERE album_id = %s
                ORDER BY create_time DESC
            '''
            cursor.execute(sql, (album_id,))
            comments = cursor.fetchall()
            cursor.close()

            # 格式化数据
            for comment in comments:
                # 时间戳格式化
                comment['create_time'] = comment['create_time'].strftime('%Y-%m-%d %H:%M:%S')
                # 解析点赞用户列表
                comment['like_user_ids'] = comment['like_user_ids'].split(',') if comment['like_user_ids'] else []
                # 兜底：确保时长字段是数字类型，防止空值
                comment['listening_duration'] = comment['listening_duration'] or 0

            return jsonify({
                "code": 200,
                "msg": "获取公共评论成功！",
                "data": comments
            })
        except Exception as e:
            print(f"❌ 获取公共评论失败：{str(e)}")
            print(traceback.format_exc())
            return jsonify({"code": 500, "msg": f"获取评论失败：{str(e)}"}), 500

    # 5. 公共评论点赞/取消点赞
    @app.route('/api/album/pool/comment/like/<int:comment_id>', methods=['POST', 'OPTIONS'])
    @login_required
    def like_public_album_comment(comment_id):
        try:
            if request.method == 'OPTIONS':
                return jsonify({"code": 200, "msg": "OPTIONS allowed"}), 200

            current_user_id = get_current_user_id()
            if not current_user_id:
                return jsonify({"code": 401, "msg": "用户未登录！"}), 401

            db = get_db()
            cursor = db.cursor(cursor=pymysql.cursors.DictCursor)

            # 查询评论
            cursor.execute('SELECT like_count, like_user_ids FROM album_comments WHERE id = %s', (comment_id,))
            comment = cursor.fetchone()
            if not comment:
                cursor.close()
                return jsonify({"code": 404, "msg": "评论不存在！"}), 404

            # 处理点赞/取消点赞
            like_user_ids = comment['like_user_ids'].split(',') if comment['like_user_ids'] else []
            current_user_id_str = str(current_user_id)

            if current_user_id_str in like_user_ids:
                # 取消点赞
                like_user_ids.remove(current_user_id_str)
                new_like_count = max(0, comment['like_count'] - 1)
                msg = "取消点赞成功！"
                is_liked = False
            else:
                # 点赞
                like_user_ids.append(current_user_id_str)
                new_like_count = comment['like_count'] + 1
                msg = "点赞成功！"
                is_liked = True

            # 更新数据库
            new_like_user_ids = ','.join(like_user_ids) if like_user_ids else ''
            sql = '''
                UPDATE album_comments 
                SET like_count = %s, like_user_ids = %s 
                WHERE id = %s
            '''
            cursor.execute(sql, (new_like_count, new_like_user_ids, comment_id))
            db.commit()
            cursor.close()

            return jsonify({
                "code": 200,
                "msg": msg,
                "data": {
                    "like_count": new_like_count,
                    "is_liked": is_liked
                }
            })
        except Exception as e:
            print(f"❌ 评论点赞失败：{str(e)}")
            print(traceback.format_exc())
            return jsonify({"code": 500, "msg": f"点赞失败：{str(e)}"}), 500


    # 6. 删除公共评论（仅作者/管理员可删）
    @app.route('/api/album/pool/comment/delete/<int:comment_id>', methods=['DELETE', 'OPTIONS'])
    @login_required
    def delete_public_album_comment(comment_id):
        try:
            if request.method == 'OPTIONS':
                return jsonify({"code": 200, "msg": "OPTIONS allowed"}), 200

            current_user_id = get_current_user_id()
            if not current_user_id:
                return jsonify({"code": 401, "msg": "用户未登录！"}), 401
            # 强制转为int，确保数据类型统一
            current_user_id = int(current_user_id)

            db = get_db()
            cursor = db.cursor(cursor=pymysql.cursors.DictCursor)

            # ========== 修复点1：修改SQL，分两步查询，先查评论作者，再查当前登录用户的管理员状态 ==========
            # 第一步：查询这条评论的作者ID，确认评论是否存在
            cursor.execute('SELECT user_id FROM album_comments WHERE id = %s', (comment_id,))
            comment = cursor.fetchone()
            if not comment:
                cursor.close()
                return jsonify({"code": 404, "msg": "评论不存在！"}), 404
            # 评论作者ID 强转int，统一数据类型
            comment_author_id = int(comment['user_id'])

            # 第二步：查询【当前登录用户】的管理员状态（核心修复！查自己，不是查评论作者）
            cursor.execute('SELECT is_admin FROM users WHERE user_id = %s', (current_user_id,))
            current_user = cursor.fetchone()
            # 默认为非管理员，防止用户表无数据的情况
            is_current_user_admin = current_user['is_admin'] == 1 if current_user else 0

            # ========== 修复点2：修复权限判断逻辑，完美逻辑 ==========
            # 权限规则：✅ 评论作者  或  ✅ 当前登录的管理员 → 允许删除；否则403
            if comment_author_id != current_user_id and not is_current_user_admin:
                cursor.close()
                return jsonify({"code": 403, "msg": "无权限删除该评论！仅评论作者或管理员可删除"}), 403

            # 执行删除
            cursor.execute('DELETE FROM album_comments WHERE id = %s', (comment_id,))
            db.commit()
            cursor.close()

            return jsonify({
                "code": 200,
                "msg": "公共评论删除成功！"
            })
        except Exception as e:
            print(f"❌ 删除公共评论失败：{str(e)}")
            print(traceback.format_exc())
            return jsonify({"code": 500, "msg": f"删除评论失败：{str(e)}"}), 500