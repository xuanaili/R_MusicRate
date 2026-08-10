# MusicRate 前端颜色工具函数统一管理（utils/color.js）

> 2026-08-10 从 BookRate 迁移（BookRate 已完成同类重构：8 组件 rgba 去重）。**MusicRate 本次仅沉淀方法与排查结果，重构留待以后**。
> 现状：MusicRate 的颜色工具重复程度远低于 BookRate 重构前，改动面小，按需择机执行。

## 1. MusicRate 现状排查（2026-08-10）

| 项 | 位置 | 说明 |
|---|---|---|
| `hexToRgb(hex)` | `views/AlbumDetail.vue`、`components/albumDetail/AlbumCommentSection.vue` | **重复 2 处**，返回 `{r, g, b}` |
| 半透明渐变 | `views/AlbumDetail.vue`（1951/1953/1975 行） | 内联 `rgba(${this.hexToRgb(...).r}, ...)` 字符串拼接 |
| 其余 `rgba(...)` | 大量 CSS 字面量 | 是 CSS 原生写法，**不属于** JS 工具函数重复，无需合并 |

对比 BookRate 重构前（8 个组件各自定义 `rgba()`/`getRgbValue`/`darken`/`hexToRgba`），MusicRate 的重复点只有 `hexToRgb` 一处，风险低。

## 2. 推荐公共实现 `frontend/src/utils/color.js`

统一健壮版（参考 BookRate 已验证实现）：

- `rgba(hex, alpha = 1)`：去 `#` → `#RGB` 简写展开 → 长度/NaN 校验 → 非法回退 `rgba(0,0,0,alpha)`
- `getRgbValue(hex)`：返回 `"r, g, b"` 字符串（CSS 变量 `--xxx-rgb` 通道），非法回退 `"255, 255, 255"`
- `darken(hex, amount = 0.1)`：各通道减 `floor(255*amount)`，下限 0，非法原样返回
- `hexToRgb(hex)`：返回 `{r, g, b}` 对象（合并现有 2 处重复实现）

三个函数均支持 `#` 可省略、大写 hex。

## 3. Vue 2 Options API 接入模式

MusicRate 是 Vue 2（Options API），把导入函数挂进 `methods`，模板 `rgba(...)` 与 `this.rgba(...)` 均解析到实例方法：

```js
import { rgba, getRgbValue, hexToRgb } from '@/utils/color'

export default {
  methods: {
    rgba, getRgbValue, hexToRgb,
  }
}
```

**注意**：导入名与方法名同名会递归调用，需用别名导入 + 方法包装（参照 `cover.js` 在 AlbumItem/AlbumPoolItem/MusicSpecial 的接入模式）：
```js
import { rgba as rgbaUtil } from '@/utils/color'
// methods: { rgba(hex, alpha) { return rgbaUtil(hex, alpha) } }
```

## 4. 未来重构接入清单（待执行）

- [ ] 新建 `frontend/src/utils/color.js`（rgba/getRgbValue/darken/hexToRgb）
- [ ] `views/AlbumDetail.vue`：`hexToRgb` 方法删除，改 import
- [ ] `components/albumDetail/AlbumCommentSection.vue`：`hexToRgb` 方法删除，改 import
- [ ] `views/AlbumDetail.vue` 内联渐变：改用 `rgba(hex, alpha)` 或 `getRgbValue` 拼接
- [ ] 验证：`npm run lint` + `npm run build` 通过

## 5. 排查命令（下次直接用）

```bash
grep -rn "hexToRgb\|const rgba\|rgba(hex" frontend/src --include="*.vue" --include="*.js"
```
注意 `rgba(` 会混入大量 CSS 字面量，需按 JS 调用模式（`rgba(hex`/`rgba(this.`）二次过滤。
