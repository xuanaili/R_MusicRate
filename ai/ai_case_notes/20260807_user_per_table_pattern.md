# 案例：用户分表架构设计

## 基本信息

- **案例编号**：20260807_user_per_table
- **关键词**：用户分表、动态表名、数据隔离、跨用户查询
- **适用场景**：多用户私有数据需要完全隔离，同时需要跨用户聚合统计

## 问题描述

MusicRate的核心业务是用户管理自己的专辑收藏。每个用户有私有的评分、听后感、标签、播放时长等数据，这些数据不能被其他用户看到。同时，系统需要支持跨用户标签统计（如"这张专辑所有用户打出的标签占比"）。

## 核心需求

1. 用户数据完全隔离（评分、评论、听后感等私有）
2. 支持公共模板（album_pool）和私有副本（albums_{user_id}）的双层结构
3. 支持跨用户聚合统计（标签统计）
4. 支持模板更新同步到用户副本

## 解决方案

### 架构设计：用户分表模式

```
album_pool (共享模板)
  ├── albums_1 (用户1的私有副本)
  ├── albums_2 (用户2的私有副本)
  └── albums_N (用户N的私有副本)
```

### 关键实现

1. **动态表名**：`get_album_table_name(user_id)` → `albums_{user_id}`
2. **自动建表**：`check_and_create_user_album_table(user_id)` 在登录时检查并创建
3. **关联字段**：`source_pool_id` 关联公共池，`sync_pool_update` 控制同步
4. **跨用户查询**：通过 `information_schema.TABLES` 查找所有 `albums_%` 表

### 代码模板

```python
# 获取用户表名
table_name = get_album_table_name(user_id)

# 查询用户私有数据
cursor.execute(f'SELECT * FROM {table_name} WHERE id = %s', (album_id,))

# 跨用户聚合统计
cursor.execute("SELECT TABLE_NAME FROM information_schema.TABLES WHERE TABLE_NAME LIKE 'albums_%'")
for row in cursor.fetchall():
    tname = row['TABLE_NAME']
    cursor.execute(f'SELECT tags FROM {tname} WHERE source_pool_id = %s', (pool_id,))
    # 聚合统计...
```

### 同步机制

**强制同步字段**：album_name, singer, release_year, duration_type
**条件同步字段**：album_intro（仅同步空值/未自定义的）
**不同步字段**：my_score, tags, review, comments, listening_duration

## 踩坑记录

1. **MySQL 1101错误**：`my_score` TEXT字段不能设置DEFAULT值，必须为TEXT无默认值
2. **动态表名SQL注入风险**：必须验证user_id为整数，表名通过 `get_album_table_name()` 获取
3. **跨用户查询性能**：遍历所有用户表在大用户量下会变慢，需要考虑缓存
4. **ALTER TABLE时机**：`listening_duration` 字段是后期添加的，需要自动检测并添加缺失列

## 适配规则

- 当用户数据完全私有且不需要JOIN查询时，使用分表模式
- 当需要频繁跨用户聚合时，考虑使用共享表+user_id字段替代
- 分表模式适合用户数<1000的场景，大规模场景需重新设计
- 新增字段时必须考虑旧表的兼容性（自动ALTER TABLE）
