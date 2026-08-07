# 后端评分计算逻辑参考

## 一、评分格式

`my_score` 字段存储为JSON数组，格式为 `[专辑整体评分, 单曲1评分, 单曲2评分, ...]`

示例：
```json
[50, 100, 20, 30, 0, 0]
```
- 第一个值 = 专辑整体评分
- 后续 = 各单曲评分，0表示未评分

---

## 二、计算函数

**位置**：`backend/utils/score.py` — `calculate_album_total_score(score_list)`

**算法**：
```
if 无有效单曲评分:
    总分 = 专辑整体评分
else:
    单曲均分 = sum(有效单曲评分) / count(有效单曲评分)
    总分 = 专辑整体评分 × 0.6 + 单曲均分 × 0.4
```

**约束**：
- 0分单曲不计入计算
- 非数字/None值容错
- 结果限制在 0~100 之间
- 保留1位小数

---

## 三、前后端一致性

**后端**：`backend/utils/score.py` — `calculate_album_total_score()`
**前端**：`frontend/src/utils/scoreCalc.js` — 同名函数

两端逻辑必须保持一致！

---

## 四、评分存储与读取

### 保存评分
- **路由**：`PUT /api/album/score/save/<int:album_id>`
- **参数**：`{score_list: []}`
- **存储**：JSON序列化后存入 `my_score` TEXT字段

### 读取评分
- **路由**：`GET /api/album/score/get/<int:album_id>`
- **返回**：`{score_list: []}`

---

## 五、评分在列表中的使用

在 `/api/album/list` 中：
1. 先计算所有专辑的 `calculated_score`
2. 按 `sort_by='my_score'` 排序时使用 `calculated_score`
3. 返回数据中包含 `calculated_score` 字段

在 `/api/playlist/get-user-audio-albums` 中：
1. 解析 `my_score` JSON
2. 调用 `calculate_album_total_score()` 计算
3. 返回 `score` 字段（综合评分）

---

## 六、标签统计评分

**位置**：`backend/utils/tag.py` — `get_album_tag_stats(album_pool_id, cursor)`

**逻辑**：
1. 查公共专辑池的标签
2. 遍历所有用户表统计标签
3. 计算每个标签占比
4. 过滤占比<10%的标签
5. 生成气泡大小和颜色

**返回格式**：
```json
[
  {"tag": "Pop【流行】", "count": 5, "percent": 45.5, "size": 131, "color": "#a3f2b1"}
]
```
