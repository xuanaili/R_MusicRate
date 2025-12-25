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
    <button @click="handleLogin">登录</button>
    <div class="error-tip" v-if="errorMsg">{{ errorMsg }}</div>
    <!-- 新增：跳注册页的链接 -->
    <div class="go-register">
      没有账号？<span @click="goRegister">立即注册</span>
    </div>
  </div>
</template>

<script>
export default {
  name: 'LoginPage',  // 新增：多单词组件名
  data() {
    return {
      username: "",  // 绑定账号输入框
      password: "",  // 绑定密码输入框
      errorMsg: ""   // 登录失败提示
    };
  },
  methods: {
    handleLogin() {
      // 清空之前的错误提示
      this.errorMsg = "";
      // 校验账号密码是否为空
      if (!this.username || !this.password) {
        this.errorMsg = "账号和密码不能为空！";
        return;
      }
      // 调用后端登录接口
      this.$axios
        .post("/api/login", {
          username: this.username,
          password: this.password
        })
        .then(res => {
          if (res.data.code === 200) {
            // 登录成功：保存token到本地（localStorage），防止页面刷新丢失
            localStorage.setItem("token", res.data.data.token);
            localStorage.setItem("username", res.data.data.username);
            // 跳转到音乐评分页面
            this.$router.push("/music");
          } else {
            this.errorMsg = res.data.msg;
          }
        })
        .catch(err => {
          console.error("登录失败：", err);
          this.errorMsg = "登录失败，请检查后端是否启动！";
        });
    },
    // 跳注册页
    goRegister(){
    this.$router.push("/register");
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