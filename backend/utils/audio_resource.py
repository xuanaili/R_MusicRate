# ========== 新增：音频合并辅助函数 ==========
import os
import subprocess
import tempfile

from mutagen.mp3 import MP3


def merge_audio_files(audio_files, output_path):
    """
    合并多个音频文件为一个MP3
    :param audio_files: 音频文件路径列表
    :param output_path: 输出文件路径
    :return: 成功返回True，失败返回False
    """
    try:
        # 1. 创建临时文件列表（ffmpeg需要文件列表作为输入）
        temp_list_file = tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False, encoding='utf-8')
        for file_path in audio_files:
            # Windows系统需要转义路径
            if os.name == 'nt':
                file_path = file_path.replace('\\', '/')
            temp_list_file.write(f"file '{file_path}'\n")
        temp_list_file.close()

        # 2. 调用ffmpeg合并音频
        cmd = [
            'ffmpeg',
            '-f', 'concat',
            '-safe', '0',
            '-i', temp_list_file.name,
            '-c:a', 'mp3',
            '-b:a', '320k',  # 比特率
            '-y',  # 覆盖输出文件
            output_path
        ]

        # 执行命令
        result = subprocess.run(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            encoding='utf-8'
        )

        # 3. 删除临时文件
        os.unlink(temp_list_file.name)

        if result.returncode != 0:
            print(f"❌ ffmpeg合并失败：{result.stderr}")
            return False

        return True
    except Exception as e:
        print(f"❌ 音频合并出错：{str(e)}")
        return False


# ========== 新增：音频解析辅助函数（提取曲目信息） ==========
def parse_audio_metadata(audio_file_path):
    """
    解析音频元数据（歌手、专辑、曲目名等）
    :param audio_file_path: 音频文件路径
    :return: 元数据字典
    """
    try:
        audio = MP3(audio_file_path)
        metadata = {
            'artist': audio.get('TPE1', ['未知歌手'])[0] if 'TPE1' in audio else '未知歌手',
            'album': audio.get('TALB', ['未知专辑'])[0] if 'TALB' in audio else '未知专辑',
            'title': audio.get('TIT2', ['未知曲目'])[0] if 'TIT2' in audio else '未知曲目',
            'duration': int(audio.info.length) if audio.info.length else 0
        }
        return metadata
    except Exception as e:
        print(f"⚠️ 解析音频元数据失败：{str(e)}")
        return {
            'artist': '未知歌手',
            'album': '未知专辑',
            'title': os.path.basename(audio_file_path),
            'duration': 0
        }