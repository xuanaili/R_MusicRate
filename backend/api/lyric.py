from flask import request, jsonify
import json
import traceback
import requests
import re
from urllib.parse import quote, unquote
from backend.utils.db import get_db, get_current_user_id
from backend.utils.decorators import login_required
import pymysql
from datetime import datetime
import time
import random
import html
import base64

# 增强版请求头，模拟真实浏览器
HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36 Edg/120.0.0.0',
    'Referer': 'https://y.qq.com/',
    'Accept': 'application/json, text/plain, */*',
    'Accept-Language': 'zh-CN,zh;q=0.9,en;q=0.8,en-GB;q=0.7,en-US;q=0.6',
    'Accept-Encoding': 'gzip, deflate, br, zstd',
    'Connection': 'keep-alive',
    'Sec-Fetch-Dest': 'empty',
    'Sec-Fetch-Mode': 'cors',
    'Sec-Fetch-Site': 'same-origin',
    'Sec-Ch-Ua': '"Not_A Brand";v="8", "Chromium";v="120", "Microsoft Edge";v="120"',
    'Sec-Ch-Ua-Mobile': '?0',
    'Sec-Ch-Ua-Platform': '"Windows"',
    'Cache-Control': 'max-age=0',
}

# 增加会话保持，添加重试机制
SESSION = requests.Session()
SESSION.headers.update(HEADERS)
SESSION.timeout = 15
# 启用重试
SESSION.mount('http://', requests.adapters.HTTPAdapter(max_retries=2))
SESSION.mount('https://', requests.adapters.HTTPAdapter(max_retries=2))


def register_lyric_routes(app):
    """注册歌词相关路由（仅保留QQ音乐歌词获取）"""

    # ✅ 1. 保存/更新歌词接口 - 保存长文本到album_lyric表
    @app.route('/api/album/lyric/save/<int:album_pool_id>', methods=['POST', 'OPTIONS'])
    @login_required
    def save_album_lyric(album_pool_id):
        try:
            current_user_id = get_current_user_id()
            if current_user_id is None:
                return jsonify({"code": 401, "msg": "用户未登录！"}), 200

            # 验证管理员权限（替换为你的实际判断逻辑）
            is_admin = True  # 请根据实际用户表判断
            if not is_admin:
                return jsonify({"code": 403, "msg": "只有管理员才能上传歌词！"}), 200

            # 获取请求数据
            data = request.get_json()
            lyric_text = data.get('lyric_text', '').strip()
            lyric_translate = data.get('lyric_translate', '{}').strip()

            # 数据验证
            if not lyric_text:
                return jsonify({"code": 400, "msg": "原版歌词内容不能为空！"}), 200

            # 确保翻译字段是合法JSON
            try:
                if lyric_translate:
                    translate_obj = json.loads(lyric_translate)
                    lyric_translate = json.dumps(translate_obj, ensure_ascii=False)
                else:
                    lyric_translate = '{}'
            except json.JSONDecodeError:
                return jsonify({"code": 400, "msg": "翻译歌词格式错误，必须是JSON格式！"}), 200

            # 连接数据库
            db = get_db()
            cursor = db.cursor(pymysql.cursors.DictCursor)
            current_time = datetime.now()

            # 1. 先查询该专辑是否已有歌词记录
            cursor.execute('''
                SELECT id FROM album_lyric 
                WHERE album_pool_id = %s
                LIMIT 1
            ''', (album_pool_id,))
            existing_record = cursor.fetchone()

            if existing_record:
                # 2. 更新现有记录
                cursor.execute('''
                    UPDATE album_lyric 
                    SET lyric_text = %s,
                        lyric_translate = %s,
                        update_time = %s
                    WHERE album_pool_id = %s
                ''', (lyric_text, lyric_translate, current_time, album_pool_id))
            else:
                # 3. 插入新记录
                cursor.execute('''
                    INSERT INTO album_lyric 
                    (album_pool_id, lyric_text, lyric_translate, create_user_id, create_time, update_time)
                    VALUES (%s, %s, %s, %s, %s, %s)
                ''', (album_pool_id, lyric_text, lyric_translate, current_user_id, current_time, current_time))

            db.commit()
            cursor.close()

            return jsonify({
                "code": 200,
                "msg": "歌词保存成功！",
                "data": {
                    "album_pool_id": album_pool_id,
                    "lyric_text_length": len(lyric_text),
                    "has_translate": lyric_translate != '{}'
                }
            })
        except Exception as e:
            print(f"❌ 保存歌词出错：{str(e)}")
            print(traceback.format_exc())
            return jsonify({"code": 500, "msg": f"保存歌词失败：{str(e)}"}), 200

    # ✅ 2. 获取歌词接口 - 读取长文本歌词
    @app.route('/api/album/lyric/get/<int:album_pool_id>', methods=['GET', 'OPTIONS'])
    @login_required
    def get_album_lyric(album_pool_id):
        try:
            # 连接数据库
            db = get_db()
            cursor = db.cursor(pymysql.cursors.DictCursor)

            # 查询歌词
            cursor.execute('''
                SELECT lyric_text, lyric_translate 
                FROM album_lyric 
                WHERE album_pool_id = %s
                LIMIT 1
            ''', (album_pool_id,))

            lyric_record = cursor.fetchone()
            cursor.close()

            # 格式化返回数据
            result = {
                "lyric_text": "",
                "lyric_translate": "{}"
            }

            if lyric_record:
                result = {
                    "lyric_text": lyric_record.get('lyric_text', ''),
                    "lyric_translate": lyric_record.get('lyric_translate', '{}')
                }

            return jsonify({
                "code": 200,
                "msg": "获取歌词成功！",
                "data": result
            })
        except Exception as e:
            print(f"❌ 获取歌词出错：{str(e)}")
            print(traceback.format_exc())
            return jsonify({"code": 500, "msg": f"获取歌词失败：{str(e)}"}), 200

    # ✅ 3. 自动获取QQ音乐歌词接口
    @app.route('/api/lyric/fetch_auto', methods=['POST', 'OPTIONS'])
    @login_required
    def fetch_auto_lyric():
        """仅保留QQ音乐歌词获取功能"""
        try:
            data = request.get_json()
            song_name = data.get('song_name', '').strip()
            artist = data.get('artist', '').strip()
            duration = data.get('duration', 0)

            if not song_name:
                return jsonify({"code": 400, "msg": "歌曲名不能为空！"}), 200

            print(f"\n🎵 开始获取QQ音乐歌词：{song_name} - {artist}")

            result = {
                "qq": {"status": "failed", "lyric": "", "msg": ""}
            }

            # 仅尝试QQ音乐获取歌词
            try:
                print("尝试QQ音乐...")
                time.sleep(random.uniform(0.5, 1.5))
                qq_lyric = fetch_qq_lyric(song_name, artist)
                if qq_lyric:
                    result["qq"] = {
                        "status": "success",
                        "lyric": qq_lyric,
                        "msg": f"获取成功，{len(qq_lyric)}字符"
                    }
                    print(f"✅ QQ音乐成功: {len(qq_lyric)}字符")
                    print(qq_lyric[:100] + "..." if len(qq_lyric) > 100 else qq_lyric)
                else:
                    result["qq"]["msg"] = "未找到歌词"
                    print("❌ QQ音乐无结果")
            except Exception as e:
                result["qq"]["msg"] = str(e)[:100]
                print(f"❌ QQ音乐异常: {e}")

            # 统计成功数量
            success_count = sum(1 for r in result.values() if r["status"] == "success")

            return jsonify({
                "code": 200,
                "msg": f"获取完成，成功{success_count}个平台",
                "data": {
                    "request_params": {"song_name": song_name, "artist": artist},
                    "lyrics": result,
                    "summary": {
                        "total_platforms": len(result),
                        "success_count": success_count,
                        "has_lyric": success_count > 0
                    }
                }
            })

        except Exception as e:
            print(f"❌ 自动获取歌词出错：{traceback.format_exc()}")
            return jsonify({"code": 500, "msg": f"自动获取歌词失败：{str(e)}"}), 200

    # ==================== QQ音乐歌词获取函数 ====================

    def fetch_qq_lyric(song_name, artist):
        """QQ音乐歌词获取（增强版）"""
        try:
            # 使用更稳定的QQ音乐API
            search_url = f"https://c.y.qq.com/soso/fcgi-bin/client_search_cp?p=1&n=10&w={quote(song_name + ' ' + artist)}&format=json"

            headers = {
                'Referer': 'https://y.qq.com/',
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
                'Accept': 'application/json, text/javascript, */*; q=0.01',
            }

            response = SESSION.get(search_url, headers=headers, timeout=10)

            # QQ音乐返回的是jsonp格式，需要处理
            content = response.text.strip()
            if content.startswith('callback('):
                content = content[9:-1]  # 移除 callback( 和最后的 )
            elif content.startswith('jsonp1('):
                content = content[6:-1]

            # 清理可能的多余字符
            content = re.sub(r'^\s+|\s+$', '', content)
            data = json.loads(content)

            if not data.get('data', {}).get('song', {}).get('list'):
                return ""

            song = data['data']['song']['list'][0]
            song_mid = song.get('songmid', '')

            if not song_mid:
                return ""

            # 获取歌词 - 使用更稳定的接口
            lyric_url = f"https://c.y.qq.com/lyric/fcgi-bin/fcg_query_lyric_new.fcg?songmid={song_mid}&g_tk=5381&format=json&inCharset=utf8&outCharset=utf-8&notice=0&platform=yqq.json&needNewCode=0"

            lyric_response = SESSION.get(lyric_url, headers=headers, timeout=10)
            lyric_content = lyric_response.text.strip()

            # 处理JSONP格式
            if lyric_content.startswith('callback('):
                lyric_content = lyric_content[9:-1]

            lyric_data = json.loads(lyric_content)
            encoded_lyric = lyric_data.get('lyric', '')

            if not encoded_lyric:
                return ""

            # 解码base64歌词
            try:
                decoded = base64.b64decode(encoded_lyric).decode('utf-8', errors='ignore')
                return clean_lyric(decoded, keep_timestamp=True)
            except:
                # 如果解码失败，直接清理返回
                return clean_lyric(encoded_lyric, keep_timestamp=True)

        except Exception as e:
            print(f"QQ音乐歌词获取错误: {e}")
            return ""

    # ==================== 酷狗 KRC 转 LRC 接口（新增） ====================
    @app.route('/api/lyric/krc2lrc', methods=['POST', 'OPTIONS'])
    @login_required
    def krc_to_lrc():
        """
        酷狗 KRC 文件 转换为 标准 LRC 歌词接口
        前端上传 .krc 文件，返回标准 LRC 文本
        """
        try:
            # 1. 获取上传的 krc 文件
            if 'krc_file' not in request.files:
                return jsonify({"code": 400, "msg": "请上传 KRC 文件"}), 200

            file = request.files['krc_file']
            if not file.filename.endswith('.krc'):
                return jsonify({"code": 400, "msg": "仅支持 .krc 格式文件"}), 200

            # 2. 读取文件二进制
            krc_data = file.read()
            if len(krc_data) < 100:
                return jsonify({"code": 400, "msg": "KRC 文件无效"}), 200

            # 3. 酷狗 KRC 固定解密密钥
            KEY = [64, 71, 97, 119, 94, 50, 116, 71, 81, 54, 49, 161, 127, 129, 164, 194]

            # 4. 解密
            decrypted = bytearray()
            for i, b in enumerate(krc_data):
                decrypted.append(b ^ KEY[i % len(KEY)])

            json_str = decrypted.decode('utf-8', errors='ignore')
            js = json.loads(json_str)

            # 5. 生成标准 LRC
            lrc_lines = []

            # 标题/歌手（可选）
            if 'ti' in js:
                lrc_lines.append(f"[ti:{js['ti']}]")
            if 'ar' in js:
                lrc_lines.append(f"[ar:{js['ar']}]")

            # 逐行解析
            for item in js.get("lrc", []):
                time_ms = item["t"]
                text = item["c"].strip()
                if not text:
                    continue

                # 毫秒转 [mm:ss.xx]
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
            return jsonify({
                "code": 500,
                "msg": f"KRC 解析失败：{str(e)}"
            }), 200
    def clean_lyric(raw_lyric, keep_timestamp=True):
        """
        清理歌词格式
        :param raw_lyric: 原始歌词
        :param keep_timestamp: 是否保留时间戳
        :return: 格式化的歌词文本
        """
        if not raw_lyric:
            return ""

        # 统一换行符
        cleaned = raw_lyric.replace('\r\n', '\n').replace('\r', '\n')

        # 清理标签
        if keep_timestamp:
            # 保留时间戳 [mm:ss.xx]，移除其他标签
            cleaned = re.sub(r'\[(ti|ar|al|by|offset|re|ve):.*?\]', '', cleaned)
            # 修复时间戳格式
            cleaned = re.sub(r'\[(\d+):(\d+):(\d+)\]', r'[\1:\2.\3]', cleaned)
        else:
            # 移除所有标签
            cleaned = re.sub(r'\[.*?\]', '', cleaned)

        # 清理特殊字符和注释
        cleaned = re.sub(r'//.*?$', '', cleaned, flags=re.MULTILINE)
        cleaned = re.sub(r'#.*?$', '', cleaned, flags=re.MULTILINE)
        cleaned = re.sub(r';.*?$', '', cleaned, flags=re.MULTILINE)

        # 清理空行和多余空格
        lines = []
        for line in cleaned.split('\n'):
            line = line.strip()
            if line and not line.startswith('[广告]') and not line.startswith('//'):
                lines.append(line)

        # 去重并保留顺序
        unique_lines = list(dict.fromkeys(lines))

        # 移除过短的无意义行
        unique_lines = [line for line in unique_lines if len(line) > 1 or (keep_timestamp and '[' in line)]

        return '\n'.join(unique_lines)

    return app  # 返回app实例，方便链式调用


# 导出注册函数
__all__ = ['register_lyric_routes']