# v0.7 P1 个人中心设置（头像上传 + 蒙版透明度调节 + 侧边栏样式美化）

## 一、案例基本信息
- 问题场景分类：新功能开发（v0.7 P1 设置）→ 头像上传链路 + 全局 CSS 变量蒙版调节 + 侧边栏样式美化
- 产生时间：2026-08-10
- 项目模块：
  - 后端：`backend/api/user.py`（新增 `POST /api/user/avatar`）、`backend/utils/user.py`（新增 `validate_avatar_url`）
  - 前端：`frontend/src/components/user/`（新 AppearancePanel.vue、改 ProfilePanel.vue / UserCenter.vue）、`PlayerPlaylist.vue`、`WebHome.vue`、`AlbumDetail.vue`
  - 测试：`backend/tests/test_user_avatar.py`（新，8 分支）
- 相似问题判定特征：
  1. "个人中心 / 头像 / 设置类新功能" → 复用 P0 的 UserCenter 容器模式（子 tab + 面板组件 + props 传三色），P1 只需替换占位面板
  2. "全局视觉可调项（蒙版/透明度）" → CSS 变量 `--mask-opacity` 挂 documentElement + localStorage 持久化 + 各容器 `rgba(255,255,255,var(--mask-opacity,默认))`
  3. "上传文件后存 URL" → `/api/upload_img` 图床返回 img_url → 业务接口只存 URL；纯函数校验 URL 抽 `backend/utils/` 可单测
  4. "跨组件实时刷新" → window `CustomEvent` 广播 + 监听（Vue 2 无事件总线时的轻量方案）
  5. "便携 Python 启动后端" → 必须 `python backend/run.py`，`-m backend.run` 报 ModuleNotFoundError（cwd 不在 sys.path）

## 二、原始问题描述
- 背景：v0.7 P0 已搭好个人用户中心骨架（资料/改密码/退出登录 + 歌单/个人中心模式切换）。P1 要补齐「设置」类功能：头像上传、蒙版透明度调节、侧边栏样式美化（v0.6 遗留）。
- 痛点/约束：
  - 头像要复用现有图床 `/api/upload_img`（返回 `http://localhost:5000/covers/xxx.png`），业务接口只存 URL；未上传回退首字母圆形头像
  - 蒙版透明度要「联动侧边栏 + 专辑详情页」（README 明确），还要顺手带上主页；需 localStorage 持久化，滑块即时全局生效
  - 头像改完 WebHome 右上角 UserAvatar 要实时刷新，但 ProfilePanel 与 WebHome 无父子关系（两入口各自嵌 UserCenter）
  - `$message` 全局未注册，反馈用 `if (this.$message) {...} else alert(...)` 兜底
  - 便携 Python 的 cwd 不在 sys.path，`python -m backend.run` 启动后端直接报错（本次新发现的坑）

## 三、核心诉求
1. 后端：`POST /api/user/avatar`（存 URL）+ `validate_avatar_url()` 纯函数（非空 + http(s) 完整链接，防本地路径/协议注入）
2. 前端：ProfilePanel 头像点击上传（hover 遮罩提示 → 图床 → 存 URL → 广播）；WebHome 监听刷新右上角头像
3. 前端：AppearancePanel 蒙版滑块（0-60%，默认 25%）+ 恢复默认，CSS 变量联动三处毛玻璃容器
4. 前端：PlayerPlaylist 侧边栏样式美化（模式切换分段控件、卡片/tab/搜索框细节）
5. 测试先行：`test_user_avatar.py` 单测 + 真实接口端到端验证 + 全量回归

## 四、最终解决方案/改造步骤
1. **后端纯函数**（`backend/utils/user.py`）：
   ```python
   _HTTP_URL_RE = re.compile(r'^https?://[^\s/$.?#].[^\s]*$', re.IGNORECASE)
   def validate_avatar_url(avatar_url):
       url = (avatar_url or '').strip()
       if not url: return '头像地址不能为空'
       if not _HTTP_URL_RE.match(url): return '头像地址必须为 http(s) 完整链接'
       return None
   ```
2. **后端接口**（`backend/api/user.py`）：`POST /api/user/avatar`（`@login_required`，含 OPTIONS），校验通过 `UPDATE users SET avatar=%s`，返回 `{"code":200,"msg":"头像更新成功！","data":{"avatar":url}}`
3. **前端头像上传**（`ProfilePanel.vue`）：头像包 `position:relative` + hover 遮罩「更换」→ 隐藏 `<input type=file accept="image/*">` → `FormData` 上传 `/api/upload_img` → `POST /api/user/avatar` → 更新本地 + `localStorage.setItem('avatar', url)` + `window.dispatchEvent(new CustomEvent('user-avatar-changed',{detail:url}))`
4. **WebHome 实时刷新**：`created` 里 `window.addEventListener('user-avatar-changed', this.handleAvatarChanged)`，`beforeDestroy` 移除；`handleAvatarChanged(e){ this.userAvatar = e?.detail || '' }`
5. **蒙版全局联动**（新 `AppearancePanel.vue`）：
   - 滑块 `0-60%`，`oninput` 写入 `localStorage.maskOpacity` 并 `document.documentElement.style.setProperty('--mask-opacity', (val/100).toFixed(2))`
   - `created` 读 localStorage 回填并应用
   - 三处毛玻璃容器（WebHome `.nav-mask-container`、PlayerPlaylist `.playlist-sidebar`、AlbumDetail `.main-content`）背景改 `rgba(255, 255, 255, var(--mask-opacity, 0.25))`
6. **UserCenter** 挂载：`appearance` tab 从占位改为 `<AppearancePanel>`（props 传三色）
7. **侧边栏美化**（`PlayerPlaylist.vue`）：模式切换改带图标（♪/👤）分段控件（flex:1 + 主题色选中 + 阴影），歌单 tab 选中阴影/hover 上浮、卡片 hover 阴影、搜索框聚焦描边；删除无用 `modeBtnStyle` 方法
8. **测试**：`test_user_avatar.py` 8 分支（空/空白/非URL/ftp/无域名/合法 http/https/带query），红灯→绿灯

## 五、关键代码/配置/模板（可直接复用）
```html
<!-- ProfilePanel 头像上传交互骨架 -->
<span class="profile-avatar" @click="triggerAvatarUpload">
  <img v-if="userInfo.avatar" :src="userInfo.avatar" />
  <span v-else>{{ avatarLetter }}</span>
  <span class="avatar-upload-mask">{{ uploadingAvatar ? '上传中' : '更换' }}</span>
</span>
<input type="file" ref="avatarFileInput" accept="image/*" style="display:none" @change="handleAvatarFileChange" />
```
```js
// 上传链路（ProfilePanel.uploadAvatar）
const fd = new FormData(); fd.append('image', file)
const res = await this.$axios.post('/api/upload_img', fd, { headers: {'Content-Type':'multipart/form-data'}, timeout: 15000 })
const url = res.data.data.img_url
await this.$axios.post('/api/user/avatar', { avatarUrl: url })
localStorage.setItem('avatar', url)
window.dispatchEvent(new CustomEvent('user-avatar-changed', { detail: url }))
```
```js
// 蒙版全局变量应用（AppearancePanel）
document.documentElement.style.setProperty('--mask-opacity', (this.maskOpacity / 100).toFixed(2))
// 容器侧（任何毛玻璃层）：
background: rgba(255, 255, 255, var(--mask-opacity, 0.25));
```
```css
/* 模式切换分段控件（PlayerPlaylist） */
.sidebar-mode-toggle { display:flex; gap:6px; padding:4px; border-radius:12px; background: rgba(255,255,255,0.3); border-bottom:2px solid; }
.mode-toggle-btn { flex:1; display:flex; justify-content:center; gap:6px; padding:7px 0; border-radius:9px; color: v-bind(mainColorDark); }
.mode-toggle-btn.active { background: v-bind(mainColorDark); color:#fff; box-shadow: 0 2px 8px rgba(0,0,0,0.2); }
```

## 六、踩坑点 & 注意事项（非常重要）
- **`python -m backend.run` 在便携 Python 下 100% 报错**：`ModuleNotFoundError: No module named 'backend'`（cwd 不在 sys.path，且 `PYTHONPATH=` 也不生效）。正确启动：`PYTHONIOENCODING=utf-8 portable\python\python.exe backend/run.py`（run.py 第 14 行自带 `sys.path.insert(0, 项目根)`）。CLAUDE.md 已更新，别再绕 `-m`
- **后端未重启致接口 404**：新增路由必须重启后端才生效（本次 `/api/user/avatar` 重启前 404、重启后 401）。验证「路由是否注册成功」用「401 vs 404」判断，不用凑登录
- **`python -c` 内联脚本无项目根 sys.path**：统一 `import sys, os; sys.path.insert(0, os.getcwd())`
- **Windows GBK 控制台 print emoji 崩溃**：脚本/后端输出设 `PYTHONIOENCODING=utf-8`，或打印用纯 ASCII（emoji 换成 `OK/FAIL`）
- **urllib 端到端脚本的非法 URL 测试**：别用 `c:/windows/evil.jpg`（urllib 解析成 scheme `c:` 直接 HTTP 400 到不了接口），用 `ftp://x/y.png`、`abc.png`、空串
- **`rgba(255,255,255,var(--mask-opacity,0.25))` 依赖 CSS 变量做 alpha**：现代浏览器均支持；若出现透明度失效先查 var 是否被意外赋非法值（AppearancePanel 只赋 `(val/100).toFixed(2)`，0-0.6 安全）
- **头像改了 WebHome 不刷新**：两入口各自嵌 UserCenter，无父子关系 → 必须用 window CustomEvent 广播（Vue 2 无全局事件总线的轻量替代）

## 七、同类问题快速适配规则
下次遇到相似问题，只需改：
- 【适配点1】任何「上传文件后存 URL」：复制 ProfilePanel 上传链路，改业务接口（如 `/api/user/avatar`）；URL 校验抽 `backend/utils/` 纯函数 + 单测
- 【适配点2】任何「全局可调视觉项」：复制 AppearancePanel（滑块 + localStorage + `--xxx` CSS 变量），把目标容器的写死 rgba 改成 `var(--xxx, 默认)`
- 【适配点3】跨组件实时刷新：复制 window CustomEvent 广播 + created/beforeDestroy 监听对
- 【适配点4】侧边栏/容器加分段切换：复制 `.sidebar-mode-toggle` 分段控件 + 图标
- 【适配点5】给用户表加字段：复用 P0 幂等迁移 `ensure_users_avatar_column` 模式（改表名/列名）

---

## 八、优化复盘（2026-08-10 本次对话）

**流程效率**：整体顺畅。铁律生效：先加载开发 + 测试 skill → 读 README 定位 v0.7 P1 任务清单 → 测试先行（`test_user_avatar.py` 先红灯后绿灯）→ 实现 → 全量回归 → 提交。头像/蒙版/美化三项功能一次实现、一次全量测试通过，无返工。

**浪费点**：
1. **后端重启 + 启动命令坑耗时最多（约 3 轮）**：`python -m backend.run` 便携 Python 报 `No module named 'backend'`；试了 `PYTHONPATH=` 也不生效；最后才定位到正确方式是 `python backend/run.py`（脚本内部自带 sys.path.insert）。教训：便携 Python 启动后端固定用 `python backend/run.py`，不要 `-m`。这个坑已写进 CLAUDE.md 防复发
2. **`python -c` 内联脚本 print emoji 在 GBK 控制台崩溃**（1 轮）：诊断输出带 ✅ 直接 UnicodeEncodeError。教训：冒烟/诊断脚本输出纯 ASCII，或 `PYTHONIOENCODING=utf-8`
3. **端到端验证脚本用 `c:/windows/evil.jpg` 测非法 URL**（1 轮）：urllib 把 `c:` 当 scheme，HTTP 400 在到达接口前就抛了，误导以为是接口问题。教训：非法 URL 校验用例用 `ftp://` / `abc.png` / 空串
4. 前端交互未真机手测（依赖 dev server 热更新 + 后端接口冒烟兜底）；若 P2 涉及时序/布局建议让用户手测

**下次快速命中清单**：
- 后端启动：`PYTHONIOENCODING=utf-8 portable\python\python.exe backend/run.py`（别再 `-m backend.run`）
- 新增后端校验纯函数：复制 `validate_avatar_url` / `validate_password_change` 到 `backend/utils/user.py`，测试放 `backend/tests/test_<模块>.py`
- 前端新面板：复制 ProfilePanel/AppearancePanel（props 三色 + v-bind 主题色 + `if(this.$message) else alert` 兜底）
- 全局蒙版：`--mask-opacity` CSS 变量 + localStorage，三容器统一 `var(--mask-opacity, 0.25)`
- 头像链路：`/api/upload_img` → `/api/user/avatar` → window CustomEvent → WebHome 监听
