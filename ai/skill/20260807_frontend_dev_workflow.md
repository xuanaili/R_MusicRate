# 前端开发思维流程与检查清单

## 一、新增页面流程

### 思考步骤
1. 确定路由路径和名称
2. 在 `main.js` 中注册路由
3. 是否需要认证？→ 添加到 `authRequired` 数组
4. 是否需要主题色？→ 接收 `mainColor`/`mainColorDark`/`mainColorDarkDouble` props
5. 是否需要背景图？→ emit `@sendCoverBg`
6. 是否在WebHome的Tab中展示？→ 添加到对应Tab区域

### 检查清单
- [ ] 路由已在 `main.js` 中注册
- [ ] 认证路由已添加到 `authRequired` 数组
- [ ] 主题色props已声明和传递
- [ ] API调用已附带 `Authorization` 请求头
- [ ] 响应格式按 `{code, msg, data}` 处理
- [ ] 错误处理覆盖网络错误和业务错误

## 二、新增子组件流程

### 思考步骤
1. 确定所属功能目录（albumDetail/discoverMusic/myMusic/sidebar/item）
2. 确定与父组件的通信方式（props + $emit）
3. 是否需要主题色？→ 接收三个颜色props
4. 是否需要API调用？→ 使用 `this.$axios`
5. 是否需要侧边栏？→ 遵循侧边栏组件模式

### 检查清单
- [ ] 组件name属性已设置
- [ ] Props已声明类型和默认值
- [ ] $emit事件名使用kebab-case
- [ ] 主题色通过v-bind()绑定到CSS
- [ ] API调用有loading状态和错误处理
- [ ] 组件已注册到父组件components中

## 三、新增侧边栏组件流程

### 思考步骤
1. 确定是普通侧边栏还是DOM端口侧边栏
2. 普通侧边栏：标准visible/close模式
3. DOM端口侧边栏：需要uid后缀避免CSS冲突
4. 是否需要子侧边栏？→ 嵌套侧边栏模式

### 检查清单
- [ ] visible props已声明（Boolean, default: false）
- [ ] @close事件已emit
- [ ] 遮罩层点击关闭已实现
- [ ] 滑入动画已实现
- [ ] DOM端口模式：mounted/beforeDestroy已处理
- [ ] 表单重置方法已实现

## 四、主题色相关开发

### 思考步骤
1. 是否需要从封面提取颜色？→ 使用canvas采样
2. 颜色传递方向：子→父（@sendThemeColor）→ WebHome → localStorage
3. CSS中使用v-bind()绑定
4. 颜色变体：dark（×0.7）、darkDouble（×0.4）、white（混合白色）、whiteDouble

### 检查清单
- [ ] 三个颜色props已声明
- [ ] CSS中使用v-bind()而非硬编码颜色
- [ ] 颜色变更已持久化到localStorage
- [ ] 颜色提取函数已处理透明/无效图片

## 五、前后端联调

### 常见问题
1. **401错误** → 检查token是否过期、请求头是否包含Authorization
2. **CORS错误** → 检查后端CORS配置是否为 `origins=r".*"`
3. **数据格式错误** → 检查JSON字段是否已解析（可能返回字符串）
4. **评分为0** → 检查my_score是否为字符串格式需JSON.parse()
5. **标签不显示** → 检查标签格式是否为 `English【中文】`

### 注意事项
- 后端返回的JSON字段（tracks, my_score, tags等）可能是字符串，需手动解析
- 分页数据在 `res.data.data.pagination` 中
- 管理员判断通过 `localStorage.getItem('is_admin') === '1'`
- 跨页面Tab切换通过 `localStorage.setItem('targetMainTab', ...)` 实现
