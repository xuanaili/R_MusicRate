# backend/app.py
from flask import Flask, request, jsonify
from flask_cors import CORS
import json
import os

# 初始化Flask应用
app = Flask(__name__)
# 允许跨域（解决前端调后端的跨域问题）
CORS(app)

# 配置JSON数据文件路径（和app.py同目录的data文件夹）
DATA_DIR = os.path.join(os.path.dirname(__file__), 'data')
DATA_FILE = os.path.join(DATA_DIR, 'music_data.json')

# 初始化数据文件（如果不存在就创建）
def init_data():
    # 创建data文件夹（如果不存在）
    if not os.path.exists(DATA_DIR):
        os.makedirs(DATA_DIR)
    # 创建初始音乐数据
    initial_data = [
        {"id": 1, "name": "晴天 - 周杰伦", "score": 8.5, "comments": ["好听", "经典"]},
        {"id": 2, "name": "七里香 - 周杰伦", "score": 9.2, "comments": []}
    ]
    # 如果JSON文件不存在，写入初始数据
    if not os.path.exists(DATA_FILE):
        with open(DATA_FILE, 'w', encoding='utf-8') as f:
            json.dump(initial_data, f, ensure_ascii=False, indent=2)

# 启动时初始化数据
init_data()

# 接口1：获取所有音乐列表
@app.route('/api/music', methods=['GET'])
def get_music_list():
    # 读取JSON文件
    with open(DATA_FILE, 'r', encoding='utf-8') as f:
        music_list = json.load(f)
    # 返回JSON数据
    return jsonify(music_list)

# 接口2：提交评分和评论
@app.route('/api/music/comment', methods=['POST'])
def submit_comment():
    # 获取前端传的参数
    data = request.get_json()
    music_id = data.get('musicId')
    comment = data.get('comment')
    score = data.get('score', 0)

    # 校验参数
    if not music_id or not comment:
        return jsonify({"code": 400, "msg": "音乐ID和评论不能为空"}), 400

    # 读取现有数据
    with open(DATA_FILE, 'r', encoding='utf-8') as f:
        music_list = json.load(f)

    # 找到对应音乐，更新评论和评分
    for music in music_list:
        if music['id'] == music_id:
            # 添加新评论
            music['comments'].append(comment)
            # 简单计算新评分（原有评分 + 新评分）/2
            if score > 0:
                music['score'] = round((music['score'] + score) / 2, 1)
            break

    # 保存更新后的数据到JSON文件
    with open(DATA_FILE, 'w', encoding='utf-8') as f:
        json.dump(music_list, f, ensure_ascii=False, indent=2)

    # 返回成功响应
    return jsonify({"code": 200, "msg": "提交成功", "data": music_list})

# 启动服务
if __name__ == '__main__':
    # 调试模式，端口5000，允许外部访问（方便前端调用）
    app.run(debug=True, host='0.0.0.0', port=5000)