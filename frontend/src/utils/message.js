// src/utils/message.js
// 轻量全局消息提示（toast）+ 升级横幅；挂载到 Vue.prototype.$message
// 背景：本项目无 UI 库，既有 this.$message?.success(...) 全是可选链静默 no-op；
// 挂载后这些调用真正生效，并新增升级横幅（levelUp）用于 v0.7.1 等级反馈
let container = null
let styleInjected = false

function injectStyle() {
  if (styleInjected || typeof document === 'undefined') return
  styleInjected = true
  const style = document.createElement('style')
  style.textContent = `
    .mr-toast-container{position:fixed;top:20px;left:50%;transform:translateX(-50%);z-index:99999;display:flex;flex-direction:column;align-items:center;gap:10px;pointer-events:none}
    .mr-toast{padding:9px 18px;border-radius:8px;font-size:13px;color:#fff;box-shadow:0 4px 16px rgba(0,0,0,.18);opacity:0;transform:translateY(-12px);transition:all .28s ease;max-width:80vw;white-space:nowrap;overflow:hidden;text-overflow:ellipsis}
    .mr-toast.show{opacity:1;transform:translateY(0)}
    .mr-toast-success{background:rgba(34,139,34,.92)}
    .mr-toast-info{background:rgba(64,158,255,.92)}
    .mr-toast-warning{background:rgba(255,152,0,.92)}
    .mr-toast-error{background:rgba(220,38,38,.92)}
    .mr-levelup{display:flex;flex-direction:column;align-items:center;gap:4px;padding:14px 28px;border-radius:12px;background:linear-gradient(135deg,#f6d365 0%,#fda085 100%);color:#7a4a00;box-shadow:0 8px 30px rgba(0,0,0,.25);opacity:0;transform:scale(.85);transition:all .32s cubic-bezier(.34,1.56,.64,1)}
    .mr-levelup.show{opacity:1;transform:scale(1)}
    .mr-levelup-badge{font-size:20px;font-weight:700}
    .mr-levelup-title{font-size:13px}
  `
  document.head.appendChild(style)
}

function ensureContainer() {
  injectStyle()
  if (!container) {
    container = document.createElement('div')
    container.className = 'mr-toast-container'
    document.body.appendChild(container)
  }
  return container
}

function show(type, msg, opts = {}) {
  ensureContainer()
  const el = document.createElement('div')
  el.className = `mr-toast mr-toast-${type}`
  el.textContent = msg
  ensureContainer().appendChild(el)
  // 触发过渡动画
  requestAnimationFrame(() => el.classList.add('show'))
  const duration = opts.duration || 2400
  setTimeout(() => {
    el.classList.remove('show')
    setTimeout(() => el.remove(), 300)
  }, duration)
}

// 升级横幅：更大、更醒目（等级经验反馈）
function levelUp(level, title) {
  ensureContainer()
  const el = document.createElement('div')
  el.className = 'mr-levelup'
  const badge = document.createElement('div')
  badge.className = 'mr-levelup-badge'
  badge.textContent = `🎉 升级至 Lv.${level}`
  const titleEl = document.createElement('div')
  titleEl.className = 'mr-levelup-title'
  titleEl.textContent = title || ''
  el.appendChild(badge)
  el.appendChild(titleEl)
  ensureContainer().appendChild(el)
  requestAnimationFrame(() => el.classList.add('show'))
  setTimeout(() => {
    el.classList.remove('show')
    setTimeout(() => el.remove(), 400)
  }, 4500)
}

const message = {
  info: msg => show('info', msg),
  success: msg => show('success', msg),
  warning: msg => show('warning', msg),
  error: msg => show('error', msg),
  levelUp
}

export default message
