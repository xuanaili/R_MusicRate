# MusicRate\backend\api\lyric.py 歌词接口（v0.8 重构）
# 决策（README v0.8）：彻底移除 QQ 音乐自动获取（fetch_auto / fetch_qq_lyric / clean_lyric），
# 保留 krc2lrc（本地 KRC 文件转换）；save / upload 均改真实管理员校验（is_admin_user）。
# 存储格式全站统一：每行 `mm:ss 歌词` 或 `mm:ss.x 歌词`（1 位小数），由 lrc.py 校验 + 规范化。
from flask import request, jsonify
import json
import traceback
from datetime import datetime

from backend.utils.db import get_db, get_current_user_id
from backend.utils.decorators import login_required, is_admin_user
from backend.utils.lrc import normalize_to_storage, validate_lyric_text
import pymysql

# 上传 LRC 文件大小上限（1MB，UTF-8 歌词约 1~3 万行足够）
MAX_LRC_FILE_SIZE = 1024 * 1024


def upsert_album_lyric(db, album_pool_id, lyric_text, lyric_translate, current_user_id):
    """保存/更新歌词落库（save 与 upload 共用，幂等：已存在则更新，不存在则插入）
    返回规范化后的 lyric_text（调用方已校验 + 规范化，此处直接落库）
    """
    cursor = db.cursor(pymysql.cursors.DictCursor)
    current_time = datetime.now()
    cursor.execute('''
        SELECT id FROM album_lyric
        WHERE album_pool_id = %s
        LIMIT 1
    ''', (album_pool_id,))
    existing = cursor.fetchone()
    if existing:
        cursor.execute('''
            UPDATE album_lyric
            SET lyric_text = %s, lyric_translate = %s, update_time = %s
            WHERE album_pool_id = %s
        ''', (lyric_text, lyric_translate, current_time, album_pool_id))
    else:
        cursor.execute('''
            INSERT INTO album_lyric
            (album_pool_id, lyric_text, lyric_translate, create_user_id, create_time, update_time)
            VALUES (%s, %s, %s, %s, %s, %s)
        ''', (album_pool_id, lyric_text, lyric_translate, current_user_id, current_time, current_time))
    db.commit()
    cursor.close()


def _normalize_translate(lyric_translate):
    """规范化翻译字段：JSON 对象，各语言值同样走 validate + normalize 落存储格式
    返回 (normalized_json_str, error_msg)；error_msg 非空表示失败
    """
    if isinstance(lyric_translate, str):
        try:
            translate_obj = json.loads(lyric_translate)
        except json.JSONDecodeError:
            return None, "翻译歌词格式错误，必须是JSON格式！"
    else:
        translate_obj = lyric_translate or {}
    if not isinstance(translate_obj, dict):
        return None, "翻译歌词格式错误，必须是JSON对象！"
    for lang, content in translate_obj.items():
        if not isinstance(content, str):
            return None, f"翻译[{lang}]内容必须是字符串！"
        ok, msg = validate_lyric_text(content)
        if not ok:
            return None, f"翻译[{lang}]无效：{msg}"
        translate_obj[lang] = normalize_to_storage(content)
    return json.dumps(translate_obj, ensure_ascii=False), ''


def _decode_text(raw):
    """按 utf-8 解码，失败回退 gbk（兼容中文系统导出/保存的 LRC 文件）"""
    for encoding in ('utf-8', 'gbk'):
        try:
            return raw.decode(encoding)
        except (UnicodeDecodeError, ValueError):
            continue
    return raw.decode('utf-8', errors='ignore')


def register_lyric_routes(app):
    """注册歌词相关路由（save / get / 整轨 LRC 上传 / KRC 转 LRC）"""

    # 1. 保存/更新歌词接口 - 编辑器逐单曲保存（JSON 相对/绝对时间，已按前端格式），仅管理员
    @app.route('/api/album/lyric/save/<int:album_pool_id>', methods=['POST', 'OPTIONS'])
    @login_required
    def save_album_lyric(album_pool_id):
        try:
            current_user_id = get_current_user_id()
            if current_user_id is None:
                return jsonify({"code": 401, "msg": "用户未登录！"}), 401

            # 真实管理员校验（修复原 is_admin = True 硬编码权限漏洞）
            if not is_admin_user(current_user_id):
                return jsonify({"code": 403, "msg": "只有管理员才能上传歌词！"}), 403

            db = get_db()
            cursor = db.cursor(pymysql.cursors.DictCursor)
            # 补专辑存在性校验
            cursor.execute('SELECT id FROM album_pool WHERE id = %s', (album_pool_id,))
            if not cursor.fetchone():
                cursor.close()
                return jsonify({"code": 404, "msg": f"公共专辑ID[{album_pool_id}]不存在！"}), 404
            cursor.close()

            data = request.get_json() or {}
            lyric_text = (data.get('lyric_text') or '').strip()
            ok, msg = validate_lyric_text(lyric_text)
            if not ok:
                return jsonify({"code": 400, "msg": f"原版歌词无效：{msg}"}), 400
            lyric_text = normalize_to_storage(lyric_text)

            normalized_translate, err = _normalize_translate(data.get('lyric_translate', '{}'))
            if err:
                return jsonify({"code": 400, "msg": err}), 400

            upsert_album_lyric(db, album_pool_id, lyric_text, normalized_translate, current_user_id)

            return jsonify({
                "code": 200,
                "msg": "歌词保存成功！",
                "data": {
                    "album_pool_id": album_pool_id,
                    "lyric_text": lyric_text,
                    "lyric_text_length": len(lyric_text),
                    "has_translate": normalized_translate != '{}'
                }
            })
        except Exception as e:
            print(f"❌ 保存歌词出错：{str(e)}")
            print(traceback.format_exc())
            return jsonify({"code": 500, "msg": f"保存歌词失败：{str(e)}"}), 500

    # 2. 获取歌词接口 - 读取长文本歌词
    @app.route('/api/album/lyric/get/<int:album_pool_id>', methods=['GET', 'OPTIONS'])
    @login_required
    def get_album_lyric(album_pool_id):
        try:
            db = get_db()
            cursor = db.cursor(pymysql.cursors.DictCursor)

            cursor.execute('''
                SELECT lyric_text, lyric_translate
                FROM album_lyric
                WHERE album_pool_id = %s
                LIMIT 1
            ''', (album_pool_id,))

            lyric_record = cursor.fetchone()
            cursor.close()

            result = {"lyric_text": "", "lyric_translate": "{}"}
            if lyric_record:
                result = {
                    "lyric_text": lyric_record.get('lyric_text', ''),
                    "lyric_translate": lyric_record.get('lyric_translate', '{}')
                }

            return jsonify({"code": 200, "msg": "获取歌词成功！", "data": result})
        except Exception as e:
            print(f"❌ 获取歌词出错：{str(e)}")
            print(traceback.format_exc())
            return jsonify({"code": 500, "msg": f"获取歌词失败：{str(e)}"}), 500

    # 3. 整轨 LRC 文件上传接口 - 绝对时间覆盖全专辑（multipart lrc_file，≤1MB，utf-8 失败回退 gbk），仅管理员
    @app.route('/api/album/lyric/upload/<int:album_pool_id>', methods=['POST', 'OPTIONS'])
    @login_required
    def upload_album_lyric(album_pool_id):
        try:
            current_user_id = get_current_user_id()
            if current_user_id is None:
                return jsonify({"code": 401, "msg": "用户未登录！"}), 401
            if not is_admin_user(current_user_id):
                return jsonify({"code": 403, "msg": "只有管理员才能上传歌词！"}), 403

            db = get_db()
            cursor = db.cursor(pymysql.cursors.DictCursor)
            cursor.execute('SELECT id FROM album_pool WHERE id = %s', (album_pool_id,))
            if not cursor.fetchone():
                cursor.close()
                return jsonify({"code": 404, "msg": f"公共专辑ID[{album_pool_id}]不存在！"}), 404
            cursor.close()

            # ---- 主歌词文件 ----
            if 'lrc_file' not in request.files:
                return jsonify({"code": 400, "msg": "请上传 LRC 歌词文件！"}), 400
            lrc_file = request.files['lrc_file']
            if not lrc_file.filename or not lrc_file.filename.lower().endswith('.lrc'):
                return jsonify({"code": 400, "msg": "仅支持上传 .lrc 格式文件！"}), 400
            raw = lrc_file.read()
            if len(raw) > MAX_LRC_FILE_SIZE:
                return jsonify({"code": 400, "msg": "歌词文件过大，不能超过 1MB！"}), 400

            lyric_text_source = _decode_text(raw)
            ok, msg = validate_lyric_text(lyric_text_source)
            if not ok:
                return jsonify({"code": 400, "msg": f"歌词无效：{msg}"}), 400
            lyric_text = normalize_to_storage(lyric_text_source)

            # ---- 可选翻译文件（LRC 文本）→ 存 {"CN": ...} ----
            lyric_translate = '{}'
            translate_file = request.files.get('translate_file')
            if translate_file and translate_file.filename:
                tr_raw = translate_file.read()
                if len(tr_raw) > MAX_LRC_FILE_SIZE:
                    return jsonify({"code": 400, "msg": "翻译文件过大，不能超过 1MB！"}), 400
                tr_source = _decode_text(tr_raw)
                tr_ok, tr_msg = validate_lyric_text(tr_source)
                if not tr_ok:
                    return jsonify({"code": 400, "msg": f"翻译歌词无效：{tr_msg}"}), 400
                lyric_translate = json.dumps({'CN': normalize_to_storage(tr_source)}, ensure_ascii=False)

            upsert_album_lyric(db, album_pool_id, lyric_text, lyric_translate, current_user_id)

            return jsonify({
                "code": 200,
                "msg": "整轨 LRC 歌词上传成功！",
                "data": {
                    "album_pool_id": album_pool_id,
                    "lyric_text": lyric_text,  # 直接回前端，免二次 GET
                    "lyric_text_length": len(lyric_text),
                    "has_translate": lyric_translate != '{}'
                }
            })
        except Exception as e:
            print(f"❌ 整轨 LRC 上传出错：{str(e)}")
            print(traceback.format_exc())
            return jsonify({"code": 500, "msg": f"歌词上传失败：{str(e)}"}), 500

    # 4. 酷狗 KRC 转 LRC 接口（本地文件转换，保留）
    @app.route('/api/lyric/krc2lrc', methods=['POST', 'OPTIONS'])
    @login_required
    def krc_to_lrc():
        """
        酷狗 KRC 文件 转换为 标准 LRC 歌词接口
        前端上传 .krc 文件，返回标准 LRC 文本
        """
        try:
            if 'krc_file' not in request.files:
                return jsonify({"code": 400, "msg": "请上传 KRC 文件"}), 200

            file = request.files['krc_file']
            if not file.filename.endswith('.krc'):
                return jsonify({"code": 400, "msg": "仅支持 .krc 格式文件"}), 200

            krc_data = file.read()
            if len(krc_data) < 100:
                return jsonify({"code": 400, "msg": "KRC 文件无效"}), 200

            KEY = [64, 71, 97, 119, 94, 50, 116, 71, 81, 54, 49, 161, 127, 129, 164, 194]
            decrypted = bytearray()
            for i, b in enumerate(krc_data):
                decrypted.append(b ^ KEY[i % len(KEY)])

            json_str = decrypted.decode('utf-8', errors='ignore')
            js = json.loads(json_str)

            lrc_lines = []
            if 'ti' in js:
                lrc_lines.append(f"[ti:{js['ti']}]")
            if 'ar' in js:
                lrc_lines.append(f"[ar:{js['ar']}]")

            for item in js.get("lrc", []):
                time_ms = item["t"]
                text = item["c"].strip()
                if not text:
                    continue
                mins = time_ms // 60000
                secs = (time_ms % 60000) / 1000
                lrc_lines.append(f"[{mins:02d}:{secs:05.2f}]{text}")

            lrc_content = "\n".join(lrc_lines)

            return jsonify({
                "code": 200,
                "msg": "KRC 转换 LRC 成功",
                "data": {
                    "lrc_text": lrc_content,
                    "song": js.get('ti', ''),
                    "artist": js.get('ar', '')
                }
            })
        except Exception as e:
            print("❌ KRC 转 LRC 失败：", traceback.format_exc())
            return jsonify({"code": 500, "msg": f"KRC 解析失败：{str(e)}"}), 200

    return app  # 返回app实例，方便链式调用


# 导出注册函数
__all__ = ['register_lyric_routes']
