import pymysql
from flask import jsonify
import traceback
import time
from datetime import datetime
from backend.utils.db import get_db, get_album_table_name, get_current_user_id
from backend.utils.decorators import login_required

# 全局内存存储 播放计时状态 - key: f"{user_id}_{album_id}", value: 开始时间戳
PLAYING_TIMER_CACHE = {}


def register_listening_routes(app):
    """注册专辑播放计时相关路由（播放开始+暂停保存）"""

    # ========== 核心接口1：开始播放计时 API (专辑播放触发) ==========
    @app.route('/api/album/listening/start/<int:album_id>', methods=['POST'])
    @login_required
    def start_listening_timer(album_id):
        try:
            # 1. 获取当前登录用户ID & 校验
            current_user_id = get_current_user_id()
            if current_user_id is None:
                return jsonify({"code": 401, "msg": "用户未登录，无法开始播放计时！"}), 401

            # 2. 获取用户专属专辑表名 + 数据库连接
            table_name = get_album_table_name(current_user_id)
            db = get_db()
            # ✅ 适配你的全局DictCursor，不用改，完美兼容
            cursor = db.cursor(pymysql.cursors.DictCursor)

            # 3. 查询该专辑的 原始 listening_duration 秒数 (如果字段不存在会自动初始化)
            cursor.execute(f'''
                SELECT listening_duration FROM `{table_name}` WHERE id = %s
            ''', (album_id,))
            album_data = cursor.fetchone()

            if not album_data:
                cursor.close()
                return jsonify({"code": 404, "msg": f"未找到ID为{album_id}的专辑，无法开始计时！"}), 404

            # 4. ✅ 彻底解决KeyError：字典取值用get方法，空则默认0.0，完美适配你的游标
            origin_duration = album_data.get('listening_duration') or 0.0
            origin_duration = float(origin_duration) if origin_duration else 0.0

            # 5. 生成唯一播放标识，存入内存：记录【开始时间戳】+【原始时长】
            play_unique_key = f"{current_user_id}_{album_id}"
            PLAYING_TIMER_CACHE[play_unique_key] = {
                "start_timestamp": time.time(),  # 当前精确时间戳
                "origin_duration": origin_duration  # 播放前的原始时长
            }

            cursor.close()
            # 返回成功响应 + 初始时长，给前端展示
            return jsonify({
                "code": 200,
                "msg": "专辑播放计时已开始！",
                "data": {
                    "album_id": album_id,
                    "user_id": current_user_id,
                    "origin_listening_duration": origin_duration,
                    "start_time": int(time.time())
                }
            })
        except Exception as e:
            print(f"❌ 开始播放计时出错：{str(e)}")
            print(traceback.format_exc())
            return jsonify({"code": 500, "msg": f"开始计时失败：{str(e)}"}), 500

    # ========== 核心接口2：暂停播放并保存时长 API (专辑暂停触发) ==========
    @app.route('/api/album/listening/pause/<int:album_id>', methods=['POST'])
    @login_required
    def pause_listening_timer(album_id):
        try:
            # 1. 获取当前登录用户ID & 校验
            current_user_id = get_current_user_id()
            if current_user_id is None:
                return jsonify({"code": 401, "msg": "用户未登录，无法暂停播放计时！"}), 401

            # 2. 生成唯一播放标识，校验是否在播放中
            play_unique_key = f"{current_user_id}_{album_id}"
            if play_unique_key not in PLAYING_TIMER_CACHE:
                return jsonify({"code": 400, "msg": f"该专辑(ID:{album_id})当前未播放，无需暂停！"}), 400

            # 3. 获取内存中的播放数据 + 计算本次播放时长
            play_cache = PLAYING_TIMER_CACHE[play_unique_key]
            start_timestamp = play_cache["start_timestamp"]
            origin_duration = play_cache["origin_duration"]
            current_timestamp = time.time()

            # 计算：本次播放的秒数(保留1位小数，精准) + 原始时长 = 总时长
            play_seconds = round(current_timestamp - start_timestamp, 1)
            total_duration = round(origin_duration + play_seconds, 1)

            # 4. 数据库操作：更新到用户专属表的对应专辑行
            table_name = get_album_table_name(current_user_id)
            db = get_db()
            cursor = db.cursor(pymysql.cursors.DictCursor)

            # 【重要】先检测字段是否存在，不存在则自动新增 listening_duration 字段，兼容历史表
            cursor.execute(f'''
                SELECT COUNT(*) as count FROM information_schema.COLUMNS 
                WHERE TABLE_SCHEMA = DATABASE() AND TABLE_NAME = %s AND COLUMN_NAME = 'listening_duration'
            ''', (table_name,))
            field_count = cursor.fetchone()
            # ✅ 字典取值，完美适配你的游标，无KeyError
            field_exists = field_count.get('count') > 0 if field_count else False
            if not field_exists:
                # 新增字段：浮点型 存储秒数，默认0，精准记录播放时长
                cursor.execute(f'''
                    ALTER TABLE `{table_name}` 
                    ADD COLUMN listening_duration FLOAT DEFAULT 0.0 COMMENT '专辑累计播放时长(秒)'
                ''')
                print(f"✅ 为用户{current_user_id}的专辑表{table_name}补充 listening_duration 字段")

            # 5. 更新时长到数据库
            cursor.execute(f'''
                UPDATE `{table_name}` SET listening_duration = %s WHERE id = %s
            ''', (total_duration, album_id))
            db.commit()

            # 6. 清除内存中的播放状态，释放缓存 + 关闭游标
            del PLAYING_TIMER_CACHE[play_unique_key]
            cursor.close()

            # 返回成功响应，给前端最新时长
            return jsonify({
                "code": 200,
                "msg": "专辑播放已暂停，时长已保存！",
                "data": {
                    "album_id": album_id,
                    "user_id": current_user_id,
                    "this_play_seconds": play_seconds,
                    "total_listening_duration": total_duration
                }
            })
        except Exception as e:
            db.rollback() if 'db' in locals() else None
            print(f"❌ 暂停播放计时出错：{str(e)}")
            print(traceback.format_exc())
            return jsonify({"code": 500, "msg": f"暂停计时并保存失败：{str(e)}"}), 500

    # ========== 核心接口3：记录最近收听时间 (打开专辑详情页触发，用于「最近收听」排序) ==========
    @app.route('/api/album/listening/touch/<int:album_id>', methods=['POST'])
    @login_required
    def touch_last_listened(album_id):
        try:
            # 1. 获取当前登录用户ID & 校验
            current_user_id = get_current_user_id()
            if current_user_id is None:
                return jsonify({"code": 401, "msg": "用户未登录，无法记录收听！"}), 401

            # 2. 获取用户专属专辑表名 + 数据库连接
            table_name = get_album_table_name(current_user_id)
            db = get_db()
            cursor = db.cursor(pymysql.cursors.DictCursor)

            # 3. 【重要】先检测字段是否存在，不存在则自动新增 last_listened 字段，兼容历史表
            cursor.execute(f'''
                SELECT COUNT(*) as count FROM information_schema.COLUMNS
                WHERE TABLE_SCHEMA = DATABASE() AND TABLE_NAME = %s AND COLUMN_NAME = 'last_listened'
            ''', (table_name,))
            field_count = cursor.fetchone()
            field_exists = field_count.get('count') > 0 if field_count else False
            if not field_exists:
                cursor.execute(f'''
                    ALTER TABLE `{table_name}`
                    ADD COLUMN last_listened DATETIME NULL COMMENT '最近收听时间'
                ''')
                print(f"✅ 为用户{current_user_id}的专辑表{table_name}补充 last_listened 字段")

            # 4. 校验专辑存在
            cursor.execute(f'''
                SELECT id FROM `{table_name}` WHERE id = %s
            ''', (album_id,))
            album_data = cursor.fetchone()
            if not album_data:
                cursor.close()
                return jsonify({"code": 404, "msg": f"未找到ID为{album_id}的专辑，无法记录收听！"}), 404

            # 5. 更新最近收听时间为当前时间
            cursor.execute(f'''
                UPDATE `{table_name}` SET last_listened = NOW() WHERE id = %s
            ''', (album_id,))
            db.commit()
            cursor.close()

            # 返回成功响应
            return jsonify({
                "code": 200,
                "msg": "最近收听时间已更新！",
                "data": {
                    "album_id": album_id,
                    "user_id": current_user_id,
                    "last_listened": datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                }
            })
        except Exception as e:
            db.rollback() if 'db' in locals() else None
            print(f"❌ 记录最近收听时间出错：{str(e)}")
            print(traceback.format_exc())
            return jsonify({"code": 500, "msg": f"记录最近收听失败：{str(e)}"}), 500