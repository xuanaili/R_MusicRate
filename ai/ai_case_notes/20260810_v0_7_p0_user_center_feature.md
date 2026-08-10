# v0.7 P0 个人用户中心骨架（avatar 幂等迁移 + /api/user/info + 改密码 + 模式切换入口）

## 一、案例基本信息
- 问题场景分类：新功能开发（v0.7 P0 骨架）→ 后端表迁移 + 新 API 模块 + 前端侧边栏改造 + 多入口复用
- 产生时间：2026-08-10
- 项目模块：
  - 后端：`backend/utils/db.py`、`backend/api/user.py`（新）、`backend/utils/user.py`（新）、`backend/api/__init__.py`
  - 前端：`frontend/src/components/user/`（新：UserAvatar / ProfilePanel / UserCenter）、`PlayerPlaylist.vue`、`WebHome.vue`
- 相似问题判定特征：
  1. "给已有表加列 / 表结构迁移" → `information_schema.columns` 查缺列才 ALTER，幂等迁移模式（缺列→ALTER，已存在→跳过）
  2. "个人中心 / 账号 / 用户信息" → 抽公共容器组件，多入口复用（播放列表侧边栏 tab + 主页右上角抽屉）
  3. "新增后端 API 模块" → `backend/api/<模块>.py` + `__init__.py` 注册 + 全部 `@login_required`
  4. "改密码 / 表单校验分支" → 校验纯函数抽到 `backend/utils/`，零 DB 依赖可单测
  5. "侧边栏/组件加新模式切换" → 顶部 toggle + 原内容 `v-if` 包裹 + 新内容 `v-else`，旧逻辑原样保留

## 二、原始问题描述
- 背景：v0.7 把 BookRate 的个人用户功能搬来 MusicRate，落点定为「用户播放歌曲时的播放列表侧边栏」——`PlayerPlaylist.vue` 与个人用户界面合并。P0 只做骨架，P1（头像上传/蒙版调节）、P2（听取统计）后续迭代。
- 痛点/约束：
  - `users` 表加列在本项目无先例，必须幂等（重复启动不报错），并挂进 `init_base_tables()`
  - `GET /api/user/info` 的专辑数要取 `albums_{user_id}` 实时 COUNT（非 `users.album_count` 静态字段）
  - WebHome 无专辑播放上下文，UserCenter 独立抽屉主色取自 localStorage 主题色；两入口（侧边栏/主页）共享同一组件
  - 前端为 Vue 2 Options API（无 `<script setup>`），用 `this.$axios`；`$message` 全局未注册，组件需 `alert` 兜底
  - 主题色组件用 `mainColor`/`mainColorDark`/`mainColorDarkDouble` 三个 props + `v-bind()` 绑定

## 三、核心诉求
1. `users.avatar` 列幂等迁移（VARCHAR(255) 存图片 URL，默认空串），新库建表直接带列、旧库 ALTER 补列
2. `GET /api/user/info`（用户名/注册时间/等级/专辑数/头像/最近登录/会员）
3. `POST /api/user/change-password`（bcrypt 校验旧密码 + 更新新密码）
4. PlayerPlaylist 顶部「歌单 / 个人中心」模式切换；歌单模式原有拖拽/备份/防抖全部不动
5. UserCenter/ProfilePanel/UserAvatar 组件 + WebHome 右上角头像入口弹独立抽屉
6. 测试先行：`test_user_table_migration.py`（avatar 幂等迁移）+ `test_password.py`（改密码校验分支）

## 四、最终解决方案/改造步骤
1. **后端迁移**（`backend/utils/db.py`）：
   - `needs_avatar_column(existing_columns)`：纯函数，`'avatar' not in [c.lower() for c in cols]`（大小写容错）
   - `ensure_users_avatar_column()`：查 `information_schema.COLUMNS` → 缺列才 `ALTER TABLE users ADD COLUMN avatar VARCHAR(255) DEFAULT ''`；`create_users()` DDL 同步加列（新库直接建出）
   - `init_base_tables()` 中 `create_users()` 之后调用
2. **后端校验**（`backend/utils/user.py`）：`validate_password_change(old, new, current_hashed)` 返回错误串或 None，分支：旧空/新空/长度<6/新旧相同/旧密码错误（`verify_password`）
3. **后端接口**（`backend/api/user.py`，新）：`register_user_routes(app)`，`GET /api/user/info` + `POST /api/user/change-password` 均 `@login_required`；`__init__.py` 导入并注册
4. **前端组件**（`frontend/src/components/user/`，新）：
   - `UserAvatar.vue`：头像圆（img 或首字母回退）+ 用户名，点击 emit `click`
   - `ProfilePanel.vue`：拉 `/api/user/info` 展示资料 + 改密码表单（旧/新/确认，前端校验）+ 退出登录（清 localStorage + 跳 /login）；消息用 `if(this.$message) ... else alert(...)`
   - `UserCenter.vue`：子 tab（个人资料/外观/音乐统计）+ `dismissible` prop（真→显示关闭按钮 emit `close`）；外观/统计留 P1/P2 占位
5. **PlayerPlaylist.vue**：顶部加模式 toggle（`sidebarMode: 'playlist'|'user'`），原内容包 `<template v-if="sidebarMode==='playlist'">`，`v-else` 渲染 `<UserCenter>`（传 mainColorDark 兜底主色）
6. **WebHome.vue**：右上角替换为 `<UserAvatar @click="showUserCenter=true">`；新增独立抽屉（`.uc-mask` + `.uc-drawer` 固定右侧 380px 同款样式）内嵌 `<UserCenter dismissible>`；created 里拉 `/api/user/info` 取头像

## 五、关键代码/配置/模板（可直接复用）
```python
# backend/utils/db.py —— 幂等迁移（任意表加列可直接套用）
def needs_avatar_column(existing_columns):
    return 'avatar' not in [c.lower() for c in existing_columns]

def ensure_users_avatar_column():
    # SELECT COLUMN_NAME FROM information_schema.COLUMNS WHERE TABLE_SCHEMA=%s AND TABLE_NAME='users'
    # if needs_avatar_column(columns): ALTER TABLE users ADD COLUMN avatar VARCHAR(255) DEFAULT '' ...
```
```python
# backend/utils/user.py —— 表单校验纯函数（零 DB 可单测）
def validate_password_change(old_password, new_password, current_hashed):
    if not old_password: return '旧密码不能为空'
    if not new_password: return '新密码不能为空'
    if len(new_password) < 6: return '新密码长度不能少于6位'
    if old_password == new_password: return '新旧密码不能相同'
    if not verify_password(old_password, current_hashed): return '旧密码错误'
    return None
```
```python
# backend/api/user.py 骨架 —— 新 API 模块三步走
@login_required
def user_info():
    # SELECT user_id, username, create_time, level, last_login, is_vip, avatar FROM users WHERE user_id=%s
    # album_count = SELECT COUNT(*) FROM `albums_{uid}`
```
前端模式切换骨架（侧边栏/组件加新模式）：
```html
<div class="toggle">
  <div :class="{active: mode==='a'}" @click="mode='a'">模式A</div>
  <div :class="{active: mode==='b'}" @click="mode='b'">模式B</div>
</div>
<template v-if="mode==='a'"><!-- 原内容原样 --></template>
<CompB v-else .../>
```

## 六、踩坑点 & 注意事项（非常重要）
- **`get_db()` 依赖 Flask app context**（内部用 `flask.g`）：脚本单独验证迁移/接口会报 `RuntimeError: Working outside of application context` → 必须 `create_app()` 后用 `with app.app_context():` 包住
- **Windows GBK 控制台 print emoji 崩溃**：迁移函数 print `❌/✅` 在 GBK 控制台直接 `UnicodeEncodeError` → 跑脚本前 `PYTHONIOENCODING=utf-8`
- **纯函数测试要与 DB 封装分离**：`needs_avatar_column` / `validate_password_change` 独立成纯函数，测试才做到零 DB 依赖（README 测试清单里"迁移单测"实际测的是决策纯函数，不是 DB 操作）
- **`$message` 全局未注册**：全仓库 `this.$message?.xxx` 是"可能未定义"容错写法；新组件要保证有反馈用 `if (this.$message) {...} else alert(...)`
- **Bash 工作目录跨调用保持**：`cd frontend` 后再跑 pytest 会 `No such file` → 用项目根绝对路径或回到根目录
- **albums_{uid} 表 COUNT**：`@login_required` 已保证建表，直接 `SELECT COUNT(*)` 即可，不必再 `check_and_create`
- 主题色兜底：PlayerPlaylist 只有 `mainColorDark/Double` 两个色，嵌 UserCenter 时用 `mainColorDark` 同时顶替 `mainColor`

## 七、同类问题快速适配规则
下次遇到相似问题，只需改：
- 【适配点1】给任意已有表加列：复制 `ensure_users_avatar_column`，改表名 / 新列名 / ALTER DDL；纯判断 `needs_avatar_column` 泛化为 `needs_column(cols, col_name)`
- 【适配点2】新增 API 模块：复制 `backend/api/user.py` 三步走（新模块 + `__init__.py` 导入注册 + `@login_required`），校验分支抽 `backend/utils/` 纯函数
- 【适配点3】前端新抽屉/新 tab：复制 UserCenter 容器模式（子 tab + `dismissible` + 占位面板），宿主负责定位（侧边栏内嵌 / 主页 `.uc-drawer`）
- 【适配点4】新接口返回字段：前端新增展示字段只需改 `ProfilePanel` 的 `info-row` 与 `/api/user/info` 的 SELECT；`userInfo` 对象用 `{...默认, ...res.data.data}` 合并防 undefined

## 八、优化复盘（2026-08-10 本次对话）
**流程效率**：整体顺畅。按铁律先加载开发 skill + 测试 skill，读 README 定位 v0.7 P0 任务清单，按「测试先行→实现→验证→提交」推进。测试先行这一步起效明显：`needs_avatar_column` / `validate_password_change` 先写测试定死分支，实现零返工，11 个新单测一次绿灯。

**浪费点**：
1. **`-c` 脚本直接 import backend 报 `No module named 'backend'`**：`python -c` 不含项目根 sys.path。教训：冒烟脚本统一 `import sys; sys.path.insert(0, '.')`（pytest 靠 conftest 已自动处理，无需担心）
2. **迁移验证第一次跑挂**：忘了 `get_db()` 依赖 Flask app context，直接调 `ensure_users_avatar_column()` 报 `Working outside of application context`；且抛错后 GBK 控制台打印 emoji 再报 `UnicodeEncodeError`，两个坑叠一起。教训：涉及 `flask.g` 的函数验证一律 `create_app().app_context()` + `PYTHONIOENCODING=utf-8`
3. **Bash 工作目录漂移**：先在 `frontend/` 跑过 build，回跑 pytest 时 `portable/python/python.exe` 相对路径找不到。教训：跨目录操作后用绝对路径或先 `cd` 回项目根
4. 前端交互未真机手测（dev server + backend 未启动），仅靠 build + lint + 真实 DB 接口冒烟兜底。若后续 P1/P2 涉及时序/布局，建议启动 `npm run serve` + 后端让用户手测

**下次快速命中清单**：
- 本次可复用模板：幂等迁移函数（第五节）、改密码校验纯函数、UserCenter 容器模式、PlayerPlaylist 模式切换骨架
- 真实 DB 冒烟范式：`create_app()` → `test_client()` → `/api/login` 拿 token → 带 `Authorization` 头调接口（不污染数据的路径：改密码用错误旧密码只验 400）
- 已记录可依赖事实：`@login_required` 自动建 `albums_{uid}` 表；`v-bind()` CSS 变量本项目可用；avatar 空串=前端回退首字母圆头像
