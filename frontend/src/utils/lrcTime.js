// frontend/src/utils/lrcTime.js 歌词时间纯函数（v0.8.3 P0 抽公共，可被 node 直接测试）
// 与后端 backend/utils/lrc.py 的 str_to_seconds / seconds_to_str 语义一致：
//   存储格式 'mm:ss' 或 'mm:ss.x'（1 位小数，时间按升序、去重保留首个）
//   小数按「真实小数位」归一：'.5'=0.5、'.05'=0.05、'.123'=0.123
// 修复原组件内 parseTimeStr 的 /1000 bug（'00:05.5' 被解析成 5.005s → 现为 5.5s）

/**
 * 时间字符串 'mm:ss' / 'mm:ss.x'（x 可为 1~3 位小数）→ 秒数（浮点）
 * 按小数位数除法：1 位 /10、2 位 /100、3 位 /1000（与后端 str_to_seconds 一致）
 */
export function parseTimeStr(str) {
  try {
    const [mPart, rest] = String(str).split(':');
    const m = parseInt(mPart, 10);
    let sec = 0;
    if (rest && rest.includes('.')) {
      const [sPart, msPart] = rest.split('.');
      sec = parseInt(sPart, 10) + (msPart ? parseInt(msPart, 10) / Math.pow(10, msPart.length) : 0);
    } else {
      sec = parseInt(rest, 10);
    }
    return m * 60 + sec;
  } catch {
    return 0;
  }
}

/**
 * 秒数 → 存储格式 'mm:ss' 或 'mm:ss.x'（1 位小数，为 0 时省略；与后端 seconds_to_str 一致）
 */
export function formatTime(s) {
  if (!s || isNaN(s) || s < 0) return '00:00';
  const min = Math.floor(s / 60);
  const sec = Math.floor(s % 60);
  const ms = Math.floor((s % 1) * 10);
  return ms > 0
    ? `${min.toString().padStart(2, '0')}:${sec.toString().padStart(2, '0')}.${ms}`
    : `${min.toString().padStart(2, '0')}:${sec.toString().padStart(2, '0')}`;
}

// 与 formatTime 完全同逻辑，仅保留别名以兼容组件内原调用点
export const formatTimeForOutput = formatTime;
