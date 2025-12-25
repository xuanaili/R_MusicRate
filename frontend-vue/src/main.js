// src/main.js
import Vue from 'vue'
import App from './App.vue'
import axios from 'axios'
import VueRouter from 'vue-router'
// 导入页面组件
import LoginPage from './views/LoginPage.vue'
import MusicList from './views/MusicList.vue'
import RegisterPage from "@/views/RegisterPage.vue";
import AddAlbum from './views/AddAlbum.vue'
import AlbumDetail from './views/AlbumDetail.vue'

// 安装插件
Vue.use(VueRouter)
Vue.config.productionTip = false

// ========== 1. 先定义路由（关键！） ==========
const router = new VueRouter({
  mode: 'hash', // 强制hash模式，避免路径问题
  routes: [
    { path: '/', redirect: '/login' },
    { path: '/login', component: LoginPage },
    { path: '/register', component: RegisterPage },
    { path: '/music', component: MusicList },
    { path: '/add-album', component: AddAlbum },
    { path: '/album/detail/:id', component: AlbumDetail } // 动态参数路由
  ]
})

// ========== 2. 配置axios ==========
axios.defaults.baseURL = 'http://127.0.0.1:5000'
axios.defaults.timeout = 10000 // 增加超时时间

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

// 响应拦截器：处理401（此时router已定义）
axios.interceptors.response.use(
  response => response,
  error => {
    if (error.response && error.response.status === 401) {
      localStorage.clear()
      alert(error.response.data.msg || '登录已过期，请重新登录')
      router.push('/login') // 此时router已定义
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