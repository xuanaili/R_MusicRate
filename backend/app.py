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

# ========== 初始化音乐数据 ==========
def init_data():
    try:
        if not os.path.exists(DATA_DIR):
            os.makedirs(DATA_DIR)
            print(f"创建data文件夹成功：{DATA_DIR}")

        initial_data = [
            {"id": 1, "name": "晴天 - 周杰伦", "score": 8.5, "comments": ["好听", "经典"]},
            {"id": 2, "name": "七里香 - 周杰伦", "score": 9.2, "comments": []}
        ]
        if not os.path.exists(DATA_FILE):
            with open(DATA_FILE, 'w', encoding='utf-8') as file:  # 改变量名：f → file
                json.dump(initial_data, file, ensure_ascii=False, indent=2)
            print(f"创建音乐文件成功：{DATA_FILE}")
        else:
            print(f"音乐文件已存在：{DATA_FILE}")
    except Exception as e:
        print(f"初始化音乐数据失败：{str(e)}")
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


# ========== 获取音乐列表 ==========
@app.route('/api/music', methods=['GET'])
@login_required
def get_music_list():
    try:
        if not os.path.exists(DATA_FILE):
            print(f"音乐文件不存在：{DATA_FILE}")
            return jsonify({"code": 500, "msg": "音乐数据文件缺失！"}), 500

        with open(DATA_FILE, 'r', encoding='utf-8') as file:  # 改变量名：f → file
            music_list = json.load(file)

        print(f"返回音乐列表：{music_list}")
        return jsonify(music_list)
    except Exception as e:
        print(f"获取音乐列表出错：{str(e)}")
        print(traceback.format_exc())
        return jsonify({"code": 500, "msg": f"获取音乐出错：{str(e)}"}), 500


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