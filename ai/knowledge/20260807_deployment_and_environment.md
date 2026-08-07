---
name: deployment-and-environment
description: 项目部署环境、依赖管理、IDE配置、.gitignore规则、自动录屏工具
metadata:
  type: reference
---

# 部署与环境配置

## 运行环境

- **操作系统**: Windows 11 Pro
- **Python**: 3.10 / 3.12（IDE中配置了两个版本，项目使用 3.10）
- **Node.js**: 需要支持 Vue CLI 5
- **MySQL**: 8.0.44，安装在移动硬盘 `U:/__/app/MySQL/`，数据库 `music_rate`
- **数据库用户**: `music_user@localhost`，端口 `3306`
- **MySQL配置文件**: `U:/__/app/MySQL/MySQL Server 8.0/my.ini`（basedir/datadir指向U盘路径）
- **浏览器**: Edge（自动录屏使用）

## 启动命令

### 前端
```bash
cd frontend/
npm run serve    # 开发服务器 http://0.0.0.0:8080
npm run build    # 生产构建
npm run lint     # ESLint检查
```

### 后端
```bash
python -m backend.run   # 启动Flask http://0.0.0.0:5000
# Windows下自动检测MySQL端口就绪，优先尝试MySQL80服务，失败则直接启动mysqld
```

### 手动启动MySQL（移动硬盘/U盘环境）
```bash
# 如果run.py自动启动失败，可手动执行：
"U:/__/app/MySQL/MySQL Server 8.0/bin/mysqld.exe" --defaults-file="U:/__/app/MySQL/MySQL Server 8.0/my.ini"
```

### MySQL启动逻辑（run.py）
1. 先检测3306端口是否已就绪 → 直接继续
2. 尝试Windows服务(MySQL80)启动 → 轮询端口等待就绪（最多60秒）
3. 服务启动失败 → 根据项目所在盘符推算mysqld路径直接启动
4. Windows终端UTF-8输出配置：`sys.stdout.reconfigure(encoding='utf-8')`，防止emoji崩溃

## Python 依赖（requirements.txt）

### 核心依赖
| 包名 | 版本 | 用途 |
|------|------|------|
| Flask | 3.1.3 | Web框架 |
| flask-cors | 6.0.5 | CORS跨域支持 |
| PyMySQL | 1.2.0 | MySQL数据库驱动 |
| bcrypt | 5.0.0 | 密码加密 |
| Werkzeug | 3.1.8 | WSGI工具库（Flask依赖） |

### 音频处理
| 包名 | 版本 | 用途 |
|------|------|------|
| mutagen | 1.48.1 | 音频元数据读取 |
| pydub | 0.25.1 | 音频处理（MP3合并等） |
| pyaes | 1.6.1 | AES解密（NCM解密用） |

### 图像处理
| 包名 | 版本 | 用途 |
|------|------|------|
| Pillow | 12.3.0 | 图片处理（封面等） |

### 网络请求
| 包名 | 版本 | 用途 |
|------|------|------|
| requests | 2.34.2 | HTTP请求 |

### 间接依赖
| 包名 | 版本 | 用途 |
|------|------|------|
| blinker | 1.9.0 | Flask信号机制 |
| click | 8.4.2 | CLI工具（Flask依赖） |
| Jinja2 | 3.1.6 | 模板引擎 |
| itsdangerous | 2.2.0 | 安全签名 |
| MarkupSafe | 3.0.3 | HTML转义 |
| certifi | 2026.7.22 | SSL证书 |
| cffi | 2.1.1 | C FFI（bcrypt依赖） |
| pycparser | 3.0 | C解析器（cffi依赖） |
| colorama | 0.4.6 | 终端颜色 |
| charset-normalizer | 3.4.9 | 字符编码检测 |
| idna | 3.18 | 国际化域名 |
| typing_extensions | 4.16.0 | 类型扩展 |
| urllib3 | 2.7.0 | HTTP库（requests依赖） |

## 前端依赖（package.json）

### 核心依赖
| 包名 | 版本 | 用途 |
|------|------|------|
| vue | ^2.6.14 | 前端框架 |
| vue-router | ^3.5.4 | 路由（hash模式） |
| axios | ^0.27.2 | HTTP客户端 |
| echarts | ^5.4.3 | 图表（气泡图/柱状图） |
| core-js | ^3.6.5 | Polyfill |

### 开发依赖
| 包名 | 版本 | 用途 |
|------|------|------|
| @vue/cli-service | ^5.0.9 | Vue CLI构建工具 |
| @vue/cli-plugin-babel | ^5.0.9 | Babel编译 |
| @vue/cli-plugin-eslint | ^5.0.9 | ESLint检查 |
| vue-template-compiler | ^2.6.14 | 模板编译器（必须与vue版本匹配） |
| eslint | ^7.32.0 | 代码检查 |
| eslint-plugin-vue | ^7.20.0 | Vue ESLint插件 |
| @babel/core | ^7.18.6 | Babel核心 |
| @babel/eslint-parser | ^7.18.9 | Babel ESLint解析器 |
| playwright | ^1.58.2 | 自动化录屏 |

### ESLint配置（内嵌package.json）
- 继承：`plugin:vue/essential` + `eslint:recommended`
- 解析器：`@babel/eslint-parser`
- 浏览器兼容：`> 1%`、`last 2 versions`、`not dead`

## .gitignore 规则

### 前端忽略项
- `frontend/node_modules/` — 依赖包
- `frontend/dist/`、`frontend/build/` — 打包产物
- `frontend/.cache/`、`frontend/.npm/` — 缓存
- `frontend/.env*` — 环境变量文件
- `frontend/*.log` — 日志文件

### 后端忽略项
- `backend/venv/` — Python虚拟环境
- `__pycache__/`、`*.py[cod]` — Python缓存
- `backend/*.log` — 日志
- `backend/*.db` — SQLite文件（如果存在）
- `backend/data/album_covers` — 封面图目录
- `backend/data/album_track` — 音频文件目录
- `backend/tools/ffmpeg/*.exe` — FFmpeg可执行文件
- `backend/tools/unlock/*.exe` — 解密工具可执行文件
- `backend/tools/*.exe` — 其他工具可执行文件

### 通用忽略项
- `.idea/`、`*.iml`、`*.ipr`、`*.iws` — PyCharm配置
- `.DS_Store`、`Thumbs.db` — 系统文件
- `*.tmp`、`*.bak` — 临时文件
- `frontend-cdn/` — CDN版前端临时文件
- `node_modules/` — 根目录node_modules

## IDE 配置（.idea/）

### 项目结构
- 模块类型：PYTHON_MODULE
- SDK：Python 3.10 (MusicRate) + Python 3.12（Black格式化）
- 排除目录：`.venv`
- VCS：Git（项目根目录）

### 数据源配置
- 主数据源：`music_rate@localhost`（MySQL 8，utf8mb4）
- 次数据源：`book_rate@localhost`（MySQL 8）
- DB Navigator连接：`music_user@localhost`，auto-commit关闭
- 连接池最大7，空闲断开30秒

### 代码检查
- DuplicatedCode：启用（Python最小98行）

## 自动录屏工具（auto-record.js）

### 用途
使用 Playwright + Edge 浏览器 + FFmpeg 自动录制专辑页面播放视频，用于B站分享。

### 工作流程
1. 启动Edge浏览器（全屏模式）
2. 打开登录页，注入 localStorage 认证信息
3. 刷新页面使路由守卫验证token
4. 跳转到指定专辑页面
5. 等待页面渲染完成（检测`.album_name`元素）
6. 滚动到播放器位置（`.album-rotate-box`）
7. 点击播放按钮
8. 启动FFmpeg gdigrab录屏（Windows桌面捕获）
9. 等待录制时长结束
10. 关闭FFmpeg和浏览器

### 配置参数
```javascript
const CONFIG = {
  albumUrl: "http://localhost:8080/#/album/detail/898?id=898",
  loginUrl: "http://localhost:8080/#/login",
  token: "xxx",           // 用户token
  userId: "2",            // 用户ID
  isAdmin: "1",           // 是否管理员
  recordTime: 10,         // 录制时长（秒）
  outputVideo: "album_record.mp4",
  ffmpegPath: "U:\\MusicRate\\backend\\tools\\ffmpeg\\ffmpeg.exe"
}
```

### FFmpeg参数
- `-f gdigrab` — Windows桌面捕获
- `-framerate 20` — 帧率20fps
- `-c:v libx264` — H.264编码
- `-preset medium` — 编码速度
- `-crf 23` — 质量参数
- `-pix_fmt yuv420p` — 像素格式
- `-movflags +faststart` — MP4快速启动

### 运行方式
```bash
cd frontend/
node auto-record.js
```

### 注意事项
- 需要安装Playwright浏览器：`npx playwright install`
- FFmpeg路径必须正确
- token需要有效（过期的token会导致重定向到登录页）
- 录屏是全屏桌面捕获，不是浏览器内录屏
- 错误时会自动截图保存为 `page-error.png`

## 前端构建配置

### vue.config.js
```javascript
const { defineConfig } = require('@vue/cli-service')
module.exports = defineConfig({
  transpileDependencies: true
})
```
- 极简配置，仅开启依赖转译
- 无代理配置（前后端通过CORS直连）

### jsconfig.json
- 路径别名：`@/*` → `src/*`
- 编译目标：es5
- 模块系统：esnext

### babel.config.js
- 使用 `@vue/cli-plugin-babel/preset` 默认配置

## 相关文档

- [[backend-config-reference]] — 后端配置文件详解
- [[frontend-routes-and-config]] — 前端路由与配置
