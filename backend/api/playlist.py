# MusicRate\backend\api\playlist.py 播放列表专属API
import json

from flask import request, jsonify
import traceback
import pymysql

from ..db_utils import get_db, get_current_user_id, get_album_table_name, check_and_create_user_album_table
from ..decorators import login_required


def register_playlist_routes(app):
    """注册播放列表相关路由"""

    # ========== 原有接口：查询用户可播放的专辑列表 (保留，不修改) ==========
    @app.route('/api/playlist/get-user-audio-albums', methods=['GET'])
    @login_required
    def get_user_audio_albums_for_playlist():
        try:
            # 获取当前登录用户ID
            current_user_id = get_current_user_id()
            if not current_user_id:
                return jsonify({"code": 401, "msg": "用户未登录，请先登录"}), 401
            current_user_id = int(current_user_id)

            # 校验并创建用户专辑表（兜底，防止表不存在）
            check_and_create_user_album_table(current_user_id)
            user_album_table = get_album_table_name(current_user_id)

            db = get_db()
            cursor = db.cursor(pymysql.cursors.DictCursor)

            sql = f'''
                SELECT 
                    ua.my_score as score,
                    ua.album_name,
                    ua.created_at,
                    ua.source_pool_id,
                    ua.singer
                FROM `{user_album_table}` ua
                INNER JOIN album_pool ap ON ua.source_pool_id = ap.id
                WHERE 
                    ua.source_pool_id IS NOT NULL 
                    AND ap.mp3_url IS NOT NULL 
                    AND ap.mp3_url != ''
                ORDER BY ua.created_at DESC
            '''
            cursor.execute(sql)
            album_list = cursor.fetchall()

            cursor.close()

            return jsonify({
                "code": 200,
                "msg": f"查询成功，共获取 {len(album_list)} 张可播放专辑",
                "data": album_list
            })

        except Exception as e:
            print(f"❌ 播放列表筛选可播放专辑失败：{str(e)}")
            print(traceback.format_exc())
            return jsonify({
                "code": 500,
                "msg": f"查询失败：{str(e)}",
                "data": []
            })

    # ========== ✅ 修复后完整版：获取用户个人播放列表完整数据 (解决所有初始化BUG) ==========
    @app.route('/api/playlist/get-user-playlist-data', methods=['GET'])
    @login_required
    def get_user_playlist_data():
        try:
            current_user_id = get_current_user_id()
            if not current_user_id:
                return jsonify({"code": 401, "msg": "用户未登录，请先登录"}), 401
            current_user_id = int(current_user_id)
            print(current_user_id)
            db = get_db()
            cursor = db.cursor(pymysql.cursors.DictCursor)

            select_sql = '''
                SELECT playlist, current_album_id, current_playlist_id, play_mode 
                FROM user_playlist 
                WHERE user_id = %s
            '''
            cursor.execute(select_sql, (current_user_id,))
            print(cursor)
            user_playlist_info = cursor.fetchone()

            print(user_playlist_info)

            default_playlist = [{"name": "默认歌单", "tracks": []}]
            default_playlist_str = json.dumps(default_playlist, ensure_ascii=False)

            if not user_playlist_info:
                insert_sql = '''
                    INSERT INTO user_playlist (user_id, playlist, current_album_id, current_playlist_id, play_mode)
                    VALUES (%s, %s, %s, %s, %s)
                '''
                # ✅ BUG2修复：current_album_id 默认值改为 -1 (无播放/无选中)
                cursor.execute(insert_sql, (current_user_id, default_playlist_str, -1, 0, 'order'))
                db.commit()
                user_playlist_info = {
                    'playlist': default_playlist_str,
                    'current_album_id': -1,
                    'current_playlist_id': 0,
                    'play_mode': 'order'
                }

            playlist_data = []
            if user_playlist_info['playlist'] and user_playlist_info['playlist'] != '':
                try:
                    playlist_data = json.loads(user_playlist_info['playlist'])
                except:
                    playlist_data = default_playlist
            else:
                playlist_data = default_playlist

            result_data = {
                # ✅ BUG1修复【核心】：返回 解析后的数组 playlist_data 而不是原始字符串
                "playlist": playlist_data,
                "current_album_id": user_playlist_info['current_album_id'],
                # ✅ BUG3修复：对current_playlist_id做兜底，防止None报错
                "current_playlist_id": user_playlist_info.get('current_playlist_id', 0),
                "play_mode": user_playlist_info.get('play_mode', 'order')
            }



            cursor.close()
            return jsonify({
                "code": 200,
                "msg": "用户播放列表数据获取成功",
                "data": result_data
            })

        except Exception as e:
            print(f"❌ 获取用户播放列表数据失败：{str(e)}")
            print(traceback.format_exc())
            return jsonify({
                "code": 500,
                "msg": f"获取播放列表失败：{str(e)}",
                "data": {}
            })


    @app.route('/api/playlist/save-user-playlist-data', methods=['POST'])
    @login_required
    def save_user_playlist_data():
        try:
            current_user_id = get_current_user_id()
            if not current_user_id:
                return jsonify({"code": 401, "msg": "用户未登录，请先登录"}), 401
            current_user_id = int(current_user_id)

            data = request.get_json()
            # ========== 修复点1：接收前端传的 activeTabIndex 而不是 current_playlist_id ==========
            playlist = data.get('playlist', [{"name": "默认歌单", "tracks": []}])
            current_album_id = data.get('current_album_id', 0)
            current_playlist_id = data.get('activeTabIndex', 0)  # ✅ 这里改了！接收前端的activeTabIndex
            play_mode = data.get('play_mode', 'order')

            # ========== 修复点2：必须对playlist做JSON序列化！！！核心中的核心 ==========
            playlist_str = json.dumps(playlist, ensure_ascii=False)

            db = get_db()
            cursor = db.cursor(pymysql.cursors.DictCursor)
            select_sql = '''SELECT id FROM user_playlist WHERE user_id = %s'''
            cursor.execute(select_sql, (current_user_id,))
            user_playlist_info = cursor.fetchone()

            if user_playlist_info:
                update_sql = '''
                    UPDATE user_playlist 
                    SET playlist = %s, current_album_id = %s, current_playlist_id = %s, play_mode = %s
                    WHERE user_id = %s
                '''
                # ========== 注意：这里传入的是序列化后的 playlist_str ==========
                cursor.execute(update_sql,
                               (playlist_str, current_album_id, current_playlist_id, play_mode, current_user_id))
            else:
                insert_sql = '''
                    INSERT INTO user_playlist (user_id, playlist, current_album_id, current_playlist_id, play_mode)
                    VALUES (%s, %s, %s, %s, %s)
                '''
                # ========== 同样传入 playlist_str ==========
                cursor.execute(insert_sql,
                               (current_user_id, playlist_str, current_album_id, current_playlist_id, play_mode))

            db.commit()  # 提交事务
            cursor.close()
            return jsonify({"code": 200, "msg": "用户播放列表数据保存成功", "data": {}})

        except Exception as e:
            print(f"❌ 保存用户播放列表数据失败：{str(e)}")
            print(traceback.format_exc())
            return jsonify({"code": 500, "msg": f"保存播放列表失败：{str(e)}", "data": {}})
    # ========== ✅ 新增核心接口：专辑播放完成后，切换下一个专辑（处理所有播放模式逻辑） ==========
    @app.route('/api/playlist/switch-next-album', methods=['POST'])
    @login_required
    def switch_next_album():
        try:
            current_user_id = get_current_user_id()
            if not current_user_id:
                return jsonify({"code": 401, "msg": "用户未登录，请先登录"}), 401
            current_user_id = int(current_user_id)

            # 1. 获取前端传入的核心参数 (前端必须传这几个值，兜底有默认值)
            data = request.get_json()
            current_playlist_id = data.get('current_playlist_id', 0)  # 当前选中的歌单ID
            current_album_id = data.get('current_album_id', 0)       # 当前播放的专辑索引
            play_mode = data.get('play_mode', 'order')               # 播放模式：order/random/loop
            playlist = data.get('playlist', [{"name": "默认歌单", "tracks": []}]) # 当前完整歌单数据


            print(current_playlist_id)
            print(current_album_id)
            print(play_mode)
            # 2. 校验当前歌单是否存在、当前歌单内是否有专辑
            if current_playlist_id >= len(playlist):
                return jsonify({"code": 400, "msg": "当前歌单ID无效", "data": {}})
            current_playlist_tracks = playlist[current_playlist_id]['tracks']  # 当前歌单的专辑列表
            album_count = len(current_playlist_tracks)  # 当前歌单的专辑总数
            if album_count == 0:
                return jsonify({"code": 400, "msg": "当前歌单暂无专辑，无法切换", "data": {}})

            # 3. 核心逻辑：根据播放模式计算新的current_album_id
            new_album_id = current_album_id
            if play_mode == 'single':
                # 🔹 循环播放：单曲循环，专辑ID不变
                new_album_id = current_album_id
            elif play_mode == 'order':
                # 🔹 顺序播放：自增1，越界则重置为0（回到歌单第一首）
                new_album_id = current_album_id + 1
                if new_album_id >= album_count:
                    new_album_id = 0
            elif play_mode == 'random':
                # 🔹 随机播放：在当前歌单内随机选一个合法的专辑ID
                import random
                new_album_id = random.randint(0, album_count - 1)

            # 4. 把最新的播放状态 更新到数据库 (持久化，下次打开页面能恢复)
            db = get_db()
            cursor = db.cursor(pymysql.cursors.DictCursor)
            # 序列化歌单数据，避免存入数据库报错
            playlist_str = json.dumps(playlist, ensure_ascii=False)
            # 更新user_playlist表的核心字段
            update_sql = '''
                UPDATE user_playlist 
                SET playlist = %s, current_album_id = %s, current_playlist_id = %s, play_mode = %s
                WHERE user_id = %s
            '''
            cursor.execute(
                update_sql,
                (playlist_str, new_album_id, current_playlist_id, play_mode, current_user_id)
            )
            db.commit()
            cursor.close()

            # 5. 返回最新的播放状态给前端，前端直接渲染即可
            return jsonify({
                "code": 200,
                "msg": f"播放模式【{play_mode}】，切换专辑成功",
                "data": {
                    "current_playlist_id": current_playlist_id,
                    "current_album_id": new_album_id,
                    "play_mode": play_mode,
                    "album_count": album_count # 前端可选：返回当前歌单专辑总数
                }
            })

        except Exception as e:
            print(f"❌ 切换下一张专辑失败：{str(e)}")
            print(traceback.format_exc())
            return jsonify({
                "code": 500,
                "msg": f"切换专辑失败：{str(e)}",
                "data": {}
            })