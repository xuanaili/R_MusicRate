// frontend/src/utils/duration.js 听取时长格式化（v0.8.3 P2 抽公共）
// 统一 AlbumItem / AlbumBaseInfo / AlbumReviewEditor / AlbumCommentSection 4 处
// 「已听时长」显示格式，避免各处格式各异（有无补零 / 0 占位不一）：
//   统一规则：
//     - 非法 / <=0 → emptyText（默认 '0min'，调用方可传 '未知' 等自定义占位）
//     - 不足 1 小时 → 'Xmin'
//     - 整小时 → 'Xh'
//     - 其余 → 'XhYmin'（分钟不补零，如 '1h5min'）
// 可被 node 直接测试（golden 硬编码进 backend/tests/test_duration_format.py）

/**
 * 听取时长：秒数 → 'XhYmin' 紧凑格式
 * @param {number|string} seconds 秒数
 * @param {string} [emptyText='0min'] 非法/<=0 时的占位文案
 * @returns {string} 格式化后的时长文案
 */
export function formatDuration(seconds, emptyText = '0min') {
  const sec = Number(seconds);
  if (isNaN(sec) || sec <= 0) return emptyText;
  const hours = Math.floor(sec / 3600);
  const mins = Math.floor((sec % 3600) / 60);
  if (hours === 0) return `${mins}min`;
  if (mins === 0) return `${hours}h`;
  return `${hours}h${mins}min`;
}
