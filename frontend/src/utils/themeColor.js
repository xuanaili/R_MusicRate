// MusicRate/frontend/src/utils/themeColor.js 主题色工具（v0.7 修复）
// 背景：今日推荐取色失败时 DailyRecommend 会 emit 'transparent'，若被持久化到
// persistMainColor* ，所有 v-bind(mainColorDark) 的文字颜色会变成透明、ECharts 渐变色
// 会拼出 'transparent33' 抛异常。本模块统一收敛【合法性校验 + 兜底默认色 + 坏值修复】。

// 兜底默认色：Element UI 主色 #409eff（历史无主题时的页面默认色）
export const DEFAULT_MAIN_COLOR = '#409eff'

// 颜色合法性校验：合法 hex / rgb / rgba / hsl / hsla 通过；空值/transparent/none/inherit 拒绝
export function isValidColor(value) {
  if (typeof value !== 'string') return false
  const v = value.trim().toLowerCase()
  if (!v || v === 'transparent' || v === 'none' || v === 'inherit') return false
  // #rgb / #rgba / #rrggbb / #rrggbbaa
  if (/^#([0-9a-f]{3}|[0-9a-f]{4}|[0-9a-f]{6}|[0-9a-f]{8})$/i.test(v)) return true
  // rgb() / rgba() / hsl() / hsla()
  if (/^(rgb|rgba|hsl|hsla)\(/.test(v)) return true
  return false
}

// 主题色兜底：非法值（含 'transparent'/空）一律回退默认，避免文字/图表色变成透明
export function sanitizeThemeColor(value) {
  return isValidColor(value) ? value : DEFAULT_MAIN_COLOR
}

// 与 DailyRecommend.darkenColor 一致：hex 变暗 amount（0-1）
function darkenColor(hex, amount) {
  const r = parseInt(hex.slice(1, 3), 16) * (1 - amount)
  const g = parseInt(hex.slice(3, 5), 16) * (1 - amount)
  const b = parseInt(hex.slice(5, 7), 16) * (1 - amount)
  return `#${Math.round(r).toString(16).padStart(2, 0)}${Math.round(g).toString(16).padStart(2, 0)}${Math.round(b).toString(16).padStart(2, 0)}`
}

// 读取并【修复】持久化主题色：
// - localStorage 里可能存着 'transparent' 这类坏值（取色失败被覆盖进去）
// - 主色合法 → 保留整套，损坏的暗色派生值用主色重算（保持同色系层级）
// - 主色也损坏 → 整套回退默认色
// - 返回值与坏值不同时会写回 localStorage（一次性修复，刷新不再反复）
// 返回 { mainColor, mainColorDark, mainColorDarkDouble }
export function getSavedTheme() {
  const base = localStorage.getItem('persistMainColor')
  const dark = localStorage.getItem('persistMainColorDark')
  const darkDouble = localStorage.getItem('persistMainColorDarkDouble')

  let theme
  if (isValidColor(base)) {
    theme = {
      mainColor: base,
      mainColorDark: isValidColor(dark) ? dark : darkenColor(base, 0.3),
      mainColorDarkDouble: isValidColor(darkDouble) ? darkDouble : darkenColor(base, 0.5)
    }
  } else {
    theme = {
      mainColor: DEFAULT_MAIN_COLOR,
      mainColorDark: darkenColor(DEFAULT_MAIN_COLOR, 0.3),
      mainColorDarkDouble: darkenColor(DEFAULT_MAIN_COLOR, 0.5)
    }
  }

  if (localStorage.getItem('persistMainColor') !== theme.mainColor) localStorage.setItem('persistMainColor', theme.mainColor)
  if (localStorage.getItem('persistMainColorDark') !== theme.mainColorDark) localStorage.setItem('persistMainColorDark', theme.mainColorDark)
  if (localStorage.getItem('persistMainColorDarkDouble') !== theme.mainColorDarkDouble) localStorage.setItem('persistMainColorDarkDouble', theme.mainColorDarkDouble)

  return theme
}
