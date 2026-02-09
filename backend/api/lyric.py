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
import struct
import zlib

# 增强版请求头，模拟真实浏览器
HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36 Edg/120.0.0.0',
    'Referer': 'https://music.163.com/',
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
    """注册歌词相关路由（长文本存储版）"""

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

    # ✅ 3. 自动获取多平台歌词接口
    @app.route('/api/lyric/fetch_auto', methods=['POST', 'OPTIONS'])
    @login_required
    def fetch_auto_lyric():
        """增强版自动获取歌词，添加详细日志和备用方案"""
        try:
            data = request.get_json()
            song_name = data.get('song_name', '').strip()
            artist = data.get('artist', '').strip()
            duration = data.get('duration', 0)

            if not song_name:
                return jsonify({"code": 400, "msg": "歌曲名不能为空！"}), 200

            print(f"\n🎵 开始获取歌词：{song_name} - {artist}")

            result = {
                "netease": {"status": "failed", "lyric": "", "msg": ""},
                "kugou": {"status": "failed", "lyric": "", "msg": ""},
                "genius": {"status": "failed", "lyric": "", "msg": ""},
                "qq": {"status": "failed", "lyric": "", "msg": ""}
            }

            # 1. 网易云（主方案）- 增加重试和更详细的错误日志
            try:
                print("尝试网易云...")
                # 随机延迟，避免被风控
                time.sleep(random.uniform(0.5, 1.5))
                netease_lyric = fetch_netease_lyric(song_name, artist, duration)
                if netease_lyric:
                    result["netease"] = {
                        "status": "success",
                        "lyric": netease_lyric,
                        "msg": f"获取成功，{len(netease_lyric)}字符"
                    }
                    print(f"✅ 网易云成功: {len(netease_lyric)}字符")
                else:
                    result["netease"]["msg"] = "未找到歌词"
                    print("❌ 网易云无结果")
            except Exception as e:
                error_msg = str(e)[:100]
                result["netease"]["msg"] = f"接口错误: {error_msg}"
                print(f"❌ 网易云异常: 网易云接口错误：{e}")
                # 打印详细的错误堆栈
                print(traceback.format_exc())

            # 2. 酷狗（第二方案）
            try:
                print("尝试酷狗...")
                time.sleep(random.uniform(0.5, 1.5))
                kugou_lyric = fetch_kugou_lyric(song_name, artist, duration)
                if kugou_lyric:
                    result["kugou"] = {
                        "status": "success",
                        "lyric": kugou_lyric,
                        "msg": f"获取成功，{len(kugou_lyric)}字符"
                    }
                    print(f"✅ 酷狗成功: {len(kugou_lyric)}字符")
                else:
                    result["kugou"]["msg"] = "未找到歌词"
                    print("❌ 酷狗无结果")
            except Exception as e:
                error_msg = str(e)[:100]
                result["kugou"]["msg"] = f"接口错误: {error_msg}"
                print(f"❌ 酷狗异常: {e}")

            # 3. QQ音乐（新增备用）
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
                    print(qq_lyric)
                else:
                    result["qq"]["msg"] = "未找到歌词"
                    print("❌ QQ音乐无结果")
            except Exception as e:
                result["qq"]["msg"] = str(e)[:100]
                print(f"❌ QQ音乐异常: {e}")

            # 4. Genius（最后尝试）
            if not any(r["status"] == "success" for r in result.values()):
                try:
                    print("尝试Genius...")
                    time.sleep(random.uniform(0.5, 1.5))
                    genius_lyric = fetch_genius_lyric(song_name, artist)
                    if genius_lyric:
                        result["genius"] = {
                            "status": "success",
                            "lyric": genius_lyric,
                            "msg": f"获取成功，{len(genius_lyric)}字符"
                        }
                        print(f"✅ Genius成功: {len(genius_lyric)}字符")
                    else:
                        result["genius"]["msg"] = "未找到歌词"
                        print("❌ Genius无结果")
                except Exception as e:
                    result["genius"]["msg"] = str(e)[:100]
                    print(f"❌ Genius异常: {e}")

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

    # ==================== 各平台歌词获取函数（修复增强版） ====================

    def fetch_qq_lyric(song_name, artist):
        """QQ音乐备用接口（增强版）"""
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

    def parse_kugou_krc(krc_content):
        """解析酷狗KRC格式歌词（增强版）"""
        try:
            # 检查是否为KRC格式
            if not krc_content or (isinstance(krc_content, str) and not krc_content.startswith('krc1')):
                return clean_lyric(krc_content, keep_timestamp=True)

            # KRC解密密钥
            key = [64, 71, 97, 119, 94, 50, 116, 71, 81, 54, 49, 45, 206, 210, 110, 105]

            # 移除krc1头部
            encrypted_data = krc_content[4:] if isinstance(krc_content, str) else krc_content[4:]

            # 解密数据
            decrypted_bytes = bytearray()
            for i, byte in enumerate(encrypted_data):
                if isinstance(byte, str):
                    byte = ord(byte)
                decrypted_bytes.append(byte ^ key[i % 16])

            # 解压缩
            try:
                decompressed_data = zlib.decompress(bytes(decrypted_bytes))
            except:
                decompressed_data = bytes(decrypted_bytes)

            # 解析KRC格式
            lyric_text = parse_krc_binary(decompressed_data)

            return clean_lyric(lyric_text, keep_timestamp=True)

        except Exception as e:
            print(f"KRC解析失败: {e}")
            return extract_text_from_krc(krc_content)

    def parse_krc_binary(data):
        """解析KRC二进制数据（增强版）"""
        if not data:
            return ""

        lines = []
        pos = 0
        data_len = len(data)

        while pos < data_len:
            try:
                if pos + 8 > data_len:
                    break

                # 读取时间戳和长度
                timestamp = struct.unpack('<I', data[pos:pos + 4])[0]
                pos += 4

                lyric_len = struct.unpack('<I', data[pos:pos + 4])[0]
                pos += 4

                if lyric_len == 0 or pos + lyric_len > data_len:
                    break

                # 读取歌词文本
                lyric_text = data[pos:pos + lyric_len].decode('utf-8', errors='ignore')
                pos += lyric_len

                # 格式化时间戳
                minutes = timestamp // 60000
                seconds = (timestamp % 60000) / 1000
                timestamp_str = f"[{minutes:02d}:{seconds:06.3f}]".replace('.', ':')

                # 清理歌词文本
                clean_text = re.sub(r'<\d+,\d+,\d+>', '', lyric_text)
                clean_text = re.sub(r'\([^)]*\)', '', clean_text)
                clean_text = clean_text.strip()

                if clean_text:
                    lines.append(f"{timestamp_str}{clean_text}")

            except:
                pos += 1

        return '\n'.join(lines)

    def extract_text_from_krc(krc_content):
        """从KRC内容中提取文本（降级方案）"""
        try:
            # 提取中文字符、英文字符和常见标点
            text_matches = re.findall(r'[\u4e00-\u9fff\w\s,.!?;:，。！？；：、]+', str(krc_content))
            extracted = ' '.join(text_matches)

            if not extracted:
                try:
                    decoded = str(krc_content).encode('utf-8', errors='ignore').decode('utf-8', errors='ignore')
                    decoded = re.sub(r'[\x00-\x1f\x7f-\x9f]', '', decoded)
                    return decoded
                except:
                    return ""

            return extracted
        except:
            return ""

    def fetch_netease_lyric(song_name, artist, duration=0):
        """
        获取网易云音乐歌词（修复增强版）
        解决 Expecting value: line 1 column 1 (char 0) 错误
        """
        try:
            # 方案1: 使用官方API（带更完善的请求头和错误处理）
            search_url = "https://music.163.com/api/search/get/"
            search_params = {
                's': f"{song_name} {artist}",
                'type': 1,
                'limit': 10,
                'offset': 0,
                'total': True,
                'csrf_token': ''
            }

            headers = {
                **HEADERS,
                'Referer': 'https://music.163.com/search/',
                'Host': 'music.163.com',
                'X-Real-IP': '114.114.114.114',  # 模拟真实IP
            }

            # 发送请求并处理响应
            response = SESSION.get(search_url, params=search_params, headers=headers, timeout=10)

            # 打印响应信息用于调试
            print(f"网易云响应状态码: {response.status_code}")
            print(f"网易云响应内容长度: {len(response.text)}")

            if response.status_code != 200:
                print(f"网易云返回非200状态码: {response.status_code}")
                # 尝试方案2: 使用备用接口
                return fetch_netease_lyric_backup(song_name, artist)

            # 处理响应内容
            try:
                search_result = response.json()
            except json.JSONDecodeError as e:
                print(f"网易云返回非JSON内容: {response.text[:200]}")
                # 尝试方案2: 使用备用接口
                return fetch_netease_lyric_backup(song_name, artist)

            if not search_result.get('result', {}).get('songs'):
                print("网易云未搜索到歌曲")
                return ""

            # 选择最佳匹配
            songs = search_result['result']['songs']
            best_match = None

            # 智能匹配（优先完全匹配）
            song_name_lower = song_name.lower()
            artist_lower = artist.lower()

            for song in songs:
                song_name_api = song.get('name', '').lower()
                song_artists = [ar['name'].lower() for ar in song.get('artists', [])]

                # 匹配规则：歌曲名包含 + 歌手包含
                if (song_name_lower in song_name_api or song_name_api in song_name_lower) and \
                        (any(artist_lower in a for a in song_artists) or not artist_lower):
                    best_match = song
                    break

            if not best_match:
                best_match = songs[0]

            song_id = best_match['id']
            print(f"选中歌曲ID: {song_id}")

            # 获取歌词 - 使用更稳定的接口
            lyric_url = f"https://music.163.com/api/song/lyric/v1?id={song_id}&lv=1&kv=1&tv=-1"

            lyric_response = SESSION.get(lyric_url, headers=headers, timeout=10)

            if lyric_response.status_code != 200:
                print(f"歌词接口返回非200状态码: {lyric_response.status_code}")
                return ""

            try:
                lyric_data = lyric_response.json()
            except json.JSONDecodeError:
                print(f"歌词接口返回非JSON内容: {lyric_response.text[:200]}")
                return ""

            # 解析歌词
            lyric_text = ""

            # 优先获取原版歌词
            if 'lrc' in lyric_data and lyric_data['lrc'].get('lyric'):
                lyric_text = lyric_data['lrc']['lyric']

            # 合并翻译歌词
            if 'tlyric' in lyric_data and lyric_data['tlyric'].get('lyric'):
                trans_lyric = lyric_data['tlyric']['lyric']
                if trans_lyric and trans_lyric != '[99:00.00]纯音乐，请欣赏\n':
                    lyric_text += "\n\n【翻译】\n" + trans_lyric

            return clean_lyric(lyric_text, keep_timestamp=True) if lyric_text else ""

        except Exception as e:
            print(f"网易云歌词获取详细错误: {str(e)}")
            # 尝试备用方案
            try:
                return fetch_netease_lyric_backup(song_name, artist)
            except:
                raise Exception(f"网易云接口错误：{str(e)}")

    def fetch_netease_lyric_backup(song_name, artist):
        """网易云备用接口（使用第三方公开API）"""
        try:
            # 使用公开的网易云歌词API作为备用
            backup_url = f"https://api.uomg.com/api/lyric?song={quote(song_name)}&singer={quote(artist)}"
            response = SESSION.get(backup_url, timeout=10)

            if response.status_code == 200:
                data = response.json()
                if data.get('code') == 1 and data.get('data', {}).get('lyric'):
                    return clean_lyric(data['data']['lyric'], keep_timestamp=True)

            return ""
        except:
            return ""

    def fetch_kugou_lyric(song_name, artist, duration=0):
        """获取酷狗音乐歌词（修复增强版）"""
        try:
            # 1. 访问首页获取cookies
            SESSION.get("https://www.kugou.com/", timeout=5)

            # 2. 搜索歌曲
            search_params = {
                'keyword': f"{song_name} {artist}",
                'page': 1,
                'pagesize': 10,
                'platform': 'WebFilter',
                'format': 'json',
                'userid': -1,
                'clientver': '',
                'clienttime': int(time.time()),
                'mid': str(int(time.time())),
                'uuid': str(int(time.time())),
            }

            headers = {
                **HEADERS,
                'Referer': 'https://www.kugou.com/',
                'Host': 'songsearch.kugou.com',
                'X-Requested-With': 'XMLHttpRequest',
            }

            response = SESSION.get(
                "https://songsearch.kugou.com/song_search_v2",
                params=search_params,
                headers=headers,
                timeout=10
            )

            if response.status_code != 200:
                return fetch_kugou_backup_lyric_by_name(song_name, artist)

            search_data = response.json()

            if not search_data.get('data', {}).get('lists'):
                print("酷狗未搜索到歌曲")
                return ""

            # 3. 智能匹配歌曲
            best_match = None
            song_name_lower = song_name.lower()
            artist_lower = artist.lower()

            for song in search_data['data']['lists']:
                song_title = html.unescape(song.get('SongName', '')).lower()
                singer_name = html.unescape(song.get('Singername', '')).lower()

                if (song_name_lower in song_title or song_title in song_name_lower) and \
                        (artist_lower in singer_name or not artist_lower):
                    best_match = song
                    break

            if not best_match:
                best_match = search_data['data']['lists'][0]

            # 4. 获取歌词
            hash_value = best_match.get('FileHash', '')
            album_id = best_match.get('AlbumID', '')

            if not hash_value:
                return ""

            # 使用新的酷狗歌词API
            lyric_url = "https://krcs.kugou.com/search"
            lyric_params = {
                'ver': 1,
                'man': 'yes',
                'client': 'mobi',
                'hash': hash_value,
                'album_audio_id': album_id,
                '_': int(time.time() * 1000)
            }

            lyric_headers = {
                **HEADERS,
                'Referer': 'https://www.kugou.com/',
                'Host': 'krcs.kugou.com',
            }

            lyric_response = SESSION.get(lyric_url, params=lyric_params, headers=lyric_headers, timeout=10)

            if lyric_response.status_code != 200:
                return fetch_kugou_backup_lyric(hash_value)

            lyric_data = lyric_response.json()

            if lyric_data.get('status') != 1 or not lyric_data.get('candidates'):
                return fetch_kugou_backup_lyric(hash_value)

            # 获取歌词内容
            lyric_info = lyric_data['candidates'][0]
            lyric_id = lyric_info.get('id', '')
            accesskey = lyric_info.get('accesskey', '')

            if not lyric_id or not accesskey:
                return ""

            # 下载歌词文件
            download_url = f"https://krcs.kugou.com/download?ver=1&client=pc&id={lyric_id}&accesskey={accesskey}&fmt=krc&charset=utf8"
            lyric_response = SESSION.get(download_url, timeout=10)

            if lyric_response.status_code != 200:
                return ""

            # 解析KRC歌词
            raw_lyric = lyric_response.text
            cleaned_lyric = parse_kugou_krc(raw_lyric)

            return cleaned_lyric

        except Exception as e:
            print(f"酷狗歌词获取详细错误: {str(e)}")
            # 尝试多种备用方案
            try:
                return fetch_kugou_simple(song_name, artist)
            except:
                try:
                    return fetch_kugou_backup_lyric_by_name(song_name, artist)
                except:
                    raise Exception(f"酷狗接口错误：{str(e)}")

    def fetch_kugou_backup_lyric(hash_value):
        """酷狗备用接口"""
        try:
            url = f"https://lyrics.kugou.com/download"
            params = {
                'ver': 1,
                'client': 'pc',
                'fmt': 'lrc',
                'charset': 'utf8',
                'id': hash_value,
                'accesskey': hash_value,
                '_': int(time.time() * 1000)
            }

            response = SESSION.get(url, params=params, timeout=10)
            if response.status_code == 200:
                data = response.json()
                if data.get('status') == 200:
                    lyric_content = data.get('content', '')
                    if lyric_content:
                        decoded = base64.b64decode(lyric_content).decode('utf-8', errors='ignore')
                        return clean_lyric(decoded, keep_timestamp=True)
            return ""
        except:
            return ""

    def fetch_kugou_backup_lyric_by_name(song_name, artist):
        """通过歌名歌手直接获取酷狗歌词"""
        try:
            url = f"https://api.kugou.com/lyric/search?keyword={quote(f'{song_name} {artist}')}&format=json"
            response = SESSION.get(url, timeout=10)

            if response.status_code == 200:
                data = response.json()
                if data.get('status') == 0 and data.get('candidates'):
                    lyric_id = data['candidates'][0].get('id')
                    if lyric_id:
                        lyric_url = f"https://api.kugou.com/lyric/detail?lyricId={lyric_id}&format=json"
                        lyric_resp = SESSION.get(lyric_url, timeout=10)
                        if lyric_resp.status_code == 200:
                            lyric_data = lyric_resp.json()
                            if lyric_data.get('status') == 0:
                                return clean_lyric(lyric_data.get('content', ''), keep_timestamp=True)
            return ""
        except:
            return ""

    def fetch_kugou_simple(song_name, artist):
        """最简单的酷狗歌词获取（通过网页解析）"""
        try:
            search_url = f"https://www.kugou.com/yy/song/detail/{quote(song_name + '-' + artist)}.html"

            response = SESSION.get(search_url, timeout=10)

            # 多种正则匹配方式
            patterns = [
                r'<div class="lyric" id="lyric-content">([\s\S]*?)</div>',
                r'data-lyrics="([^"]+)"',
                r'<p class="lyric-line">([^<]+)</p>'
            ]

            for pattern in patterns:
                match = re.search(pattern, response.text)
                if match:
                    lyric = html.unescape(match.group(1))
                    return clean_lyric(lyric, keep_timestamp=False)

            return ""
        except:
            return ""

    def fetch_genius_lyric(song_name, artist):
        """获取Genius歌词（修复增强版）"""
        try:
            # 1. 使用更稳定的搜索接口
            search_term = f"{song_name} {artist}"
            search_url = f"https://genius.com/api/search/song?q={quote(search_term)}"

            headers = {
                **HEADERS,
                'Referer': 'https://genius.com/',
                'Host': 'genius.com',
                'Accept-Language': 'en-US,en;q=0.9',
            }

            response = SESSION.get(search_url, headers=headers, timeout=15)

            if response.status_code != 200:
                return ""

            data = response.json()

            # 2. 寻找歌曲URL
            song_url = None
            hits = data.get('response', {}).get('hits', [])

            for hit in hits:
                result = hit.get('result', {})
                if result.get('_type') == 'song':
                    primary_artist = result.get('primary_artist', {}).get('name', '').lower()
                    if artist.lower() in primary_artist or not artist:
                        song_url = result.get('url')
                        break

            if not song_url:
                return ""

            # 3. 获取歌词页面
            page_response = SESSION.get(song_url, headers=headers, timeout=15)

            if page_response.status_code != 200:
                return ""

            # 4. 多种方式解析歌词
            html_content = page_response.text

            # 方法1: 新的Genius歌词容器
            lyric_sections = re.findall(r'<div[^>]*data-lyrics-container="true"[^>]*>([\s\S]*?)</div>', html_content)

            if lyric_sections:
                raw_lyric = ''.join(lyric_sections)
            else:
                # 方法2: 传统方式
                lyric_match = re.search(r'<div class="lyrics">([\s\S]*?)</div>', html_content)
                if lyric_match:
                    raw_lyric = lyric_match.group(1)
                else:
                    # 方法3: 备用选择器
                    lyric_match = re.search(r'<div[^>]*class="[^"]*Lyrics__Container[^"]*"[^>]*>([\s\S]*?)</div>',
                                            html_content)
                    if lyric_match:
                        raw_lyric = lyric_match.group(1)
                    else:
                        return ""

            # 5. 深度清理歌词
            raw_lyric = re.sub(r'<[^>]+>', '', raw_lyric)
            raw_lyric = html.unescape(raw_lyric)

            # 移除广告、注释等无关内容
            raw_lyric = re.sub(r'(\[.*?\])|(\(.*?\))', '', raw_lyric)

            # 清理空白行和重复行
            lines = [line.strip() for line in raw_lyric.split('\n') if line.strip()]
            seen = set()
            unique_lines = []

            for line in lines:
                if line not in seen and len(line) > 1:
                    seen.add(line)
                    unique_lines.append(line)

            return '\n'.join(unique_lines)

        except Exception as e:
            print(f"Genius歌词获取详细错误: {str(e)}")
            return ""

    def clean_lyric(raw_lyric, keep_timestamp=True):
        """
        清理歌词格式（修复增强版）
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