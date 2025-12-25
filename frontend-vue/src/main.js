// src/main.js
import Vue from 'vue'
import App from './App.vue'
import axios from 'axios'
// 新增：导入路由
import VueRouter from 'vue-router'
// 导入登录页面和音乐页面
import LoginPage from './views/LoginPage.vue'
import MusicList from './views/MusicList.vue'
import RegisterPage from "@/views/RegisterPage.vue";
import AddAlbum from './views/AddAlbum.vue'



// 安装路由插件
Vue.use(VueRouter)

// 配置后端基础地址
axios.defaults.baseURL = 'http://127.0.0.1:5000'

// ========== 新增：请求拦截器（所有请求自动加token） ==========
axios.interceptors.request.use(
  config => {
    // 从本地取token，有就加到请求头里
    const token = localStorage.getItem('token')
    if (token) {
      config.headers.Authorization = token
    }
    return config
  },
  error => {
    return Promise.reject(error)
  }
)

// ========== 新增：响应拦截器（统一处理登录过期） ==========
axios.interceptors.response.use(
  response => {
    return response
  },
  error => {
    // 如果后端返回401（未登录/登录过期），跳回登录页
    if (error.response && error.response.status === 401) {
      localStorage.removeItem('token')  // 清空无效token
      localStorage.removeItem('username')
      alert(error.response.data.msg)
      router.push('/login')  // 跳登录页
    }
    return Promise.reject(error)
  }
)

// 挂载axios
Vue.prototype.$axios = axios
Vue.config.productionTip = false

// ========== 新增：配置路由规则 ==========
const router = new VueRouter({
  routes: [
    { path: '/', redirect: '/login' },  // 默认跳登录页
    { path: '/login', component: LoginPage },  // 登录页
    { path: '/register', component: RegisterPage },  // 新增：注册页
    { path: '/music', component: MusicList },   // 音乐列表页
    { path: '/add-album', component: AddAlbum } //音乐添加页
  ]
})

// 启动Vue（挂载路由）
new Vue({
  router,  // 加路由
  render: h => h(App)
}).$mount('#app')