// MusicRate/frontend/src/main.js
import Vue from 'vue'
import App from './App.vue'
import axios from 'axios'
import VueRouter from 'vue-router'
// v0.7 P1：蒙版透明度启动时恢复（否则页面刷新后 --mask-opacity 丢失，毛玻璃样式与设置不一致）
import { applyMaskOpacity } from '@/utils/maskOpacity'
// 导入页面组件（统一用@别名，避免路径错误）
import LoginPage from '@/views/LoginPage.vue'
import MusicList from '@/components/myMusic/MusicList.vue'
import RegisterPage from '@/views/RegisterPage.vue'
import AddAlbum from '@/components/sidebar/AddAlbum.vue'
import AlbumDetail from '@/views/AlbumDetail.vue'
import SearchAlbumPool from '@/components/searchMusic/SearchAlbumPool.vue'
// ========== 核心新增：导入编辑页组件 ==========
import EditPoolAlbum from '@/components/sidebar/EditPoolAlbum.vue'
import TagDetail from "@/views/TagDetail.vue";
// ========== 新增结束 ==========

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
  mode: 'hash', // 强制hash模式，✅ 手机访问必开这个，不会有路径404问题，保留！
  routes: [
    { path: '/', redirect: '/login' },
    { path: '/login', name: 'Login', component: LoginPage },
    { path: '/register', name: 'Register', component: RegisterPage },
    { path: '/albumDetail', name: 'MusicList', component: MusicList },
    { path: '/add-album', name: 'AddAlbum', component: AddAlbum },
    { path: '/album/detail/:id', name: 'albumDetail', component: AlbumDetail }, // 动态参数路由
    {
      path: '/album-pool',
      name: 'SearchAlbumPool',
      component: SearchAlbumPool
    },
    {
      path: '/album/pool/detail/:poolId',
      name: 'AlbumPoolDetail',
      component: () => import('@/views/AlbumPoolDetail.vue')
    },
    {
      path: '/album/pool/edit/:poolId',
      name: 'EditPoolAlbum',
      component: EditPoolAlbum,
      meta: { requiresAuth: true }
    },
    // ========== 新增WebHome主页路由【核心】 ==========
    { path: '/webhome', name: 'WebHome', component: () => import('@/views/WebHome.vue') },



          {
      path: '/tag-detail',
      name: 'TagDetail',
      component: TagDetail,
      meta: {
        title: '标签详情'
      }
    }

  ]
})

// ========== 新增：全局路由守卫 ==========
router.beforeEach((to, from, next) => {
  const authRequired = ['WebHome','MusicList', 'AddAlbum', 'albumDetail', 'SearchAlbumPool', 'AlbumPoolDetail', 'EditPoolAlbum']
  const hasToken = !!localStorage.getItem('token')
  if (authRequired.includes(to.name) && !hasToken) {
    if (from.name !== 'Login') {
      next('/login')
    } else {
      next(false)
    }
  } else {
    next()
  }
})

// ========== ✅✅✅ 核心修改点 1 (重中之重！手机访问必改) ==========
// 原地址：axios.defaults.baseURL = 'http://127.0.0.1:5000' → 手机永远访问不到
// 修改为：你的【电脑连手机热点后的内网IP】+ 后端端口5000
// ✅ 正确配置

// axios.defaults.baseURL = 'http://192.168.0.105:5000'
axios.defaults.baseURL = 'http://localhost:5000'
axios.defaults.timeout = 10000
axios.defaults.withCredentials = true // ✅ 保留，后端需要这个接收token
axios.defaults.crossDomain = true; // ✅✅✅ 新增这一行，解决手机端跨域请求拦截问题
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

// 响应拦截器：优化401处理
// ⚠️ 铁律：401 只清【认证相关键】，绝不能用 localStorage.clear()
// （否则会把 persistMainColor / persistCoverBg / maskOpacity 等用户偏好一并清掉，导致主题/蒙版丢失）
const AUTH_LOCALSTORAGE_KEYS = ['token', 'username', 'user_id', 'is_admin', 'is_vip', 'avatar', 'level']
axios.interceptors.response.use(
  response => response,
  error => {
    if (error.response) {
      const { status, data } = error.response
      if (status === 401) {
        AUTH_LOCALSTORAGE_KEYS.forEach(k => localStorage.removeItem(k))
        if (router.currentRoute.name !== 'Login') {
          alert(data.msg || '登录已过期，请重新登录')
          router.replace('/login')
        }
      }
    }
    return Promise.reject(error)
  }
)

// 挂载axios
Vue.prototype.$axios = axios

// v0.7 P1：蒙版透明度启动时从 localStorage 恢复
applyMaskOpacity()

// ========== 3. 启动Vue ==========
new Vue({
  router,
  render: h => h(App)
}).$mount('#app')