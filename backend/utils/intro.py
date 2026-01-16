import pymysql

from backend.utils.db import get_db


def save_user_album_intro(user_id, album_id, intro_content):
    try:
        db = get_db()
        cursor = db.cursor()
        cursor.execute('''
            SELECT id FROM user_album_intro WHERE user_id = %s AND album_id = %s
        ''', (user_id, album_id))
        existing = cursor.fetchone()

        if existing:
            cursor.execute('''
                UPDATE user_album_intro 
                SET album_intro = %s 
                WHERE user_id = %s AND album_id = %s
            ''', (intro_content, user_id, album_id))
        else:
            cursor.execute('''
                INSERT INTO user_album_intro (user_id, album_id, album_intro) 
                VALUES (%s, %s, %s)
            ''', (user_id, album_id, intro_content))

        # 第二步：同步更新 albums_用户ID 表中的 album_intro 字段
        table_name = f"albums_{user_id}"
        # 先检查表是否存在（避免表不存在报错）
        cursor.execute('''
            SELECT TABLE_NAME FROM information_schema.TABLES 
            WHERE TABLE_NAME = %s AND TABLE_SCHEMA = DATABASE()
        ''', (table_name,))
        table_exist = cursor.fetchone()
        if table_exist:
            # 更新该用户表中对应专辑的简介
            cursor.execute(f'''
                UPDATE `{table_name}` 
                SET album_intro = %s 
                WHERE id = %s
            ''', (intro_content, album_id))



        db.commit()
        cursor.close()
        return True
    except Exception as e:
        db.rollback()
        print(f"❌ 保存用户专辑简介失败：{str(e)}")
        return False

def get_user_album_intro(user_id, album_id):
    try:
        db = get_db()
        cursor = db.cursor(pymysql.cursors.DictCursor)
        cursor.execute('''
            SELECT album_intro FROM user_album_intro 
            WHERE user_id = %s AND album_id = %s
        ''', (user_id, album_id))
        result = cursor.fetchone()
        cursor.close()
        return result['album_intro'] if result else ""
    except Exception as e:
        print(f"❌ 获取用户专辑简介失败：{str(e)}")
        return ""