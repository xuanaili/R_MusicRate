# 后端开发思维流程与检查清单

## 一、新增API路由流程

### 思考步骤
1. 确定路由所属模块（auth/album/album_pool/score/review/comment/playlist/listening/recommend/tags/lyric/share/unlock/audio_resource/upload_utils）
2. 是否需要登录？→ 加 `@login_required`
3. 是否仅管理员？→ 加 `is_admin` 检查
4. 请求方法？GET/POST/PUT/DELETE
5. 请求参数？Query params / JSON body / multipart form
6. 涉及哪张表？共享表 or 用户表？
7. 返回数据格式？`{code, msg, data}`

### 检查清单
- [ ] 路由函数已加 `@login_required`（如需）
- [ ] 管理员权限已检查（如需）
- [ ] SQL使用参数化查询
- [ ] 排序字段使用白名单
- [ ] JSON字段使用 `safe_json_loads()` 解析
- [ ] 错误处理使用 try/except
- [ ] 响应格式符合 `{code, msg, data}` 规范
- [ ] 已在 `register_*_routes()` 中注册路由

## 二、新增数据库表流程

### 思考步骤
1. 表名确定：共享表直接命名，用户表用 `albums_{user_id}` 模式
2. 字段设计：JSON数组用TEXT类型存储
3. 是否需要索引？搜索字段加索引
4. 外键约束？是否需要级联
5. 初始化：在 `init_base_tables()` 中添加创建函数

### 检查清单
- [ ] `my_score` 等JSON字段用TEXT类型（无默认值）
- [ ] 字符集使用utf8mb4
- [ ] create_* 函数已添加到 `init_base_tables()` 调用链
- [ ] 错误处理包含 `db.rollback()`
- [ ] 考虑了与现有表的关联关系

## 三、修改现有功能流程

### 思考步骤
1. 影响范围：前端是否需要同步修改？
2. 评分计算：是否影响前后端一致性？
3. 数据库：是否需要ALTER TABLE？旧数据如何兼容？
4. API兼容性：是否会影响现有前端调用？

### 检查清单
- [ ] 前后端评分逻辑已同步
- [ ] API响应格式向后兼容
- [ ] 数据库字段变更已处理旧数据
- [ ] 已测试管理员和普通用户两种场景

## 四、音频处理相关开发

### 思考步骤
1. 输入格式：NCM/KGG/MP3/OGG/FLAC/WAV/M4A/MP4？
2. 是否需要解密？→ 选择对应解密工具
3. 是否需要合并？→ 使用FFmpeg concat
4. 封面处理：提取/上传/写入
5. 元数据：mutagen提取/写入

### 检查清单
- [ ] 临时文件使用 `tempfile.TemporaryDirectory()`
- [ ] 文件大小未超过200MB限制
- [ ] FFmpeg路径已正确配置
- [ ] 封面压缩后不超过256KB
- [ ] 合并后时长验证（10%误差容忍）

## 五、CORS与认证问题排查

### 常见问题
1. **跨域被拦截** → 检查CORS配置是否为 `origins=r".*"`
2. **401错误** → 检查token是否有效、请求头是否包含Authorization
3. **OPTIONS预检失败** → 检查allow_headers是否包含所需头
4. **凭证携带失败** → 检查 `supports_credentials=True` 和 `withCredentials: true`

### 注意事项
- `origins="*"` 不能与 `supports_credentials=True` 同时使用
- 必须用正则 `r".*"` 替代通配符
- OPTIONS请求由 `@login_required` 装饰器自动放行
