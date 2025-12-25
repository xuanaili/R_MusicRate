# 1. 导入需要的工具：
from flask import Flask, request, jsonify
from flask_cors import CORS
import json
import os
import uuid
from functools import wraps
import traceback

# 2. 初始化Flask应用
app = Flask(__name__)
CORS(app, supports_credentials=True)  # 允许跨域带凭证

# 3. 配置数据文件路径（绝对路径，避免相对路径问题）
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(BASE_DIR, 'data')
DATA_FILE = os.path.join(DATA_DIR, 'music_data.json')
USER_FILE = os.path.join(DATA_DIR, 'user_data.json')


# ========== 初始化用户数据 ==========
def init_user():
    try:
        if not os.path.exists(DATA_DIR):
            os.makedirs(DATA_DIR)
            print(f"创建data文件夹成功：{DATA_DIR}")

        initial_users = [{"id": 1, "username": "admin", "password": "123456", "token": ""}]
        if not os.path.exists(USER_FILE):
            with open(USER_FILE, 'w', encoding='utf-8') as file:  # 改变量名：f → file
                json.dump(initial_users, file, ensure_ascii=False, indent=2)
            print(f"创建用户文件成功：{USER_FILE}")
        else:
            print(f"用户文件已存在：{USER_FILE}")
    except Exception as e:
        print(f"初始化用户数据失败：{str(e)}")
        print(traceback.format_exc())


# ========== 登录校验装饰器（核心修复：变量名+逻辑） ==========
def login_required(func):  # 改变量名：f → func，避免冲突
    @wraps(func)
    def wrapper(*args, **kwargs):  # 改函数名：decorated_function → wrapper
        try:
            # 1. 获取请求头的token
            token = request.headers.get('Authorization')
            if not token:
                print("请求头无Authorization token")
                return jsonify({"code": 401, "msg": "请先登录！"}), 401

            # 2. 检查用户文件是否存在
            if not os.path.exists(USER_FILE):
                print(f"用户文件不存在：{USER_FILE}")
                return jsonify({"code": 500, "msg": "用户数据文件缺失！"}), 500

            # 3. 读取用户数据（改变量名：f → file）
            with open(USER_FILE, 'r', encoding='utf-8') as file:
                users = json.load(file)

            # 4. 验证token是否有效
            valid_user = None
            for u in users:
                if u.get('token') == token:
                    valid_user = u
                    break

            if not valid_user:
                print(f"token无效：{token}")
                return jsonify({"code": 401, "msg": "登录已过期，请重新登录！"}), 401

            # 5. 校验通过，执行原函数
            return func(*args, **kwargs)
        except Exception as e:
            print(f"登录校验失败：{str(e)}")
            print(traceback.format_exc())
            return jsonify({"code": 500, "msg": f"登录校验出错：{str(e)}"}), 500

    return wrapper


# ========== 工具函数：生成唯一用户ID ==========
def get_next_user_id():
    """读取用户文件，返回下一个可用的用户ID（避免重复）"""
    try:
        if not os.path.exists(USER_FILE):
            return 1  # 没有用户文件，第一个用户ID为1
        with open(USER_FILE, 'r', encoding='utf-8') as file:
            users = json.load(file)
        if not users:
            return 1
        # 取最大ID +1
        max_id = max([u['id'] for u in users])
        return max_id + 1
    except Exception as e:
        print(f"生成用户ID失败：{str(e)}")
        return 1  # 兜底返回1
# ========== 工具函数：生成唯一专辑ID ==========
def get_next_album_id():
    """读取专辑文件，返回下一个可用的专辑ID"""
    try:
        if not os.path.exists(DATA_FILE):
            return 1
        with open(DATA_FILE, 'r', encoding='utf-8') as file:
            albums = json.load(file)
        if not albums:
            return 1
        max_id = max([album['id'] for album in albums])
        return max_id + 1
    except Exception as e:
        print(f"生成专辑ID失败：{str(e)}")
        return 1




# ========== 初始化专辑数据（替换原有init_data） ==========
# ========== 初始化专辑数据（扩展字段） ==========
def init_data():
    try:
        if not os.path.exists(DATA_DIR):
            os.makedirs(DATA_DIR)
            print(f"创建data文件夹成功：{DATA_DIR}")

        # 扩展后的专辑数据结构（包含你要的所有详情字段）
        initial_data = [
            {
                "id": 1,
                "album_name": "七里香",
                "cover_img": "",
                "singer": "周杰伦",
                "release_year": 2004,
                "start_time": "2004-08-03",  # 开始时间
                "track_count": 10,           # 曲目数量
                "track_duration": "40.00",   # 曲目时长
                "my_score": 92.0,            # 我的评分（50.9这种格式）
                "burn_class": "",            # 刻录分类
                "duration_type": "LP",       # 时长类型
                "tags": ["经典", "华语"],
                "main_type": ["流行"],       # 主要类型（数组）
                "code": "04080307",          # 代号
                "video_shared": "",          # 视频已分享
                "mandopop_code": "040113",   # Mandopop代码
                # 曲目详情（核心）
                "tracks": [
                    {"name": "七里香", "time": "0:00", "score": 9.5},
                    {"name": "外婆", "time": "4:32", "score": 8.8},
                    {"name": "将军", "time": "8:15", "score": 9.0}
                ],
                # 听后感/评论（简化版）
                "review": {
                    "single_score": 91.5,    # 单曲打分
                    "private_score": 0.5,    # 私自打分
                    "final_score": 92.0,     # 最终评分
                    "personal_feeling": "经典华语专辑，百听不厌",  # 个人感想
                    "comments": {            # 各平台评论
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



# 启动时初始化
init_user()
init_data()



# ========== 注册接口 ==========
@app.route('/api/register', methods=['POST'])
def register():
    try:
        data = request.get_json()
        print(f"注册请求参数：{data}")

        # 1. 校验必填字段
        username = data.get('username')
        password = data.get('password')
        if not username or not password:
            return jsonify({"code": 400, "msg": "用户名和密码不能为空！"}), 400

        # 2. 确保data文件夹存在
        if not os.path.exists(DATA_DIR):
            os.makedirs(DATA_DIR)

        # 3. 读取/初始化用户数据
        users = []
        if os.path.exists(USER_FILE):
            with open(USER_FILE, 'r', encoding='utf-8') as file:
                users = json.load(file)

        # 4. 检查用户名是否已存在（核心：避免重复注册）
        for u in users:
            if u['username'] == username:
                print(f"用户名已存在：{username}")
                return jsonify({"code": 400, "msg": "用户名已被注册！"}), 400

        # 5. 生成新用户数据
        new_user = {
            "id": get_next_user_id(),  # 唯一ID
            "username": username,
            "password": password,  # 注意：实际项目要加密，这里简化
            "token": ""  # 初始token为空
        }
        users.append(new_user)

        # 6. 保存新用户数据
        with open(USER_FILE, 'w', encoding='utf-8') as file:
            json.dump(users, file, ensure_ascii=False, indent=2)

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

# ========== 登录接口 ==========
@app.route('/api/login', methods=['POST'])
def login():
    try:
        data = request.get_json()
        print(f"登录请求参数：{data}")

        username = data.get('username')
        password = data.get('password')

        if not username or not password:
            return jsonify({"code": 400, "msg": "账号和密码不能为空！"}), 400

        if not os.path.exists(USER_FILE):
            return jsonify({"code": 500, "msg": "用户数据文件缺失！"}), 500

        with open(USER_FILE, 'r', encoding='utf-8') as file:  # 改变量名：f → file
            users = json.load(file)

        # 查找匹配的用户（改用循环，避免next()报错）
        login_user = None
        for u in users:
            if u['username'] == username and u['password'] == password:
                login_user = u
                break

        if not login_user:
            print(f"账号密码错误：用户名={username}，密码={password}")
            return jsonify({"code": 401, "msg": "账号或密码错误！"}), 401

        # 生成token并更新
        token = str(uuid.uuid4())
        login_user['token'] = token  # 直接更新用户token

        # 保存用户数据
        with open(USER_FILE, 'w', encoding='utf-8') as file:  # 改变量名：f → file
            json.dump(users, file, ensure_ascii=False, indent=2)

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


# ========== 获取专辑列表（原get_music_list，改名更贴合） ==========
@app.route('/api/music', methods=['GET'])
@login_required
def get_album_list():  # 函数名从get_music_list改成get_album_list
    try:
        if not os.path.exists(DATA_FILE):
            print(f"专辑文件不存在：{DATA_FILE}")
            return jsonify({"code": 500, "msg": "专辑数据文件缺失！"}), 500

        with open(DATA_FILE, 'r', encoding='utf-8') as file:
            album_list = json.load(file)

        print(f"返回专辑列表：{album_list}")
        return jsonify(album_list)
    except Exception as e:
        print(f"获取专辑列表出错：{str(e)}")
        print(traceback.format_exc())
        return jsonify({"code": 500, "msg": f"获取专辑出错：{str(e)}"}), 500
# ========== 添加专辑接口 ==========
@app.route('/api/album/add', methods=['POST'])
@login_required  # 必须登录才能添加
def add_album():
    try:
        data = request.get_json()
        print(f"添加专辑请求参数：{data}")

        # 1. 校验必填字段（根据你的需求调整）
        required_fields = ['album_name', 'singer', 'release_year', 'main_type']
        for field in required_fields:
            if not data.get(field):
                return jsonify({"code": 400, "msg": f"{field}不能为空！"}), 400

        # 2. 整理专辑数据
        new_album = {
            "id": get_next_album_id(),
            "album_name": data.get('album_name'),
            "cover_img": data.get('cover_img', ''),
            "singer": data.get('singer'),
            "release_year": int(data.get('release_year')),
            "start_time": data.get('start_time', ''),  # 新增
            "track_count": int(data.get('track_count', 0)),  # 新增
            "track_duration": data.get('track_duration', ''),  # 新增
            "my_score": float(data.get('my_score', 0.0)),  # 新增
            "burn_class": data.get('burn_class', ''),  # 新增
            "duration_type": data.get('duration_type', ''),  # 新增
            "main_type": data.get('main_type', []),  # 新增（数组）
            "code": data.get('code', ''),  # 新增
            "video_shared": data.get('video_shared', ''),  # 新增
            "mandopop_code": data.get('mandopop_code', ''),  # 新增
            "tags": data.get('tags', []),
            # 曲目和评论默认空
            "tracks": data.get('tracks', []),
            "review": {
                "single_score": 0.0,
                "private_score": 0.0,
                "final_score": 0.0,
                "personal_feeling": "",
                "comments": {}
            },
            "score": float(data.get('score', 0.0)),
            "comments": []
        }

        # 3. 读取现有专辑数据
        albums = []
        if os.path.exists(DATA_FILE):
            with open(DATA_FILE, 'r', encoding='utf-8') as file:
                albums = json.load(file)

        # 4. 添加新专辑
        albums.append(new_album)

        # 5. 保存更新后的数据
        with open(DATA_FILE, 'w', encoding='utf-8') as file:
            json.dump(albums, file, ensure_ascii=False, indent=2)

        print(f"添加专辑成功：{new_album['album_name']}")
        return jsonify({
            "code": 200,
            "msg": "专辑添加成功！",
            "data": new_album
        })
    except Exception as e:
        print(f"添加专辑出错：{str(e)}")
        print(traceback.format_exc())
        return jsonify({
            "code": 500,
            "msg": f"添加专辑失败：{str(e)}"
        }), 500

# ========== 新增：删除专辑接口 ==========
@app.route('/api/album/delete/<int:album_id>', methods=['DELETE'])
@login_required
def delete_album(album_id):
    try:
        if not os.path.exists(DATA_FILE):
            return jsonify({"code": 404, "msg": "专辑数据文件不存在！"}), 404

        # 读取所有专辑
        with open(DATA_FILE, 'r', encoding='utf-8') as file:
            albums = json.load(file)

        # 过滤掉要删除的专辑
        new_albums = [a for a in albums if a['id'] != album_id]
        if len(new_albums) == len(albums):
            return jsonify({"code": 404, "msg": f"未找到ID为{album_id}的专辑！"}), 404

        # 保存删除后的数据
        with open(DATA_FILE, 'w', encoding='utf-8') as file:
            json.dump(new_albums, file, ensure_ascii=False, indent=2)

        return jsonify({
            "code": 200,
            "msg": f"删除ID为{album_id}的专辑成功！"
        })
    except Exception as e:
        print(f"删除专辑出错：{str(e)}")
        return jsonify({"code": 500, "msg": f"删除专辑失败：{str(e)}"}), 500

# ========== 新增：编辑听后感接口 ==========
@app.route('/api/album/review/edit/<int:album_id>', methods=['POST'])
@login_required
def edit_review(album_id):
    try:
        data = request.get_json()
        if not data or not data.get('personal_feeling'):
            return jsonify({"code": 400, "msg": "听后感内容不能为空！"}), 400

        if not os.path.exists(DATA_FILE):
            return jsonify({"code": 404, "msg": "专辑数据文件不存在！"}), 404

        # 读取所有专辑
        with open(DATA_FILE, 'r', encoding='utf-8') as file:
            albums = json.load(file)

        # 查找并更新听后感
        album = None
        for a in albums:
            if a['id'] == album_id:
                album = a
                break
        if not album:
            return jsonify({"code": 404, "msg": f"未找到ID为{album_id}的专辑！"}), 404

        # 更新听后感（添加时间戳）
        album['review']['personal_feeling'] = data.get('personal_feeling')
        album['review']['update_time'] = data.get('update_time')  # 前端传的时间戳

        # 保存更新后的数据
        with open(DATA_FILE, 'w', encoding='utf-8') as file:
            json.dump(albums, file, ensure_ascii=False, indent=2)

        return jsonify({
            "code": 200,
            "msg": "听后感编辑成功！",
            "data": album['review']
        })
    except Exception as e:
        print(f"编辑听后感出错：{str(e)}")
        return jsonify({"code": 500, "msg": f"编辑听后感失败：{str(e)}"}), 500

# ========== 新增：删除听后感接口 ==========
@app.route('/api/album/review/delete/<int:album_id>', methods=['DELETE'])
@login_required
def delete_review(album_id):
    try:
        if not os.path.exists(DATA_FILE):
            return jsonify({"code": 404, "msg": "专辑数据文件不存在！"}), 404

        # 读取所有专辑
        with open(DATA_FILE, 'r', encoding='utf-8') as file:
            albums = json.load(file)

        # 查找并清空听后感
        album = None
        for a in albums:
            if a['id'] == album_id:
                album = a
                break
        if not album:
            return jsonify({"code": 404, "msg": f"未找到ID为{album_id}的专辑！"}), 404

        # 清空听后感
        album['review']['personal_feeling'] = ""
        album['review']['update_time'] = ""

        # 保存更新后的数据
        with open(DATA_FILE, 'w', encoding='utf-8') as file:
            json.dump(albums, file, ensure_ascii=False, indent=2)

        return jsonify({
            "code": 200,
            "msg": "听后感删除成功！"
        })
    except Exception as e:
        print(f"删除听后感出错：{str(e)}")
        return jsonify({"code": 500, "msg": f"删除听后感失败：{str(e)}"}), 500
# ========== 获取专辑详情接口 ==========
@app.route('/api/album/detail/<int:album_id>', methods=['GET'])
@login_required
def get_album_detail(album_id):
    try:
        if not os.path.exists(DATA_FILE):
            return jsonify({"code": 404, "msg": "专辑数据文件不存在！"}), 404

        # 读取所有专辑数据
        with open(DATA_FILE, 'r', encoding='utf-8') as file:
            albums = json.load(file)

        # 根据ID查找专辑
        album = None
        for a in albums:
            if a['id'] == album_id:
                album = a
                break

        if not album:
            return jsonify({"code": 404, "msg": f"未找到ID为{album_id}的专辑！"}), 404

        # 返回专辑详情
        return jsonify({
            "code": 200,
            "msg": "获取专辑详情成功！",
            "data": album
        })
    except Exception as e:
        print(f"获取专辑详情出错：{str(e)}")
        print(traceback.format_exc())
        return jsonify({
            "code": 500,
            "msg": f"获取专辑详情失败：{str(e)}"
        }), 500

# ========== 提交评论 ==========
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

        if not os.path.exists(DATA_FILE):
            return jsonify({"code": 500, "msg": "音乐数据文件缺失！"}), 500

        with open(DATA_FILE, 'r', encoding='utf-8') as file:  # 改变量名：f → file
            music_list = json.load(file)

        # 更新评论和评分
        for music in music_list:
            if music['id'] == music_id:
                music['comments'].append(comment)
                if score > 0:
                    music['score'] = round((music['score'] + score) / 2, 1)
                break

        # 保存更新后的数据
        with open(DATA_FILE, 'w', encoding='utf-8') as file:  # 改变量名：f → file
            json.dump(music_list, file, ensure_ascii=False, indent=2)

        return jsonify({"code": 200, "msg": "提交成功", "data": music_list})
    except Exception as e:
        print(f"提交评论出错：{str(e)}")
        print(traceback.format_exc())
        return jsonify({"code": 500, "msg": f"提交评论出错：{str(e)}"}), 500


# 启动服务
if __name__ == '__main__':
    print(f"后端服务启动：http://0.0.0.0:5000")
    print(f"数据文件夹路径：{DATA_DIR}")
    app.run(debug=True, host='0.0.0.0', port=5000)