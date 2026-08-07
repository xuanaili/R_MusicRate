# 后端开发规范与编码约束

## 一、路由注册规范

- 每个API模块必须导出 `register_*_routes(app)` 函数
- 新模块需在 `backend/api/__init__.py` 的 `register_all_api_routes()` 中添加注册调用
- 路由函数名使用下划线命名法（snake_case）
- 路由URL使用连字符命名法（kebab-case）

## 二、认证与权限规则

- 所有需要登录的接口必须使用 `@login_required` 装饰器
- 管理员专属接口在函数内检查 `is_admin == 1`
- 管理员检查代码模式：
  ```python
  cursor.execute('SELECT is_admin FROM users WHERE user_id = %s', (current_user_id,))
  user = cursor.fetchone()
  if not user or user['is_admin'] != 1:
      return jsonify({"code": 403, "msg": "无管理员权限"}), 200
  ```
- 无需登录的公开接口（如unlock、upload_utils）不加装饰器

## 三、API响应格式

- 统一使用 `{"code": N, "msg": "...", "data": ...}` 格式
- 成功：code=200
- 业务错误：code=400/401/403/404/409，HTTP状态码仍为200
- 服务器错误：code=500
- 使用 `jsonify()` 返回JSON响应

## 四、数据库操作规范

- 使用 `get_db()` 获取连接，不要自行创建
- 使用参数化查询（`%s` 占位符），禁止字符串拼接SQL
- 排序字段必须使用白名单校验（`VALID_SORT_FIELDS`）
- 用户专辑表名通过 `get_album_table_name(user_id)` 获取
- JSON字段使用 `safe_json_loads()` 解析，不要直接 `json.loads()`
- 错误时调用 `if db: db.rollback()` 后返回（**禁止直接 `db.rollback()`**）
- **try/except 中 db 变量安全模式**（强制）：`try` 前必须 `db = None`，`except` 中必须 `if db: db.rollback()`，防止 `get_db()` 失败时 `UnboundLocalError`

## 五、错误处理模式

- 所有路由函数使用 try/except 包裹
- 异常时 `traceback.print_exc()` + `print()` 打印错误
- 返回 `{"code": 500, "msg": "错误描述"}`
- 工具函数返回安全默认值（False, 空字符串, 空列表, 0）

## 六、JSON字段处理

- 存入数据库前用 `json.dumps()` 序列化
- 从数据库读出后用 `safe_json_loads()` 反序列化
- 返回前端时确保已解析为原生对象（不是字符串）
- 容错处理：解析失败返回空列表或None

## 七、文件操作规范

- 上传文件名使用 `secure_filename()` 处理（保留中文字符）
- 文件存储路径使用 `config.py` 中的常量
- 临时文件使用 `tempfile.TemporaryDirectory()` 自动清理
- 删除文件前检查文件是否存在

## 八、编码约定

- 注释和UI文本使用中文
- 风格/标签名格式：`English【中文】`
- 变量/函数名使用英文snake_case
- 导入顺序：标准库 → 第三方库 → 项目内模块
- 每个模块文件顶部标注功能说明

## 九、前后端一致性检查

- 评分计算逻辑：修改后端 `calculate_album_total_score()` 时必须同步修改前端 `scoreCalc.js`
- API接口变更：需同步更新前端对应调用
- 响应格式变更：需确保前端能正确解析

## 十、Git提交规范

- 每次修改必须git上传
- 提交信息使用中文，说明修改内容
- 遵循项目铁律：`每次修改，都要git上传，并说明修改内容`
