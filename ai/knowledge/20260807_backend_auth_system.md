# 后端认证与授权系统参考

## 一、认证流程

### 1. 注册流程
```
前端POST /api/register {username, password}
  → 校验用户名非法字符(%^&)
  → 检查用户名是否已存在
  → bcrypt加密密码 (encrypt_password)
  → INSERT INTO users
  → 创建用户专属专辑表 albums_{user_id}
  → 返回成功
```

### 2. 登录流程
```
前端POST /api/login {username, password}
  → 查询users表
  → bcrypt验证密码 (verify_password)
  → 生成UUID token
  → UPDATE users SET token, last_login
  → 返回 {token, username, user_id, is_admin, is_vip, level}
```

### 3. 请求认证流程
```
前端每次请求附带 Authorization: <token> 请求头
  → @login_required 装饰器拦截
  → 跳过OPTIONS请求的token校验
  → 从请求头获取token
  → 查询users表验证token
  → 设置 g.current_user_id
  → 检查并创建用户专辑表
  → 执行原函数
```

---

## 二、@login_required 装饰器

**位置**：`backend/utils/decorators.py`

**核心逻辑**：
1. OPTIONS请求直接放行（返回200）
2. 从 `request.headers.get('Authorization')` 获取token
3. 查询 `users WHERE token = %s` 验证
4. 设置 `g.current_user_id`
5. 调用 `check_and_create_user_album_table` 确保表存在

**错误码**：
- 401：未登录/token无效
- 500：校验出错

---

## 三、管理员权限判断

**判断方式**：`users.is_admin == 1`

**管理员专属功能**：
- 添加/编辑公共池专辑
- 添加/编辑风格标签
- 上传/删除音频资源
- 删除公共专辑
- 删除公共评论

**代码模式**：
```python
cursor.execute('SELECT is_admin FROM users WHERE user_id = %s', (current_user_id,))
user = cursor.fetchone()
if not user or user['is_admin'] != 1:
    return jsonify({"code": 403, "msg": "无管理员权限"}), 200
```

---

## 四、CORS配置

**位置**：`backend/__init__.py`

```python
CORS(
    app,
    supports_credentials=True,  # 允许携带cookie/token
    origins=r".*",              # 正则匹配任意来源（开发环境）
    methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
    allow_headers=["Content-Type", "Authorization", "X-Requested-With"],
    expose_headers=["Content-Type", "Authorization"],
    max_age=3600                # 预检缓存1小时
)
```

**重要**：`origins="*"` 不能与 `supports_credentials=True` 同时使用，必须用正则 `r".*"` 替代。

---

## 五、前端Token存储与传递

- **存储**：`localStorage.setItem('token', response.data.token)`
- **传递**：Axios请求头 `Authorization: <token>`
- **401拦截**：`main.js` 中Axios拦截器，401响应自动清除localStorage并跳转 `/login`
- **路由守卫**：未认证用户重定向到 `/login`

---

## 六、密码加密

**工具**：`backend/utils/auth.py`，使用bcrypt

```python
def encrypt_password(password: str) -> str:
    salt = bcrypt.gensalt()
    hashed = bcrypt.hashpw(password.encode('utf-8'), salt)
    return hashed.decode('utf-8')

def verify_password(plain_password: str, hashed_password: str) -> bool:
    return bcrypt.checkpw(plain_password.encode('utf-8'), hashed_password.encode('utf-8'))
```

---

## 七、用户ID获取

**方式**：`get_current_user_id()` — 从Flask g对象获取

```python
def get_current_user_id():
    return getattr(g, 'current_user_id', None)
```

**用户表名**：`get_album_table_name(user_id)` — 返回 `albums_{user_id}`
