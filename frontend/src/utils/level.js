// src/utils/level.js
// 等级-经验纯函数（与 backend/utils/level.py 逻辑一致，复用 scoreCalc「前后端一致」模式）
// 规则：level = floor(sqrt(xp / 3600))，Lv.N 约需 N² 小时；每日加分（评分/听后感/评论）上限 100
const HOURS_TO_XP = 3600
const DAILY_BONUS_LIMIT = 100

// 等级称号分段：与后端 _LEVEL_TITLES 一致
const LEVEL_TITLES = [
  [30, '传奇乐迷'],
  [20, '乐评达人'],
  [13, '音乐行家'],
  [8, '资深乐迷'],
  [4, '爱乐人'],
  [0, '初听者']
]

// 经验值归一化：None/非法 → 0，负数 → 0
function toXp(xp) {
  const val = Number(xp == null ? 0 : xp)
  return isNaN(val) || val < 0 ? 0 : val
}

// 等级推导：floor(sqrt(xp / 3600))
export function computeLevel(xp) {
  return Math.floor(Math.sqrt(toXp(xp) / HOURS_TO_XP))
}

// 距下一级所需经验：下一级边界 (level+1)²*3600 − 当前 xp
export function xpToNextLevel(xp) {
  const v = toXp(xp)
  const level = computeLevel(v)
  const nextBoundary = (level + 1) ** 2 * HOURS_TO_XP
  return Math.ceil(nextBoundary - v)
}

// 当前级内进度 0~1（保留 4 位小数）
export function levelProgress(xp) {
  const v = toXp(xp)
  const level = computeLevel(v)
  const base = level ** 2 * HOURS_TO_XP
  const nextBoundary = (level + 1) ** 2 * HOURS_TO_XP
  const span = nextBoundary - base
  if (span <= 0) return 0
  const progress = (v - base) / span
  return Number(Math.max(0, Math.min(progress, 1)).toFixed(4))
}

// 等级称号：Lv0-3 初听者 → Lv4-7 爱乐人 → Lv8-12 资深乐迷 → …
export function levelTitle(level) {
  const lv = Number(level) || 0
  for (const [threshold, title] of LEVEL_TITLES) {
    if (lv >= threshold) return title
  }
  return '初听者'
}

// 每日加分上限计算：实际加分 = min(amount, 100 - todayBonus)，可为部分或 0
export function computeBonusGain(todayBonus, amount) {
  const tb = Number(todayBonus) || 0
  const amt = Number(amount) || 0
  if (amt <= 0) return 0
  const remaining = Math.max(0, DAILY_BONUS_LIMIT - tb)
  return Math.min(amt, remaining)
}
