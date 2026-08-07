# 后端配置参考

## 一、Flask配置 (`backend/config.py`)

| 配置项 | 值 | 说明 |
|--------|-----|------|
| SECRET_KEY | `albumDetail-rate-secret-key` | Flask密钥 |
| DEBUG | True | 调试模式 |
| HOST | localhost | 服务地址 |
| PORT | 5000 | 服务端口 |

---

## 二、MySQL配置

| 配置项 | 值 |
|--------|-----|
| host | localhost |
| port | 3306 |
| user | music_user |
| password | 123456 |
| db | music_rate |
| charset | utf8mb4 |
| cursorclass | pymysql.cursors.DictCursor |

---

## 三、文件路径配置

| 配置项 | 路径 | URL前缀 |
|--------|------|---------|
| UPLOAD_FOLDER | `backend/data/album_covers` | `http://localhost:5000/covers/` |
| AUDIO_UPLOAD_FOLDER | `backend/data/album_track` | `http://localhost:5000/tracks/` |
| NCM_UPLOAD_TEMP_DIR | `backend/data/ncm_temp` | — |
| NCM_DECRYPT_TEMP_DIR | `backend/data/ncm_decrypt_temp` | — |

---

## 四、常量配置

| 配置项 | 值 | 说明 |
|--------|-----|------|
| DEFAULT_PAGE | 1 | 默认页码 |
| DEFAULT_PAGE_SIZE | 10 | 默认每页条数 |
| VALID_SORT_FIELDS | album_name, release_year, singer, my_score, created_at | 排序字段白名单 |
| DEFAULT_ADMIN_USER | admin | 默认管理员账号 |
| DEFAULT_ADMIN_PWD | 123456 | 默认管理员密码 |
| NCM_MAX_FILE_SIZE | 200MB | NCM文件大小限制 |
| NCM_TEMP_FILE_EXPIRE_HOURS | 24 | 临时文件过期时间 |

---

## 五、FFmpeg路径

**位置**：`backend/utils/unlock.py`

```python
current_dir = os.path.dirname(os.path.abspath(__file__))
FFMPEG_PATH = os.path.abspath(os.path.join(current_dir, '..', 'tools', 'ffmpeg', 'ffmpeg.exe'))
FFPROBE_PATH = os.path.abspath(os.path.join(current_dir, '..', 'tools', 'ffmpeg', 'ffprobe.exe'))
```

**KGG解密工具**：`backend/tools/unlock/kgg-dec.exe`

---

## 六、启动流程 (`backend/run.py`)

1. 添加项目根目录到sys.path
2. 创建Flask应用实例 `create_app()`
3. 检查MySQL80服务状态，未运行则启动
4. 执行 `init_base_tables()` 创建所有基础表
5. 执行 `init_default_admin()` 创建默认管理员
6. 启动Flask `app.run(debug=True, host='0.0.0.0', port=5000)`

**Windows MySQL服务启动**：
```python
# 使用PowerShell以管理员权限启动
ps_cmd = 'powershell -Command "Start-Process cmd -ArgumentList \'/c sc start MySQL80\' -Verb RunAs"'
```

---

## 七、编码问题

Windows下Python默认GBK编码，print含emoji会崩溃：
```bash
PYTHONIOENCODING=utf-8 python -m backend.run
```

---

## 八、依赖清单

**Python核心依赖**：
- Flask + Flask-CORS
- PyMySQL
- bcrypt
- mutagen (音频元数据)
- pydub (音频处理)
- pyaes (NCM解密AES)
- Pillow (图片处理)
- requests (QQ音乐歌词获取)

**系统工具**：
- FFmpeg (音频转码/合并/封面提取)
- kgg-dec.exe (KGG解密)
