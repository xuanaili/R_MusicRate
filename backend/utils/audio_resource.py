# MusicRate\backend\api\audio_resource.py 音频资源专属接口 - 专辑MP3上传/查询/删除/时长解析
from flask import request, jsonify
import json
import traceback
import os
import uuid
import os.path
from datetime import datetime

from .db import get_current_user_id, get_db
from .decorators import login_required
from ..config import MYSQL_CONFIG, AUDIO_BASE_URL, AUDIO_UPLOAD_FOLDER
import pymysql
# 音频时长解析核心库（python自带，无需额外安装）
from mutagen.mp3 import MP3
from mutagen import MutagenError
