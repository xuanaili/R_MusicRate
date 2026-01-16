import json


# ========== 复用你原有代码的安全JSON解析函数 ==========
def safe_json_loads(s):
    if s is None or s == "":
        return None
    try:
        return json.loads(s)
    except (json.JSONDecodeError, TypeError):
        return None