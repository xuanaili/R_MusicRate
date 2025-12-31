// src/utils/scoreCalc.js
export function calculateAlbumTotalScore(scoreList) {
  if (!Array.isArray(scoreList) || scoreList.length === 0) return 0.0;
  const albumScore = scoreList[0] ?? 0;
  const trackScores = scoreList.slice(1);
  const validTrackScores = trackScores.filter(s => typeof s === 'number' && s > 0);
  let avgTrackScore = 0.0;
  if (validTrackScores.length > 0) {
    avgTrackScore = validTrackScores.reduce((a, b) => a + b, 0) / validTrackScores.length;
  }
  let totalScore = albumScore * 0.6 + avgTrackScore * 0.4;
  totalScore = Math.max(0, Math.min(totalScore, 100));
  return Number(totalScore.toFixed(1));
}