# MusicRate\backend\upload_utils.py 本地图床工具 - 包含图片上传、音频访问、图片访问接口
from flask import send_from_directory, request, jsonify
import os
import uuid
import traceback
from backend.config import UPLOAD_FOLDER, COVER_BASE_URL, AUDIO_UPLOAD_FOLDER, COVER_THUMB_UPLOAD_FOLDER  # 新增：缩略图配置
# 缩略图生成依赖 Pillow（已安装）
from PIL import Image

# 封面缩略图尺寸：300px（列表页展示100px左右，300px兼容高清屏，文件仅十几KB）
COVER_THUMB_SIZE = 300
# 静态图片资源强缓存时间（文件名是UUID永不变，浏览器直接本地缓存不再请求）
CACHE_MAX_AGE = 31536000

def _generate_cover_thumb(original_path, thumb_path):
    """生成封面缩略图（保持比例缩到300px内），失败时静默返回，不阻塞主流程"""
    try:
        with Image.open(original_path) as im:
            im = im.convert('RGB')
            im.thumbnail((COVER_THUMB_SIZE, COVER_THUMB_SIZE), Image.LANCZOS)
            im.save(thumb_path, 'JPEG', quality=82, optimize=True)
        return True
    except Exception as e:
        print(f"⚠️ 缩略图生成失败：{str(e)}")
        return False

def _apply_cover_cache(response):
    """给图片响应设置强缓存头（文件名UUID不变，immutable确保永不重新校验）"""
    response.headers['Cache-Control'] = f'public, max-age={CACHE_MAX_AGE}, immutable'
    return response

def register_upload_routes(app):
    """注册图床相关路由（需传入Flask app实例）- 封面+音频"""

    # 1. 提供图片访问的接口（用于前端显示封面）【原有代码，不动】+ 强缓存头
    @app.route('/covers/<filename>')
    def serve_cover(filename):
        """根据文件名返回本地图片（原始封面，详情页大图用）"""
        try:
            return _apply_cover_cache(send_from_directory(UPLOAD_FOLDER, filename))
        except Exception as e:
            print(f"❌ 图片访问失败：{str(e)}")
            return jsonify({"code": 404, "msg": "图片不存在"}), 404

    # 1.5 ✅ 新增：提供封面缩略图访问接口（列表页小图用，避免下载几MB原图）
    # 缩略图不存在时从原图懒生成并落盘缓存，旧封面无需批量处理，首次访问自动生成
    @app.route('/covers_thumb/<filename>')
    def serve_cover_thumb(filename):
        """根据文件名返回封面缩略图（不存在则从原图懒生成）"""
        try:
            thumb_path = os.path.join(COVER_THUMB_UPLOAD_FOLDER, filename)
            if not os.path.exists(thumb_path):
                original_path = os.path.join(UPLOAD_FOLDER, filename)
                if not os.path.exists(original_path):
                    return jsonify({"code": 404, "msg": "图片不存在"}), 404
                # 懒生成缩略图（并发下可能重复生成，幂等无害）
                if not _generate_cover_thumb(original_path, thumb_path):
                    # 生成失败则回退返回原图，保证功能可用
                    return _apply_cover_cache(send_from_directory(UPLOAD_FOLDER, filename))
            return _apply_cover_cache(send_from_directory(COVER_THUMB_UPLOAD_FOLDER, filename))
        except Exception as e:
            print(f"❌ 缩略图访问失败：{str(e)}")
            return jsonify({"code": 404, "msg": "图片不存在"}), 404

    # ========== 新增：提供音频访问的接口（用于前端播放MP3，和封面同规范） ==========
    @app.route('/tracks/<filename>')
    def serve_track(filename):
        """根据文件名返回本地MP3音频文件"""
        try:
            return _apply_cover_cache(send_from_directory(AUDIO_UPLOAD_FOLDER, filename))
        except Exception as e:
            print(f"❌ 音频访问失败：{str(e)}")
            return jsonify({"code": 404, "msg": "音频不存在"}), 404

    # 2. 上传图片接口（替换原有imgBB/SM.MS逻辑）【原有代码，完全不动】
    @app.route('/api/upload_img', methods=['POST'])
    def upload_img_proxy():
        """接收前端上传的图片，保存到本地并返回访问URL"""
        try:
            # 检查是否有图片文件
            if 'image' not in request.files:
                return jsonify({"code": 400, "msg": "请上传图片文件"}), 400
            image_file = request.files['image']

            # 生成唯一文件名（避免重复）
            ext = os.path.splitext(image_file.filename)[-1]  # 获取文件后缀（.jpg/.png）
            filename = f"{uuid.uuid4()}{ext}"  # 用UUID生成唯一名
            save_path = os.path.join(UPLOAD_FOLDER, filename)

            # 保存图片到本地
            image_file.save(save_path)

            # 同步生成缩略图（列表页小图专用，加载更快）
            thumb_path = os.path.join(COVER_THUMB_UPLOAD_FOLDER, filename)
            _generate_cover_thumb(save_path, thumb_path)

            # 生成本地直链（前端能直接访问）
            img_url = f"{COVER_BASE_URL}{filename}"

            return jsonify({
                "code": 200,
                "msg": "图片上传成功（本地图床）",
                "data": {"img_url": img_url}
            })

        except Exception as e:
            print(f"❌ 图片上传失败：{str(e)}")
            print(traceback.format_exc())
            return jsonify({"code": 500, "msg": f"上传失败：{str(e)}"}), 500