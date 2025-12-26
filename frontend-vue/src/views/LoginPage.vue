<!--MusicRate/frontend-vue/src/views/LoginPage.vue-->
<template>
  <div class="login-container">
    <h2>用户登录</h2>
    <div class="form-item">
      <label>账号：</label>
      <input v-model="username" type="text" placeholder="请输入账号">
    </div>
    <div class="form-item">
      <label>密码：</label>
      <input v-model="password" type="password" placeholder="请输入密码">
    </div>
    <button @click="handleLogin" :disabled="loading">
      {{ loading ? '登录中...' : '登录' }}
    </button>
    <div class="error-tip" v-if="errorMsg">{{ errorMsg }}</div>
    <div class="go-register">
      没有账号？<span @click="goRegister">立即注册</span>
    </div>
  </div>
</template>

<script>
export default {
  name: 'LoginPage',
  data() {
    return {
      username: "",
      password: "",
      errorMsg: "",
      loading: false  // 新增：登录加载状态，防止重复点击
    };
  },
  methods: {
    handleLogin() {
      // 1. 清空之前的错误提示
      this.errorMsg = "";
      // 2. 前端严格校验（去除空格，避免空字符串提交）
      const username = this.username.trim();
      const password = this.password.trim();

      if (!username) {
        this.errorMsg = "账号不能为空！";
        return;
      }
      if (!password) {
        this.errorMsg = "密码不能为空！";
        return;
      }

      // 3. 设置加载状态，防止重复提交
      this.loading = true;

      // 4. 调用后端登录接口
      this.$axios
        .post("/api/login", { username, password })
        .then(res => {
          this.loading = false; // 关闭加载
          // 5. 处理后端响应（严格判断code）
          if (res.data && res.data.code === 200) {
            // 登录成功：保存token和用户名,存储管理员标识
            localStorage.setItem("token", res.data.data.token);
            localStorage.setItem("username", res.data.data.username);
            // 优化后：显式存储为字符串 "1"/"0"，确保类型统一
            localStorage.setItem("is_admin", res.data.data.is_admin.toString());
            // 存一下用户id
            localStorage.setItem("user_id", res.data.data.user_id.toString());
            // 跳转到音乐评分页面
            this.$router.push("/music");
          } else {
            // 后端返回非200的业务错误（如参数错误）
            this.errorMsg = res.data?.msg || "登录失败，请重试！";
          }
        })
        .catch(err => {
          this.loading = false; // 关闭加载
          console.error("登录失败：", err);
          // 6. 精准捕获不同类型的错误
          if (err.response) {
            // 有响应但状态码非200（重点：捕获401账号密码错误）
            const { code, msg } = err.response.data || {};
            if (code === 401) {
              this.errorMsg = msg || "账号或密码错误！";
              // 清空密码框，提升体验
              this.password = "";
            } else if (code === 400) {
              this.errorMsg = msg || "账号或密码格式错误！";
            } else {
              this.errorMsg = "服务器错误，请稍后重试！";
            }
          } else if (err.request) {
            // 无响应（后端没启动/网络问题）
            this.errorMsg = "连接服务器失败，请检查后端是否启动！";
          } else {
            // 其他错误（如请求配置错误）
            this.errorMsg = "登录出错，请重试！";
          }
        });
    },
    goRegister() {
      // 优化：跳转到注册页前，先判断是否已经在注册页（避免重复导航报错）
      if (this.$route.path !== '/register') {
        this.$router.push("/register");
      }
    }
  }
};
</script>

<style scoped>
.login-container {
  width: 400px;
  margin: 100px auto;
  padding: 20px;
  border: 1px solid #eee;
  border-radius: 8px;
  text-align: center;
}
.form-item {
  margin: 15px 0;
  text-align: left;
}
.form-item input {
  width: 100%;
  padding: 8px;
  margin-top: 5px;
  box-sizing: border-box;
}
button {
  width: 100%;
  padding: 10px;
  background: #42b983;
  color: white;
  border: none;
  border-radius: 4px;
  cursor: pointer;
  /* 禁用状态样式 */
  opacity: 1;
  transition: opacity 0.3s;
}
button:disabled {
  opacity: 0.7;
  cursor: not-allowed;
}
.error-tip {
  color: red;
  margin-top: 10px;
}
.go-register {
  margin-top: 15px;
  color: #666;
}
.go-register span {
  color: #42b983;
  cursor: pointer;
}
</style>