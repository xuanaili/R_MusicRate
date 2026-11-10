// MusicRate/frontend/src/main.js
import Vue from 'vue'
import App from './App.vue'
import axios from 'axios'
import VueRouter from 'vue-router'
// v0.7 P1：蒙版透明度启动时恢复（否则页面刷新后 --mask-opacity 丢失，毛玻璃样式与设置不一致）
import { applyMaskOpacity } from '@/utils/maskOpacity'
// 阻断浏览器把已保存用户名自动填充进搜索输入框（Chrome 无视 autocomplete=off/new-password）
import noAutofill from '@/directives/noAutofill'
// v0.7 修复：启动时修复持久化主题色的 transparent 坏值（一次性写回默认色，避免文字/图表透明）
import { getSavedTheme } from '@/utils/themeColor'
// v0.7.1 P0：全局消息提示（toast + 升级横幅），挂载为 Vue.prototype.$message
import message from '@/utils/message'
// 后端地址动态解析 + 响应里写死的本机媒体地址改写（局域网/手机访问用）
import { apiOrigin, normalizeBackendUrls } from '@/utils/apiBase'
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

// 全局注册：v-no-autofill 阻断浏览器用户名/密码自动填充
Vue.directive('no-autofill', noAutofill)

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

// ========== 后端地址：跟随页面访问的主机，不再写死 localhost ==========
// 原来写死 'http://localhost:5000'，手机（http://192.168.19.139:8080）打开时
// localhost 指向手机自己 → 登录请求发不出去，表现为“服务异常/连接服务器失败”。
// 现在由 apiOrigin() 自动推导：本机 → localhost:5000；手机/局域网 → 同一主机的 5000 端口。
// 需要指向别的机器时在控制台设置 localStorage.backend_origin（见 utils/apiBase.js 说明）
axios.defaults.baseURL = apiOrigin()
axios.defaults.timeout = 10000
axios.defaults.withCredentials = true // ✅ 保留，后端需要这个接收token
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
  response => {
    // 数据库里存的是 http://localhost:5000/... 的封面/缩略图/音频绝对地址，
    // 手机用局域网 IP 访问时 localhost 是手机自己 → 统一改写成当前后端地址，否则封面和音频全挂
    if (response && response.data) normalizeBackendUrls(response.data)
    return response
  },
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
// v0.7.1 P0：挂载全局消息提示（既有 this.$message?.xxx 可选链调用从此真正生效）
Vue.prototype.$message = message

// v0.7 P1：蒙版透明度启动时从 localStorage 恢复
applyMaskOpacity()
// v0.7 修复：启动时修复持久化主题色的 transparent 坏值（一次性写回默认色，避免文字/图表透明）
getSavedTheme()

// ========== 3. 启动Vue ==========
new Vue({
  router,
  render: h => h(App)
}).$mount('#app')