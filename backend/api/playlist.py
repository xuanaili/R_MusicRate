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

    # ========== ✅ 获取用户个人播放列表完整数据 (原代码保留，无BUG) ==========
    @app.route('/api/playlist/get-user-playlist-data', methods=['GET'])
    @login_required
    def get_user_playlist_data():
        try:
            current_user_id = get_current_user_id()
            if not current_user_id:
                return jsonify({"code": 401, "msg": "用户未登录，请先登录"}), 401
            current_user_id = int(current_user_id)

            db = get_db()
            cursor = db.cursor(pymysql.cursors.DictCursor)

            select_sql = '''
                SELECT playlist, current_album_id, current_playlist_id, play_mode 
                FROM user_playlist 
                WHERE user_id = %s
            '''
            cursor.execute(select_sql, (current_user_id,))
            user_playlist_info = cursor.fetchone()

            default_playlist = [{"name": "默认歌单", "tracks": []}]
            default_playlist_str = json.dumps(default_playlist, ensure_ascii=False)

            if not user_playlist_info:
                insert_sql = '''
                    INSERT INTO user_playlist (user_id, playlist, current_album_id, current_playlist_id, play_mode)
                    VALUES (%s, %s, %s, %s, %s)
                '''
                cursor.execute(insert_sql, (current_user_id, default_playlist_str, 0, 0, 'order'))
                db.commit()
                user_playlist_info = {
                    'playlist': default_playlist_str,
                    'current_album_id': 0,
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
                "playlist": playlist_data,
                "current_album_id": user_playlist_info['current_album_id'],
                "current_playlist_id": user_playlist_info['current_playlist_id'],
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