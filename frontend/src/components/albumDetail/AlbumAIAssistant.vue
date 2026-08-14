<template>
  <div class="tab-content ai-assistant">
    <!-- 顶部工具条：标题 + 重置对话 -->
    <div class="ai-header">
      <span class="ai-title" :style="{ color: mainColorDarkDouble }">AI 助手</span>
      <span class="ai-subtitle" :style="{ color: mainColorDarkDouble }">围绕这张专辑提问，我会结合你的评分/听后感、歌词、节奏、评论与全网听后感来回答</span>
      <button
        class="ai-reset-btn"
        :style="{ borderColor: mainColorDark, color: mainColorDarkDouble }"
        :disabled="!messages.length || thinking"
        @click="resetConversation"
      >重置对话</button>
    </div>

    <!-- v0.8.3 P1：节奏分析中提示条（打开 AI 助手 tab 预触发 BPM，轮询就绪后隐藏） -->
    <div v-if="tempoAnalyzing" class="ai-tempo-banner" :style="{ backgroundColor: mainColorDark, color: '#ffffff' }">
      ⏳ 正在分析专辑节奏（BPM），完成后会自动加入 AI 上下文…
    </div>

    <!-- 消息列表 -->
    <div class="ai-chat-body" ref="chatBody">
      <div v-if="loadingHistory" class="ai-loading" :style="{ color: mainColorDarkDouble }">加载对话历史…</div>

      <!-- 空态：引导问题 -->
      <div v-else-if="!messages.length" class="ai-empty">
        <div class="ai-empty-avatar" :style="{ backgroundColor: mainColorDark }">🤖</div>
        <div class="ai-empty-text" :style="{ color: mainColorDarkDouble }">
          我是你的 AI 音乐助手。关于这张专辑的创作背景、歌词解读、节奏情绪、我的个人听感，都可以问我～
        </div>
        <div class="ai-suggest-list">
          <button
            v-for="(q, i) in suggestedQuestions"
            :key="i"
            class="ai-suggest-item"
            :style="{ borderColor: mainColorDark, color: mainColorDarkDouble }"
            @click="sendSuggested(q)"
          >{{ q }}</button>
        </div>
      </div>

      <!-- 消息列表 -->
      <div v-else class="ai-msg-list">
        <div
          v-for="(msg, i) in messages"
          :key="msg.id || msg.tempId || i"
          class="ai-msg-row"
          :class="msg.role"
        >
          <div class="ai-bubble" :class="msg.role" :style="msg.role === 'user' ? { backgroundColor: mainColorDark, color: '#ffffff' } : bubbleAiStyle">
            <!-- 用户消息：纯文本 -->
            <template v-if="msg.role === 'user'">{{ msg.content }}</template>
            <!-- AI 消息：markdown 渲染（markdown-it html:false 防 XSS） -->
            <div v-else class="ai-markdown" v-html="mdRender(msg.content)"></div>
            <!-- 思考中动画（首段 delta 未到） -->
            <div v-if="msg.streaming && !msg.content" class="ai-thinking"><span></span><span></span><span></span></div>
          </div>
          <button
            v-if="!msg.streaming"
            class="ai-msg-del"
            :title="msg.id ? '删除这条消息' : '移除这条消息'"
            @click="deleteMessage(msg)"
          >✕</button>
        </div>
      </div>
    </div>

    <!-- 底部输入区 -->
    <div class="ai-input-area">
      <textarea
        v-model="question"
        class="ai-input"
        :style="inputStyle"
        rows="1"
        placeholder="提问这张专辑…（Enter 发送，Shift+Enter 换行）"
        :disabled="thinking"
        @keydown="handleKeydown"
      ></textarea>
      <button
        class="ai-send-btn"
        :style="{ backgroundColor: mainColorDark, borderColor: mainColorDark }"
        :disabled="!canSend"
        @click="sendMessage"
      >{{ thinking ? '思考中…' : '发送' }}</button>
    </div>
  </div>
</template>

<script>
// MusicRate\frontend\src\components\albumDetail\AlbumAIAssistant.vue AI 助手子页（v0.8.1 P6）
// 专辑详情左侧菜单「AI 助手」子页（非侧边栏形态）：围绕当前专辑与 AI 对话。
// 决策（README v0.8.1）：
//   - SSE 流式：axios 无法流式且 10s 超时杀长流 → 原生 fetch + ReadableStream 解析 `data:` 事件（delta/done/error）
//   - BPM 预触发（v0.8.3 P1）：created() 打开 tab 即调 /api/ai/tempo/ensure（幂等），analyzing → 顶部提示条 +
//     轮询 status 就绪隐藏；chat 不再返回 tempo_analyzing 占位（照常回答，BPM 就绪后自动带上）
//   - 消息成功才落库：乐观渲染 user 气泡 + AI 临时占位（tempId），done 事件回填真实 user_msg_id/assistant_msg_id
//   - 对话历史按 album_pool_id 持久化，挂载时 GET /api/ai/conversation 加载
//   - markdown 渲染 markdown-it({html:false}) 转义原始 HTML 防 XSS；Enter 发送 / Shift+Enter 换行
import MarkdownIt from 'markdown-it'

const md = new MarkdownIt({ html: false, linkify: true, breaks: true })

export default {
  name: 'AlbumAIAssistant',
  props: {
    albumPoolId: {
      type: [String, Number],
      required: true,
      default: ''
    },
    mainColor: { type: String, default: 'transparent' },
    mainColorDark: { type: String, default: 'transparent' },
    mainColorDarkDouble: { type: String, default: 'transparent' },
    mainColorWhite: { type: String, default: 'transparent' },
    mainColorWhiteDouble: { type: String, default: 'transparent' }
  },
  data() {
    return {
      messages: [],          // {id, role, content, streaming?, tempId?}
      question: '',
      thinking: false,       // 等待/流式输出中
      loadingHistory: false,
      abortController: null, // 离开页面时中断流式
      tempoAnalyzing: false, // v0.8.3 P1：节奏分析中提示条显隐
      tempoPollTimer: null,  // 轮询节奏分析任务状态的定时器
      suggestedQuestions: [
        '这张专辑的主题和风格是什么？',
        '结合我的评分和听后感，分析一下我的听歌口味',
        '推荐这张专辑里最值得单曲循环的歌曲',
        '这张专辑的节奏（BPM）有什么特点？'
      ]
    }
  },
  computed: {
    canSend() {
      return !this.thinking && !!this.question.trim()
    },
    bubbleAiStyle() {
      return {
        backgroundColor: 'rgba(255, 255, 255, 0.45)',
        color: this.mainColorDarkDouble,
        borderColor: 'rgba(255, 255, 255, 0.5)'
      }
    },
    inputStyle() {
      return {
        backgroundColor: 'rgba(255, 255, 255, 0.4)',
        color: this.mainColorDarkDouble,
        borderColor: 'rgba(255, 255, 255, 0.5)'
      }
    }
  },
  created() {
    this.loadHistory()
    // v0.8.3 P1：打开 AI 助手 tab 即预触发 BPM 节奏分析（幂等；analyzing 则轮询就绪显示提示条）
    this.preloadTempo()
  },
  beforeDestroy() {
    // 切换子页面/离开详情时中断进行中的流式请求（防泄漏）+ 停止节奏轮询定时器
    if (this.abortController) {
      this.abortController.abort()
    }
    this.stopTempoPolling()
  },
  methods: {
    mdRender(content) {
      return md.render(content || '')
    },
    // ==================== v0.8.3 P1：BPM 预触发 + 节奏分析提示条 ====================
    preloadTempo() {
      if (!this.albumPoolId) return
      this.$axios.post(`/api/ai/tempo/ensure/${this.albumPoolId}`).then(res => {
        if (res.data.code !== 200) return
        const d = res.data.data || {}
        if (d.ready) return                       // 已有缓存，无需提示
        if (d.analyzing && d.task_id) {
          this.tempoAnalyzing = true
          this.pollTempoStatus(d.task_id)
        }
        // 无 mp3 / 池不存在 → 忽略（不展示提示条）
      }).catch(err => {
        // 预触发失败不阻断（非关键路径）
        console.error('❌ 预触发节奏分析失败：', err)
      })
    },
    pollTempoStatus(taskId) {
      this.stopTempoPolling()
      this.tempoPollTimer = setInterval(() => {
        this.$axios.get(`/api/ai/tempo/status/${taskId}`).then(res => {
          if (res.data.code !== 200) {
            this.stopTempoPolling()
            this.tempoAnalyzing = false
            return
          }
          const st = res.data.data || {}
          // done/failed → 停止轮询并隐藏提示条（failed 也隐藏，避免一直卡提示）
          if (st.status === 'done' || st.status === 'failed') {
            this.stopTempoPolling()
            this.tempoAnalyzing = false
          }
        }).catch(() => {
          // 任务不存在（后端重启丢内存任务）/ 网络异常 → 停止轮询，隐藏提示条
          this.stopTempoPolling()
          this.tempoAnalyzing = false
        })
      }, 4000)
    },
    stopTempoPolling() {
      if (this.tempoPollTimer) {
        clearInterval(this.tempoPollTimer)
        this.tempoPollTimer = null
      }
    },
    // ==================== 会话历史 ====================
    loadHistory() {
      if (!this.albumPoolId) return
      this.loadingHistory = true
      this.$axios.get('/api/ai/conversation', {
        params: { album_pool_id: this.albumPoolId }
      }).then(res => {
        if (res.data.code === 200) {
          const msgs = (res.data.data && res.data.data.messages) || []
          this.messages = msgs.map(m => ({
            id: m.id, role: m.role, content: m.content, streaming: false
          }))
        }
      }).catch(err => {
        console.error('❌ 加载 AI 对话历史失败：', err)
      }).finally(() => {
        this.loadingHistory = false
        this.$nextTick(() => this.scrollToBottom())
      })
    },
    deleteMessage(msg) {
      // 未落库消息（分析中提示/临时占位）→ 仅移除本地
      if (!msg.id) {
        this.messages = this.messages.filter(m => m !== msg)
        return
      }
      this.$axios.post('/api/ai/conversation/delete', { message_id: msg.id }).then(res => {
        if (res.data.code === 200) {
          this.messages = this.messages.filter(m => m !== msg)
        } else {
          this.showMsg('error', res.data.msg || '删除失败')
        }
      }).catch(err => {
        console.error('❌ 删除 AI 消息失败：', err)
        this.showMsg('error', '删除失败，请稍后重试')
      })
    },
    resetConversation() {
      if (!this.messages.length || this.thinking) return
      if (!window.confirm('确定清空与 AI 的这段对话吗？')) return
      this.$axios.post('/api/ai/conversation/reset', {
        album_pool_id: this.albumPoolId
      }).then(res => {
        if (res.data.code === 200) {
          this.messages = []
        } else {
          this.showMsg('error', res.data.msg || '重置失败')
        }
      }).catch(err => {
        console.error('❌ 重置 AI 对话失败：', err)
        this.showMsg('error', '重置失败，请稍后重试')
      })
    },
    // ==================== 发送 ====================
    sendSuggested(q) {
      this.question = q
      this.sendMessage()
    },
    handleKeydown(e) {
      // Enter 发送，Shift+Enter 换行（保留 textarea 默认换行行为）
      if (e.key === 'Enter' && !e.shiftKey) {
        e.preventDefault()
        this.sendMessage()
      }
    },
    async sendMessage() {
      const q = this.question.trim()
      if (!q || this.thinking) return
      if (!this.albumPoolId) {
        this.showMsg('error', '未找到公共专辑，无法使用 AI 助手')
        return
      }

      // 乐观渲染：用户消息 + AI 临时占位（tempId，done 事件回填真实 id）
      const userMsg = { id: null, role: 'user', content: q, tempId: `u-${Date.now()}` }
      const aiMsg = { id: null, role: 'assistant', content: '', tempId: `a-${Date.now()}`, streaming: true }
      this.messages.push(userMsg)
      this.messages.push(aiMsg)
      this.question = ''
      this.thinking = true
      this.scrollToBottom()

      const controller = new AbortController()
      this.abortController = controller

      const body = {
        album_pool_id: Number(this.albumPoolId),
        question: q,
        // v0.8.5：整张专辑歌词由后端在组装上下文时现查 album_lyric（与 BPM 同一步），不依赖播放曲目索引
        stream: true
      }

      try {
        // 原生 fetch：axios 无法流式且 10s 超时会杀长流
        const res = await fetch('http://localhost:5000/api/ai/chat', {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json',
            'Authorization': localStorage.getItem('token') || ''
          },
          body: JSON.stringify(body),
          signal: controller.signal
        })

        if (!res.ok) {
          // 非 2xx → JSON 错误（403 无 key / 404 池不存在 / 500 服务异常）
          let msg = '请求失败，请稍后重试'
          try {
            const err = await res.json()
            msg = err.msg || msg
          } catch (e) { /* 忽略解析失败 */ }
          throw new Error(msg)
        }

        const contentType = res.headers.get('Content-Type') || ''
        if (contentType.includes('text/event-stream')) {
          await this.parseSseStream(res, aiMsg, userMsg)
        } else {
          // 普通 JSON 回答（v0.8.3 P1：chat 已不再返回 tempo_analyzing 占位，BPM 缺失时照常回答无 BPM 段）
          const json = await res.json()
          if (json.code !== 200) throw new Error(json.msg || '请求失败')
          const d = json.data || {}
          aiMsg.content = d.answer || ''
          aiMsg.streaming = false
          aiMsg.id = d.assistant_msg_id || null
          userMsg.id = d.user_msg_id || null
        }
      } catch (err) {
        if (err.name === 'AbortError') {
          // 用户离开页面中断 → 保留已流式收到的内容；完全没内容则移除临时占位
          aiMsg.streaming = false
          if (!aiMsg.content) {
            this.messages = this.messages.filter(m => m !== aiMsg && m !== userMsg)
          }
          return
        }
        aiMsg.streaming = false
        if (!aiMsg.content) {
          aiMsg.content = `⚠️ ${err.message || '请求失败，请稍后重试'}`
        }
        this.showMsg('error', err.message || '请求失败')
      } finally {
        this.thinking = false
        this.abortController = null
        this.scrollToBottom()
      }
    },
    // ==================== SSE 流式解析 ====================
    parseSseStream(res, aiMsg, userMsg) {
      return new Promise((resolve, reject) => {
        const reader = res.body.getReader()
        const decoder = new TextDecoder('utf-8')
        let buffer = ''
        let doneEvent = null

        const pump = () => {
          reader.read().then(({ done, value }) => {
            if (done) {
              aiMsg.streaming = false
              // 流提前结束且无 done 事件、也无内容 → 判定异常
              if (!doneEvent && !aiMsg.content) {
                reject(new Error('AI 未返回内容，请稍后重试'))
                return
              }
              resolve()
              return
            }
            buffer += decoder.decode(value, { stream: true })
            let sep
            while ((sep = buffer.indexOf('\n\n')) !== -1) {
              const chunk = buffer.slice(0, sep)
              buffer = buffer.slice(sep + 2)
              for (const line of chunk.split('\n')) {
                const t = line.trim()
                if (!t.startsWith('data:')) continue
                const payload = t.slice(5).trim()
                if (!payload) continue
                let evt
                try { evt = JSON.parse(payload) } catch (e) { continue }
                if (evt.type === 'delta') {
                  aiMsg.content += evt.content || ''
                } else if (evt.type === 'done') {
                  doneEvent = evt
                  aiMsg.id = evt.assistant_msg_id || null
                  userMsg.id = evt.user_msg_id || null
                } else if (evt.type === 'error') {
                  reject(new Error(evt.msg || 'AI 服务异常'))
                  reader.cancel()
                  return
                }
              }
            }
            pump()
          }).catch(err => reject(err))
        }
        pump()
      })
    },
    scrollToBottom() {
      this.$nextTick(() => {
        if (this.$refs.chatBody) {
          this.$refs.chatBody.scrollTop = this.$refs.chatBody.scrollHeight
        }
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
.ai-assistant {
  height: 90vh;
  display: flex;
  flex-direction: column;
  padding: 10px;
  box-sizing: border-box;
  gap: 10px;
}

/* 顶部工具条 */
.ai-header {
  display: flex;
  align-items: center;
  gap: 12px;
  flex-shrink: 0;
}
.ai-title {
  font-size: 16px;
  font-weight: 600;
}
.ai-subtitle {
  flex: 1;
  font-size: 12px;
  opacity: 0.6;
}
.ai-reset-btn {
  padding: 5px 14px;
  border-radius: 6px;
  border: 1px solid;
  background: transparent;
  font-size: 12px;
  cursor: pointer;
  transition: all 0.2s;
}
.ai-reset-btn:disabled {
  opacity: 0.4;
  cursor: not-allowed;
}

/* v0.8.3 P1：节奏分析中提示条 */
.ai-tempo-banner {
  padding: 8px 14px;
  border-radius: 8px;
  font-size: 13px;
  flex-shrink: 0;
  opacity: 0.92;
}

/* 消息列表 */
.ai-chat-body {
  flex: 1;
  overflow-y: auto;
  padding: 6px 4px;
  border-radius: 8px;
  background: rgba(255, 255, 255, 0.18);
  min-height: 0;
}
.ai-loading {
  text-align: center;
  padding: 40px 0;
  font-size: 13px;
  opacity: 0.7;
}

/* 空态引导 */
.ai-empty {
  padding: 36px 20px;
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 14px;
}
.ai-empty-avatar {
  width: 52px;
  height: 52px;
  border-radius: 50%;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 26px;
}
.ai-empty-text {
  font-size: 13px;
  line-height: 1.7;
  text-align: center;
  max-width: 420px;
}
.ai-suggest-list {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
  justify-content: center;
  margin-top: 6px;
}
.ai-suggest-item {
  padding: 8px 14px;
  border-radius: 16px;
  border: 1px solid;
  background: transparent;
  font-size: 13px;
  cursor: pointer;
  transition: all 0.2s;
}
.ai-suggest-item:hover {
  opacity: 0.85;
  transform: translateY(-1px);
}

/* 消息气泡 */
.ai-msg-list {
  display: flex;
  flex-direction: column;
  gap: 12px;
}
.ai-msg-row {
  display: flex;
  align-items: flex-start;
  gap: 8px;
}
.ai-msg-row.user {
  flex-direction: row-reverse;
}
.ai-bubble {
  max-width: 78%;
  padding: 10px 14px;
  border-radius: 12px;
  font-size: 14px;
  line-height: 1.7;
  word-break: break-word;
  white-space: pre-wrap;
}
.ai-bubble.user {
  border-bottom-right-radius: 4px;
}
.ai-bubble.assistant {
  border: 1px solid;
  border-bottom-left-radius: 4px;
}
.ai-msg-del {
  border: none;
  background: transparent;
  color: rgba(0, 0, 0, 0.35);
  font-size: 12px;
  cursor: pointer;
  opacity: 0;
  transition: opacity 0.2s;
  padding: 2px 4px;
  flex-shrink: 0;
}
.ai-msg-row:hover .ai-msg-del {
  opacity: 1;
}

/* markdown 内容 */
.ai-markdown :deep(p) {
  margin: 0 0 8px;
}
.ai-markdown :deep(p:last-child) {
  margin-bottom: 0;
}
.ai-markdown :deep(ul),
.ai-markdown :deep(ol) {
  margin: 4px 0 8px;
  padding-left: 20px;
}
.ai-markdown :deep(li) {
  margin: 2px 0;
}
.ai-markdown :deep(code) {
  background: rgba(0, 0, 0, 0.08);
  padding: 1px 5px;
  border-radius: 4px;
  font-size: 12px;
}
.ai-markdown :deep(a) {
  color: #2563eb;
  text-decoration: underline;
}

/* 思考中动画 */
.ai-thinking {
  display: inline-flex;
  gap: 5px;
  padding: 2px 0;
}
.ai-thinking span {
  width: 7px;
  height: 7px;
  border-radius: 50%;
  background: currentColor;
  opacity: 0.5;
  animation: ai-blink 1.2s infinite ease-in-out;
}
.ai-thinking span:nth-child(2) { animation-delay: 0.2s; }
.ai-thinking span:nth-child(3) { animation-delay: 0.4s; }
@keyframes ai-blink {
  0%, 80%, 100% { opacity: 0.2; transform: translateY(0); }
  40% { opacity: 0.9; transform: translateY(-3px); }
}

/* 底部输入区 */
.ai-input-area {
  display: flex;
  gap: 8px;
  flex-shrink: 0;
}
.ai-input {
  flex: 1;
  padding: 10px 14px;
  border-radius: 8px;
  border: 1px solid;
  font-size: 14px;
  outline: none;
  resize: none;
  line-height: 1.5;
  box-sizing: border-box;
}
.ai-input:disabled {
  opacity: 0.6;
}
.ai-send-btn {
  padding: 0 22px;
  border-radius: 8px;
  border: 1px solid;
  font-size: 14px;
  font-weight: 500;
  color: #fff;
  cursor: pointer;
  transition: all 0.2s;
  flex-shrink: 0;
}
.ai-send-btn:disabled {
  opacity: 0.55;
  cursor: not-allowed;
}
</style>
