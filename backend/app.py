from flask import Flask, request, jsonify, g, send_from_directory
from flask_cors import CORS
import json
import os
import uuid
from functools import wraps
import traceback
import pymysql
from pymysql.err import ProgrammingError
import requests

# ========== 基础配置 ==========
app = Flask(__name__)
CORS(app, supports_credentials=True)
app.secret_key = 'music-rate-secret-key'

# MySQL配置（替换为你的实际配置）
MYSQL_CONFIG = {
    'host': 'localhost',
    'port': 3306,
    'user': 'music_user',
    'password': '123456',  # 替换为你设置的密码
    'db': 'music_rate',
    'charset': 'utf8mb4',
    'cursorclass': pymysql.cursors.DictCursor  # 默认返回字典格式
}

# 全局变量：当前登录用户ID
current_user_id = None


# ========== 数据库核心工具（适配MySQL+分表） ==========
def get_db():
    """获取MySQL连接（Flask上下文隔离）"""
    db = getattr(g, '_database', None)
    if db is None:
        try:
            db = g._database = pymysql.connect(**MYSQL_CONFIG)
        except pymysql.MySQLError as e:
            print(f"MySQL连接失败：{str(e)}")
            raise e  # 抛出异常，让启动时能发现问题
    return db


@app.teardown_appcontext
def close_db(exception):
    """关闭MySQL连接"""
    db = getattr(g, '_database', None)
    if db is not None:
        db.close()


def get_album_table_name(user_id):
    """生成用户专属的专辑表名：albums_用户ID"""
    return f'albums_{user_id}'


def create_user_album_table(user_id):
    """为新用户创建专属的专辑表"""
    try:
        db = get_db()
        cursor = db.cursor()
        table_name = get_album_table_name(user_id)
        # 修复：移除所有TEXT字段的DEFAULT默认值（MySQL语法限制）
        cursor.execute(f'''
            CREATE TABLE IF NOT EXISTS `{table_name}` (
                id INT PRIMARY KEY AUTO_INCREMENT,
                album_name VARCHAR(100) NOT NULL,
                cover_img VARCHAR(255) DEFAULT "",
                singer VARCHAR(100) NOT NULL,
                release_year INT NOT NULL,
                start_time VARCHAR(50) DEFAULT "",
                track_count INT DEFAULT 0,
                track_duration VARCHAR(50) DEFAULT "",
                my_score FLOAT DEFAULT 0.0,
                burn_class VARCHAR(50) DEFAULT "",
                duration_type VARCHAR(50) DEFAULT "",
                tags TEXT,  -- 移除DEFAULT ""
                main_type TEXT,  -- 移除DEFAULT ""
                code VARCHAR(50) DEFAULT "",
                video_shared VARCHAR(50) DEFAULT "",
                mandopop_code VARCHAR(50) DEFAULT "",
                tracks TEXT,  -- 移除DEFAULT ""
                review TEXT,  -- 移除DEFAULT ""
                score FLOAT DEFAULT 0.0,
                comments TEXT,  -- 移除DEFAULT ""
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
        ''')
        db.commit()
        cursor.close()
        print(f"为用户{user_id}创建专辑表{table_name}成功！")
    except Exception as e:
        print(f"创建用户专辑表失败：{str(e)}")
        raise e


def check_and_create_user_album_table(user_id):
    """检查用户专辑表是否存在，不存在则创建"""
    try:
        db = get_db()
        cursor = db.cursor()
        table_name = get_album_table_name(user_id)
        # 检查表是否存在
        cursor.execute(f'''
            SELECT COUNT(*) FROM information_schema.TABLES 
            WHERE TABLE_SCHEMA = %s AND TABLE_NAME = %s
        ''', (MYSQL_CONFIG['db'], table_name))
        table_exists = cursor.fetchone()['COUNT(*)'] > 0

        if not table_exists:
            # 表不存在则创建
            create_user_album_table(user_id)
        cursor.close()
    except Exception as e:
        print(f"检查/创建用户专辑表失败：{str(e)}")
        raise e


def init_base_tables():
    """初始化基础表（仅users表，专辑表按用户动态创建）"""
    try:
        db = get_db()
        cursor = db.cursor()
        # 创建用户表（核心基础表，不分表）
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS users (
                id INT PRIMARY KEY AUTO_INCREMENT,
                username VARCHAR(50) UNIQUE NOT NULL,
                password VARCHAR(50) NOT NULL,
                token VARCHAR(100) DEFAULT "",
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
        ''')

        # ========== 修复：创建专辑搜索池表（解决TEXT索引长度问题） ==========
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS album_pool (
                id INT PRIMARY KEY AUTO_INCREMENT,
                album_name VARCHAR(100) NOT NULL,
                cover_img VARCHAR(255) DEFAULT "",
                singer VARCHAR(100) NOT NULL,
                release_year INT NOT NULL,
                main_type VARCHAR(50) DEFAULT "",  # 改VARCHAR更合适（短文本）
                tags TEXT,
                my_score FLOAT DEFAULT 0.0,
                create_user INT NOT NULL COMMENT '创建用户ID',
                create_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                -- 修复：给TEXT字段的索引指定长度，VARCHAR字段无需指定
                INDEX idx_album_name (album_name),
                INDEX idx_singer (singer),
                INDEX idx_tags (tags(50)),  # 指定索引长度为50（足够匹配关键词）
                INDEX idx_main_type (main_type)  # VARCHAR字段直接索引
            ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='专辑搜索池表';
        ''')

        db.commit()
        cursor.close()
        print("MySQL基础表（users + album_pool）初始化成功！")

        # 初始化默认admin用户（如果不存在）
        init_default_admin()
    except Exception as e:
        print(f"初始化基础表失败：{str(e)}")
        print(traceback.format_exc())


def init_default_admin():
    """初始化默认admin用户，并创建其专属专辑表"""
    try:
        db = get_db()
        cursor = db.cursor()
        # 检查admin是否存在
        cursor.execute('SELECT id FROM users WHERE username = "admin"')
        user = cursor.fetchone()
        if not user:
            # 创建admin用户
            cursor.execute('''
                INSERT INTO users (username, password, token) 
                VALUES ("admin", "123456", "")
            ''')
            admin_id = cursor.lastrowid
            db.commit()
            # 为admin创建专属专辑表
            create_user_album_table(admin_id)
            print("默认admin用户创建成功，并生成专属专辑表！")
        else:
            print("默认admin用户已存在，无需重复创建")
        cursor.close()
    except Exception as e:
        print(f"初始化admin用户失败：{str(e)}")
        print(traceback.format_exc())


# ========== 登录校验装饰器（适配MySQL） ==========
def login_required(func):
    @wraps(func)
    def wrapper(*args, **kwargs):
        global current_user_id
        current_user_id = None
        try:
            token = request.headers.get('Authorization')
            if not token:
                return jsonify({"code": 401, "msg": "请先登录！"}), 401

            # MySQL验证token
            db = get_db()
            cursor = db.cursor()
            cursor.execute('SELECT id, username FROM users WHERE token = %s', (token,))
            user = cursor.fetchone()
            cursor.close()

            if not user:
                return jsonify({"code": 401, "msg": "登录已过期，请重新登录！"}), 401

            current_user_id = user["id"]
            # 关键修复：登录成功后，检查并创建用户专辑表
            check_and_create_user_album_table(current_user_id)

            return func(*args, **kwargs)
        except Exception as e:
            print(f"登录校验失败：{str(e)}")
            print(traceback.format_exc())
            return jsonify({"code": 500, "msg": f"登录校验出错：{str(e)}"}), 500

    return wrapper


# ========== 自建本地图床（免费、直链永久有效） ==========
# 1. 配置图片保存路径（自动创建文件夹）
UPLOAD_FOLDER = "./album_covers"  # 图片保存在项目根目录的album_covers文件夹
if not os.path.exists(UPLOAD_FOLDER):
    os.makedirs(UPLOAD_FOLDER)


# 2. 新增：提供图片访问的接口（用于前端显示封面）
@app.route('/covers/<filename>')
def serve_cover(filename):
    return send_from_directory(UPLOAD_FOLDER, filename)


# 3. 上传图片接口（替换原有imgBB/SM.MS逻辑）
@app.route('/api/upload_img', methods=['POST'])
def upload_img_proxy():
    try:
        # 接收前端上传的图片
        if 'image' not in request.files:
            return jsonify({"code": 400, "msg": "请上传图片文件"}), 400
        image_file = request.files['image']

        # 生成唯一文件名（避免重复）
        ext = os.path.splitext(image_file.filename)[-1]  # 获取文件后缀（.jpg/.png）
        filename = f"{uuid.uuid4()}{ext}"  # 用UUID生成唯一名
        save_path = os.path.join(UPLOAD_FOLDER, filename)

        # 保存图片到本地
        image_file.save(save_path)

        # 生成本地直链（前端能直接访问）
        img_url = f"http://127.0.0.1:5000/covers/{filename}"

        return jsonify({
            "code": 200,
            "msg": "图片上传成功（本地图床）",
            "data": {"img_url": img_url}
        })

    except Exception as e:
        print(f"上传失败：{str(e)}")
        return jsonify({"code": 500, "msg": f"上传失败：{str(e)}"}), 500


# ========== 工具函数 ==========
def get_next_id(table_name):
    """获取指定表的下一个自增ID"""
    try:
        db = get_db()
        cursor = db.cursor()
        cursor.execute(f'SELECT MAX(id) FROM `{table_name}`')
        max_id = cursor.fetchone()["MAX(id)"]  # 修复：字典取值
        cursor.close()
        return 1 if max_id is None else max_id + 1
    except Exception as e:
        print(f"生成ID失败：{str(e)}")
        return 1


# ========== 业务接口（全量适配MySQL+分表） ==========
# 1. 注册接口（自动创建用户专属专辑表）
@app.route('/api/register', methods=['POST'])
def register():
    try:
        data = request.get_json()
        username = data.get('username')
        password = data.get('password')

        if not username or not password:
            return jsonify({"code": 400, "msg": "用户名和密码不能为空！"}), 400

        db = get_db()
        cursor = db.cursor()
        # 检查用户名是否存在
        cursor.execute('SELECT id FROM users WHERE username = %s', (username,))
        if cursor.fetchone():
            cursor.close()
            return jsonify({"code": 400, "msg": "用户名已被注册！"}), 400

        # 创建新用户
        cursor.execute('''
            INSERT INTO users (username, password, token) 
            VALUES (%s, %s, "")
        ''', (username, password))
        new_user_id = cursor.lastrowid
        db.commit()

        # 为新用户创建专属专辑表
        create_user_album_table(new_user_id)

        cursor.close()
        return jsonify({
            "code": 200,
            "msg": "注册成功！请登录",
            "data": {"username": username}
        })
    except Exception as e:
        print(f"注册出错：{str(e)}")
        print(traceback.format_exc())
        return jsonify({"code": 500, "msg": f"注册失败：{str(e)}"}), 500


# 2. 登录接口
@app.route('/api/login', methods=['POST'])
def login():
    try:
        data = request.get_json()
        username = data.get('username')
        password = data.get('password')

        if not username or not password:
            return jsonify({"code": 400, "msg": "账号和密码不能为空！"}), 400

        # MySQL验证账号密码
        db = get_db()
        cursor = db.cursor()
        cursor.execute('''
            SELECT id, username FROM users 
            WHERE username = %s AND password = %s
        ''', (username, password))
        user = cursor.fetchone()

        if not user:
            cursor.close()
            return jsonify({"code": 401, "msg": "账号或密码错误！"}), 401

        # 生成token并更新
        token = str(uuid.uuid4())
        cursor.execute('UPDATE users SET token = %s WHERE id = %s', (token, user["id"]))
        db.commit()
        cursor.close()

        return jsonify({
            "code": 200,
            "msg": "登录成功！",
            "data": {"token": token, "username": username}
        })
    except Exception as e:
        print(f"登录出错：{str(e)}")
        print(traceback.format_exc())
        return jsonify({"code": 500, "msg": f"登录出错：{str(e)}"}), 500


# 3. 获取专辑列表（读取用户专属表）- 保留分页和排序
# ========== 新增：兼容前端的 /api/album/list 接口 ==========
@app.route('/api/album/list', methods=['GET'])
@login_required
def album_list_compatible():
    # 直接调用原有/get_album_list函数的逻辑，复用所有分页、排序功能
    return get_album_list()


@app.route('/api/music', methods=['GET'])
@login_required
def get_album_list():
    try:
        # 获取分页和排序参数
        page = int(request.args.get('page', 1))  # 默认第1页
        page_size = int(request.args.get('page_size', 10))  # 默认每页10条
        sort_by = request.args.get('sort_by', 'album_name')  # 默认按专辑名排序
        sort_order = request.args.get('sort_order', 'asc')  # 默认升序

        # 验证排序字段合法性
        valid_sort_fields = ['album_name', 'release_year', 'singer', 'my_score']
        if sort_by not in valid_sort_fields:
            sort_by = 'album_name'

        # 验证排序方向
        if sort_order not in ['asc', 'desc']:
            sort_order = 'asc'

        table_name = get_album_table_name(current_user_id)
        db = get_db()
        cursor = db.cursor()

        # 1. 查询总条数（用于分页）
        cursor.execute(f'SELECT COUNT(*) as total FROM `{table_name}`')
        total = cursor.fetchone()['total']

        # 2. 计算分页偏移量
        offset = (page - 1) * page_size

        # 3. 带排序和分页的查询
        cursor.execute(f'''
            SELECT * FROM `{table_name}` 
            ORDER BY `{sort_by}` {sort_order.upper()}
            LIMIT %s OFFSET %s
        ''', (page_size, offset))
        albums = cursor.fetchall()
        cursor.close()

        # 解析JSON字段
        album_list = []
        for album in albums:
            album_dict = {
                "id": album["id"],
                "album_name": album["album_name"],
                "cover_img": album["cover_img"],
                "singer": album["singer"],
                "release_year": album["release_year"],
                "start_time": album["start_time"],
                "track_count": album["track_count"],
                "track_duration": album["track_duration"],
                "my_score": album["my_score"],
                "burn_class": album["burn_class"],
                "duration_type": album["duration_type"],
                "tags": json.loads(album["tags"] or "") if (album["tags"] is not None) else [],
                "main_type": json.loads(album["main_type"] or "") if (album["main_type"] is not None) else [],
                "code": album["code"],
                "video_shared": album["video_shared"],
                "mandopop_code": album["mandopop_code"],
                "tracks": json.loads(album["tracks"] or "") if (album["tracks"] is not None) else [],
                "review": json.loads(album["review"] or "") if (album["review"] is not None) else {},
                "score": album["score"],
                "comments": json.loads(album["comments"] or "") if (album["comments"] is not None) else []
            }
            album_list.append(album_dict)

        # 返回分页数据
        return jsonify({
            "code": 200,
            "msg": "获取专辑列表成功",
            "data": {
                "list": album_list,
                "pagination": {
                    "total": total,
                    "page": page,
                    "page_size": page_size,
                    "total_pages": (total + page_size - 1) // page_size
                }
            }
        })
    except Exception as e:
        print(f"获取专辑列表出错：{str(e)}")
        print(traceback.format_exc())
        return jsonify({"code": 500, "msg": f"获取专辑出错：{str(e)}"}), 500


# 4. 添加专辑（写入用户专属表）- 整合重构后的review结构
@app.route('/api/album/add', methods=['POST'])
@login_required
def add_album():
    try:
        data = request.get_json()
        table_name = get_album_table_name(current_user_id)

        # 校验必填字段
        required_fields = ['album_name', 'singer', 'release_year', 'main_type']
        for field in required_fields:
            if not data.get(field):
                return jsonify({"code": 400, "msg": f"{field}不能为空！"}), 400

        # 整理数据（整合重构后的review结构）
        new_album = {
            "album_name": data.get('album_name').strip(),
            "cover_img": data.get('cover_img', '').strip(),
            "singer": data.get('singer').strip(),
            "release_year": int(data.get('release_year')),
            "start_time": data.get('start_time', ''),
            "track_count": int(data.get('track_count', 0)),
            "track_duration": data.get('track_duration', ''),
            "my_score": float(data.get('my_score', 0.0)),
            "burn_class": data.get('burn_class', ''),
            "duration_type": data.get('duration_type', ''),
            "tags": json.dumps(data.get('tags', [])) or "",
            "main_type": json.dumps(data.get('main_type', [])) or "",
            "code": data.get('code', ''),
            "video_shared": data.get('video_shared', ''),
            "mandopop_code": data.get('mandopop_code', ''),
            "tracks": json.dumps(data.get('tracks', [])) or "",
            # 重构后的review结构
            "review": json.dumps({
                "feelings": [],  # 保留原有听后感列表
                "single_score": 0.0,
                "private_score": 0.0,
                "final_score": 0.0,
                "personal_feeling": "",  # 新增的单条听后感
                "update_time": ""
            }) or "",
            "score": float(data.get('score', 0.0)),
            "comments": json.dumps([]) or ""
        }

        # 写入用户专属表
        db = get_db()
        cursor = db.cursor()
        cursor.execute(f'''
            INSERT INTO `{table_name}` (
                album_name, cover_img, singer, release_year, start_time,
                track_count, track_duration, my_score, burn_class, duration_type,
                tags, main_type, code, video_shared, mandopop_code,
                tracks, review, score, comments
            ) VALUES (
                %s, %s, %s, %s, %s, %s, %s, %s, %s, %s,
                %s, %s, %s, %s, %s, %s, %s, %s, %s
            )
        ''', (
            new_album['album_name'], new_album['cover_img'], new_album['singer'],
            new_album['release_year'], new_album['start_time'], new_album['track_count'],
            new_album['track_duration'], new_album['my_score'], new_album['burn_class'],
            new_album['duration_type'], new_album['tags'], new_album['main_type'],
            new_album['code'], new_album['video_shared'], new_album['mandopop_code'],
            new_album['tracks'], new_album['review'], new_album['score'],
            new_album['comments']
        ))
        new_album_id = cursor.lastrowid

        # ========== 新增：同步插入专辑搜索池 ==========
        # 适配main_type字段类型变更（从TEXT改为VARCHAR）
        main_type_str = json.dumps(data.get('main_type', [])) if data.get('main_type') else ""
        cursor.execute('''
            INSERT INTO album_pool (
                album_name, cover_img, singer, release_year, 
                main_type, tags, my_score, create_user
            ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
        ''', (
            new_album['album_name'],
            new_album['cover_img'],
            new_album['singer'],
            new_album['release_year'],
            main_type_str,  # 存储JSON字符串（适配VARCHAR(50)）
            new_album['tags'],  # 直接存储JSON字符串
            new_album['my_score'],
            current_user_id  # 记录创建用户ID
        ))

        db.commit()
        cursor.close()

        # 构造返回数据
        return_album = new_album.copy()
        return_album['id'] = new_album_id
        return_album['tags'] = json.loads(return_album['tags'])
        return_album['main_type'] = json.loads(return_album['main_type'])
        return_album['tracks'] = json.loads(return_album['tracks'])
        return_album['review'] = json.loads(return_album['review'])
        return_album['comments'] = json.loads(return_album['comments'])

        return jsonify({
            "code": 200,
            "msg": "专辑添加成功！",
            "data": return_album
        })
    except Exception as e:
        print(f"添加专辑出错：{str(e)}")
        print(traceback.format_exc())
        return jsonify({"code": 500, "msg": f"添加专辑失败：{str(e)}"}), 500


@app.route('/api/album/pool/detail/<int:pool_id>', methods=['GET'])
@login_required
def get_pool_album_detail(pool_id):
    try:
        db = get_db()
        cursor = db.cursor(dictionary=True)
        # 查album_pool表（公共表），而非用户分表
        cursor.execute('SELECT * FROM album_pool WHERE id = %s', (pool_id,))
        album = cursor.fetchone()
        cursor.close()

        if not album:
            return jsonify({"code": 404, "msg": "未找到该公共专辑"}), 404

        # 处理tags字段（JSON字符串转数组）
        if album.get('tags'):
            import json
            album['tags'] = json.loads(album['tags'])

        return jsonify({
            "code": 200,
            "msg": "获取成功",
            "data": album
        })
    except Exception as e:
        print(f"获取公共专辑详情失败：{str(e)}")
        return jsonify({"code": 500, "msg": f"获取失败：{str(e)}"}), 500

# 5. 删除专辑（删除用户专属表数据）
@app.route('/api/album/delete/<int:album_id>', methods=['DELETE'])
@login_required
def delete_album(album_id):
    try:
        # 关键点1：必须用当前登录用户的分表名（current_user_id）
        table_name = get_album_table_name(current_user_id)
        db = get_db()
        cursor = db.cursor()

        # 关键点2：删除条件必须包含album_id（前端传的ID）
        cursor.execute(f'DELETE FROM `{table_name}` WHERE id = %s', (album_id,))
        affected_rows = cursor.rowcount  # 关键：获取受影响行数
        db.commit()
        cursor.close()

        # 关键点3：判断是否真的删除成功（affected_rows > 0 才是成功）
        if affected_rows == 0:
            return jsonify({"code": 404, "msg": f"未找到ID为{album_id}的专辑！"}), 404

        return jsonify({
            "code": 200,
            "msg": f"删除ID为{album_id}的专辑成功！"
        })
    except Exception as e:
        print(f"删除专辑出错：{str(e)}")
        print(traceback.format_exc())
        return jsonify({"code": 500, "msg": f"删除专辑失败：{str(e)}"}), 500

# ========== 新增：专辑搜索池 - 搜索接口 ==========
@app.route('/api/album/pool/search', methods=['GET'])
@login_required
def search_album_pool():
    try:
        # 获取前端参数
        keyword = request.args.get('keyword', '').strip()
        page = int(request.args.get('page', 1))
        page_size = int(request.args.get('page_size', 10))

        # 校验参数
        if page < 1:
            page = 1
        if page_size < 1 or page_size > 50:
            page_size = 10

        db = get_db()
        cursor = db.cursor()

        # 1. 构建查询条件（模糊匹配专辑名/歌手/标签）
        query = "SELECT * FROM album_pool WHERE 1=1"
        params = []
        if keyword:
            query += " AND (album_name LIKE %s OR singer LIKE %s OR tags LIKE %s OR main_type LIKE %s)"
            params.extend([f'%{keyword}%', f'%{keyword}%', f'%{keyword}%', f'%{keyword}%'])

        # 2. 查询总条数（分页用）
        count_query = query.replace("SELECT *", "SELECT COUNT(*) as total")
        cursor.execute(count_query, params)
        total = cursor.fetchone()['total']

        # 3. 计算分页偏移量
        offset = (page - 1) * page_size

        # 4. 带分页和模糊查询的主查询
        query += " ORDER BY create_time DESC LIMIT %s OFFSET %s"
        params.extend([page_size, offset])
        cursor.execute(query, params)
        album_list = cursor.fetchall()
        cursor.close()

        # 解析JSON字段（tags/main_type）
        result_list = []
        for album in album_list:
            result_list.append({
                "id": album['id'],
                "album_name": album['album_name'],
                "cover_img": album['cover_img'],
                "singer": album['singer'],
                "release_year": album['release_year'],
                "main_type": json.loads(album['main_type']) if album['main_type'] else [],
                "tags": json.loads(album['tags']) if album['tags'] else [],
                "my_score": album['my_score'],
                "create_user": album['create_user'],
                "create_time": album['create_time'].strftime('%Y-%m-%d %H:%M:%S') if album['create_time'] else ''
            })

        # 构造分页信息
        total_pages = (total + page_size - 1) // page_size
        pagination = {
            "total": total,
            "page": page,
            "page_size": page_size,
            "total_pages": total_pages
        }

        return jsonify({
            "code": 200,
            "msg": "搜索专辑池成功",
            "data": {
                "list": result_list,
                "pagination": pagination
            }
        })
    except Exception as e:
        print(f"搜索专辑池出错：{str(e)}")
        print(traceback.format_exc())
        return jsonify({"code": 500, "msg": f"搜索专辑池失败：{str(e)}"}), 500


# ========== 新增：专辑搜索池 - 复制专辑接口 ==========
@app.route('/api/album/pool/copy/<int:album_id>', methods=['POST'])
@login_required
def copy_album(album_id):
    try:
        db = get_db()
        cursor = db.cursor()

        # 1. 查询要复制的专辑池数据
        cursor.execute('SELECT * FROM album_pool WHERE id = %s', (album_id,))
        pool_album = cursor.fetchone()
        if not pool_album:
            cursor.close()
            return jsonify({"code": 404, "msg": f"未找到ID为{album_id}的专辑副本！"}), 404

        # 2. 获取当前用户的分表名
        table_name = get_album_table_name(current_user_id)

        # 3. 构造复制后的专辑数据（默认值适配用户分表结构）
        copy_album_data = {
            "album_name": pool_album['album_name'],
            "cover_img": pool_album['cover_img'],
            "singer": pool_album['singer'],
            "release_year": pool_album['release_year'],
            "start_time": "",
            "track_count": 0,
            "track_duration": "",
            "my_score": 0.0,  # 副本默认评分为0，用户可自行修改
            "burn_class": "",
            "duration_type": "",
            "tags": pool_album['tags'],  # 直接复用JSON字符串
            "main_type": pool_album['main_type'],  # 直接复用JSON字符串（适配TEXT）
            "code": "",
            "video_shared": "",
            "mandopop_code": "",
            "tracks": json.dumps([]),
            "review": json.dumps({
                "feelings": [],
                "single_score": 0.0,
                "private_score": 0.0,
                "final_score": 0.0,
                "personal_feeling": "",
                "update_time": ""
            }),
            "score": 0.0,
            "comments": json.dumps([])
        }

        # 4. 插入到当前用户的分表
        cursor.execute(f'''
            INSERT INTO `{table_name}` (
                album_name, cover_img, singer, release_year, start_time,
                track_count, track_duration, my_score, burn_class, duration_type,
                tags, main_type, code, video_shared, mandopop_code,
                tracks, review, score, comments
            ) VALUES (
                %s, %s, %s, %s, %s, %s, %s, %s, %s, %s,
                %s, %s, %s, %s, %s, %s, %s, %s, %s
            )
        ''', (
            copy_album_data['album_name'],
            copy_album_data['cover_img'],
            copy_album_data['singer'],
            copy_album_data['release_year'],
            copy_album_data['start_time'],
            copy_album_data['track_count'],
            copy_album_data['track_duration'],
            copy_album_data['my_score'],
            copy_album_data['burn_class'],
            copy_album_data['duration_type'],
            copy_album_data['tags'],
            copy_album_data['main_type'],
            copy_album_data['code'],
            copy_album_data['video_shared'],
            copy_album_data['mandopop_code'],
            copy_album_data['tracks'],
            copy_album_data['review'],
            copy_album_data['score'],
            copy_album_data['comments']
        ))

        new_copy_id = cursor.lastrowid
        db.commit()
        cursor.close()

        return jsonify({
            "code": 200,
            "msg": "复制专辑副本成功！",
            "data": {"copy_album_id": new_copy_id}
        })
    except Exception as e:
        print(f"复制专辑出错：{str(e)}")
        print(traceback.format_exc())
        return jsonify({"code": 500, "msg": f"复制专辑失败：{str(e)}"}), 500


# 6. 新增：添加单条听后感（保留原有逻辑）
@app.route('/api/album/review/add/<int:album_id>', methods=['POST'])
@login_required
def add_single_review(album_id):
    try:
        data = request.get_json()
        content = data.get('content', '').strip()
        if not content:
            return jsonify({"code": 400, "msg": "听后感内容不能为空！"}), 400

        table_name = get_album_table_name(current_user_id)
        db = get_db()
        cursor = db.cursor()

        # 查询原有review
        cursor.execute(f'SELECT review FROM `{table_name}` WHERE id = %s', (album_id,))
        album = cursor.fetchone()
        if not album:
            cursor.close()
            return jsonify({"code": 404, "msg": f"未找到ID为{album_id}的专辑！"}), 404

        # 初始化review结构（兼容旧数据）
        review = json.loads(album["review"]) if album["review"] else {"feelings": []}
        if "feelings" not in review:
            review["feelings"] = []

        # 生成单条听后感记录（用uuid做唯一id）
        new_feeling = {
            "id": str(uuid.uuid4()),
            "content": content,
            "create_time": data.get('create_time', '')
        }
        review["feelings"].append(new_feeling)

        # 保存更新
        new_review = json.dumps(review)
        cursor.execute(f'''
            UPDATE `{table_name}` SET review = %s WHERE id = %s
        ''', (new_review, album_id))
        db.commit()
        cursor.close()

        return jsonify({
            "code": 200,
            "msg": "听后感添加成功！",
            "data": new_feeling
        })
    except Exception as e:
        print(f"添加听后感出错：{str(e)}")
        print(traceback.format_exc())
        return jsonify({"code": 500, "msg": f"添加听后感失败：{str(e)}"}), 500


# 7. 新增：删除单条听后感
@app.route('/api/album/review/delete/single/<int:album_id>', methods=['POST'])
@login_required
def delete_single_review(album_id):
    try:
        data = request.get_json()
        feeling_id = data.get('feeling_id')
        if not feeling_id:
            return jsonify({"code": 400, "msg": "请指定要删除的听后感！"}), 400

        table_name = get_album_table_name(current_user_id)
        db = get_db()
        cursor = db.cursor()

        # 查询原有review
        cursor.execute(f'SELECT review FROM `{table_name}` WHERE id = %s', (album_id,))
        album = cursor.fetchone()
        if not album:
            cursor.close()
            return jsonify({"code": 404, "msg": f"未找到ID为{album_id}的专辑！"}), 404

        # 过滤要删除的记录
        review = json.loads(album["review"]) if album["review"] else {"feelings": []}
        if "feelings" not in review:
            cursor.close()
            return jsonify({"code": 400, "msg": "暂无听后感记录！"}), 400

        # 保留不等于该id的记录
        review["feelings"] = [f for f in review["feelings"] if f.get("id") != feeling_id]
        new_review = json.dumps(review)

        # 保存更新
        cursor.execute(f'''
            UPDATE `{table_name}` SET review = %s WHERE id = %s
        ''', (new_review, album_id))
        db.commit()
        cursor.close()

        return jsonify({
            "code": 200,
            "msg": "听后感删除成功！"
        })
    except Exception as e:
        print(f"删除单条听后感出错：{str(e)}")
        print(traceback.format_exc())
        return jsonify({"code": 500, "msg": f"删除听后感失败：{str(e)}"}), 500


# 8. 修改：清空所有听后感
@app.route('/api/album/review/delete/<int:album_id>', methods=['DELETE'])
@login_required
def delete_all_review(album_id):
    try:
        table_name = get_album_table_name(current_user_id)
        db = get_db()
        cursor = db.cursor()

        cursor.execute(f'SELECT review FROM `{table_name}` WHERE id = %s', (album_id,))
        album = cursor.fetchone()
        if not album:
            cursor.close()
            return jsonify({"code": 404, "msg": f"未找到ID为{album_id}的专辑！"}), 404

        # 清空所有听后感（兼容重构后的结构）
        review = json.loads(album["review"]) if album["review"] else {}
        review["feelings"] = []
        review["personal_feeling"] = ""
        new_review = json.dumps(review)

        cursor.execute(f'''
            UPDATE `{table_name}` SET review = %s WHERE id = %s
        ''', (new_review, album_id))
        db.commit()
        cursor.close()

        return jsonify({
            "code": 200,
            "msg": "所有听后感已清空！"
        })
    except Exception as e:
        print(f"清空听后感出错：{str(e)}")
        print(traceback.format_exc())
        return jsonify({"code": 500, "msg": f"清空听后感失败：{str(e)}"}), 500


# 9. 编辑听后感（重构后的单条听后感编辑）
@app.route('/api/album/review/edit/<int:album_id>', methods=['POST'])
@login_required
def edit_review(album_id):
    try:
        data = request.get_json()
        if not data or not data.get('personal_feeling'):
            return jsonify({"code": 400, "msg": "听后感内容不能为空！"}), 400

        table_name = get_album_table_name(current_user_id)
        db = get_db()
        cursor = db.cursor()

        # 查询原有review
        cursor.execute(f'SELECT review FROM `{table_name}` WHERE id = %s', (album_id,))
        album = cursor.fetchone()
        if not album:
            cursor.close()
            return jsonify({"code": 404, "msg": f"未找到ID为{album_id}的专辑！"}), 404

        # 更新听后感（重构后的结构）
        review = json.loads(album["review"]) if album["review"] else {}
        review['personal_feeling'] = data.get('personal_feeling')
        review['update_time'] = data.get('update_time', '')
        new_review = json.dumps(review)

        # 保存更新
        cursor.execute(f'''
            UPDATE `{table_name}` SET review = %s WHERE id = %s
        ''', (new_review, album_id))
        db.commit()
        cursor.close()

        return jsonify({
            "code": 200,
            "msg": "听后感编辑成功！",
            "data": review
        })
    except Exception as e:
        print(f"编辑听后感出错：{str(e)}")
        print(traceback.format_exc())
        return jsonify({"code": 500, "msg": f"编辑听后感失败：{str(e)}"}), 500


# 10. 获取专辑详情（读取用户专属表）
@app.route('/api/album/detail/<int:album_id>', methods=['GET'])
@login_required
def get_album_detail(album_id):
    try:
        table_name = get_album_table_name(current_user_id)
        db = get_db()
        cursor = db.cursor()

        # 查询专辑详情
        cursor.execute(f'SELECT * FROM `{table_name}` WHERE id = %s', (album_id,))
        album = cursor.fetchone()
        cursor.close()

        if not album:
            return jsonify({"code": 404, "msg": f"未找到ID为{album_id}的专辑！"}), 404

        # 解析JSON字段
        album_dict = {
            "id": album["id"],
            "album_name": album["album_name"],
            "cover_img": album["cover_img"],
            "singer": album["singer"],
            "release_year": album["release_year"],
            "start_time": album["start_time"],
            "track_count": album["track_count"],
            "track_duration": album["track_duration"],
            "my_score": album["my_score"],
            "burn_class": album["burn_class"],
            "duration_type": album["duration_type"],
            "tags": json.loads(album["tags"]) if album["tags"] else [],
            "main_type": json.loads(album["main_type"]) if album["main_type"] else [],
            "code": album["code"],
            "video_shared": album["video_shared"],
            "mandopop_code": album["mandopop_code"],
            "tracks": json.loads(album["tracks"]) if album["tracks"] else [],
            "review": json.loads(album["review"]) if album["review"] else {},
            "score": album["score"],
            "comments": json.loads(album["comments"]) if album["comments"] else []
        }

        return jsonify({
            "code": 200,
            "msg": "获取专辑详情成功！",
            "data": album_dict
        })
    except Exception as e:
        print(f"获取专辑详情出错：{str(e)}")
        print(traceback.format_exc())
        return jsonify({"code": 500, "msg": f"获取专辑详情失败：{str(e)}"}), 500


# 11. 提交评论（更新用户专属表）
@app.route('/api/music/comment', methods=['POST'])
@login_required
def submit_comment():
    try:
        data = request.get_json()
        music_id = data.get('musicId')
        comment = data.get('comment')
        score = data.get('score', 0)

        if not music_id or not comment:
            return jsonify({"code": 400, "msg": "音乐ID和评论不能为空"}), 400

        table_name = get_album_table_name(current_user_id)
        db = get_db()
        cursor = db.cursor()

        # 查询原有数据
        cursor.execute(f'SELECT score, comments FROM `{table_name}` WHERE id = %s', (music_id,))
        album = cursor.fetchone()
        if not album:
            cursor.close()
            return jsonify({"code": 404, "msg": f"未找到ID为{music_id}的专辑！"}), 404

        # 更新评论和评分
        comments = json.loads(album["comments"]) if album["comments"] else []
        comments.append(comment)
        new_score = album["score"]
        if score > 0:
            new_score = round((album["score"] + score) / 2, 1)

        # 保存更新
        cursor.execute(f'''
            UPDATE `{table_name}` SET score = %s, comments = %s WHERE id = %s
        ''', (new_score, json.dumps(comments), music_id))
        db.commit()

        # 返回更新后的专辑列表
        cursor.execute(f'SELECT * FROM `{table_name}`')
        albums = cursor.fetchall()
        cursor.close()

        album_list = []
        for a in albums:
            a_dict = {
                "id": a["id"],
                "album_name": a["album_name"],
                "cover_img": a["cover_img"],
                "singer": a["singer"],
                "release_year": a["release_year"],
                "start_time": a["start_time"],
                "track_count": a["track_count"],
                "track_duration": a["track_duration"],
                "my_score": a["my_score"],
                "burn_class": a["burn_class"],
                "duration_type": a["duration_type"],
                "tags": json.loads(a["tags"]) if a["tags"] else [],
                "main_type": json.loads(a["main_type"]) if a["main_type"] else [],
                "code": a["code"],
                "video_shared": a["video_shared"],
                "mandopop_code": a["mandopop_code"],
                "tracks": json.loads(a["tracks"]) if a["tracks"] else [],
                "review": json.loads(a["review"]) if a["review"] else {},
                "score": a["score"],
                "comments": json.loads(a["comments"]) if a["comments"] else []
            }
            album_list.append(a_dict)

        return jsonify({"code": 200, "msg": "提交成功", "data": album_list})
    except Exception as e:
        print(f"提交评论出错：{str(e)}")
        print(traceback.format_exc())
        return jsonify({"code": 500, "msg": f"提交评论出错：{str(e)}"}), 500


# 12. 兼容的专辑评论添加接口（适配前端原有调用格式）
@app.route('/api/album/comment/add/<int:album_id>', methods=['POST'])
@login_required
def add_album_comment(album_id):
    try:
        data = request.get_json()
        comment = data.get('comment')

        if not comment:
            return jsonify({"code": 400, "msg": "评论内容不能为空！"}), 400

        # 调用原有submit_comment的核心逻辑
        table_name = get_album_table_name(current_user_id)
        db = get_db()
        cursor = db.cursor()

        # 查询原有数据
        cursor.execute(f'SELECT score, comments FROM `{table_name}` WHERE id = %s', (album_id,))
        album = cursor.fetchone()
        if not album:
            cursor.close()
            return jsonify({"code": 404, "msg": f"未找到ID为{album_id}的专辑！"}), 404

        # 更新评论
        comments = json.loads(album["comments"]) if album["comments"] else []
        comments.append(comment)

        # 保存更新（评分保持不变）
        cursor.execute(f'''
            UPDATE `{table_name}` SET comments = %s WHERE id = %s
        ''', (json.dumps(comments), album_id))
        db.commit()
        cursor.close()

        return jsonify({
            "code": 200,
            "msg": "评论提交成功！",
            "data": {"comments": comments}
        })
    except Exception as e:
        print(f"添加专辑评论出错：{str(e)}")
        print(traceback.format_exc())
        return jsonify({"code": 500, "msg": f"添加评论失败：{str(e)}"}), 500


# ========== 启动初始化 ==========
with app.app_context():
    init_base_tables()

# ========== 启动服务 ==========
if __name__ == '__main__':
    print("MySQL版音乐评分系统后端启动！")
    print(f"服务地址：http://0.0.0.0:5000")
    app.run(debug=True, host='0.0.0.0', port=5000)
