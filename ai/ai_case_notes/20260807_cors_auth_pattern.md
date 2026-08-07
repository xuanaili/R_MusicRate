# 案例：CORS跨域与认证配置

## 基本信息

- **案例编号**：20260807_cors_auth_config
- **关键词**：CORS、跨域、Token认证、Flask-CORS、credentials
- **适用场景**：前后端分离开发，前端localhost:8080访问后端localhost:5000

## 问题描述

MusicRate前端运行在 `localhost:8080`（Vue CLI dev server），后端运行在 `localhost:5000`（Flask）。由于端口不同，属于跨域请求。同时需要携带认证token（Authorization请求头），且需要支持cookie传递。

## 核心需求

1. 跨域请求不被浏览器拦截
2. 支持携带Authorization请求头
3. 支持credentials（cookie/token）
4. 支持OPTIONS预检请求
5. 换电脑/换网络后不需要重新配置

## 解决方案

### CORS配置（Flask-CORS）

```python
from flask_cors import CORS

CORS(
    app,
    supports_credentials=True,    # 必须开启：允许携带凭证
    origins=r".*",                # 正则匹配任意来源（不是"*"）
    methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
    allow_headers=["Content-Type", "Authorization", "X-Requested-With"],
    expose_headers=["Content-Type", "Authorization"],
    max_age=3600                  # 预检缓存1小时
)
```

### 关键陷阱：`origins="*"` 与 `supports_credentials=True` 冲突

浏览器规范规定：当 `Access-Control-Allow-Credentials: true` 时，`Access-Control-Allow-Origin` 不能为 `*`。

**错误写法**：
```python
CORS(app, origins="*", supports_credentials=True)  # 浏览器会拒绝！
```

**正确写法**：
```python
CORS(app, origins=r".*", supports_credentials=True)  # 正则匹配，返回具体origin
```

Flask-CORS的 `origins=r".*"` 会将请求的Origin原样返回在响应头中，而不是返回 `*`，从而满足浏览器规范。

### 前端Axios配置

```javascript
const api = axios.create({
    baseURL: 'http://localhost:5000',
    withCredentials: true,  // 携带cookie
    headers: { 'Authorization': token }
})
```

### @login_required装饰器处理OPTIONS

```python
def login_required(func):
    @wraps(func)
    def wrapper(*args, **kwargs):
        # OPTIONS预检请求直接放行
        if request.method == 'OPTIONS':
            return jsonify({"code": 200, "msg": "OPTIONS allowed"}), 200
        # ... 正常token校验
    return wrapper
```

## 踩坑记录

1. **换电脑IP变化**：原来用 `origins="http://192.168.x.x:8080"` 硬编码，换网络后失效 → 改为 `origins=r".*"`
2. **预检请求被拦截**：OPTIONS请求不带token，被 `@login_required` 拦截 → 装饰器中跳过OPTIONS
3. **凭证模式冲突**：`origins="*"` + `supports_credentials=True` 组合无效 → 必须用正则
4. **缓存问题**：预检请求结果被缓存，修改CORS配置后需清除浏览器缓存 → 设置 `max_age=3600`

## 适配规则

- 开发环境使用 `origins=r".*"`，生产环境应限制为具体域名
- 任何需要认证的跨域请求都必须设置 `supports_credentials=True`
- 前端Axios必须设置 `withCredentials: true`
- `@login_required` 装饰器必须处理OPTIONS请求
- 如需支持多环境部署，CORS origins应从环境变量读取
