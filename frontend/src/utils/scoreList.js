// frontend/src/utils/scoreList.js 评分列表纯函数（v0.8.4 P0 抽公共）
// 服务于歌词展示页顶部「当前单曲快捷评分」：评分数组 [专辑整体分, 单曲1分, 单曲2分, ...]
// 与 AlbumTrackList 的 my_score 格式一致（index0 = 专辑整体分，index N = 第 N 首单曲分，0 表示未评分）。
// 可被 node 直接测试（golden 硬编码进 backend/tests/test_score_list.py，镜像 duration/lrcTime 既有模式）。

/**
 * 归一化 album.my_score（兼容 数组 / JSON 字符串 / 空值 / 非法）为数字数组。
 * 至少保留 index0（专辑整体分）占位，保证 getTrackScore 的 index+1 不越界；
 * 非法项置 0，数值收敛到 0-100。
 * @param {Array|string|undefined|null} myScore 详情接口返回的 my_score
 * @returns {number[]} 规范化后的评分数组
 */
export function parseScoreList(myScore) {
  let list = [];
  if (Array.isArray(myScore)) {
    list = myScore;
  } else if (typeof myScore === 'string') {
    try {
      list = JSON.parse(myScore);
    } catch (e) {
      list = [];
    }
  }
  if (!Array.isArray(list)) list = [];
  const clean = list.map(v => {
    const n = Number(v);
    return isNaN(n) ? 0 : Math.max(0, Math.min(100, n));
  });
  if (clean.length === 0) clean.push(0); // index0 占位
  return clean;
}

/**
 * 取第 trackIndex 首单曲的评分（评分数组 index0 是专辑整体分，故单曲分在 index+1）。
 * @param {number[]} scoreList 评分数组
 * @param {number} trackIndex 单曲序号（0 起）
 * @returns {number} 0-100，未评分/越界/非法 → 0
 */
export function getTrackScore(scoreList, trackIndex) {
  const list = Array.isArray(scoreList) ? scoreList : [];
  const v = Number(list[trackIndex + 1]);
  return isNaN(v) ? 0 : Math.max(0, Math.min(100, v));
}

/**
 * 写入第 trackIndex 首单曲的评分，返回新数组（不污染原数组，触发 Vue 响应式）。
 * 数组长度不足时按 0 补位；分数 round 到整数后收敛 0-100。
 * @param {number[]} scoreList 评分数组
 * @param {number} trackIndex 单曲序号（0 起）
 * @param {number} newScore 新评分（0-100）
 * @returns {number[]} 新评分数组
 */
export function setTrackScore(scoreList, trackIndex, newScore) {
  const list = Array.isArray(scoreList) ? scoreList.slice() : [0];
  const idx = trackIndex + 1;
  while (list.length <= idx) list.push(0);
  const n = Number(newScore);
  list[idx] = isNaN(n) ? 0 : Math.max(0, Math.min(100, Math.round(n)));
  return list;
}
