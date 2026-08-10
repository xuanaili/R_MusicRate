# MusicRate\backend\tests\conftest.py pytest 全局配置
# 自动把项目根加入 sys.path，测试内可直接 `from backend.utils.xxx import ...`
import os
import sys

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)
