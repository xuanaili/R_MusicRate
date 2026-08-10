# MusicRate 新功能开发工作流

> **配对加载**：与「测试 skill」（`20260810_testing_workflow.md`）**必须成对使用**。
> 新需求开启新对话时，同时加载本文件 + 测试 skill，按「测试先行 → 实现 → 验证 → 提交」推进。
> 每个功能点产出 = 实现代码 + 测试用例，测试与开发并行、互相验证修改。

## 1. 需求解读 → README对齐

- **先读 README.md**，确认需求是否在「进行中」或「待做」列表中
- 将 README 中的需求拆解为可执行的任务清单，不要遗漏任何细节
- 如果需求有模糊处（如"评分范围多少"），自行定义合理阈值并告知用户

## 2. 代码探索 → 全链路扫描

开发前必须阅读以下文件，理解现有架构：

| 层级 | 必读文件 | 目的 |
|------|---------|------|
| 后端 | `backend/api/__init__.py` | 确认路由注册方式 |
| 后端 | `backend/utils/db.py` | 确认表结构、字段名、已有字段（用户分表 `albums_{user_id}`） |
| 后端 | `backend/api/<相关模块>.py` | 复用现有查询模式、`safe_json_loads`、评分计算等 |
| 前端 | `frontend/src/views/WebHome.vue` | 确认 Tab 结构、子组件挂载方式 |
| 前端 | `frontend/src/main.js` | 确认 axios 挂载、路由配置、认证守卫 |
| 前端 | 对应的现有组件 | 复用样式模式、`mainColor`/`mainColorDark`/`mainColorDarkDouble` props 用法 |

**关键原则**：不要假设字段存在或不存在，去 `db.py` 的建表 DDL 里确认。

## 3. 任务拆分 → 逐步交付

使用 TaskCreate 工具拆分任务，每个任务粒度适中：
- 一个后端 API 文件 = 一个任务
- 一个后端函数/工具及其测试用例 = 一个任务（测试先行，规范见测试 skill）
- 一个前端组件 = 一个任务
- 路由注册 = 独立任务
- Git 提交 = 独立任务

**每个任务完成后立即 TaskUpdate 标记 completed**，保持进度可见。

## 4. 后端开发模式

### 4.1 新增 API 模块三步走
1. 新建 `backend/api/<module>.py`，定义 `register_<module>_routes(app)` 函数
2. 在 `backend/api/__init__.py` 中导入并注册
3. 所有接口加 `@login_required` 装饰器

### 4.2 用户专属表查询模板
```python
table_name = get_album_table_name(current_user_id)
db = get_db()
cursor = db.cursor(pymysql.cursors.DictCursor)
# ... 查询逻辑 ...
cursor.close()
```

### 4.3 JSON 字段处理
- 读取：`safe_json_loads(album.get("tags", "[]"))`（backend/utils/json.py）
- 返回：直接返回解析后的数组/对象，**不要让前端再做 JSON.parse**
- 存储：`json.dumps(tags, ensure_ascii=False)`

### 4.4 评分计算
- 复用 `backend/utils/score.py` 的 `calculate_album_total_score()`
- 规则：专辑分 × 0.6 + 单曲均分 × 0.4（0 分单曲不计入）；前端用 `frontend/src/utils/scoreCalc.js`，**前后端逻辑必须一致**

### 4.5 随机查询
- 使用 `ORDER BY RAND() LIMIT 1`，简单可靠
- 先查 `COUNT(*)` 判断总数，避免空结果

## 5. 前端开发模式

### 5.1 新组件开发（Vue 2 Options API）
- 页面级放 `views/`，功能子组件放 `components/`（albumDetail/discoverMusic/myMusic/sidebar/item）
- 使用 `this.$axios`，成功判断 `res.data.code === 200`
- 需要主题色 → 声明 `mainColor`/`mainColorDark`/`mainColorDarkDouble` 三个 props，CSS 用 `v-bind(...)` 绑定
- **不要混用** setup + methods（本项目是 Vue 2，无 `<script setup>`）

### 5.2 布局模式
- 左右布局：`display: flex; gap: 24px;`，左侧 `flex: 1`，右侧固定宽度
- 响应式：`@media (max-width: 768px) { flex-direction: column; }`
- 列表封面一律小图用缩略图 URL：`coverThumb()`（`frontend/src/utils/cover.js`），避免下载几 MB 原图

### 5.3 父子组件数据传递
- **不要让子组件重复请求已有的数据**，通过 props 传递
- 子组件需要的数据如果父组件已经 fetch 过，直接 prop 传入

## 6. 调试排错模式

### 6.1 前端报错排查流程
1. 打开浏览器控制台看 console.error
2. 检查是否是**后端返回数据格式与前端解析不匹配**（如双重 JSON.parse）
3. 检查 eslint 编译错误（未使用变量、类型错误等）
4. 检查组件 props/emit 是否正确传递

### 6.2 后端数据格式常见陷阱
| 陷阱 | 症状 | 解决 |
|------|------|------|
| 后端已解析 JSON，前端又 parse | `JSON.parse` 报错 → 加载失败 | 后端 `safe_json_loads` 已解析，前端直接用 |
| 数据库字段为空字符串 | `json.loads("")` 报错 | 使用 `safe_json_loads` |
| 新增字段未在详情接口返回 | 前端拿不到数据 | 检查接口返回字典是否包含新字段 |
| 用户分表未创建 | 查询报错表不存在 | 确认 `@login_required` 里已建表 |

### 6.3 组件销毁时异步请求丢失
- `beforeDestroy` 中使用 `async/.then()` 的请求可能被中断
- **解决方案**：使用同步 `XMLHttpRequest`（`xhr.open(..., false)`）确保请求发出
- 对于用户主动触发的操作，使用 `await` 即可

## 7. Git 提交规范

- 每个功能点完成后立即 commit
- commit message 格式：`中文标题：具体改动内容`
- 多行 commit message 分层描述：
  - 第一行：简要总结
  - 空行后：具体改动列表（用 `-` 开头）
- `git push` 前检查是否有远程仓库

## 8. 质量检查清单

开发完成后逐项检查：

- [ ] 后端新接口是否加了 `@login_required`
- [ ] 后端新接口是否在 `__init__.py` 注册
- [ ] 后端返回的 JSON 字段是否用 `safe_json_loads` 解析
- [ ] 前端是否通过 props 正确接收主题色
- [ ] 前端是否有 eslint 错误（未使用变量等）
- [ ] 前端子组件是否重复请求了父组件已有的数据
- [ ] 响应式布局是否正常（窄屏/宽屏）
- [ ] beforeDestroy 中是否有未完成的异步请求
- [ ] 后端逻辑改动是否跑过 `pytest`（见测试 skill：`portable\python\python.exe -m pytest`）
- [ ] 已提交 git

---

以下为固定指令，下次新开对话直接贴本文件 + 测试 skill（20260810_testing_workflow.md）+ 再贴下方指令：
请以本文档 + 测试 skill 为标准工作流范式，开发我接下来的新功能需求。测试与开发并行、互相验证修改：先写测试（红灯）→ 实现 → 跑测试（绿灯）→ 提交（代码+测试一起）。优先复用本文的需求解读→代码探索→任务拆分→开发→调试→提交流程，不要从零重新思考。根据新需求的差异点做适配微调，输出稳定、同规范的解决方案。
