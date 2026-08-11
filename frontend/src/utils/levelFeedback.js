// src/utils/levelFeedback.js
// 统一处理带等级反馈的接口响应（pause / 评分 / 听后感 / 评论）
// - 升级横幅：对比 localStorage 上次等级，跨会话检测升级（level 递增才弹，幂等）
// - +N 经验 toast：加分接口返回 xp_gained > 0 时提示（收听经验不 toast，避免刷屏）
import message from '@/utils/message'

const LS_LEVEL_KEY = 'level'

// 检测升级并弹横幅：对比 localStorage 上次等级，跨会话检测升级
// 首次初始化（localStorage 无记录）只写入基线不弹横幅，避免老用户误弹「升级」
export function detectLevelUp(newLevel, title) {
  const level = Number(newLevel) || 0
  const raw = localStorage.getItem(LS_LEVEL_KEY)
  if (raw === null || raw === undefined || raw === '') {
    localStorage.setItem(LS_LEVEL_KEY, String(level))
    return false
  }
  const oldLevel = parseInt(raw, 10) || 0
  localStorage.setItem(LS_LEVEL_KEY, String(level))
  if (level > oldLevel) {
    message.levelUp(level, title)
    return true
  }
  return false
}

// 统一处理：升级横幅 +（可选）+N 经验 toast
// data: 接口返回的 data（含 level / xp_gained）
// opts.toast: 加分提示前缀文案，如 '评论发布'；不传则不 toast 加分
export function handleLevelFeedback(data, opts = {}) {
  if (!data) return
  if (data.level != null) {
    detectLevelUp(data.level, data.level_title)
  }
  const gained = Number(data.xp_gained) || 0
  if (opts.toast && gained > 0) {
    message.success(`${opts.toast} +${gained} 经验`)
  }
}
