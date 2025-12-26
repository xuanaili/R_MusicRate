<!--MusicRate/frontend-vue/src/views/RegisterPage.vue-->
<template>
  <div class="register-container">
    <h2>用户注册</h2>
    <div class="form-item">
      <label>用户名：</label>
      <input v-model="username" type="text" placeholder="请输入用户名">
    </div>
    <div class="form-item">
      <label>密码：</label>
      <input v-model="password" type="password" placeholder="请输入密码">
    </div>
    <button @click="handleRegister" :disabled="loading">
      {{ loading ? '注册中...' : '注册' }}
    </button>
    <div class="error-tip" v-if="errorMsg">{{ errorMsg }}</div>
    <div class="go-login">
      已有账号？<span @click="goLogin">立即登录</span>
    </div>
  </div>
</template>

<script>
export default {
  name: 'RegisterPage',
  data() {
    return {
      username: "",
      password: "",
      errorMsg: "",
      loading: false  // 新增：注册加载状态
    };
  },
  methods: {
    handleRegister() {
      this.errorMsg = "";
      // 1. 前端校验（去除空格）
      const username = this.username.trim();
      const password = this.password.trim();

      if (!username) {
        this.errorMsg = "用户名不能为空！";
        return;
      }
      if (!password) {
        this.errorMsg = "密码不能为空！";
        return;
      }

      // 2. 设置加载状态
      this.loading = true;

      // 3. 调用注册接口
      this.$axios
        .post("/api/register", { username, password })
        .then(res => {
          this.loading = false;
          if (res.data && res.data.code === 200) {
            // 注册成功：友好提示 + 跳转登录页（避免alert弹窗）
            this.$message?.success ? this.$message.success("注册成功！即将跳转到登录页") : alert("注册成功！即将跳转到登录页");
            // 优化：判断是否已在登录页，避免重复跳转
            if (this.$route.path !== '/login') {
              this.$router.push("/login");
            }
            // 清空输入框
            this.username = "";
            this.password = "";
          } else {
            // 业务错误（如用户名重复）
            this.errorMsg = res.data?.msg || "注册失败，请重试！";
          }
        })
        .catch(err => {
          this.loading = false;
          console.error("注册失败：", err);
          // 4. 精准捕获错误类型
          if (err.response) {
            const { msg } = err.response.data || {};
            this.errorMsg = msg || "注册失败，用户名已存在！";
          } else if (err.request) {
            this.errorMsg = "连接服务器失败，请检查后端是否启动！";
          } else {
            this.errorMsg = "注册出错，请重试！";
          }
        });
    },
    goLogin() {
      // 优化：避免重复跳转
      if (this.$route.path !== '/login') {
        this.$router.push("/login");
      }
    }
  }
};
</script>

<style scoped>
.register-container {
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
  margin-top: 10px;
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
.go-login {
  margin-top: 15px;
  color: #666;
}
.go-login span {
  color: #42b983;
  cursor: pointer;
}
</style>