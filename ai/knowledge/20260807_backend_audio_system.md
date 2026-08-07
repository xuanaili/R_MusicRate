# 后端音频处理系统参考

## 一、音频处理管线

```
上传文件 → 格式检测 → 解密(如需) → 提取元数据 → 合并 → 上传 → 返回URL
```

---

## 二、支持的音频格式

**格式白名单**：`mp3, ogg, flac, wav, m4a, mp4`

**加密格式**：
- NCM（网易云加密格式）→ 解密为MP3/FLAC
- KGG（酷狗加密格式）→ 解密为OGG → 转码为MP3

---

## 三、NCM解密流程

**位置**：`backend/utils/ncm_unlock.py`

**核心类**：`NcmDecrypt`

**解密算法**：
1. 验证MAGIC_HEADER (`CTENFDAM`)
2. 提取加密Key数据 → XOR 0x64 → AES-ECB解密(CORE_KEY) → 去除PKCS7填充 → 生成RC4 Key Box
3. 提取元数据 → XOR 0x63 → Base64解码 → AES-ECB解密(META_KEY) → JSON解析
4. 提取音频数据 → 用Key Box做RC4流解密
5. 嗅探音频格式(MP3/FLAC)
6. 写入ID3标签(标题/歌手/专辑/封面)

**密钥**：
- `CORE_KEY = 687a4852416d736f356b496e62617857`
- `META_KEY = 2331346c6a6b5f215c5d2630553c2728`

**批量接口**：`batch_convert_ncm_to_mp3(ncm_files, output_dir)` → 返回 `(success, mp3_files, temp_cover_map)`

---

## 四、KGG解密流程

**位置**：`backend/utils/kgg_converter.py`

**流程**：`KGG → kgg-dec.exe → OGG → FFmpeg → MP3`

**步骤**：
1. 复制kgg-dec.exe和KGG文件到输出目录
2. 运行 `kgg-dec.exe` 转换为OGG
3. 清理文件名(移除`_kgg-dec`后缀)
4. FFmpeg转码：`OGG → MP3 (192k, 44100Hz, 2ch)`
5. 从OGG提取元数据写入MP3

**批量接口**：`batch_convert_kgg_to_mp3(kgg_files, output_dir)`

---

## 五、通用音频处理

**位置**：`backend/utils/unlock.py`

### FFmpeg路径配置
```python
FFMPEG_PATH = os.path.join(current_dir, '..', 'tools', 'ffmpeg', 'ffmpeg.exe')
FFPROBE_PATH = os.path.join(current_dir, '..', 'tools', 'ffmpeg', 'ffprobe.exe')
AudioSegment.converter = FFMPEG_PATH
AudioSegment.ffprobe = FFPROBE_PATH
```

### 元数据提取 `get_audio_metadata(file_path, file_ext)`
- 使用mutagen库提取：标题/歌手/专辑/曲目号/年份/时长/封面
- 时长提取优先级：ffprobe > pydub
- 封面保存为临时文件，路径存入 `metadata['cover_img']`

### 音频合并 `merge_audio_files(audio_files, output_dir, album_name, artist, album_id)`
- 单文件：直接转码为320k MP3
- 多文件：使用FFmpeg concat滤镜重编码合并
- 验证：对比合并前后时长(允许10%误差)

### 文件上传 `upload_merged_audio(merge_file_path, album_id, artist, album_name)`
- 文件名格式：`{序号}_{歌手名}_{专辑名}.mp3`
- 重复文件名添加4位随机后缀
- 使用mutagen.MP3解析时长

### 封面处理
- `upload_cover_to_imgbed(cover_path)` — 复制到图床目录，返回URL
- `extract_album_cover(audio_files, output_dir)` — FFmpeg提取封面
- `write_cover_to_mp3(mp3_file_path, cover_data)` — 写入ID3 APIC标签

---

## 六、API路由汇总

| 路由 | 方法 | 功能 |
|------|------|------|
| `/api/audio/unlock/parse` | POST | 多文件解析→合并→上传 |
| `/api/audio/unlock/convert-kgg-only` | POST | KGG转MP3(返回Base64) |
| `/api/audio/unlock/convert-ncm-only` | POST | NCM转MP3(返回Base64) |
| `/api/audio/unlock/convert-mp3-only` | POST | 通用音频转MP3 |
| `/api/audio/unlock/parse-sorted-mp3` | POST | 排序后MP3解析 |
| `/api/album/pool/audio/upload` | POST | 管理员上传MP3 |
| `/api/album/pool/audio/upload/merged` | POST | 管理员上传合并音频 |
| `/api/album/pool/audio/delete` | POST | 管理员删除音频 |
| `/api/album/pool/audio/info/<id>` | GET | 查询音频信息 |
| `/api/album/user/has-audio` | GET | 用户有音频的专辑 |
| `/tracks/<filename>` | GET | 音频文件访问 |
| `/covers/<filename>` | GET | 封面图片访问 |
| `/api/upload_img` | POST | 图片上传 |

---

## 七、临时文件处理

- 使用 `tempfile.TemporaryDirectory()` 自动清理
- 临时封面文件在处理完成后手动清理
- NCM临时目录：`backend/data/ncm_temp`
- NCM解密临时目录：`backend/data/ncm_decrypt_temp`
- 文件大小限制：200MB（NCM_MAX_FILE_SIZE）
- 临时文件过期：24小时

---

## 八、时长格式化

- `format_duration(seconds)` → `H:MM:SS` 格式
- 数据库存储：秒数(int)
- 前端展示：`m:ss` 或 `H:MM:SS`
