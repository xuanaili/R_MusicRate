// MusicRate/frontend-vue/src/main.js
import Vue from 'vue'
import App from './App.vue'
import axios from 'axios'
import VueRouter from 'vue-router'
// 导入页面组件（统一用@别名，避免路径错误）
import LoginPage from '@/views/LoginPage.vue'
import MusicList from '@/views/MusicList.vue'
import RegisterPage from '@/views/RegisterPage.vue'
import AddAlbum from '@/views/AddAlbum.vue'
import AlbumDetail from '@/views/AlbumDetail.vue'
import SearchAlbumPool from '@/components/SearchAlbumPool.vue' // 补充.vue后缀

// 安装插件
Vue.use(VueRouter)
Vue.config.productionTip = false

// ========== 核心修复1：拦截路由重复导航错误（解决登录/注册跳转崩溃） ==========
const originalPush = VueRouter.prototype.push
VueRouter.prototype.push = function push(location) {
  return originalPush.call(this, location).catch(err => {
    // 只忽略"重复导航"错误，其他错误正常抛出
    if (err.name !== 'NavigationDuplicated') {
      throw err
    }
  })
}

// ========== 1. 定义路由（修正所有路径问题） ==========
const router = new VueRouter({
  mode: 'hash', // 强制hash模式，避免路径问题
  routes: [
    { path: '/', redirect: '/login' },
    { path: '/login', name: 'Login', component: LoginPage },
    { path: '/register', name: 'Register', component: RegisterPage },
    { path: '/music', name: 'MusicList', component: MusicList },
    { path: '/add-album', name: 'AddAlbum', component: AddAlbum },
    { path: '/album/detail/:id', name: 'AlbumDetail', component: AlbumDetail }, // 动态参数路由
    // 专辑搜索池路由（已修正：补充.vue后缀）
    {
      path: '/album-pool',
      name: 'SearchAlbumPool',
      component: SearchAlbumPool
    },
    // 公共专辑详情路由（核心修正：路径改为@/views/）
    {
      path: '/album/pool/detail/:poolId',
      name: 'AlbumPoolDetail',
      // 正确路径：@代表src目录，views在src下
      component: () => import('@/views/AlbumPoolDetail.vue')
    }
  ]
})

// ========== 新增：全局路由守卫（补充SearchAlbumPool和AlbumPoolDetail需要登录） ==========
router.beforeEach((to, from, next) => {
  // 需要登录的页面名称列表（补充新增的页面）
  const authRequired = ['MusicList', 'AddAlbum', 'AlbumDetail', 'SearchAlbumPool', 'AlbumPoolDetail']
  // 判断是否已登录（token存在）
  const hasToken = !!localStorage.getItem('token')

  // 逻辑优化：避免登录页/注册页重复跳转
  if (authRequired.includes(to.name) && !hasToken) {
    // 只有当前不在登录页时，才跳登录页
    if (from.name !== 'Login') {
      next('/login')
    } else {
      next(false) // 阻止跳转，避免重复导航
    }
  } else {
    next() // 其他情况正常放行
  }
})

// ========== 2. 配置axios ==========
axios.defaults.baseURL = 'http://127.0.0.1:5000'
axios.defaults.timeout = 10000 // 增加超时时间
axios.defaults.withCredentials = true // 补充：允许跨域携带cookie（后端需要）

// 请求拦截器：自动加token
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

// 响应拦截器：优化401处理（避免重复弹窗/跳转）
axios.interceptors.response.use(
  response => response,
  error => {
    if (error.response) {
      const { status, data } = error.response
      // 处理401未登录/登录过期
      if (status === 401) {
        // 清空本地存储
        localStorage.clear()
        // 只有当前不在登录页时，才提示并跳转
        if (router.currentRoute.name !== 'Login') {
          alert(data.msg || '登录已过期，请重新登录')
          router.replace('/login') // 改用replace，避免历史记录
        }
      }
    }
    return Promise.reject(error)
  }
)

// 挂载axios
Vue.prototype.$axios = axios

// ========== 3. 启动Vue ==========
new Vue({
  router, // 挂载路由
  render: h => h(App)
}).$mount('#app')