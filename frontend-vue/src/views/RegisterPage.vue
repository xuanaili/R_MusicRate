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
    <button @click="handleRegister">注册</button>
    <div class="error-tip" v-if="errorMsg">{{ errorMsg }}</div>
    <!-- 新增：跳登录页的链接 -->
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
      errorMsg: ""
    };
  },
  methods: {
    // 注册逻辑
    handleRegister() {
      this.errorMsg = "";
      // 1. 空值校验
      if (!this.username || !this.password) {
        this.errorMsg = "用户名和密码不能为空！";
        return;
      }
      // 2. 调用后端注册接口
      this.$axios
        .post("/api/register", {
          username: this.username,
          password: this.password
        })
        .then(res => {
          if (res.data.code === 200) {
            alert("注册成功！即将跳转到登录页");
            this.$router.push("/login");  // 注册成功跳登录
          } else {
            this.errorMsg = res.data.msg;  // 显示用户名重复等错误
          }
        })
        .catch(err => {
          console.error("注册失败：", err);
          this.errorMsg = "注册失败，请检查后端是否启动！";
        });
    },
    // 跳登录页
    goLogin() {
      this.$router.push("/login");
    }
  }
};
</script>

<style scoped>
/* 样式和登录页几乎一致，仅微调标题 */
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