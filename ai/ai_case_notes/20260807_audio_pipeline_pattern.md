# 案例：音频解密与合并处理管线

## 基本信息

- **案例编号**：20260807_audio_pipeline
- **关键词**：NCM解密、KGG解密、FFmpeg、音频合并、元数据提取、ID3标签
- **适用场景**：加密音乐文件解密、多轨音频合并为整轨、封面提取与嵌入

## 问题描述

MusicRate支持用户上传加密音乐文件（网易云NCM、酷狗KGG），系统需要解密、提取元数据、合并为整轨MP3，并上传到服务器供播放。

## 核心需求

1. 支持NCM/KGG/MP3/OGG/FLAC/WAV等多种格式
2. 解密后提取元数据（标题/歌手/专辑/封面/曲目号）
3. 多文件合并为整轨MP3（含时间戳）
4. 封面提取、压缩、上传到图床
5. 返回完整数据供前端创建专辑

## 解决方案

### 管线架构

```
上传文件
  ├─ NCM → NcmDecrypt → AES-ECB解密 → RC4流解密 → MP3/FLAC
  ├─ KGG → kgg-dec.exe → OGG → FFmpeg → MP3
  └─ MP3/OGG/FLAC/WAV → 直接处理
      ↓
提取元数据 (mutagen)
  ├─ 标题/歌手/专辑/曲目号/年份
  ├─ 封面图片 → 压缩(<256KB) → 上传图床
  └─ 时长 (ffprobe优先, pydub备选)
      ↓
按曲目号排序
      ↓
合并音频 (FFmpeg concat filter)
  ├─ 单文件: 直接转码320k MP3
  └─ 多文件: concat重编码 → 验证时长(10%误差容忍)
      ↓
上传合并文件 → 生成URL
      ↓
返回 {album_name, singer, cover_img, mp3_url, songs:[{name, duration, timestamp}]}
```

### NCM解密算法

```python
# 1. 验证文件头
MAGIC_HEADER = bytes([0x43, 0x54, 0x45, 0x4e, 0x46, 0x44, 0x41, 0x4d])  # CTENFDAM

# 2. 解密Key
key_data = XOR(key_ciphertext, 0x64)
key_data = AES_ECB_DECRYPT(key_data, CORE_KEY)
key_data = PKCS7_UNPAD(key_data)[17:]  # 去除"neteasecloudmusic"前缀
key_box = RC4_KSA(key_data)  # 256字节替换表

# 3. 解密元数据
meta_data = XOR(meta_ciphertext, 0x63)
meta_data = BASE64_DECODE(meta_data[22:])  # 去除"163 key(Don't modify):"前缀
meta_data = AES_ECB_DECRYPT(meta_data, META_KEY)
meta_data = JSON_PARSE(PKCS7_UNPAD(meta_data))

# 4. 解密音频
audio = XOR(audio_data, key_box)  # 逐字节 XOR key_box[cur & 0xff]
```

### FFmpeg合并命令

```bash
# 多文件合并
ffmpeg -f concat -safe 0 -i filelist.txt -c:a libmp3lame -b:a 320k -ar 44100 -ac 2 output.mp3

# filelist.txt 内容
file 'path/to/track1.mp3'
file 'path/to/track2.mp3'
```

### 封面处理

```python
# 提取封面
extract_album_cover(audio_files, output_dir)  # FFmpeg -an -vcodec copy -f image2

# 压缩封面
compress_image(img_data, max_size=256*1024)  # 迭代降低JPEG质量 80→10

# 写入ID3标签
write_cover_to_mp3(mp3_path, cover_bytes)  # mutagen ID3 APIC

# 上传图床
upload_cover_to_imgbed(cover_path)  # 复制到UPLOAD_FOLDER, UUID文件名
```

## 踩坑记录

1. **Windows FFmpeg路径**：必须使用绝对路径，`os.path.join` 后需 `os.path.abspath()`
2. **中文文件名**：`secure_filename()` 需要自定义，标准库会删除中文字符
3. **合并时长误差**：FFmpeg concat可能产生微小时长差异，设置10%容忍阈值
4. **KGG文件名清理**：`kgg-dec.exe` 输出文件名带 `_kgg-dec` 后缀，需要手动清理
5. **封面过大**：未压缩的封面可达数MB，写入ID3后MP3文件膨胀 → 压缩到256KB以下
6. **编码问题**：Windows下Python默认GBK，print含emoji会崩溃 → `PYTHONIOENCODING=utf-8`

## 适配规则

- 新增加密格式时，参考NCM/KGG的解密模式，在 `backend/utils/` 下新增解密模块
- 新增音频格式时，在 `allowed_file()` 和 `get_audio_metadata()` 中添加支持
- 临时文件必须使用 `tempfile.TemporaryDirectory()` 自动清理
- 封面压缩阈值256KB，JPEG质量从80逐步降低到10
- 合并后时长验证使用10%误差容忍
- 文件大小限制200MB（NCM_MAX_FILE_SIZE）
