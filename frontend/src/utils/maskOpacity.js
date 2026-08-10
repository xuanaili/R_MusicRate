// MusicRate/frontend/src/utils/maskOpacity.js 蒙版透明度工具（v0.7 P1/P2）
// 取值区间 0-60%，默认 25%（对应历史 rgba(255,255,255,0.25)）
// 由 localStorage 持久化，启动时全局恢复，AppearancePanel 调节
export const MASK_MIN = 0
export const MASK_MAX = 60
export const MASK_DEFAULT = 25

// 读取已保存的蒙版透明度（无/越界时回退默认 25）
export function getSavedMaskOpacity() {
  const saved = parseInt(localStorage.getItem('maskOpacity'), 10)
  if (!isNaN(saved) && saved >= MASK_MIN && saved <= MASK_MAX) {
    return saved
  }
  return MASK_DEFAULT
}

// 把当前蒙版透明度应用到全局 --mask-opacity（毛玻璃容器统一读取，含 WebHome/PlayerPlaylist/AlbumDetail）
export function applyMaskOpacity() {
  const val = getSavedMaskOpacity()
  document.documentElement.style.setProperty('--mask-opacity', (val / 100).toFixed(2))
  return val
}
