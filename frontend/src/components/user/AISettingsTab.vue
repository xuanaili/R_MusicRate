<template>
  <div class="ai-settings-tab">
    <!-- 当前配置状态 -->
    <div class="ai-status" :style="statusStyle">
      <span v-if="status.has_key" class="status-dot" style="background: #22c55e"></span>
      <span v-else class="status-dot" style="background: #eab308"></span>
      <span class="status-text" :style="{ color: mainColorDarkDouble }">
        {{ status.has_key ? `已配置（${providerName(status.provider)}）` : '未配置 API 密钥' }}
      </span>
    </div>

    <p class="ai-hint" :style="{ color: mainColorDarkDouble }">
      配置密钥后，专辑详情页的「AI 助手」才会显示。密钥仅存于后端，前端不保存明文。
    </p>

    <!-- 配置表单 -->
    <div class="ai-form">
      <label class="ai-label" :style="{ color: mainColorDarkDouble }">AI 服务商</label>
      <select v-model="provider" class="ai-input" :style="inputStyle">
        <option value="deepseek">DeepSeek（国内直连，推荐）</option>
        <option value="openai">OpenAI</option>
      </select>

      <label class="ai-label" :style="{ color: mainColorDarkDouble }">API 密钥</label>
      <input
        v-model="apiKey"
        type="password"
        class="ai-input"
        :placeholder="status.has_key ? '已配置，输入新密钥可覆盖' : '请输入 API 密钥'"
        :style="inputStyle"
        autocomplete="new-password"
        v-no-autofill
      />

      <button class="ai-save-btn" :style="saveBtnStyle" :disabled="saving" @click="handleSave">
        {{ saving ? '保存中…' : (status.has_key ? '更新密钥' : '保存密钥') }}
      </button>
    </div>

    <!-- 今日用量 -->
    <div v-if="status.has_key" class="ai-quota" :style="{ color: mainColorDarkDouble }">
      <div class="quota-item">今日提问：{{ status.today_requests }} 次</div>
      <div class="quota-item">今日字符：{{ status.today_chars }}</div>
    </div>
  </div>
</template>

<script>
export default {
  name: 'AISettingsTab',
  props: {
    mainColor: { type: String, default: 'transparent' },
    mainColorDark: { type: String, default: 'transparent' },
    mainColorDarkDouble: { type: String, default: 'transparent' }
  },
  data() {
    return {
      status: {
        has_key: false,
        provider: 'deepseek',
        today_requests: 0,
        today_chars: 0
      },
      provider: 'deepseek',
      apiKey: '',
      saving: false
    }
  },
  computed: {
    statusStyle() {
      return { borderColor: this.mainColorDark }
    },
    inputStyle() {
      return {
        backgroundColor: 'rgba(255, 255, 255, 0.4)',
        color: this.mainColorDarkDouble,
        borderColor: 'rgba(255, 255, 255, 0.5)'
      }
    },
    saveBtnStyle() {
      return { backgroundColor: this.mainColorDark, borderColor: this.mainColorDark }
    }
  },
  created() {
    this.loadStatus()
  },
  methods: {
    providerName(key) {
      return ({ deepseek: 'DeepSeek', openai: 'OpenAI' }[key] || key)
    },
    loadStatus() {
      this.$axios.get('/api/ai/status').then(res => {
        if (res.data.code === 200) {
          const d = res.data.data
          this.status.has_key = !!d.has_key
          this.status.provider = d.provider || 'deepseek'
          this.status.today_requests = d.today_requests || 0
          this.status.today_chars = d.today_chars || 0
          if (d.provider) this.provider = d.provider
        }
      }).catch(err => {
        console.error('❌ 获取 AI 配置状态失败：', err)
      })
    },
    handleSave() {
      if (!this.apiKey.trim()) {
        this.showMsg('error', '请输入 API 密钥')
        return
      }
      this.saving = true
      this.$axios.post('/api/ai/key', {
        provider: this.provider,
        api_key: this.apiKey.trim(),
        is_enabled: true
      }).then(res => {
        if (res.data.code === 200) {
          this.showMsg('success', res.data.msg || '保存成功')
          this.apiKey = '' // 铁律：前端不保留明文
          this.loadStatus()
        } else {
          this.showMsg('error', res.data.msg || '保存失败')
        }
      }).catch(err => {
        console.error('❌ 保存 AI 密钥失败：', err)
        this.showMsg('error', (err.response && err.response.data && err.response.data.msg) || '保存失败，请稍后重试')
      }).then(() => {
        this.saving = false
      })
    },
    showMsg(type, msg) {
      if (this.$message && this.$message[type]) {
        this.$message[type](msg)
      } else {
        alert(msg)
      }
    }
  }
}
</script>

<style scoped>
.ai-settings-tab {
  display: flex;
  flex-direction: column;
  gap: 14px;
}

.ai-status {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 10px 12px;
  border-radius: 8px;
  border: 1px solid;
  background: rgba(255, 255, 255, 0.3);
}

.status-dot {
  width: 10px;
  height: 10px;
  border-radius: 50%;
  flex-shrink: 0;
}

.status-text {
  font-size: 14px;
  font-weight: 500;
}

.ai-hint {
  font-size: 12px;
  line-height: 1.6;
  opacity: 0.75;
  margin: 0;
}

.ai-form {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.ai-label {
  font-size: 13px;
  font-weight: 500;
  margin-top: 4px;
}

.ai-input {
  padding: 9px 12px;
  border-radius: 6px;
  border: 1px solid;
  font-size: 14px;
  outline: none;
  transition: border-color 0.2s;
  width: 100%;
  box-sizing: border-box;
}

.ai-save-btn {
  margin-top: 10px;
  padding: 10px 0;
  border-radius: 6px;
  border: 1px solid;
  font-size: 14px;
  font-weight: 500;
  color: #fff;
  cursor: pointer;
  transition: all 0.2s;
}

.ai-save-btn:disabled {
  opacity: 0.6;
  cursor: not-allowed;
}

.ai-quota {
  display: flex;
  gap: 16px;
  font-size: 12px;
  opacity: 0.7;
  padding-top: 4px;
}
</style>
