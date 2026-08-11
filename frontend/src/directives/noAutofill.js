// 阻断浏览器（尤其 Chrome）把已保存的用户名/密码自动填充到非登录表单的纯文本输入框。
//
// 背景：Chrome 自 2015 起无视 autocomplete="off"，对疑似登录字段（无 name/id 信号的纯文本输入框）
//       启发式误判后仍会自动填入用户名；autocomplete="new-password" 也偶有漏网。
//       但 Chrome 永远不会自动填充 readonly 字段，因此本指令在元素挂载时置 readonly，
//       用户首次聚焦/点击时再移除，恢复可编辑。
//
// 用法：<input type="text" v-no-autofill ... />
export default {
  inserted(el) {
    el.readOnly = true
    const enable = () => { el.readOnly = false }
    // 用 { once: true }，触发一次后监听器自动移除，避免与后续输入产生干扰
    el.addEventListener('focus', enable, { once: true })
    el.addEventListener('mousedown', enable, { once: true })
  }
}
