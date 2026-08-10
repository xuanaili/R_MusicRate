# 最近收听排序功能 + 验收失败排查（后端未重启，新接口 404）

## 一、案例基本信息
- 问题场景分类：新功能开发 + 验收失败排查（后端进程跑旧代码 → 新接口 404 → 数据库新列从未写入）
- 产生时间：2026-08-10
- 项目模块：`backend/api/listening.py`（touch 接口）、`backend/api/album.py`（列表排序）、`backend/utils/db.py`（建表 DDL）、`backend/utils/last_listened.py`（排序纯逻辑）、`frontend/src/views/AlbumDetail.vue`（上报）、`frontend/src/components/myMusic/MusicList.vue`（默认排序）
- 相似问题判定特征：
  1. 新后端接口"改完没生效" → **直接查数据库新列是否存在**；列不存在 = 幂等迁移从没跑过 = 接口从没被成功调用
  2. 列表"永远某张专辑排第一" → 排序字段全为 NULL（列缺失时 `album.get()` 返回 None），稳定排序退化为表内原始顺序
  3. 前端用 `catch(err){ console.log(...) }` 静默吞错 → touch 404 无任何用户感知，验收"看似没实现"
  4. 5000 端口有 python.exe 在跑，但进程启动时间在代码改动**之前** → 跑的是旧代码，新路由 404

## 二、原始问题描述
- 需求：我的音乐/专辑列表默认按「最近收听」排序；每次打开专辑详情页自动上报最近收听时间。
- 实现：albums 表新增 `last_listened DATETIME` 列（建表 DDL + touch 接口幂等迁移补列）；`POST /api/album/listening/touch/<album_id>` 更新 `NOW()`；列表接口支持 `last_listened` 排序（从未收听固定排最后）；前端 `MusicList` 默认 `sortBy=last_listened&desc`、`AlbumDetail` 打开时上报。
- 痛点：全部实现 + 单测 + eslint 通过后，用户验收发现「打开专辑后 last_listened 没更新，黑色柳丁永远排第一」。
- 约束：无法直接访问运行中的后端进程代码；需要从"数据库实际状态"反推接口是否被调用过。

## 三、核心诉求
1. 定位为什么 last_listened 未更新（接口没生效？前端没调用？）
2. 确认排序退化成"黑色柳丁恒第一"的根因
3. 修复后验证 touch 接口真实可用（端到端，而非只靠单测）
4. 沉淀排查方法：如何快速判断"后端进程是旧代码"

## 四、最终解决方案/改造步骤
**功能开发（已提交 `6f984fd`）**
1. `backend/utils/db.py` 建表 DDL 加 `last_listened DATETIME NULL COMMENT '最近收听时间'`
2. `backend/api/listening.py` 新增 `POST /api/album/listening/touch/<int:album_id>`：先查 `information_schema.COLUMNS` 判断 `last_listened` 列是否存在，缺失则 `ALTER TABLE ... ADD COLUMN`（幂等迁移，兼容历史表），再 `UPDATE albums_{user_id} SET last_listened=NOW() WHERE id=%s`
3. `backend/utils/last_listened.py` 纯函数 `last_listened_sort_key(album, sort_order)`：从未收听（缺字段/None）降序用 `datetime.min`、升序用 `datetime.max` 兜底 → **固定排最后**
4. `backend/api/album.py`：`VALID_SORT_FIELDS` 加 `last_listened`；排序分支加 `elif`；列表返回 dict 带 `last_listened`
5. `frontend/src/components/myMusic/MusicList.vue`：默认 `sortBy:'last_listened'`、`sortOrder:'desc'`，`sortByMap` 加「最近收听」
6. `frontend/src/views/AlbumDetail.vue`：`created()` 中 `getAlbumDetail` 后 `await this.reportLastListened()`（调用 touch 接口，失败仅 console.log）
7. `backend/tests/test_last_listened.py`：7 项排序纯逻辑单测（零 DB 依赖）

**验收失败排查（本次核心）**
1. 查数据库：`information_schema.COLUMNS` 确认所有 `albums_{user_id}` 表 **都没有 `last_listened` 列** → touch 接口从未被调用（若调用过，幂等迁移会自动补列）
2. 查 5000 端口：`netstat -ano | grep :5000` 找到监听进程 PID 25076（python.exe）
3. 判定：该进程是**改动前启动的旧代码**，新路由 `/api/album/listening/touch/1` 不存在 → 前端 POST 404 → `catch` 静默吞掉
4. 解法：**重启后端**（`python -m backend.run`）让新代码生效；重启后打开专辑，touch 会幂等补列并写 `NOW()`，列表按最近收听降序
5. 验证口径：重启后 curl `POST /api/album/listening/touch/1`（不带 token 返回 401=路由存在；404=路由不存在）+ 查库确认列与值

## 五、关键代码/配置/模板（可直接复用）
```python
# backend/utils/last_listened.py —— 最近收听排序纯逻辑（零 DB 依赖）
import datetime

def last_listened_sort_key(album, sort_order='desc'):
    """从未收听（缺字段/None）固定排最后：降序用 datetime.min，升序用 datetime.max"""
    listened_time = album.get('last_listened')
    if not listened_time:
        return datetime.datetime.min if sort_order == 'desc' else datetime.datetime.max
    return listened_time
```

```python
# backend/api/listening.py —— touch 接口：幂等补列 + 更新（兼容历史表的关键模式）
cursor.execute(f'''
    SELECT COUNT(*) as count FROM information_schema.COLUMNS
    WHERE TABLE_SCHEMA = DATABASE() AND TABLE_NAME = %s AND COLUMN_NAME = 'last_listened'
''', (table_name,))
field_exists = cursor.fetchone().get('count') > 0
if not field_exists:
    cursor.execute(f'ALTER TABLE `{table_name}` ADD COLUMN last_listened DATETIME NULL COMMENT \'最近收听时间\'')
cursor.execute(f'UPDATE `{table_name}` SET last_listened = NOW() WHERE id = %s', (album_id,))
db.commit()
```

```python
# backend/api/album.py —— 列表排序分支（从未收听排最后）
elif sort_by == 'last_listened':
    all_albums.sort(key=lambda x: last_listened_sort_key(x, sort_order), reverse=(sort_order == 'desc'))
```

```js
// frontend/src/views/AlbumDetail.vue —— 打开专辑上报（失败静默，不影响使用）
async reportLastListened() {
  const token = localStorage.getItem('token') || '';
  if (!token || !this.album.id) return;
  try {
    await this.$axios.post(`/api/album/listening/touch/${this.album.id}`, {}, {headers: {Authorization: token}});
  } catch (err) { console.log(`ℹ️ 上报最近收听失败(不影响使用)：`, err.message); }
}
```

## 六、踩坑点 & 注意事项（非常重要）
- **开发后端接口后必须重启后端进程**：Flask 非 debug 热重载时，旧进程不加载新代码，新路由 404。前端热更新会让前端代码最新、后端旧 → 表面"改了没生效"。这是本案例最大坑。
- **前端 `catch` 静默吞错是验收失败的主要帮凶**：touch 404 只 `console.log`，用户无感知。排查新接口是否生效，第一动作是查数据库状态（幂等迁移没跑 = 从没成功调用），而不是反复看前端代码。
- **排序字段全 NULL 时的退化行为**：列缺失时 `SELECT *` 不含该键，`album.get('last_listened')` 返回 None → 全部兜底同值 → Python `sort` 稳定 → 保持表内原始插入顺序。表现即"某张专辑永远第一"。
- **`datetime.min`/`datetime.max` 兜底 vs `reverse`**：降序（`reverse=True`）必须用 `datetime.min` 兜底才会排最后；升序用 `datetime.max`。反过来写会导致从未收听排最前。此逻辑已有单测锁定，勿随手改。
- **PYTHONPATH 注入不可靠**：本项目 portable python 忽略环境变量 `PYTHONPATH`，直接 `python -c "import backend..."` 会失败；验证导入用 pytest（conftest 已加 `sys.path`）或显式 `sys.path.insert(0, 'U:\\MusicRate')`。
- **判断进程新旧代码**：`netstat -ano | grep :5000` 拿 PID → `wmic process where processid=<PID> get creationdate` → 与代码改动时间对比；或 curl 一个新路由看 401（存在）/404（不存在）。

## 七、同类问题快速适配规则
下次遇到"新后端接口改完没生效 / 验收失败"，按此顺序命中：
- 【适配点1】数据库新列/新表是否存在（查 `information_schema.COLUMNS/TABLES`）→ 不存在 = 接口从未成功调用
- 【适配点2】`netstat -ano | grep :5000` 确认后端进程 → `wmic ... get creationdate` 对比代码改动时间，判定旧进程
- 【适配点3】`curl -X POST http://localhost:5000/<新路由>/1`（不带 token）：401=路由已注册，404=后端是旧代码需重启
- 【适配点4】重启后端后，用 `pytest -m realdata` 或 curl 带 token 验证接口真实写库
- 其余（幂等补列模式 / 排序兜底 / 静默 catch 排查）原样复用本方案

## 八、优化复盘（2026-08-10 本次对话）
**流程效率**：开发阶段按铁律先加载开发 skill + 测试 skill，测试先行（先写 `test_last_listened.py` 红→绿）、后端三件（建表/touch/排序）+ 前端两件（默认排序/上报）逐任务推进、pytest 全量 22 passed + eslint 通过后提交，开发链路顺畅无弯路。

**浪费点**：
1. **开发阶段缺端到端验证**：只跑了 pytest 单测 + 模块 import 冒烟 + eslint，没有实际启动后端调用一次 touch 接口。单测验证不了"路由真的注册 + 能写库"，导致接口 404 的问题被带到验收环节。下次开发新后端接口，必须在提交前启动后端（或 `pytest -m realdata`）真调一次。
2. **排查阶段先审代码链路再查数据库，顺序反了**：我先读了 `AlbumItem.vue` 全文件 + 全局 grep 跳转逻辑（确认前端调用存在，这部分不白费），但如果第一时间查数据库 `last_listened` 列是否存在，一眼就能断定"touch 从没成功执行"，直接跳到"进程是否旧代码"，省掉大半轮次。
3. **验收结论依赖用户"重跑一次"**：`netstat` 确认进程 25076 存在后，我没有先拿启动时间/curl 路由再下结论，本可以直接自证"旧代码 404"。应该先在本地完整取证（进程启动时间 + curl 404 + 库无列），再让用户重启。

**下次快速命中清单**：
- 验证后端接口是否生效：① 查库新列（幂等迁移没跑 = 没被调用）→ ② `netstat` 找 5000 进程 + `wmic` 查启动时间 → ③ curl 新路由（401/404）→ ④ 重启后端再验
- 开发后端新接口后的必做项：`pytest -m realdata` 或启动后端真调一次，别只靠单测 + import 冒烟
- 关键文件：touch 接口 `backend/api/listening.py`；排序 `backend/api/album.py` + `backend/utils/last_listened.py`；上报 `AlbumDetail.vue::reportLastListened`；默认排序 `MusicList.vue`；单测 `backend/tests/test_last_listened.py`
- 可复用模板：幂等补列（information_schema 查列→ALTER）+ 排序兜底（datetime.min/max 按升降序）
