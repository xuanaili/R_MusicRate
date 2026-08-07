# 案例：Axios拦截器与路由守卫模式

## 基本信息

- **案例编号**：20260807_axios_router_guard
- **关键词**：Axios拦截器、路由守卫、Token认证、401处理、localStorage
- **适用场景**：前后端分离的SPA应用，Token认证模式

## 问题描述

MusicRate前端需要实现完整的认证流程：登录获取token → 每次请求携带token → token过期自动跳转登录页 → 未登录用户不能访问受保护页面。

## 核心需求

1. 自动携带token到每个请求
2. 401响应自动清除登录状态并跳转
3. 未登录用户无法访问受保护页面
4. 路由跳转不报重复导航错误

## 解决方案

### 1. 请求拦截器：自动加Token

```javascript
axios.interceptors.request.use(
  config => {
    const token = localStorage.getItem('token')
    if (token) {
      config.headers.Authorization = token
    }
    return config
  },
  error => Promise.reject(error)
)
```

### 2. 响应拦截器：401自动处理

```javascript
axios.interceptors.response.use(
  response => response,
  error => {
    if (error.response) {
      const { status, data } = error.response
      if (status === 401) {
        localStorage.clear()
        if (router.currentRoute.name !== 'Login') {
          alert(data.msg || '登录已过期，请重新登录')
          router.replace('/login')
        }
      }
    }
    return Promise.reject(error)
  }
)
```

### 3. 路由守卫：未登录拦截

```javascript
router.beforeEach((to, from, next) => {
  const authRequired = ['WebHome','MusicList','AddAlbum','albumDetail',
                        'SearchAlbumPool','AlbumPoolDetail','EditPoolAlbum']
  const hasToken = !!localStorage.getItem('token')
  if (authRequired.includes(to.name) && !hasToken) {
    next('/login')
  } else {
    next()
  }
})
```

### 4. 路由重复导航修复

```javascript
const originalPush = VueRouter.prototype.push
VueRouter.prototype.push = function push(location) {
  return originalPush.call(this, location).catch(err => {
    if (err.name !== 'NavigationDuplicated') throw err
  })
}
```

### 5. 登录时存储认证信息

```javascript
// LoginPage.vue
if (res.data.code === 200) {
  localStorage.setItem('token', res.data.data.token)
  localStorage.setItem('username', res.data.data.username)
  localStorage.setItem('is_admin', res.data.data.is_admin.toString())
  localStorage.setItem('user_id', res.data.data.user_id.toString())
  this.$router.push('/webhome')
}
```

## 踩坑记录

1. **401死循环**：401响应时跳转/login，但/login路由守卫又触发 → 只在非Login页才跳转
2. **重复导航报错**：登录后push到/webhome，但用户已在/webhome → 使用NavigationDuplicated修复
3. **Token过期但不跳转**：部分组件使用原始axios而非this.$axios → 统一使用this.$axios
4. **localStorage类型问题**：`is_admin`存为数字但localStorage只存字符串 → 使用 `.toString()` 转换
5. **刷新页面丢失状态**：Vuex状态在刷新后丢失 → 使用localStorage持久化关键数据

## 适配规则

- 所有API请求必须通过 `this.$axios` 调用，确保拦截器生效
- 新增受保护路由必须添加到 `authRequired` 数组
- 登录成功后存储所有必要信息到localStorage
- 退出登录时使用 `localStorage.clear()` 清除所有数据
- 路由跳转前检查当前路由避免重复导航
