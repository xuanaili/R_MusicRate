# 案例：搜索输入框被 Chrome 自动填入登录用户名（readonly 方案根治）

## 一、案例基本信息

- 问题场景分类：前端浏览器自动填充（Chrome 用户名 autofill 误判非登录输入框）
- 产生时间：2026-08-11
- 项目模块：前端搜索输入框（MusicList / SearchAlbumPool / TagDetail / MusicSpecial）
- 相似问题判定特征（用于下次自动识别同类问题）：
  1. 刷新或组件重建后，某个**纯文本输入框**被自动填入登录用户名
  2. 该输入框无 `name`/`id`/`autocomplete` 等任何表单信号（仅 `v-model` + `placeholder`）
  3. `autocomplete="off"` 无效
  4. `autocomplete="new-password"` 也无效
  5. 输入框所在页面不包含密码框（非登录页，Chrome 按启发式猜测用户名框）

## 二、原始问题描述

专辑详情页点击「返回专辑列表」后，「搜索专辑类型/标签」输入框会自动填入用户名；刷新后点击「我的音乐 → 专辑列表」也必现。

排查结论：
- Vue 状态无泄漏：无 keep-alive，MusicList 每次导航全新创建，`tagKeyword` 数据只有初始化 `''` 和清空两处赋值；`username` 仅存于 `this.username`（展示用），从未写入搜索框；全项目无全局 mixin/directive 写入。
- 确认根因：**Chrome 启发式自动填充**。Chrome 自 2015 起对疑似登录字段无视 `autocomplete="off"`；对 `autocomplete="new-password"` 也偶有漏网。它把无 name/id 信号的纯文本输入框误判为用户名框，刷新/挂载时自动填入已保存的登录账号。

## 三、优化复盘（本次流程浪费与快速命中）

**浪费的轮次：**
1. 第一版用 `autocomplete="off"` —— Chrome 对疑似登录字段**有意无视**该值（防止网站禁用密码管理器），注定无效，白跑一轮。
2. 第二版用 `autocomplete="new-password"` —— 是社区公认常见方案，但在用户 Chrome 上仍无效（个别版本启发式激进），再白跑一轮。
3. 真正该第一步就走 `readonly` 挂载方案：Chrome 对 **readonly 字段一律不自动填充**，这是唯一确定有效的阻断点。
4. 附带教训：两次"修复无效"很可能是用户**没有硬刷新**、还在跑旧 bundle。让用户验证前必须强调 Ctrl+Shift+R。

**快速命中清单：**
1. 可复用文件：`frontend/src/directives/noAutofill.js`（已全局注册），任何输入框被自动填充时直接加 `v-no-autofill` 即可，无需再写逻辑。
2. 排查起点：先 `grep` 该字段的 `v-model`/`username` 赋值排除代码写入，再判定为浏览器自动填充。
3. 若 readonly 方案仍被填充 → 大概率是**第三方插件**（密码管理器/填表扩展），给输入框加随机 `name` 让启发式匹配失败，或禁用扩展验证。

## 四、最终解决方案 / 改造步骤

1. 新建 `frontend/src/directives/noAutofill.js`：指令在元素挂载（`inserted`）时置 `el.readOnly = true`，并在 `focus`/`mousedown` 事件上各挂一个 `{ once: true }` 监听器，首次聚焦/点击时移除 readonly 恢复可编辑。
2. 在 `frontend/src/main.js` 全局注册：`Vue.directive('no-autofill', noAutofill)`。
3. 给全部搜索输入框加 `v-no-autofill`（本次 7 处）：MusicList×2、SearchAlbumPool×2、TagDetail×1、MusicSpecial×2。
4. 保留 `autocomplete="new-password"` 作为 Firefox/Safari 的额外防线（这些浏览器尊重 autocomplete）。
5. 验证：用户硬刷新（Ctrl+Shift+R）→ 刷新进专辑列表 → 确认搜索框为空 → 点入可正常输入。

## 五、关键代码 / 配置（可直接复用）

```js
// frontend/src/directives/noAutofill.js
export default {
  inserted(el) {
    el.readOnly = true
    const enable = () => { el.readOnly = false }
    el.addEventListener('focus', enable, { once: true })
    el.addEventListener('mousedown', enable, { once: true })
  }
}
```

```js
// frontend/src/main.js
import noAutofill from '@/directives/noAutofill'
Vue.directive('no-autofill', noAutofill)
```

```html
<!-- 用法：加 v-no-autofill，可保留 autocomplete="new-password" 做兜底 -->
<input type="text" v-model="tagKeyword" placeholder="搜索专辑类型/标签" autocomplete="new-password" v-no-autofill>
```

## 六、踩坑点 & 注意事项（非常重要）

- **`autocomplete="off"` 对 Chrome 用户名启发式填充完全无效**（2015 年起官方有意忽略，防止禁用密码管理器），不要再用它当方案。
- **`autocomplete="new-password"` 大部分情况有效但不保证**，个别 Chrome 版本/激进启发式仍会填充；不可作为唯一防线。
- readonly 方案要点：`readonly` 字段仍可聚焦（区别于 `disabled`，disabled 不能聚焦），所以 `focus` 事件一定能触发、readonly 能及时解除。
- Vue 2 里 `:readonly="true"` 常量绑定在重渲染时不会重复写回 DOM（新旧 vnode 的 attrs 相等则跳过 patch），JS 里移除 readonly 可持久，不会被 Vue 改回。
- 监听器务必用 `{ once: true }`，否则解锁后仍挂着空操作监听，虽无害但不干净。
- **验证时用户必须硬刷新**：Vue 开发服务器会自动重编译，但浏览器缓存可能拦截新代码，导致"改了没生效"的假象。
- readonly 字段仍可选中复制（这点与 disabled 不同），对搜索框场景无副作用。

## 七、同类问题快速适配规则

【适配点1】项目里**新增的搜索/纯文本输入框**被自动填入用户名 → 直接加 `v-no-autofill`，无需改其他代码。
【适配点2】若某页面输入框是第三方插件（密码管理器/填表扩展）填充 → 加随机 `name`（如 `name="f_<random>"`）破坏启发式匹配；或在浏览器禁用扩展逐一验证来源。
【适配点3】后端/其他浏览器（Safari/Firefox）行为验证 → 依赖 `autocomplete="new-password"`，两者兼容。

---

相关案例：[[20260811_score_revert_stale_get_fix]]（同日另一个前端状态回退类 bug）。
