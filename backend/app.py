# 1. 导入需要的工具（新增sqlite3、hashlib，保留你原有所有导入）
from flask import Flask, request, jsonify, g
from flask_cors import CORS
import json
import os
import uuid
from functools import wraps
import traceback
import sqlite3  # 新增：数据库
import hashlib  # 可选：密码加密（你原有代码是明文，保留兼容）

# 2. 初始化Flask应用
app = Flask(__name__)
CORS(app, supports_credentials=True)  # 保留你的跨域配置！
app.secret_key = 'music-rate-secret-key'  # 新增：确保上下文安全

# 3. 配置（保留原有DATA_DIR，新增数据库路径）
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(BASE_DIR, 'data')
DATA_FILE = os.path.join(DATA_DIR, 'music_data.json')  # 保留（兼容初始化）
USER_FILE = os.path.join(DATA_DIR, 'user_data.json')  # 保留（兼容旧用户）
DATABASE = os.path.join(DATA_DIR, 'music.db')  # 新增：数据库文件


# ========== 新增：数据库核心工具（保留你原有逻辑的同时新增） ==========
def get_db():
    """获取数据库连接（Flask上下文隔离）"""
    db = getattr(g, '_database', None)
    if db is None:
        db = g._database = sqlite3.connect(DATABASE)
        db.row_factory = sqlite3.Row  # 支持按列名访问
    return db


@app.teardown_appcontext
def close_db(exception):
    """关闭数据库连接"""
    db = getattr(g, '_database', None)
    if db is not None:
        db.close()


def init_db():
    """初始化数据库表（首次运行创建）"""
    try:
        # 确保data目录存在
        if not os.path.exists(DATA_DIR):
            os.makedirs(DATA_DIR)

        db = get_db()
        # 创建用户表（兼容你原有user_data.json的字段）
        db.execute('''
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                username TEXT UNIQUE NOT NULL,
                password TEXT NOT NULL,  -- 保留明文（兼容你原有代码）
                token TEXT DEFAULT "",
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        # 创建专辑表（完全对应你原有JSON的字段 + user_id关联）
        db.execute('''
            CREATE TABLE IF NOT EXISTS albums (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,  -- 核心：关联用户
                album_name TEXT NOT NULL,
                cover_img TEXT DEFAULT "",
                singer TEXT NOT NULL,
                release_year INTEGER NOT NULL,
                start_time TEXT DEFAULT "",
                track_count INTEGER DEFAULT 0,
                track_duration TEXT DEFAULT "",
                my_score REAL DEFAULT 0.0,
                burn_class TEXT DEFAULT "",
                duration_type TEXT DEFAULT "",
                tags TEXT DEFAULT "",  -- 存储JSON字符串（数组）
                main_type TEXT DEFAULT "",  -- 存储JSON字符串（数组）
                code TEXT DEFAULT "",
                video_shared TEXT DEFAULT "",
                mandopop_code TEXT DEFAULT "",
                tracks TEXT DEFAULT "",  -- 存储JSON字符串（曲目列表）
                review TEXT DEFAULT "", -- 存储JSON字符串（听后感）
                score REAL DEFAULT 0.0,
                comments TEXT DEFAULT "",  -- 存储JSON字符串（评论列表）
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES users (id) ON DELETE CASCADE
            )
        ''')
        db.commit()
        print("数据库表初始化成功！")

        # 兼容：将原有JSON的用户/专辑导入数据库（仅首次）
        migrate_old_data_to_db()
    except Exception as e:
        print(f"初始化数据库失败：{str(e)}")
        print(traceback.format_exc())


def migrate_old_data_to_db():
    """将原有JSON数据迁移到数据库（兼容旧数据）"""
    try:
        db = get_db()
        # 1. 迁移用户数据
        if os.path.exists(USER_FILE):
            with open(USER_FILE, 'r', encoding='utf-8') as f:
                old_users = json.load(f)
            for u in old_users:
                # 避免重复插入
                exists = db.execute('SELECT id FROM users WHERE id = ?', (u['id'],)).fetchone()
                if not exists:
                    db.execute(
                        'INSERT INTO users (id, username, password, token) VALUES (?, ?, ?, ?)',
                        (u['id'], u['username'], u['password'], u.get('token', ''))
                    )
            db.commit()
            print("旧用户数据迁移完成！")

        # 2. 迁移专辑数据（默认归属admin用户，id=1）
        if os.path.exists(DATA_FILE):
            with open(DATA_FILE, 'r', encoding='utf-8') as f:
                old_albums = json.load(f)
            # 先确认admin用户存在
            admin_user = db.execute('SELECT id FROM users WHERE username = "admin"').fetchone()
            if not admin_user:
                print("未找到admin用户，跳过专辑数据迁移！")
                return
            admin_id = admin_user[0]

            for a in old_albums:
                exists = db.execute('SELECT id FROM albums WHERE id = ?', (a['id'],)).fetchone()
                if not exists:
                    # 修复：严格对齐列数和值的数量（21列对应21个值）
                    db.execute('''
                        INSERT INTO albums (
                            id, user_id, album_name, cover_img, singer, release_year,
                            start_time, track_count, track_duration, my_score, burn_class,
                            duration_type, tags, main_type, code, video_shared, mandopop_code,
                            tracks, review, score, comments
                        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    ''', (
                        # 共21个值，严格对应上面的21列
                        a['id'], admin_id, a.get('album_name', ''), a.get('cover_img', ''), a.get('singer', ''),
                        a.get('release_year', 0), a.get('start_time', ''), a.get('track_count', 0),
                        a.get('track_duration', ''), a.get('my_score', 0.0), a.get('burn_class', ''),
                        a.get('duration_type', ''), json.dumps(a.get('tags', [])), json.dumps(a.get('main_type', [])),
                        a.get('code', ''), a.get('video_shared', ''), a.get('mandopop_code', ''),
                        json.dumps(a.get('tracks', [])), json.dumps(a.get('review', {})),
                        a.get('score', 0.0), json.dumps(a.get('comments', []))
                    ))
            db.commit()
            print("旧专辑数据迁移完成！")
    except Exception as e:
        print(f"迁移旧数据失败：{str(e)}")
        print(traceback.format_exc())


# ========== 保留你原有：登录校验装饰器（仅新增获取当前用户ID） ==========
# 新增：全局变量存储当前登录用户ID（替代Flask-Login，兼容你原有token逻辑）
current_user_id = None


def login_required(func):
    @wraps(func)
    def wrapper(*args, **kwargs):
        global current_user_id
        current_user_id = None  # 重置
        try:
            # 1. 获取请求头的token
            token = request.headers.get('Authorization')
            if not token:
                print("请求头无Authorization token")
                return jsonify({"code": 401, "msg": "请先登录！"}), 401

            # 2. 从数据库验证token（替换原有JSON读取）
            db = get_db()
            user = db.execute('SELECT id, username FROM users WHERE token = ?', (token,)).fetchone()
            if not user:
                print(f"token无效：{token}")
                return jsonify({"code": 401, "msg": "登录已过期，请重新登录！"}), 401

            # 3. 保存当前用户ID（后续接口用）
            current_user_id = user['id']
            # 4. 校验通过，执行原函数
            return func(*args, **kwargs)
        except Exception as e:
            print(f"登录校验失败：{str(e)}")
            print(traceback.format_exc())
            return jsonify({"code": 500, "msg": f"登录校验出错：{str(e)}"}), 500

    return wrapper


# ========== 保留你原有：工具函数（适配数据库） ==========
def get_next_user_id():
    """兼容原有逻辑，从数据库获取下一个用户ID"""
    try:
        db = get_db()
        max_id = db.execute('SELECT MAX(id) FROM users').fetchone()[0]
        return 1 if max_id is None else max_id + 1
    except Exception as e:
        print(f"生成用户ID失败：{str(e)}")
        return 1


def get_next_album_id():
    """兼容原有逻辑，从数据库获取下一个专辑ID"""
    try:
        db = get_db()
        max_id = db.execute('SELECT MAX(id) FROM albums').fetchone()[0]
        return 1 if max_id is None else max_id + 1
    except Exception as e:
        print(f"生成专辑ID失败：{str(e)}")
        return 1


# ========== 保留你原有：初始化函数（新增数据库初始化） ==========
def init_user():
    try:
        if not os.path.exists(DATA_DIR):
            os.makedirs(DATA_DIR)
            print(f"创建data文件夹成功：{DATA_DIR}")

        initial_users = [{"id": 1, "username": "admin", "password": "123456", "token": ""}]
        if not os.path.exists(USER_FILE):
            with open(USER_FILE, 'w', encoding='utf-8') as file:
                json.dump(initial_users, file, ensure_ascii=False, indent=2)
            print(f"创建用户文件成功：{USER_FILE}")
        else:
            print(f"用户文件已存在：{USER_FILE}")
    except Exception as e:
        print(f"初始化用户数据失败：{str(e)}")
        print(traceback.format_exc())


def init_data():
    try:
        if not os.path.exists(DATA_DIR):
            os.makedirs(DATA_DIR)
            print(f"创建data文件夹成功：{DATA_DIR}")

        # 你的原有初始化数据（完全保留）
        initial_data = [
            {
                "id": 1,
                "album_name": "七里香",
                "cover_img": "",
                "singer": "周杰伦",
                "release_year": 2004,
                "start_time": "2004-08-03",
                "track_count": 10,
                "track_duration": "40.00",
                "my_score": 92.0,
                "burn_class": "",
                "duration_type": "LP",
                "tags": ["经典", "华语"],
                "main_type": ["流行"],
                "code": "04080307",
                "video_shared": "",
                "mandopop_code": "040113",
                "tracks": [
                    {"name": "七里香", "time": "0:00", "score": 9.5},
                    {"name": "外婆", "time": "4:32", "score": 8.8},
                    {"name": "将军", "time": "8:15", "score": 9.0}
                ],
                "review": {
                    "single_score": 91.5,
                    "private_score": 0.5,
                    "final_score": 92.0,
                    "personal_feeling": "经典华语专辑，百听不厌",
                    "comments": {
                        "douban": ["评论1", "评论2"],
                        "netease": ["评论1", "评论2"]
                    }
                },
                "score": 9.2,
                "comments": []
            },
            {
                "id": 2,
                "album_name": "晴天",
                "cover_img": "",
                "singer": "周杰伦",
                "release_year": 2003,
                "start_time": "2003-07-31",
                "track_count": 1,
                "track_duration": "4.23",
                "my_score": 85.0,
                "burn_class": "",
                "duration_type": "Single",
                "tags": ["经典", "青春"],
                "main_type": ["流行"],
                "code": "03073107",
                "video_shared": "",
                "mandopop_code": "030113",
                "tracks": [
                    {"name": "晴天", "time": "0:00", "score": 8.5}
                ],
                "review": {
                    "single_score": 84.8,
                    "private_score": 0.2,
                    "final_score": 85.0,
                    "personal_feeling": "青春回忆，旋律动人",
                    "comments": {
                        "douban": ["评论1", "评论2"],
                        "netease": ["评论1", "评论2"]
                    }
                },
                "score": 8.5,
                "comments": ["好听", "经典"]
            }
        ]
        if not os.path.exists(DATA_FILE):
            with open(DATA_FILE, 'w', encoding='utf-8') as file:
                json.dump(initial_data, file, ensure_ascii=False, indent=2)
            print(f"创建专辑文件成功：{DATA_FILE}")
        else:
            print(f"专辑文件已存在：{DATA_FILE}")
    except Exception as e:
        print(f"初始化专辑数据失败：{str(e)}")
        print(traceback.format_exc())


# 启动时初始化（先初始化JSON，再初始化数据库，最后迁移数据）
init_user()
init_data()
with app.app_context():
    init_db()


# ========== 改造：注册接口（写入数据库） ==========
@app.route('/api/register', methods=['POST'])
def register():
    try:
        data = request.get_json()
        print(f"注册请求参数：{data}")

        # 1. 校验必填字段（保留原有逻辑）
        username = data.get('username')
        password = data.get('password')
        if not username or not password:
            return jsonify({"code": 400, "msg": "用户名和密码不能为空！"}), 400

        # 2. 数据库操作（替换原有JSON写入）
        db = get_db()
        # 检查用户名是否已存在
        existing = db.execute('SELECT id FROM users WHERE username = ?', (username,)).fetchone()
        if existing:
            print(f"用户名已存在：{username}")
            return jsonify({"code": 400, "msg": "用户名已被注册！"}), 400

        # 生成新用户数据
        new_user_id = get_next_user_id()
        db.execute(
            'INSERT INTO users (id, username, password, token) VALUES (?, ?, ?, ?)',
            (new_user_id, username, password, "")
        )
        db.commit()

        # 兼容：同步更新JSON文件（可选，可删除）
        if os.path.exists(USER_FILE):
            with open(USER_FILE, 'r', encoding='utf-8') as f:
                users = json.load(f)
        else:
            users = []
        users.append({"id": new_user_id, "username": username, "password": password, "token": ""})
        with open(USER_FILE, 'w', encoding='utf-8') as f:
            json.dump(users, f, ensure_ascii=False, indent=2)

        print(f"注册成功：用户名={username}")
        return jsonify({
            "code": 200,
            "msg": "注册成功！请登录",
            "data": {"username": username}
        })
    except Exception as e:
        print(f"注册接口出错：{str(e)}")
        print(traceback.format_exc())
        return jsonify({
            "code": 500,
            "msg": f"注册失败：{str(e)}"
        }), 500


# ========== 改造：登录接口（数据库验证 + 更新token） ==========
@app.route('/api/login', methods=['POST'])
def login():
    try:
        data = request.get_json()
        print(f"登录请求参数：{data}")

        username = data.get('username')
        password = data.get('password')

        if not username or not password:
            return jsonify({"code": 400, "msg": "账号和密码不能为空！"}), 400

        # 数据库验证（替换原有JSON读取）
        db = get_db()
        user = db.execute(
            'SELECT id, username FROM users WHERE username = ? AND password = ?',
            (username, password)
        ).fetchone()

        if not user:
            print(f"账号密码错误：用户名={username}")
            return jsonify({"code": 401, "msg": "账号或密码错误！"}), 401

        # 生成token并更新
        token = str(uuid.uuid4())
        db.execute('UPDATE users SET token = ? WHERE id = ?', (token, user['id']))
        db.commit()

        # 兼容：同步更新JSON文件
        if os.path.exists(USER_FILE):
            with open(USER_FILE, 'r', encoding='utf-8') as f:
                users = json.load(f)
            for u in users:
                if u['username'] == username:
                    u['token'] = token
                    break
            with open(USER_FILE, 'w', encoding='utf-8') as f:
                json.dump(users, f, ensure_ascii=False, indent=2)

        print(f"登录成功：用户名={username}，token={token}")
        return jsonify({
            "code": 200,
            "msg": "登录成功！",
            "data": {"token": token, "username": username}
        })
    except Exception as e:
        print(f"登录接口出错：{str(e)}")
        print(traceback.format_exc())
        return jsonify({"code": 500, "msg": f"登录出错：{str(e)}"}), 500


# ========== 改造：获取专辑列表（仅返回当前用户的专辑） ==========
@app.route('/api/music', methods=['GET'])
@login_required
def get_album_list():
    try:
        db = get_db()
        # 只查询当前用户的专辑
        albums = db.execute(
            'SELECT * FROM albums WHERE user_id = ?',
            (current_user_id,)
        ).fetchall()

        # 转换为原有JSON格式（兼容前端）
        album_list = []
        for a in albums:
            album = dict(a)
            # 解析JSON字符串为数组/字典
            album['tags'] = json.loads(album['tags']) if album['tags'] else []
            album['main_type'] = json.loads(album['main_type']) if album['main_type'] else []
            album['tracks'] = json.loads(album['tracks']) if album['tracks'] else []
            album['review'] = json.loads(album['review']) if album['review'] else {}
            album['comments'] = json.loads(album['comments']) if album['comments'] else []
            album_list.append(album)

        print(f"返回当前用户({current_user_id})的专辑列表：{album_list}")
        return jsonify(album_list)
    except Exception as e:
        print(f"获取专辑列表出错：{str(e)}")
        print(traceback.format_exc())
        return jsonify({"code": 500, "msg": f"获取专辑出错：{str(e)}"}), 500


# ========== 改造：添加专辑（关联当前用户） ==========
@app.route('/api/album/add', methods=['POST'])
@login_required
def add_album():
    try:
        data = request.get_json()
        print(f"添加专辑请求参数：{data}")

        # 1. 校验必填字段（保留原有逻辑）
        required_fields = ['album_name', 'singer', 'release_year', 'main_type']
        for field in required_fields:
            if not data.get(field):
                return jsonify({"code": 400, "msg": f"{field}不能为空！"}), 400

        # 2. 整理专辑数据（保留原有字段）
        new_album_id = get_next_album_id()
        new_album = {
            "id": new_album_id,
            "user_id": current_user_id,  # 核心：关联当前用户
            "album_name": data.get('album_name'),
            "cover_img": data.get('cover_img', ''),
            "singer": data.get('singer'),
            "release_year": int(data.get('release_year')),
            "start_time": data.get('start_time', ''),
            "track_count": int(data.get('track_count', 0)),
            "track_duration": data.get('track_duration', ''),
            "my_score": float(data.get('my_score', 0.0)),
            "burn_class": data.get('burn_class', ''),
            "duration_type": data.get('duration_type', ''),
            "tags": json.dumps(data.get('tags', [])),  # 转为JSON字符串
            "main_type": json.dumps(data.get('main_type', [])),
            "code": data.get('code', ''),
            "video_shared": data.get('video_shared', ''),
            "mandopop_code": data.get('mandopop_code', ''),
            "tracks": json.dumps(data.get('tracks', [])),
            "review": json.dumps({
                "single_score": 0.0,
                "private_score": 0.0,
                "final_score": 0.0,
                "personal_feeling": "",
                "comments": {}
            }),
            "score": float(data.get('score', 0.0)),
            "comments": json.dumps([])
        }

        # 3. 写入数据库
        db = get_db()
        db.execute('''
            INSERT INTO albums (
                id, user_id, album_name, cover_img, singer, release_year,
                start_time, track_count, track_duration, my_score, burn_class,
                duration_type, tags, main_type, code, video_shared, mandopop_code,
                tracks, review, score, comments
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?,?)
        ''', (
            new_album['id'], new_album['user_id'], new_album['album_name'],
            new_album['cover_img'], new_album['singer'], new_album['release_year'],
            new_album['start_time'], new_album['track_count'], new_album['track_duration'],
            new_album['my_score'], new_album['burn_class'], new_album['duration_type'],
            new_album['tags'], new_album['main_type'], new_album['code'],
            new_album['video_shared'], new_album['mandopop_code'], new_album['tracks'],
            new_album['review'], new_album['score'], new_album['comments']
        ))
        db.commit()

        # 4. 构造返回数据（转回原有格式）
        return_album = new_album.copy()
        return_album['tags'] = json.loads(return_album['tags'])
        return_album['main_type'] = json.loads(return_album['main_type'])
        return_album['tracks'] = json.loads(return_album['tracks'])
        return_album['review'] = json.loads(return_album['review'])
        return_album['comments'] = json.loads(return_album['comments'])

        print(f"添加专辑成功：{return_album['album_name']}（用户ID：{current_user_id}）")
        return jsonify({
            "code": 200,
            "msg": "专辑添加成功！",
            "data": return_album
        })
    except Exception as e:
        print(f"添加专辑出错：{str(e)}")
        print(traceback.format_exc())
        return jsonify({
            "code": 500,
            "msg": f"添加专辑失败：{str(e)}"
        }), 500


# ========== 改造：删除专辑（仅删除当前用户的） ==========
@app.route('/api/album/delete/<int:album_id>', methods=['DELETE'])
@login_required
def delete_album(album_id):
    try:
        db = get_db()
        # 只删除当前用户的专辑
        result = db.execute(
            'DELETE FROM albums WHERE id = ? AND user_id = ?',
            (album_id, current_user_id)
        )
        db.commit()

        if result.rowcount == 0:
            return jsonify({"code": 404, "msg": f"未找到ID为{album_id}的专辑！"}), 404

        # 兼容：同步删除JSON文件中的数据（可选）
        if os.path.exists(DATA_FILE):
            with open(DATA_FILE, 'r', encoding='utf-8') as f:
                albums = json.load(f)
            new_albums = [a for a in albums if a['id'] != album_id]
            with open(DATA_FILE, 'w', encoding='utf-8') as f:
                json.dump(new_albums, f, ensure_ascii=False, indent=2)

        return jsonify({
            "code": 200,
            "msg": f"删除ID为{album_id}的专辑成功！"
        })
    except Exception as e:
        print(f"删除专辑出错：{str(e)}")
        print(traceback.format_exc())
        return jsonify({"code": 500, "msg": f"删除专辑失败：{str(e)}"}), 500


# ========== 改造：编辑听后感（仅修改当前用户的） ==========
@app.route('/api/album/review/edit/<int:album_id>', methods=['POST'])
@login_required
def edit_review(album_id):
    try:
        data = request.get_json()
        if not data or not data.get('personal_feeling'):
            return jsonify({"code": 400, "msg": "听后感内容不能为空！"}), 400

        db = get_db()
        # 查找当前用户的专辑
        album = db.execute(
            'SELECT review FROM albums WHERE id = ? AND user_id = ?',
            (album_id, current_user_id)
        ).fetchone()

        if not album:
            return jsonify({"code": 404, "msg": f"未找到ID为{album_id}的专辑！"}), 404

        # 更新听后感
        review = json.loads(album['review']) if album['review'] else {}
        review['personal_feeling'] = data.get('personal_feeling')
        review['update_time'] = data.get('update_time', '')
        new_review = json.dumps(review)

        # 保存到数据库
        db.execute(
            'UPDATE albums SET review = ? WHERE id = ? AND user_id = ?',
            (new_review, album_id, current_user_id)
        )
        db.commit()

        return jsonify({
            "code": 200,
            "msg": "听后感编辑成功！",
            "data": review
        })
    except Exception as e:
        print(f"编辑听后感出错：{str(e)}")
        print(traceback.format_exc())
        return jsonify({"code": 500, "msg": f"编辑听后感失败：{str(e)}"}), 500


# ========== 改造：删除听后感（仅修改当前用户的） ==========
@app.route('/api/album/review/delete/<int:album_id>', methods=['DELETE'])
@login_required
def delete_review(album_id):
    try:
        db = get_db()
        # 查找当前用户的专辑
        album = db.execute(
            'SELECT review FROM albums WHERE id = ? AND user_id = ?',
            (album_id, current_user_id)
        ).fetchone()

        if not album:
            return jsonify({"code": 404, "msg": f"未找到ID为{album_id}的专辑！"}), 404

        # 清空听后感
        review = json.loads(album['review']) if album['review'] else {}
        review['personal_feeling'] = ""
        review['update_time'] = ""
        new_review = json.dumps(review)

        # 保存到数据库
        db.execute(
            'UPDATE albums SET review = ? WHERE id = ? AND user_id = ?',
            (new_review, album_id, current_user_id)
        )
        db.commit()

        return jsonify({
            "code": 200,
            "msg": "听后感删除成功！"
        })
    except Exception as e:
        print(f"删除听后感出错：{str(e)}")
        print(traceback.format_exc())
        return jsonify({"code": 500, "msg": f"删除听后感失败：{str(e)}"}), 500


# ========== 改造：获取专辑详情（仅返回当前用户的） ==========
@app.route('/api/album/detail/<int:album_id>', methods=['GET'])
@login_required
def get_album_detail(album_id):
    try:
        db = get_db()
        # 查找当前用户的专辑
        album = db.execute(
            'SELECT * FROM albums WHERE id = ? AND user_id = ?',
            (album_id, current_user_id)
        ).fetchone()

        if not album:
            return jsonify({"code": 404, "msg": f"未找到ID为{album_id}的专辑！"}), 404

        # 转换为原有格式
        album_dict = dict(album)
        album_dict['tags'] = json.loads(album_dict['tags']) if album_dict['tags'] else []
        album_dict['main_type'] = json.loads(album_dict['main_type']) if album_dict['main_type'] else []
        album_dict['tracks'] = json.loads(album_dict['tracks']) if album_dict['tracks'] else []
        album_dict['review'] = json.loads(album_dict['review']) if album_dict['review'] else {}
        album_dict['comments'] = json.loads(album_dict['comments']) if album_dict['comments'] else []

        return jsonify({
            "code": 200,
            "msg": "获取专辑详情成功！",
            "data": album_dict
        })
    except Exception as e:
        print(f"获取专辑详情出错：{str(e)}")
        print(traceback.format_exc())
        return jsonify({
            "code": 500,
            "msg": f"获取专辑详情失败：{str(e)}"
        }), 500


# ========== 改造：提交评论（仅修改当前用户的专辑） ==========
@app.route('/api/music/comment', methods=['POST'])
@login_required
def submit_comment():
    try:
        data = request.get_json()
        print(f"提交评论参数：{data}")

        music_id = data.get('musicId')
        comment = data.get('comment')
        score = data.get('score', 0)

        if not music_id or not comment:
            return jsonify({"code": 400, "msg": "音乐ID和评论不能为空"}), 400

        db = get_db()
        # 查找当前用户的专辑
        album = db.execute(
            'SELECT score, comments FROM albums WHERE id = ? AND user_id = ?',
            (music_id, current_user_id)
        ).fetchone()

        if not album:
            return jsonify({"code": 404, "msg": f"未找到ID为{music_id}的专辑！"}), 404

        # 更新评论和评分
        comments = json.loads(album['comments']) if album['comments'] else []
        comments.append(comment)
        new_score = album['score']
        if score > 0:
            new_score = round((album['score'] + score) / 2, 1)

        # 保存到数据库
        db.execute(
            'UPDATE albums SET score = ?, comments = ? WHERE id = ? AND user_id = ?',
            (new_score, json.dumps(comments), music_id, current_user_id)
        )
        db.commit()

        # 返回更新后的列表（兼容原有逻辑）
        albums = db.execute(
            'SELECT * FROM albums WHERE user_id = ?',
            (current_user_id,)
        ).fetchall()
        album_list = []
        for a in albums:
            a_dict = dict(a)
            a_dict['tags'] = json.loads(a_dict['tags']) if a_dict['tags'] else []
            a_dict['main_type'] = json.loads(a_dict['main_type']) if a_dict['main_type'] else []
            a_dict['tracks'] = json.loads(a_dict['tracks']) if a_dict['tracks'] else []
            a_dict['review'] = json.loads(a_dict['review']) if a_dict['review'] else {}
            a_dict['comments'] = json.loads(a_dict['comments']) if a_dict['comments'] else []
            album_list.append(a_dict)

        return jsonify({"code": 200, "msg": "提交成功", "data": album_list})
    except Exception as e:
        print(f"提交评论出错：{str(e)}")
        print(traceback.format_exc())
        return jsonify({"code": 500, "msg": f"提交评论出错：{str(e)}"}), 500


# 启动服务
if __name__ == '__main__':
    print(f"后端服务启动：http://0.0.0.0:5000")
    print(f"数据文件夹路径：{DATA_DIR}")
    app.run(debug=True, host='0.0.0.0', port=5000)