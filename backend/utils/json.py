import json
import re

import pymysql

from backend.utils.db import get_db


# ========== 复用你原有代码的安全JSON解析函数 ==========
def safe_json_loads(s):
    if s is None or s == "":
        return None
    try:
        return json.loads(s)
    except (json.JSONDecodeError, TypeError):
        return None


def extract_tags_from_text(text):
    """从文本中自动提取匹配的其他风格名（复用歌手/专辑提取逻辑）"""
    if not text:
        return []

    try:
        db = get_db()
        cursor = db.cursor(pymysql.cursors.DictCursor)
        # 查询所有启用的风格标签（排除自身，避免自关联）
        cursor.execute("SELECT id, tags_name FROM album_tags WHERE is_enabled=1")
        tags = cursor.fetchall()

        # 构建「风格名→风格信息」映射（按长度降序匹配）
        tag_map = {}
        for t in tags:
            tag_map[t['tags_name']] = {"id": t['id'], "name": t['tags_name']}

        tag_names = sorted(tag_map.keys(), key=lambda x: len(x), reverse=True)
        pattern = re.compile(r'\b(' + '|'.join(re.escape(name) for name in tag_names) + r')\b')

        # 提取匹配的风格名（去重）
        matched_names = pattern.findall(text)
        matched_tags = []
        seen_ids = set()
        for name in matched_names:
            tag = tag_map[name]
            if tag['id'] not in seen_ids:
                seen_ids.add(tag['id'])
                matched_tags.append(tag)

        cursor.close()
        return matched_tags
    except Exception as e:
        print(f"❌ 提取风格名失败：{str(e)}")
        return []


def extract_albums_from_text(text):
    """从文本中自动提取匹配的专辑名（逻辑和歌手提取完全一致）"""
    if not text:
        return []

    try:
        db = get_db()
        cursor = db.cursor(pymysql.cursors.DictCursor)
        # 查询album_pool表中的专辑名
        cursor.execute("SELECT id, album_name FROM album_pool WHERE is_enabled=1")
        albums = cursor.fetchall()

        # 构建「专辑名→专辑信息」映射（按长度降序匹配，避免短名匹配长名）
        album_map = {}
        for a in albums:
            album_map[a['album_name']] = {"id": a['id'], "name": a['album_name']}

        album_names = sorted(album_map.keys(), key=lambda x: len(x), reverse=True)
        pattern = re.compile(r'\b(' + '|'.join(re.escape(name) for name in album_names) + r')\b')

        # 提取匹配的专辑名（去重）
        matched_names = pattern.findall(text)
        matched_albums = []
        seen_ids = set()
        for name in matched_names:
            album = album_map[name]
            if album['id'] not in seen_ids:
                seen_ids.add(album['id'])
                matched_albums.append(album)

        cursor.close()
        return matched_albums
    except Exception as e:
        print(f"❌ 提取专辑名失败：{str(e)}")
        return []


def extract_singers_from_text(text):
    """
    从文本中自动提取匹配的歌手名
    :param text: 上传的详细介绍文本
    :return: 匹配到的歌手列表（JSON格式），如 [{"id":1,"name":"周杰伦"},...]
    """
    if not text:
        return []

    try:
        db = get_db()
        cursor = db.cursor(pymysql.cursors.DictCursor)

        # 1. 查询所有歌手名和别名，构建匹配字典
        cursor.execute("SELECT id, singer_name, singer_alias FROM singers WHERE is_enabled=1")
        singers = cursor.fetchall()

        # 2. 构建「歌手名/别名 -> 歌手信息」的映射（优先匹配全名，避免别名冲突）
        singer_map = {}
        # 先存全名（优先级最高）
        for s in singers:
            singer_map[s['singer_name']] = {"id": s['id'], "name": s['singer_name']}
        # 再存别名（如果别名和全名重复，以全名为准）
        for s in singers:
            if s['singer_alias']:
                aliases = [alias.strip() for alias in s['singer_alias'].split(',') if alias.strip()]
                for alias in aliases:
                    if alias not in singer_map:
                        singer_map[alias] = {"id": s['id'], "name": s['singer_name']}

        # 3. 按「名字长度降序」生成正则表达式（避免短名匹配长名，如先匹配「陈奕迅」再匹配「陈」）
        singer_names = sorted(singer_map.keys(), key=lambda x: len(x), reverse=True)
        # 转义特殊字符，避免正则报错
        pattern = re.compile(r'\b(' + '|'.join(re.escape(name) for name in singer_names) + r')\b')

        # 4. 扫描文本，提取匹配的歌手名（去重）
        matched_names = pattern.findall(text)
        matched_singers = []
        seen_ids = set()
        for name in matched_names:
            singer = singer_map[name]
            if singer['id'] not in seen_ids:
                seen_ids.add(singer['id'])
                matched_singers.append(singer)

        cursor.close()
        return matched_singers
    except Exception as e:
        print(f"❌ 提取歌手名失败：{str(e)}")
        return []
    finally:
        if 'db' in locals() and db.open:
            db.close()