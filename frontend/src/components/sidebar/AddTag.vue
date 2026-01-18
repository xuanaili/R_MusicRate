<template>
  <!-- 根容器仅作为占位，DOM会被移植到body -->
  <div class="sidebar-root-container">
    <!-- 蒙版：初始隐藏，移植后通过全局样式控制 -->
    <div
      :class="['sidebar-mask', `sidebar-mask-${uid}`]"
      @click="handleMaskClose"
    ></div>

    <!-- 左侧新增标签侧边栏：保留class控制，移植后通过全局样式生效 -->
    <div
      :class="['add-album-sidebar', `add-album-sidebar-${uid}`]"
    >
      <div class="sidebar-header">
        <h2>添加新音乐风格</h2>
        <button class="close-btn" @click="handleClose">×</button>
      </div>
      <div class="sidebar-content">
        <!-- 所有表单内容保持不变 -->
        <div class="form-item">
          <label>风格名称：</label>
          <input v-model="tag.tags_name" type="text" placeholder="格式：English【中文】，如：Pop【流行】">
        </div>
        <div class="form-item">
          <label>别名：</label>
          <input v-model="tag.aka_name" type="text" placeholder="多个别名用逗号分隔，如：流行乐,华语流行">
        </div>
        <div class="form-item">
          <label>样式参数（0-100整数）：</label>
          <div class="style-params-group">
            <div class="style-param-item">
              <span class="param-label">参数A：</span>
              <input
                v-model="styleParams.param_a"
                type="number"
                min="0"
                max="100"
                placeholder="0-100"
                class="small-input"
                @input="limitNumberRange('param_a')"
              >
            </div>
            <div class="style-param-item">
              <span class="param-label">参数B：</span>
              <input
                v-model="styleParams.param_b"
                type="number"
                min="0"
                max="100"
                placeholder="0-100"
                class="small-input"
                @input="limitNumberRange('param_b')"
              >
            </div>
            <div class="style-param-item">
              <span class="param-label">参数C：</span>
              <input
                v-model="styleParams.param_c"
                type="number"
                min="0"
                max="100"
                placeholder="0-100"
                class="small-input"
                @input="limitNumberRange('param_c')"
              >
            </div>
            <div class="style-param-item">
              <span class="param-label">参数D：</span>
              <input
                v-model="styleParams.param_d"
                type="number"
                min="0"
                max="100"
                placeholder="0-100"
                class="small-input"
                @input="limitNumberRange('param_d')"
              >
            </div>
            <div class="style-param-item">
              <span class="param-label">参数E：</span>
              <input
                v-model="styleParams.param_e"
                type="number"
                min="0"
                max="100"
                placeholder="0-100"
                class="small-input"
                @input="limitNumberRange('param_e')"
              >
            </div>
            <div class="style-param-item">
              <span class="param-label">参数F：</span>
              <input
                v-model="styleParams.param_f"
                type="number"
                min="0"
                max="100"
                placeholder="0-100"
                class="small-input"
                @input="limitNumberRange('param_f')"
              >
            </div>
          </div>
          <p class="intro-tip">提示：留空则默认值为0，自动生成JSON格式</p>
        </div>
        <div class="form-item">
          <label>关联歌手ID：</label>
          <input
            v-model="relatedData.singers"
            type="text"
            placeholder="多个ID用逗号分隔，如：1,2,3"
          >
          <p class="intro-tip">提示：留空则默认空数组</p>
        </div>
        <div class="form-item">
          <label>关联专辑ID：</label>
          <input
            v-model="relatedData.albums"
            type="text"
            placeholder="多个ID用逗号分隔，如：1,2,3"
          >
          <p class="intro-tip">提示：留空则默认空数组</p>
        </div>
        <div class="form-item">
          <label>关联标签ID：</label>
          <input
            v-model="relatedData.tags"
            type="text"
            placeholder="多个ID用逗号分隔，如：1,2,3"
          >
          <p class="intro-tip">提示：留空则默认空数组</p>
        </div>
        <div class="form-item">
          <label>简洁介绍：</label>
          <input v-model="tag.brief_intro" type="text" placeholder="简短介绍（500字以内）">
        </div>
        <div class="form-item">
          <label>详细介绍：</label>
          <textarea
            v-model="tag.detail_intro"
            placeholder="请输入详细介绍（支持长文本、分段）"
            class="album-intro-textarea"
            rows="6"
            spellcheck="false"
          ></textarea>
        </div>
        <div class="form-item">
          <label>父标签ID：</label>
          <input v-model="tag.parent_tag_ids" type="text" placeholder="多个父标签ID用逗号分隔，如：1,2,3">
        </div>
        <div class="btn-group">
          <button @click="submitTag" class="btn-submit">提交风格</button>
          <button @click="handleClose" class="btn-cancel">取消</button>
        </div>
        <div class="error-tip" v-if="errorMsg">{{ errorMsg }}</div>
      </div>
    </div>
  </div>
</template>

<script>
export default {
  name: 'AddTag',
  props: {
    visible: {
      type: Boolean,
      default: false
    },
    mainColorDark: {
      type: String,
      default: '#333'
    },
    mainColorDarkDouble: {
      type: String,
      default: '#111'
    },
        // 新增：接收父组件传递的唯一标识（可选，也可以内部生成）
    uid: {
      type: String,
      default: ''
    }
  },
  data() {
    return {
            // 内部生成唯一ID（如果父组件没传）
      innerUid: this.uid || `add-tag-${Date.now()}-${Math.random().toString(36).slice(2, 8)}`,

      tag: {
        tags_name: "",
        aka_name: "",
        parameter_style: "",
        brief_intro: "",
        detail_intro: "",
        parent_tag_ids: ""
      },
      styleParams: {
        param_a: "",
        param_b: "",
        param_c: "",
        param_d: "",
        param_e: "",
        param_f: ""
      },
      relatedData: {
        singers: "",
        albums: "",
        tags: ""
      },
      errorMsg: "",
      isSubmitting: false
    };
  },
  // 保留DOM移植逻辑，新增：监听visible变化控制样式类
  watch: {
    visible(newVal) {
      // 关键：通过唯一类名获取当前实例的DOM，不再用全局类名
      const mask = document.querySelector(`.sidebar-mask-${this.uid}`);
      const sidebar = document.querySelector(`.add-album-sidebar-${this.uid}`);
      if (mask && sidebar) {
        if (newVal) {
          mask.classList.add('show');
          sidebar.classList.add('show');
        } else {
          mask.classList.remove('show');
          sidebar.classList.remove('show');
        }
      }
    }
  },
  mounted() {
    this.$nextTick(() => {
      // 获取当前实例的DOM，而非全局
      const mask = this.$el.querySelector(`.sidebar-mask-${this.uid}`);
      const side = this.$el.querySelector(`.add-album-sidebar-${this.uid}`);
      if (mask) document.body.appendChild(mask);
      if (side) document.body.appendChild(side);
      // 初始化时根据visible设置初始类名
      if (this.visible) {
        mask.classList.add('show');
        side.classList.add('show');
      }
    });
  },
  beforeDestroy() {
    // 移除当前实例的DOM，不影响其他实例
    const mask = document.querySelector(`.sidebar-mask-${this.uid}`);
    const side = document.querySelector(`.add-album-sidebar-${this.uid}`);
    mask?.parentNode?.removeChild(mask);
    side?.parentNode?.removeChild(side);
  },
  methods: {
    limitNumberRange(field) {
      let value = Number(this.styleParams[field]);
      if (isNaN(value)) {
        this.styleParams[field] = "";
        return;
      }
      if (value < 0) this.styleParams[field] = 0;
      if (value > 100) this.styleParams[field] = 100;
    },
    validateForm() {
      this.errorMsg = "";
      if (!this.tag.tags_name.trim()) {
        this.errorMsg = "风格名称不能为空！";
        return false;
      }
      for (const [key, value] of Object.entries(this.styleParams)) {
        if (value !== "" && (isNaN(Number(value)) || Number(value) < 0 || Number(value) > 100)) {
          this.errorMsg = `${key.replace('param_', '参数')}必须是0-100的整数！`;
          return false;
        }
      }
      const validateRelatedIds = (value, name) => {
        if (value.trim()) {
          const ids = value.split(',').map(id => id.trim());
          for (const id of ids) {
            if (isNaN(Number(id)) || Number(id) <= 0) {
              this.errorMsg = `${name}必须是正整数，多个用逗号分隔！`;
              return false;
            }
          }
        }
        return true;
      };
      if (!validateRelatedIds(this.relatedData.singers, "关联歌手ID")) return false;
      if (!validateRelatedIds(this.relatedData.albums, "关联专辑ID")) return false;
      if (!validateRelatedIds(this.relatedData.tags, "关联标签ID")) return false;
      return true;
    },
    buildStyleParamsJson() {
      const styleObj = {};
      Object.keys(this.styleParams).forEach(key => {
        styleObj[key] = this.styleParams[key] !== "" ? Number(this.styleParams[key]) : 0;
      });
      return JSON.stringify(styleObj);
    },
    buildRelatedIdsJson(value) {
      if (!value.trim()) return "[]";
      const ids = [...new Set(
          value.split(',')
              .map(id => id.trim())
              .filter(id => id)
              .map(id => Number(id))
      )];
      return JSON.stringify(ids);
    },
    async submitTag() {
      if (!this.validateForm()) return;
      if (this.isSubmitting) return;
      this.isSubmitting = true;
      this.errorMsg = "";
      try {
        this.tag.parameter_style = this.buildStyleParamsJson();
        const submitData = {
          tags_name: this.tag.tags_name.trim(),
          aka_name: this.tag.aka_name.trim(),
          parameter_style: this.tag.parameter_style || '{}',
          brief_intro: this.tag.brief_intro.trim(),
          detail_intro: this.tag.detail_intro.trim(),
          parent_tag_ids: this.tag.parent_tag_ids.trim(),
          related_singers: this.buildRelatedIdsJson(this.relatedData.singers),
          related_albums: this.buildRelatedIdsJson(this.relatedData.albums),
          related_tags: this.buildRelatedIdsJson(this.relatedData.tags)
        };
        const res = await this.$axios({
          url: "/api/tags/add",
          method: "POST",
          headers: {
            'Authorization': localStorage.getItem('token') || '',
            'Content-Type': 'application/json'
          },
          data: submitData
        });
        if (res.data.code === 200) {
          alert("音乐风格添加成功！");
          this.handleClose();
        } else {
          this.errorMsg = res.data.msg;
        }
      } catch (err) {
        console.error("添加风格失败：", err);
        this.errorMsg = "添加失败，请检查后端是否启动或网络连接！";
      } finally {
        this.isSubmitting = false;
      }
    },
    handleClose() {
      this.resetForm();
      this.$emit('close');
    },
    handleMaskClose(e) {
      if (e.target.className.includes('sidebar-mask')) {
        this.handleClose();
      }
    },
    resetForm() {
      this.tag = {
        tags_name: "",
        aka_name: "",
        parameter_style: "",
        brief_intro: "",
        detail_intro: "",
        parent_tag_ids: ""
      };
      this.styleParams = {
        param_a: "",
        param_b: "",
        param_c: "",
        param_d: "",
        param_e: "",
        param_f: ""
      };
      this.relatedData = {
        singers: "",
        albums: "",
        tags: ""
      };
      this.errorMsg = "";
    }
  }
};
</script>

<!-- 关键：移除scoped，改为全局样式，确保body下的DOM能生效 -->
<style>
/* 全局样式：确保移植到body的DOM能获取到样式 */
.sidebar-mask {
  position: fixed;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  background: rgba(0, 0, 0, 0.5);
  backdrop-filter: blur(2px);
  z-index: 9998;
  transition: all 0.3s ease;
  /* 默认隐藏 */
  opacity: 0;
  pointer-events: none;
}

/* 显示蒙版 */
.sidebar-mask.show {
  opacity: 1;
  pointer-events: auto;
}

.add-album-sidebar {
  --main-dark: #333;
  --main-dark-double: #111;
  position: fixed;
  top: 0;
  left: 0;
  bottom: 0;
  width: 580px;
  background: rgba(255, 255, 255, 0.5);
  backdrop-filter: blur(8px);
  z-index: 9999;
  transform: translateX(-100%);
  transition: transform 0.3s ease-in-out;
  overflow-y: auto;
  padding-bottom: 30px;
  box-shadow: 2px 0 15px rgba(0, 0, 0, 0.2);
  border-right: 1px solid var(--main-dark);
  /* 默认隐藏 */
  pointer-events: none;
}

/* 显示侧边栏 */
.add-album-sidebar.show {
  transform: translateX(0);
  pointer-events: auto;
}

/* 以下是原有样式，全部改为全局 */
.sidebar-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 16px 20px;
  border-bottom: 1px solid var(--main-dark);
  margin-bottom: 10px;
}

.sidebar-header h2 {
  margin: 0;
  font-size: 18px;
  color: var(--main-dark);
}

.sidebar-content {
  padding: 0 20px;
}

.form-item {
  margin: 15px 0;
  text-align: left;
}

.form-item label {
  display: block;
  margin-bottom: 8px;
  font-weight: 600;
  color: var(--main-dark);
  font-size: 14px;
}

.form-item input {
  width: 100%;
  padding: 9px 10px;
  box-sizing: border-box;
  border: 1px solid var(--main-dark);
  border-radius: 4px;
  font-size: 14px;
  color: var(--main-dark);
  background: rgba(255, 255, 255, 0.3);
}

.form-item input::placeholder {
  color: var(--main-dark);
  opacity: 0.7;
}

.album-intro-textarea {
  width: 100%;
  padding: 10px;
  box-sizing: border-box;
  border: 1px solid var(--main-dark);
  border-radius: 4px;
  font-size: 14px;
  line-height: 1.6;
  resize: vertical;
  font-family: inherit;
  white-space: pre-wrap;
  word-wrap: break-word;
  color: var(--main-dark);
  background: rgba(255, 255, 255, 0.3);
}

.album-intro-textarea::placeholder {
  color: var(--main-dark);
  opacity: 0.7;
}

.intro-tip {
  margin: 5px 0 0 0;
  font-size: 12px;
  color: var(--main-dark);
  opacity: 0.8;
  line-height: 1.4;
}

.error-tip {
  color: #ff4444;
  margin-top: 10px;
  text-align: center;
  font-size: 14px;
  padding: 8px;
  border-radius: 4px;
  background: rgba(255, 245, 245, 0.5);
}

.close-btn {
  background: transparent;
  border: none;
  font-size: 20px;
  color: #999;
  cursor: pointer;
  width: 30px;
  height: 30px;
  line-height: 30px;
}

.close-btn:hover {
  color: #ff4444;
}

.btn-group {
  margin-top: 20px;
  display: flex;
  gap: 10px;
}

.btn-submit {
  flex: 1;
  padding: 11px;
  border: none;
  border-radius: 4px;
  cursor: pointer;
  background: var(--main-dark);
  color: white;
  font-size: 14px;
  font-weight: 600;
}

.btn-cancel {
  flex: 1;
  padding: 11px;
  border: none;
  border-radius: 4px;
  cursor: pointer;
  background: #999;
  color: white;
  font-size: 14px;
}

.add-album-sidebar::-webkit-scrollbar {
  width: 6px;
}

.add-album-sidebar::-webkit-scrollbar-thumb {
  background: var(--main-dark);
  opacity: 0.5;
  border-radius: 3px;
}

.add-album-sidebar::-webkit-scrollbar-thumb:hover {
  background: var(--main-dark-double);
}

.style-params-group {
  display: flex;
  flex-wrap: wrap;
  gap: 10px;
  margin-bottom: 8px;
}

.style-param-item {
  display: flex;
  align-items: center;
  width: calc(50% - 5px);
  margin-bottom: 8px;
}

.param-label {
  font-size: 12px;
  color: var(--main-dark);
  margin-right: 6px;
  white-space: nowrap;
  width: 60px;
}

.small-input {
  flex: 1;
  padding: 6px 8px !important;
  font-size: 12px !important;
  width: auto !important;
}


.sidebar-mask.show {
  opacity: 1;
  pointer-events: auto;
}
.add-album-sidebar.show {
  transform: translateX(0);
  pointer-events: auto;
}
</style>