from flask import request, jsonify
import json
import traceback
from backend.utils.db import get_db, get_current_user_id

import pymysql

from backend.utils.decorators import login_required


def register_tags_routes(app):
    """注册音乐风格标签相关路由（新增标签）"""

    # ✅ 1. 新增音乐风格标签接口（仅管理员可访问）
    @app.route('/api/tags/add', methods=['POST', 'OPTIONS'])
    @login_required
    def add_album_tag():
        try:
            # ========== 管理员权限校验 ==========
            current_user_id = get_current_user_id()
            if not current_user_id:
                return jsonify({"code": 401, "msg": "用户未登录！"}), 200

            # 查询当前用户是否为管理员
            db = get_db()
            cursor = db.cursor(pymysql.cursors.DictCursor)
            cursor.execute('SELECT is_admin FROM users WHERE user_id = %s', (current_user_id,))
            user = cursor.fetchone()
            # 移除 cursor.close() —— 交给 Flask 自动处理

            # 验证：is_admin=1 才是管理员
            if not user or user.get('is_admin') != 1:
                return jsonify({"code": 403, "msg": "无管理员权限，禁止添加风格！"}), 200

            # ========== 原有逻辑保留（移除手动关闭） ==========
            # 获取请求数据
            data = request.get_json()
            if not data:
                return jsonify({"code": 400, "msg": "请求参数不能为空！"}), 200

            # 提取参数并默认值处理
            tags_name = data.get('tags_name', '').strip()
            aka_name = data.get('aka_name', '').strip()
            parameter_style = data.get('parameter_style', '{}').strip()
            brief_intro = data.get('brief_intro', '').strip()
            detail_intro = data.get('detail_intro', '').strip()
            parent_tag_ids = data.get('parent_tag_ids', '').strip()

            # 必输项校验
            if not tags_name:
                return jsonify({"code": 400, "msg": "风格名称不能为空！"}), 200

            # 检查标签名是否已存在
            cursor.execute('''
                SELECT id FROM album_tags WHERE tags_name = %s AND is_enabled=1
            ''', (tags_name,))
            existing_tag = cursor.fetchone()
            if existing_tag:
                # 移除 cursor.close() 和 db.close()
                return jsonify({"code": 400, "msg": f"风格名称「{tags_name}」已存在！"}), 200

            # 构造插入数据
            insert_data = {
                'tags_name': tags_name,
                'aka_name': aka_name,
                'parameter_style': parameter_style,
                'brief_intro': brief_intro,
                'detail_intro': detail_intro,
                'parent_tag_ids': parent_tag_ids,
                'related_singers': '[]',
                'related_albums': '[]',
                'related_tags': '[]'
            }

            # 插入数据库
            cursor.execute('''
                INSERT INTO album_tags (
                    tags_name, aka_name, parameter_style, brief_intro, 
                    detail_intro, parent_tag_ids, related_singers, 
                    related_albums, related_tags
                ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
            ''', (
                insert_data['tags_name'],
                insert_data['aka_name'],
                insert_data['parameter_style'],
                insert_data['brief_intro'],
                insert_data['detail_intro'],
                insert_data['parent_tag_ids'],
                insert_data['related_singers'],
                insert_data['related_albums'],
                insert_data['related_tags']
            ))
            db.commit()
            tag_id = cursor.lastrowid

            # 移除所有手动关闭连接的代码
            # cursor.close() 和 db.close() 都删掉

            return jsonify({
                "code": 200,
                "msg": "音乐风格添加成功！",
                "data": {
                    "tag_id": tag_id,
                    "tags_name": tags_name
                }
            })

        except Exception as e:
            # 回滚事务（仅当连接未关闭时）
            if 'db' in locals() and not db._closed:
                db.rollback()
            print(f"❌ 新增音乐风格出错：{str(e)}")
            print(traceback.format_exc())
            return jsonify({"code": 500, "msg": f"添加风格失败：{str(e)}"}), 200

    # ✅ 2. 获取所有标签列表接口
    @app.route('/api/tags/list', methods=['GET', 'OPTIONS'])
    @login_required
    def get_tags_list():
        try:
            db = get_db()
            cursor = db.cursor(pymysql.cursors.DictCursor)

            # 查询所有启用的标签
            cursor.execute('''
                SELECT id, tags_name, aka_name, brief_intro 
                FROM album_tags 
                WHERE is_enabled=1 
                ORDER BY create_time DESC
            ''')
            tags_list = cursor.fetchall()

            # 移除 cursor.close() 和 db.close()

            return jsonify({
                "code": 200,
                "msg": "获取风格列表成功！",
                "data": {"tags_list": tags_list}
            })

        except Exception as e:
            print(f"❌ 获取风格列表出错：{str(e)}")
            print(traceback.format_exc())
            return jsonify({"code": 500, "msg": f"获取风格列表失败：{str(e)}"}), 200