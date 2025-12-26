# 本地图床工具 - 包含图片上传、访问接口
from flask import send_from_directory, request, jsonify
import os
import uuid
import traceback
from .config import UPLOAD_FOLDER, COVER_BASE_URL


def register_upload_routes(app):
    """注册图床相关路由（需传入Flask app实例）"""

    # 1. 提供图片访问的接口（用于前端显示封面）
    @app.route('/covers/<filename>')
    def serve_cover(filename):
        """根据文件名返回本地图片"""
        try:
            return send_from_directory(UPLOAD_FOLDER, filename)
        except Exception as e:
            print(f"❌ 图片访问失败：{str(e)}")
            return jsonify({"code": 404, "msg": "图片不存在"}), 404

    # 2. 上传图片接口（替换原有imgBB/SM.MS逻辑）
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