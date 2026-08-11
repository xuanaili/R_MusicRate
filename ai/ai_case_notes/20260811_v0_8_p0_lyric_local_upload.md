# v0.8 P0 歌词版：LRC 双端同构纯函数 + 后端重构（权限修复 + 整轨上传）+ 前端删 QQ

## 一、案例基本信息
- 问题场景分类：v0.8 功能落地（P0 四项：LRC 纯函数双端同构 + 后端重构 + 前端改造 + README 归档）
- 产生时间：2026-08-11
- 项目模块：
  - 后端：`backend/utils/lrc.py`（纯函数，新增）、`backend/api/lyric.py`（重写：删 QQ + save 修权限 + upload 接口）、`backend/utils/decorators.py`（`is_admin_user` 助手）、`backend/utils/db.py`（读库）
  - 测试：`backend/tests/test_lrc.py`（47 例单测）、`test_lyric_api_realdata.py`（15 例 realdata）
  - 前端：`frontend/src/components/albumDetail/AlbumLyricViewer.vue`（删 QQ + 整轨 LRC 上传入口）
  - 文档：`README.md`（v0.8 章节归档）
- 相似问题判定特征：
  1. "某解析函数前后端输出不一致 / 要双端同构" → 用 node 跑前端真实函数生成 golden 基线，硬编码进后端单测逐字符对比，锁定前端怪癖
  2. "任何登录用户都能调某管理接口 / 要收紧权限" → `is_admin_user(user_id)`（真实查 `users.is_admin`），别硬编码 `is_admin=True`
  3. "JSON 列 / 查询行取列报 KeyError:0 或 tuple index" → `MYSQL_CONFIG` 全局 `cursorclass=DictCursor`，行是 dict 必须 `row.get('col')`
  4. "上传 LRC / 歌词文件（utf-8/gbk 中文系统导出）" → `_decode_text` utf-8 失败回退 gbk + 大小/扩展名校验
  5. "小数点精度（JS round vs Python round）不一致" → JS `Math.round` 半进位、Python `round` 银行家舍入 → `_round_half_up = math.floor(x + 0.5)`

## 二、原始问题描述
v0.8 主题为歌词，重点是 `album/detail` 下的歌词展示页面。README v0.8 规划已定稿，用户下发"阅读README，开始v0.8版本的P0任务"。P0 四项：
- **P0-A**：`backend/utils/lrc.py` 纯函数 + `test_lrc.py`（测试先行），输出与前端 `parseLrcToStandardFormat` 逐字符一致
- **P0-B**：后端重构——`is_admin_user` 助手 → save 修权限 + 校验 + 抽 upsert → 新增整轨 upload 接口 → 删全部 QQ 代码 → realdata 测试绿 → `fetch_auto` 后端零命中
- **P0-C**：前端删 QQ + 整轨 LRC 上传入口 → `npm run lint` 过 + 手动回归
- **P0-D**：README 归档（勾选 + 优化复盘）

约束：存储格式全站唯一 `mm:ss(.x)? 歌词`（无方括号、1 位小数、升序去重取首）；权限收紧为真实管理员；P1（faster-whisper AI spike）明确不在 P0 范围。

## 三、核心诉求
1. 后端 LRC 解析/规范化纯函数与前端 `parseLrcToStandardFormat` 逐字符一致（含前端怪癖：`.5`→0.05s、多时间戳合并、元数据过滤、去重取首）
2. 修复 save 接口硬编码 `is_admin=True` 权限漏洞（任何登录用户可存歌词）
3. 新增整轨 LRC 文件上传接口（multipart ≤1MB，utf-8 回退 gbk，可选翻译文件存 `{"CN":...}`）
4. 前端删除 QQ 自动获取（批量/单曲按钮 + 弹窗 + 死代码），新增整轨上传入口复用逐单曲切分机制

## 四、最终解决方案/改造步骤
1. **P0-A LRC 纯函数**（cd5d9a3）：
   - `backend/utils/lrc.py`：`_round_half_up`（复刻 JS 半进位）→ `_round_tenths` → `str_to_seconds` / `seconds_to_str` → `parse_any_to_items`（LRC 方括号 + 存储格式双路径）→ `items_to_storage` / `normalize_to_storage` → `validate_lyric_text`
   - `test_lrc.py`（47 例）：golden 基线由 **node 直接执行前端真实 `parseLrcToStandardFormat`** 生成后硬编码，锁定 `.5`→0.05s→`00:10.1`、`[01:02.3]`→`01:02`、去重取首等怪癖
2. **P0-B 后端重构**（f1ce6ee）：
   - `decorators.py` 新增 `is_admin_user(user_id)`（真实查 users.is_admin；注意 DictCursor）
   - `lyric.py` 重写：删 `fetch_auto`/`fetch_qq_lyric`/`clean_lyric` 及 requests 等 import；抽 `upsert_album_lyric()` 共用落库；save 改真实管理员校验 + `validate_lyric_text`/`normalize_to_storage` 规范化 + 补专辑存在性（404）；新增 upload 接口；保留 krc2lrc
   - `test_lyric_api_realdata.py`（15 例）：save/upload 权限 403、规范化落库、404、400、gbk 回退、翻译文件、`fetch_auto` 移除 404
3. **P0-C 前端改造**（f6b2530）：
   - `AlbumLyricViewer.vue`：删批量/自动获取按钮 + 整个自动获取弹窗 + `fetchLyrics` 等方法 + data/watcher + ~30 段死样式（净减 399 行）；新增整轨上传按钮 + `handleWholeTrackLrcUpload`（FormData → upload 接口 → `$emit('update:lyrics')` 复用父组件双保存切分机制）
   - `npm run lint` 通过
4. **P0-D README 归档**（bb85a93）：v0.8 章节标题改「P0 已完成」，路线/清单勾选，新增「P0 实现要点（复盘速查）」

## 五、关键代码/配置/模板（可直接复用）
```python
# backend/utils/lrc.py —— 复刻 JS Math.round（半进位，Python round 是银行家舍入）
def _round_half_up(x):
    return math.floor(x + 0.5)
def _round_tenths(seconds):
    return _round_half_up(seconds * 10) / 10.0
```
```python
# backend/utils/decorators.py —— 真实管理员校验（修复 is_admin=True 硬编码漏洞）
def is_admin_user(user_id):
    if not user_id:
        return False
    try:
        db = get_db()
        cursor = db.cursor()
        cursor.execute('SELECT is_admin FROM users WHERE user_id = %s', (user_id,))
        row = cursor.fetchone()
        cursor.close()
        if not row:
            return False
        # MYSQL_CONFIG 全局 cursorclass=DictCursor → row 为 dict；兼容 tuple 游标
        is_admin = row.get('is_admin') if isinstance(row, dict) else row[0]
        return is_admin == 1
    except Exception as e:
        print(f"❌ 校验管理员权限失败：{str(e)}")
        traceback.print_exc()
        return False
```
```python
# backend/api/lyric.py —— save/upload 共用落库（幂等：存在则更新，否则插入）
def upsert_album_lyric(db, album_pool_id, lyric_text, lyric_translate, current_user_id):
    cursor = db.cursor(pymysql.cursors.DictCursor)
    cursor.execute('SELECT id FROM album_lyric WHERE album_pool_id = %s LIMIT 1', (album_pool_id,))
    existing = cursor.fetchone()
    if existing:
        cursor.execute('UPDATE album_lyric SET lyric_text=%s, lyric_translate=%s, update_time=%s WHERE album_pool_id=%s',
                       (lyric_text, lyric_translate, datetime.now(), album_pool_id))
    else:
        cursor.execute('INSERT INTO album_lyric (album_pool_id, lyric_text, lyric_translate, create_user_id, create_time, update_time) VALUES (%s,%s,%s,%s,%s,%s)',
                       (album_pool_id, lyric_text, lyric_translate, current_user_id, datetime.now(), datetime.now()))
    db.commit(); cursor.close()
```
```python
# backend/api/lyric.py —— 文件解码（utf-8 失败回退 gbk，兼容中文系统导出的 LRC）
def _decode_text(raw):
    for encoding in ('utf-8', 'gbk'):
        try:
            return raw.decode(encoding)
        except (UnicodeDecodeError, ValueError):
            continue
    return raw.decode('utf-8', errors='ignore')
```
- 前端整轨上传（FormData 惯例，与 krc2lrc/ProfilePanel/UnlockParse 一致）：
```js
const formData = new FormData();
formData.append('lrc_file', file);
const res = await this.$axios.post(`/api/album/lyric/upload/${this.album.source_pool_id || this.album.id}`, formData, {
  headers: { Authorization: localStorage.getItem('token') || '', 'Content-Type': 'multipart/form-data' }
});
// 成功后 $emit('update:lyrics', {lyric_text, lyric_translate}) → 父组件双保存（幂等）+ initTrackLyricsMap 按 tracks_time 切分
```
- 双端同构验证法（本次核心方法）：node 跑前端真实函数 → 输出硬编码进后端单测 → 逐字符 assert。比"读代码推演一致"可靠，能自动暴露 `.5`→0.05s 这类怪癖。

## 六、踩坑点 & 注意事项（非常重要）
- **DictCursor 全局生效（本次 12 测试 403 的根因）**：`MYSQL_CONFIG` 设置 `cursorclass=pymysql.cursors.DictCursor` → `db.cursor()` 返回的行是 dict，`row[0]` 抛 KeyError:0 被 `except` 吞掉返回 False → 管理员全变 403。**凡项目内取列一律 `row.get('col')`，不要 `row[0]`**
- **JS/Python 舍入不同**：JS `Math.round` 半进位、Python `round` 银行家舍入（`round(2.5)=2`）。复刻 JS 必须 `math.floor(x + 0.5)`
- **`album_pool.tracks_time` DDL 漂移**：线上库存在该列但 `db.py` 建表 DDL 未收录、无默认值 → realdata 测试插入模板必须显式传 `tracks_time='[]'`，否则报 1364
- **bytes 字面量不能含中文**：`b'[00:00]歌词'` 报 SyntaxError "bytes can only contain ASCII literal characters" → 用 `'...'.encode('utf-8')` 或纯 ASCII 内容
- **shell `grep -rn` 会挂**：`backend/data/` 有大量 MP3 大文件（U 盘 USB 慢）→ 用 Grep（ripgrep）工具验证，自动跳过二进制；不要用 Bash 的 grep/find 扫仓库
- **`python -c` 不加载 cwd**：便携 Python `python -c "from backend..."` 报 ModuleNotFoundError（cwd 不在 sys.path）；测试统一走 `backend/tests/`（conftest 处理），启动用脚本文件方式 `backend/run.py`
- **断言先核对真实文案**：test 断言 `'无效' in msg` 但错误文案是「未解析到**有效**的歌词行」→ 断言与实际不符白跑一轮；先读实现再写断言
- **前端上传成功要清 input 值**：`e.target.value = ''` 否则同文件不能再次触发 change

## 七、同类问题快速适配规则
- 【适配点1】新歌词格式 / 双端同构解析 → 复用 `lrc.py` 全套纯函数 + `test_lrc.py` 的 node golden 基线法；改存储格式只动 `seconds_to_str`/`str_to_seconds`/正则
- 【适配点2】新管理员专属接口 → `is_admin_user(user_id)` 一行校验；非管理员 403 口径与前端 `isAdmin` 一致
- 【适配点3】上传文件接口（LRC/图片/音频）→ 复用 `MAX_LRC_FILE_SIZE` 大小上限 + 扩展名校验 + `_decode_text` 编码回退 + `upsert_album_lyric` 幂等落库模式
- 【适配点4】任何读 users / 查行取列 → 一律 `row.get('col')`（DictCursor）；游标用完 `cursor.close()`
- 【适配点5】删功能回归 → grep 前端 `lyricSources`/`fetchNeteaseUrl`/`startBatchFetchLyrics`、后端 `fetch_auto` 全仓零命中；realdata 断言路由 404 而不是 200

## 八、优化复盘（2026-08-11 本次对话）
**流程效率**：全程按铁律「测试先行→实现→跑测试→提交」。P0-A 先写 47 例单测（node 生成 golden 基线）再实现纯函数；P0-B 先跑 realdata 红灯再改 lyric.py；P0-C 改完即 lint；四项均独立提交（cd5d9a3 / f1ce6ee / f6b2530 / bb85a93），可回滚。

**浪费点**：
1. **test_lrc.py 断言文案不匹配（小浪费）**：断言 `'无效' in msg`，实际错误文案是「未解析到**有效**的歌词行」→ 白跑一轮。教训：断言前先读实现确认错误文案，别猜
2. **shell grep 卡死（大浪费）**：`grep -rn` 扫到 `backend/data/` 大音频文件在 U 盘上挂起，超时。教训：仓库验证一律用 Grep（ripgrep）工具
3. **is_admin_user 12 测试 403 排查（中等浪费）**：DictCursor 导致 `row[0]` KeyError 被吞返回 False。本可避免——写代码时已知 MYSQL_CONFIG 设了 DictCursor，取列就该用 dict 方式。教训：项目内所有 `cursor.fetchone()` 结果默认按 dict 处理
4. **bytes 中文 SyntaxError（小浪费）**：`b'中文'` 报错，改 `.encode('utf-8')` 一次过

**下次快速命中清单**：
- 双端同构解析：`lrc.py` 纯函数 + node golden 基线法直接复用；新格式只改 `seconds_to_str`/正则
- 管理员权限：`is_admin_user` 直接 import；新管理接口 403 一条线
- 上传接口：大小/扩展名校验 + `_decode_text` + `upsert_*` 幂等落库 + `e.target.value=''`
- realdata 测试模板：`test_lyric_api_realdata.py` 的 `_insert_pool_album`（显式 tracks_time）/ `_upload`（multipart）/ `_get_lyric`（直查）三个 helper 直接搬
- 前端上传惯例：FormData + 显式 `Content-Type: multipart/form-data`（与 krc2lrc/ProfilePanel 一致）
