# 前端评分计算与标签处理参考

## 一、评分计算函数

**位置**：`frontend/src/utils/scoreCalc.js`

```javascript
export function calculateAlbumTotalScore(scoreList) {
  if (!Array.isArray(scoreList) || scoreList.length === 0) return 0.0
  const albumScore = scoreList[0] ?? 0
  const trackScores = scoreList.slice(1)
  const validTrackScores = trackScores.filter(s => typeof s === 'number' && s > 0)
  let totalScore
  if (validTrackScores.length === 0) {
    totalScore = albumScore
  } else {
    const avgTrackScore = validTrackScores.reduce((a, b) => a + b, 0) / validTrackScores.length
    totalScore = albumScore * 0.6 + avgTrackScore * 0.4
  }
  totalScore = Math.max(0, Math.min(totalScore, 100))
  return Number(totalScore.toFixed(1))
}
```

**与后端一致性**：此函数必须与 `backend/utils/score.py` 的 `calculate_album_total_score()` 逻辑完全一致！

---

## 二、评分数据格式处理

### my_score 字符串→数组转换

后端返回的 `my_score` 可能是字符串格式的JSON数组，需要转换：

```javascript
// AlbumItem.vue 中的转换方法
formatScoreStrToArray(scoreStr) {
  let scoreArr = []
  if (!scoreStr || typeof scoreStr !== 'string' || scoreStr.trim() === '') {
    return scoreArr
  }
  try {
    scoreArr = JSON.parse(scoreStr)
    scoreArr = scoreArr.filter(item => typeof item === 'number' && !isNaN(item) && item >= 0)
  } catch (error) {
    scoreArr = []
  }
  return scoreArr
}
```

### 评分优先级

```javascript
// AlbumItem.vue computed
albumTotalScore() {
  // 优先使用后端计算好的分数
  if (this.music.calculated_score !== undefined) {
    return this.music.calculated_score
  }
  // 退回前端计算
  const scoreStr = this.music.my_score || ''
  const scoreList = this.formatScoreStrToArray(scoreStr)
  return calculateAlbumTotalScore(scoreList)
}
```

---

## 三、标签处理

### 标签格式

标准格式：`English【中文】`，如 `Pop【流行】`、`Rock【摇滚】`

### 英文提取（展示用）

```javascript
getTagEnglish(tagStr) {
  if (!tagStr || typeof tagStr !== 'string') return ''
  const splitIndex = tagStr.indexOf('【')
  return splitIndex > -1 ? tagStr.substring(0, splitIndex).trim() : tagStr.trim()
}
```

### 中文提取（悬浮提示用）

```javascript
getTagChinese(tagStr) {
  if (!tagStr || typeof tagStr !== 'string') return ''
  const start = tagStr.indexOf('【')
  const end = tagStr.indexOf('】')
  return start > -1 && end > start ? tagStr.substring(start + 1, end).trim() : tagStr.trim()
}
```

---

## 四、标签气泡配置

**位置**：`frontend/src/config/index.js`

### 数据结构

```javascript
const tagBallConfigList = [
  { tag: 'Pop【流行】', minSize: 40, maxSize: 90, minRate: 200, maxRate: 400, numWeight: 1.1 },
  // ... 150+ 标签
]
```

### 参数说明

| 参数 | 类型 | 说明 |
|------|------|------|
| `tag` | String | 标签全名（English【中文】） |
| `minSize` | Number | 小球最小尺寸(px) |
| `maxSize` | Number | 小球最大尺寸(px) |
| `minRate` | Number | 呼吸动画最小速率(ms) |
| `maxRate` | Number | 呼吸动画最大速率(ms) |
| `numWeight` | Number | 数量权重(影响球数) |

### 风格→球参数映射

- **重型风格**（金属/硬核/朋克）：大球(80-155px)、慢速(40-180ms)、高权重(2.5-3.5)
- **轻柔风格**（氛围/古典/民谣）：小球(20-65px)、快速(280-550ms)、低权重(0.6-0.9)
- **流行风格**（流行/摇滚/嘻哈）：中球(40-120px)、中速(100-290ms)、中权重(1.1-2.0)

### 导出

```javascript
export default {
  albumTagOptions,  // string[] — 所有标签名数组
  ballConfig        // {tag: params} — 标签→小球参数映射 + default兜底
}
```

---

## 五、时长格式化

### 秒数→可读格式

```javascript
// AlbumItem.vue
formatDuration(seconds) {
  const sec = Number(seconds)
  if (isNaN(sec) || sec <= 0) return '0min'
  const hours = Math.floor(sec / 3600)
  const mins = Math.floor((sec % 3600) / 60)
  if (hours === 0) return `${mins}min`
  if (mins === 0) return `${hours}h`
  return `${hours}h${mins}min`
}
```

### 秒数→时间戳格式（曲目时间）

```javascript
// 曲目时间戳格式化（用于播放器跳转）
function formatTrackTime(seconds) {
  const mins = Math.floor(seconds / 60)
  const secs = Math.floor(seconds % 60)
  return `${mins}:${secs.toString().padStart(2, '0')}`
}
```

---

## 六、播放器相关

### 播放模式

| 模式 | 值 | 说明 |
|------|-----|------|
| 顺序播放 | `order` | 按列表顺序，最后一首后回到第一首 |
| 随机播放 | `random` | 随机选择下一首 |
| 单曲循环 | `single` | 重复播放当前曲目 |

### 音频播放API流程

```
1. GET /api/playlist/get-user-audio-albums → 获取有音频的专辑列表
2. GET /api/playlist/get-user-playlist-data → 获取播放列表和当前状态
3. POST /api/album/listening/start/{id} → 开始计时
4. POST /api/album/listening/pause/{id} → 暂停计时+累加时长
5. POST /api/playlist/switch-next-album → 切换下一首
6. POST /api/playlist/save-user-playlist-data → 保存播放状态
```
