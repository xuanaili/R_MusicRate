# 前端路由与入口配置参考

## 一、技术栈

| 技术 | 版本 | 用途 |
|------|------|------|
| Vue | 2.6.14 | 核心框架 |
| Vue Router | 3.5.4 | 路由管理（hash模式） |
| Axios | 0.27.2 | HTTP请求 |
| ECharts | 5.4.3 | 气泡图可视化 |
| Vue CLI | 5.0.9 | 构建工具 |

---

## 二、路由配置

**位置**：`frontend/src/main.js`

**模式**：hash模式（`mode: 'hash'`），兼容移动端

### 路由表

| 路径 | 名称 | 组件 | 说明 |
|------|------|------|------|
| `/` | — | — | 重定向到 `/login` |
| `/login` | Login | LoginPage | 登录页 |
| `/register` | Register | RegisterPage | 注册页 |
| `/albumDetail` | MusicList | MusicList | 我的专辑列表 |
| `/add-album` | AddAlbum | AddAlbum | 添加专辑（侧边栏） |
| `/album/detail/:id` | albumDetail | AlbumDetail | 专辑详情（动态路由） |
| `/album-pool` | SearchAlbumPool | SearchAlbumPool | 公共池搜索 |
| `/album/pool/detail/:poolId` | AlbumPoolDetail | AlbumPoolDetail | 公共池专辑详情（懒加载） |
| `/album/pool/edit/:poolId` | EditPoolAlbum | EditPoolAlbum | 编辑公共池专辑 |
| `/webhome` | WebHome | WebHome | 发现音乐主页（懒加载） |
| `/tag-detail` | TagDetail | TagDetail | 标签详情页 |

### 懒加载组件

- `AlbumPoolDetail` — `() => import('@/views/AlbumPoolDetail.vue')`
- `WebHome` — `() => import('@/views/WebHome.vue')`

---

## 三、路由守卫

**位置**：`frontend/src/main.js` — `router.beforeEach()`

**需要认证的路由**：`WebHome, MusicList, AddAlbum, albumDetail, SearchAlbumPool, AlbumPoolDetail, EditPoolAlbum`

**逻辑**：
1. 检查目标路由是否在认证列表中
2. 检查 `localStorage.getItem('token')` 是否存在
3. 未认证 → 重定向到 `/login`
4. 已认证 → 放行

---

## 四、Axios配置

```javascript
axios.defaults.baseURL = 'http://localhost:5000'
axios.defaults.timeout = 10000
axios.defaults.withCredentials = true     // 跨域携带凭证
axios.defaults.crossDomain = true         // 手机端跨域支持
```

### 请求拦截器
- 自动从 `localStorage` 获取token
- 添加到 `Authorization` 请求头

### 响应拦截器
- 401响应 → 清除 `localStorage` → 弹出提示 → 跳转 `/login`
- 其他错误 → `Promise.reject(error)`

---

## 五、VueRouter导航重复错误修复

```javascript
const originalPush = VueRouter.prototype.push
VueRouter.prototype.push = function push(location) {
  return originalPush.call(this, location).catch(err => {
    if (err.name !== 'NavigationDuplicated') throw err
  })
}
```

---

## 六、localStorage存储项

| Key | 值 | 说明 |
|-----|-----|------|
| `token` | UUID字符串 | 登录令牌 |
| `username` | 用户名 | 显示用 |
| `is_admin` | "1"/"0" | 管理员标识 |
| `user_id` | 用户ID字符串 | 用户唯一标识 |
| `persistCoverBg` | URL | 持久化背景图URL |
| `persistMainColor` | 颜色值 | 持久化主题色 |
| `persistMainColorDark` | 颜色值 | 持久化深色主题色 |
| `persistMainColorDarkDouble` | 颜色值 | 持久化双重深色主题色 |
| `targetMainTab` | tab名 | 跨页面Tab状态传递 |
| `targetSubTab` | tab名 | 跨页面SubTab状态传递 |

---

## 七、开发命令

```bash
# 在 frontend/ 目录下
npm run serve     # 开发服务器 http://0.0.0.0:8080
npm run build     # 生产构建
npm run lint      # ESLint检查
```

**注意**：`serve` 命令绑定 `0.0.0.0:8080`，允许手机通过局域网IP访问。
