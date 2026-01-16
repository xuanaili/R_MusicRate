<template>
  <!-- 根容器加唯一class，和AddAlbum保持一致 -->
  <div class="sidebar-root-container">
    <!-- 蒙版（统一为sidebar-mask） -->
    <div
      v-show="visible"
      class="sidebar-mask"
      @click="handleMaskClose"
    ></div>

    <!-- 左侧新增标签侧边栏（统一为add-album-sidebar，和AddAlbum保持类名一致） -->
    <div
      class="add-album-sidebar"
      :class="{show: visible}"
    >
      <div class="sidebar-header">
        <h2>添加新音乐风格</h2>
        <button class="close-btn" @click="handleClose">×</button>
      </div>
      <div class="sidebar-content">
        <!-- 风格名称 -->
        <div class="form-item">
          <label>风格名称：</label>
          <input v-model="tag.tags_name" type="text" placeholder="格式：English【中文】，如：Pop【流行】">
        </div>

        <!-- 别名 -->
        <div class="form-item">
          <label>别名：</label>
          <input v-model="tag.aka_name" type="text" placeholder="多个别名用逗号分隔，如：流行乐,华语流行">
        </div>

        <!-- 样式参数（6个整数参数：0-100） -->
        <div class="form-item">
          <label>样式参数（0-100整数）：</label>
          <!-- 6个小输入框容器 -->
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

        <!-- 关联歌手ID -->
        <div class="form-item">
          <label>关联歌手ID：</label>
          <input
            v-model="relatedData.singers"
            type="text"
            placeholder="多个ID用逗号分隔，如：1,2,3"
          >
          <p class="intro-tip">提示：留空则默认空数组</p>
        </div>

        <!-- 关联专辑ID -->
        <div class="form-item">
          <label>关联专辑ID：</label>
          <input
            v-model="relatedData.albums"
            type="text"
            placeholder="多个ID用逗号分隔，如：1,2,3"
          >
          <p class="intro-tip">提示：留空则默认空数组</p>
        </div>

        <!-- 关联标签ID -->
        <div class="form-item">
          <label>关联标签ID：</label>
          <input
            v-model="relatedData.tags"
            type="text"
            placeholder="多个ID用逗号分隔，如：1,2,3"
          >
          <p class="intro-tip">提示：留空则默认空数组</p>
        </div>

        <!-- 简洁介绍 -->
        <div class="form-item">
          <label>简洁介绍：</label>
          <input v-model="tag.brief_intro" type="text" placeholder="简短介绍（500字以内）">
        </div>

        <!-- 详细介绍 -->
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

        <!-- 父标签ID -->
        <div class="form-item">
          <label>父标签ID：</label>
          <input v-model="tag.parent_tag_ids" type="text" placeholder="多个父标签ID用逗号分隔，如：1,2,3">
        </div>

        <!-- 按钮区 -->
        <div class="btn-group">
          <button @click="submitTag" class="btn-submit">提交风格</button>
          <button @click="handleClose" class="btn-cancel">取消</button>
        </div>

        <!-- 错误提示 -->
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
    }
  },
  data() {
    return {
      tag: {
        tags_name: "",
        aka_name: "",
        parameter_style: "", // 最终拼接的JSON字符串
        brief_intro: "",
        detail_intro: "",
        parent_tag_ids: ""
      },
      // 6个样式参数（0-100整数）
      styleParams: {
        param_a: "",
        param_b: "",
        param_c: "",
        param_d: "",
        param_e: "",
        param_f: ""
      },
      // 关联数据（歌手/专辑/标签ID）
      relatedData: {
        singers: "",
        albums: "",
        tags: ""
      },
      errorMsg: "",
      isSubmitting: false
    };
  },
  // AddTag.vue

  methods: {
    // 限制数字范围为0-100
    limitNumberRange(field) {
      let value = Number(this.styleParams[field]);
      if (isNaN(value)) {
        this.styleParams[field] = "";
        return;
      }
      if (value < 0) this.styleParams[field] = 0;
      if (value > 100) this.styleParams[field] = 100;
    },

    // 表单验证
    validateForm() {
      this.errorMsg = "";
      // 必输项验证
      if (!this.tag.tags_name.trim()) {
        this.errorMsg = "风格名称不能为空！";
        return false;
      }
      // 验证样式参数是否为0-100整数（有值时）
      for (const [key, value] of Object.entries(this.styleParams)) {
        if (value !== "" && (isNaN(Number(value)) || Number(value) < 0 || Number(value) > 100)) {
          this.errorMsg = `${key.replace('param_', '参数')}必须是0-100的整数！`;
          return false;
        }
      }
      // 验证关联ID是否为数字（有值时）
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

    // 拼接样式参数为JSON字符串
    buildStyleParamsJson() {
      const styleObj = {};
      // 遍历6个参数，空值默认0，强制转数字
      Object.keys(this.styleParams).forEach(key => {
        styleObj[key] = this.styleParams[key] !== "" ? Number(this.styleParams[key]) : 0;
      });
      return JSON.stringify(styleObj);
    },

    // 拼接关联ID为JSON数组
    buildRelatedIdsJson(value) {
      if (!value.trim()) return "[]";
      // 去重+过滤空值+转数字
      const ids = [...new Set(
        value.split(',')
          .map(id => id.trim())
          .filter(id => id)
          .map(id => Number(id))
      )];
      return JSON.stringify(ids);
    },

    // 提交新标签
    async submitTag() {
      if (!this.validateForm()) return;
      if (this.isSubmitting) return;

      this.isSubmitting = true;
      this.errorMsg = "";

      try {
        // 拼接样式参数JSON
        this.tag.parameter_style = this.buildStyleParamsJson();

        // 构造提交数据（包含关联字段）
        const submitData = {
          tags_name: this.tag.tags_name.trim(),
          aka_name: this.tag.aka_name.trim(),
          parameter_style: this.tag.parameter_style || '{}',
          brief_intro: this.tag.brief_intro.trim(),
          detail_intro: this.tag.detail_intro.trim(),
          parent_tag_ids: this.tag.parent_tag_ids.trim(),
          // 新增关联字段，转JSON数组
          related_singers: this.buildRelatedIdsJson(this.relatedData.singers),
          related_albums: this.buildRelatedIdsJson(this.relatedData.albums),
          related_tags: this.buildRelatedIdsJson(this.relatedData.tags)
        };

        // 调用后端接口
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

    // 关闭侧边栏
    handleClose() {
      this.resetForm();
      this.$emit('close');
    },

    // 点击蒙版关闭
    handleMaskClose(e) {
      if (e.target.className === 'sidebar-mask') {
        this.handleClose();
      }
    },

    // 重置表单
    resetForm() {
      this.tag = {
        tags_name: "",
        aka_name: "",
        parameter_style: "",
        brief_intro: "",
        detail_intro: "",
        parent_tag_ids: ""
      };
      // 重置样式参数
      this.styleParams = {
        param_a: "",
        param_b: "",
        param_c: "",
        param_d: "",
        param_e: "",
        param_f: ""
      };
      // 重置关联数据
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

<!-- 全部样式改为scoped，和AddAlbum保持一致 -->
<style scoped>
/* ✅ 新增根容器样式，不影响任何布局和样式，纯占位 */
.sidebar-root-container {
  position: relative;
  z-index: 9999;
}

/* ✅ 蒙版透明度0.5 加深遮罩 */
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
}

/* ✅ 左侧添加专辑侧边栏 样式不变 */
.add-album-sidebar {
  position: fixed;
  top: 0;
  left: 0;
  bottom: 0;
  width: 580px;
  background: rgba(255,255,255,0.5);
  backdrop-filter: blur(8px);
  z-index: 9999;
  transform: translateX(-100%);
  transition: transform 0.3s ease-in-out;
  overflow-y: auto;
  padding-bottom: 30px;
	box-shadow: 2px 0 15px rgba(0,0,0,0.2);
}
.add-album-sidebar.show {
  transform: translateX(0);
}
.sidebar-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 16px 20px;
  border-bottom: 1px solid v-bind(mainColorDark);
  margin-bottom: 10px;
}

.sidebar-header h2 {
  margin: 0;
  font-size: 18px;
  color: v-bind(mainColorDark);
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
  color: v-bind(mainColorDark);
  font-size: 14px;
}

.form-item input {
  width: 100%;
  padding: 9px 10px;
  box-sizing: border-box;
  border: 1px solid v-bind(mainColorDark);
  border-radius: 4px;
  font-size: 14px;
  color: v-bind(mainColorDark);
  background: rgba(255,255,255,0.3);
}

.form-item input::placeholder {
  color: v-bind(mainColorDark);
  opacity: 0.7;
}

.album-intro-textarea {
  width: 100%;
  padding: 10px;
  box-sizing: border-box;
  border: 1px solid v-bind(mainColorDark);
  border-radius: 4px;
  font-size: 14px;
  line-height: 1.6;
  resize: vertical;
  font-family: inherit;
  white-space: pre-wrap;
  word-wrap: break-word;
  color: v-bind(mainColorDark);
  background: rgba(255,255,255,0.3);
}

.album-intro-textarea::placeholder {
  color: v-bind(mainColorDark);
  opacity: 0.7;
}

.intro-tip {
  margin: 5px 0 0 0;
  font-size: 12px;
  color: v-bind(mainColorDark);
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
  background: rgba(255,245,245,0.5);
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
  background: v-bind(mainColorDark);
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
  background: v-bind(mainColorDark);
  opacity: 0.5;
  border-radius: 3px;
}

.add-album-sidebar::-webkit-scrollbar-thumb:hover {
  background: v-bind(mainColorDarkDouble);
}

/* 样式参数小框样式 */
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
  color: v-bind(mainColorDark);
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
</style>