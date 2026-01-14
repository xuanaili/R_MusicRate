// src/utils/scoreCalc.js
export function calculateAlbumTotalScore(scoreList) {
  // 1. 基础容错：非数组/空数组直接返回 0.0
  if (!Array.isArray(scoreList) || scoreList.length === 0) return 0.0;

  // 2. 解构数据：第一个值是专辑整体评分，剩余是单曲评分
  const albumScore = scoreList[0] ?? 0;
  const trackScores = scoreList.slice(1);

  // 3. 过滤有效单曲评分（大于 0 的数字）
  const validTrackScores = trackScores.filter(s => typeof s === 'number' && s > 0);

  let totalScore;
  // 4. 核心逻辑：无有效单曲评分时，直接使用专辑整体评分
  if (validTrackScores.length === 0) {
    totalScore = albumScore;
  } else {
    // 有有效单曲评分时，按原权重计算
    const avgTrackScore = validTrackScores.reduce((a, b) => a + b, 0) / validTrackScores.length;
    totalScore = albumScore * 0.6 + avgTrackScore * 0.4;
  }

  // 5. 限制分数区间在 0~100 之间
  totalScore = Math.max(0, Math.min(totalScore, 100));

  // 6. 保留 1 位小数并转为数字类型（避免返回字符串）
  return Number(totalScore.toFixed(1));
}