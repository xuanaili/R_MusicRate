# ========== ✅ 核心复用：封装标签统计复用函数（所有接口共用） ==========
import json
import random


def get_album_tag_stats(album_pool_id, cursor):
    """
    复用标签统计逻辑，给搜索接口调用
    :param album_pool_id: 专辑池id
    :param cursor: 数据库游标（复用连接，提升性能）
    :return: 统计后的标签数组
    """
    tag_count = {}
    total_tags = 0

    # 1. 查公共专辑池的基础标签
    cursor.execute('SELECT tags FROM album_pool WHERE id = %s', (album_pool_id,))
    pool_album = cursor.fetchone()
    if pool_album and pool_album['tags']:
        try:
            pool_tags = json.loads(pool_album['tags'])
            for tag in pool_tags:
                tag = tag.strip()
                if tag:
                    tag_count[tag] = tag_count.get(tag, 0) + 1
                    total_tags += 1
        except:
            pass

    # 2. 遍历所有用户表统计标签
    cursor.execute('SELECT TABLE_NAME FROM information_schema.TABLES WHERE TABLE_NAME LIKE "albums_%"')
    user_tables = cursor.fetchall()
    for table in user_tables:
        table_name = table['TABLE_NAME']
        try:
            cursor.execute(f'''
                SELECT tags FROM `{table_name}` 
                WHERE source_pool_id = %s AND tags IS NOT NULL
            ''', (album_pool_id,))
            user_albums = cursor.fetchall()
            for album in user_albums:
                if album['tags']:
                    try:
                        tags = json.loads(album['tags'])
                        for tag in tags:
                            tag = tag.strip()
                            if tag:
                                tag_count[tag] = tag_count.get(tag, 0) + 1
                                total_tags += 1
                    except:
                        continue
        except Exception as e:
            print(f"统计用户表 {table_name} 失败：{str(e)}")
            continue

    # 3. 计算占比，过滤<10%的标签，生成颜色和大小
    result = []
    if total_tags > 0:
        for tag, count in tag_count.items():
            percent = (count / total_tags) * 100
            if percent >= 10:
                size = int(percent * 2 + 40)
                color = f"#{random.randint(0, 0xFFFFFF):06x}"
                result.append({
                    "tag": tag,
                    "count": count,
                    "percent": round(percent, 1),
                    "size": size,
                    "color": color
                })
    return result