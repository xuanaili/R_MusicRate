# 案例：JSON字段存储与双表同步模式

## 基本信息

- **案例编号**：20260807_json_field_sync
- **关键词**：JSON-as-TEXT、双表同步、简介同步、安全解析
- **适用场景**：MySQL中存储JSON数组/对象，多表数据同步

## 问题描述

MusicRate中大量字段使用JSON格式存储（tracks、my_score、tags、review、comments等），但MySQL 8的JSON列类型有诸多限制。同时，用户专辑简介需要同时存在于 `user_album_intro` 表和 `albums_{user_id}` 表中，需要保证双表数据一致性。

## 核心需求

1. JSON数组/对象在MySQL中可靠存储
2. 读取时安全解析（容错处理）
3. 简介双表同步写入
4. 模板更新时的差异化同步

## 解决方案

### 1. JSON-as-TEXT存储

使用TEXT类型存储JSON字符串，而非MySQL原生JSON类型：

```python
# 建表时
'my_score TEXT,     -- 不设DEFAULT值！避免MySQL 1101错误'
'tags TEXT,         -- JSON数组'
'review TEXT,       -- JSON对象'
```

**原因**：
- MySQL JSON类型不支持DEFAULT值
- TEXT类型兼容性更好
- 解析在Python层完成，更灵活

### 2. 安全解析函数

```python
def safe_json_loads(s):
    """安全解析JSON，返回原生对象或None"""
    if s is None or s == '' or s == 'None':
        return None
    try:
        return json.loads(s)
    except (json.JSONDecodeError, TypeError, ValueError):
        return None
```

### 3. 双表同步写入

```python
def save_user_album_intro(user_id, album_id, intro_content):
    # 1. 写入专用表
    if exists:
        UPDATE user_album_intro SET album_intro = %s
    else:
        INSERT INTO user_album_intro
    
    # 2. 同步到用户专辑表
    if table_exists(f'albums_{user_id}'):
        UPDATE albums_{user_id} SET album_intro = %s
    
    db.commit()
```

### 4. 模板更新差异化同步

```python
def update_pool_album(pool_id):
    # 强制同步字段
    force_sync = ['album_name', 'singer', 'release_year', 'duration_type']
    
    # 条件同步字段（简介）
    # 仅当用户侧为空或与旧值相同时才同步
    if user_intro == '' or user_intro == old_pool_intro:
        sync_intro = True
```

## 踩坑记录

1. **MySQL 1101错误**：`my_score TEXT DEFAULT '[]'` 会报错 → 改为 `my_score TEXT`（无默认值）
2. **JSON解析失败**：部分旧数据可能是空字符串或"None" → `safe_json_loads()` 处理所有边界情况
3. **双表不一致**：写入一张表成功但另一张失败 → 使用事务 + `db.commit()` 统一提交
4. **返回字符串而非对象**：忘记 `json.loads()` → 前端收到的是字符串而非数组
5. **tracks与tracks_time索引不一致**：修改一方时忘记同步另一方 → 必须保证数组长度一致

## 适配规则

- JSON字段一律使用TEXT类型，不设DEFAULT值
- 所有JSON解析使用 `safe_json_loads()`，不用 `json.loads()`
- 双表写入必须使用事务保证一致性
- 返回前端前确保JSON字段已解析为原生对象
- tracks和tracks_time必须成对操作，保证索引一致
- 新增JSON字段时，在读取路由中添加 `safe_json_loads()` 处理
