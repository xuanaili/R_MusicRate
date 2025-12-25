// frontend-vue/src/main.js
import Vue from 'vue'
import App from './App.vue'
import axios from 'axios'

// 配置后端接口的基础地址（和后端启动的地址一致）
axios.defaults.baseURL = 'http://127.0.0.1:5000'
// 全局挂载axios，组件里可以用this.$axios调接口
Vue.prototype.$axios = axios

Vue.config.productionTip = false

new Vue({
  render: h => h(App)
}).$mount('#app')