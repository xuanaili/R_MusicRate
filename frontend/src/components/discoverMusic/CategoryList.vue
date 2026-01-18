<template>
  <div class="container">
    <!-- 树状分类展示区 -->
    <div class="tag-tree-container" v-if="!loading && tagTree.length > 0">
      <!-- 管理员新增标签按钮 -->
      <div class="admin-add-tag-btn" v-if="isAdmin">
        <button @click="handleOpenAddTagSidebar" class="add-original-btn">+ 新增音乐风格</button>
      </div>

      <!-- 树状列表 -->
      <div class="tag-tree-list">
        <div
          v-for="rootTag in tagTree"
          :key="rootTag.id"
          class="tag-node"
        >
          <!-- 根节点 -->
          <div class="tag-item">
            <span
              class="expand-icon"
              :class="{ expanded: rootTag.expanded }"
              @click.stop="handleTagToggle(rootTag)"
            >
              {{ rootTag.children.length > 0 ? (rootTag.expanded ? '−' : '+') : '•' }}
            </span>
            <a
              :href="getTagDetailUrl(rootTag.tags_name)"
              class="tag-name"
              @click.stop.prevent="navigateToTagDetail(rootTag.tags_name)"
              :title="getChineseName(rootTag.tags_name)"
            >
              {{ getEnglishName(rootTag.tags_name) }}
            </a>
            <span v-if="rootTag.aka_name" class="tag-aka">({{ rootTag.aka_name }})</span>
            <span v-if="rootTag.brief_intro" class="tag-brief" :title="rootTag.brief_intro">
              — {{ rootTag.brief_intro.substring(0, 50) }}{{ rootTag.brief_intro.length > 50 ? '...' : '' }}
            </span>
          </div>

          <!-- 子节点（递归组件） -->
          <div
            v-if="rootTag.expanded && rootTag.children && rootTag.children.length > 0"
            class="tag-children"
          >
            <tag-tree-node
              v-for="childTag in rootTag.children"
              :key="childTag.id"
              :tag="childTag"
              :depth="1"
              @toggle="handleTagToggle"
              @navigate="navigateToTagDetail"
            />
          </div>
        </div>
      </div>
    </div>

    <!-- 加载状态 -->
    <div v-if="loading" class="loading-content">
      <p>加载音乐风格分类中...</p>
    </div>

    <!-- 无数据状态 -->
    <div v-if="!loading && tagTree.length === 0" class="empty-content">
      <h3>🎼 音乐类型</h3>
      <p>暂无音乐风格数据</p>
      <button
        v-if="isAdmin"
        @click="handleOpenAddTagSidebar"
        class="add-first-tag-btn"
      >
        添加第一个音乐风格
      </button>
    </div>

    <!-- 新增标签侧边栏组件（简化核心：仅保留响应式控制） -->
    <AddTag
      :visible="showAddTagSidebar"
      :main-color-dark="mainColorDark"
      :main-color-dark-double="mainColorDarkDouble"
      @close="handleAddTagClose"
      :uid="'add-tag-category'"
    />
  </div>
</template>

<script>
import AddTag from '@/components/sidebar/AddTag.vue'
import axios from 'axios'

// 递归组件
const TagTreeNode = {
  name: 'TagTreeNode',
  props: {
    tag: {
      type: Object,
      required: true
    },
    depth: {
      type: Number,
      required: true,
      default: 0
    }
  },
  methods: {
    // 提取英文部分（默认显示）
    getEnglishName(tagName) {
      const match = tagName.match(/(.*?)【/)
      return match ? match[1].trim() : tagName
    },
    // 提取中文部分（悬停显示）
    getChineseName(tagName) {
      const match = tagName.match(/【(.*?)】/)
      return match ? match[1].trim() : tagName
    },
    toggleTag(tag) {
      this.$emit('toggle', tag)
    },
    navigateToTag(tagName) {
      this.$emit('navigate', tagName)
    },
    getTagDetailUrl(tagName) {
      return `/tag-detail?tagName=${encodeURIComponent(tagName)}`
    }
  },
  render(createElement) {
    const tag = this.tag
    const depth = this.depth
    const englishName = this.getEnglishName(tag.tags_name)
    const chineseName = this.getChineseName(tag.tags_name)

    const childrenContent = []
    if (tag.expanded && tag.children && tag.children.length > 0) {
      tag.children.forEach(child => {
        childrenContent.push(createElement(
          'tag-tree-node',
          {
            key: child.id,
            props: {
              tag: child,
              depth: depth + 1
            },
            on: {
              toggle: this.toggleTag,
              navigate: this.navigateToTag
            }
          }
        ))
      })
    }

    const indentStyle = {
      marginLeft: `${depth * 20}px`
    }

    return createElement(
      'div',
      { class: 'tag-node' },
      [
        createElement(
          'div',
          {
            class: 'tag-item',
            style: indentStyle
          },
          [
            createElement(
              'span',
              {
                class: [
                  'expand-icon',
                  { expanded: tag.expanded }
                ],
                on: {
                  click: (e) => {
                    e.stopPropagation()
                    this.toggleTag(tag)
                  }
                }
              },
              tag.children && tag.children.length > 0
                ? (tag.expanded ? '−' : '+')
                : '•'
            ),
            createElement(
              'a',
              {
                class: 'tag-name',
                attrs: {
                  href: this.getTagDetailUrl(tag.tags_name),
                  // 子节点：设置title属性实现悬停显示中文
                  title: chineseName
                },
                on: {
                  click: (e) => {
                    e.stopPropagation()
                    e.preventDefault()
                    this.navigateToTag(tag.tags_name)
                  }
                }
              },
              // 子节点默认显示英文
              englishName
            ),
            tag.aka_name ? createElement('span', { class: 'tag-aka' }, `(${tag.aka_name})`) : '',
            tag.brief_intro ? createElement(
              'span',
              {
                class: 'tag-brief',
                attrs: { title: tag.brief_intro }
              },
              `— ${tag.brief_intro.substring(0, 50)}${tag.brief_intro.length > 50 ? '...' : ''}`
            ) : ''
          ]
        ),
        tag.expanded && tag.children && tag.children.length > 0
          ? createElement('div', { class: 'tag-children' }, childrenContent)
          : ''
      ]
    )
  }
}

export default {
  name: 'CategoryList',
  components: {
    AddTag,
    TagTreeNode
  },
  props: {
    activeSubTab: String,
    mainColor: { type: String, default: 'transparent' },
    mainColorDark: { type: String, default: '#333' },
    mainColorDarkDouble: { type: String, default: '#111' }
  },
  data() {
    return {
      showAddTagSidebar: false, // 唯一控制侧边栏显隐的变量
      isAdmin: false,
      loading: true,
      tagTree: [],
      totalTagCount: 0
    }
  },
  created() {
    // 登录验证
    if (!localStorage.getItem('token')) {
      this.$router.push('/login')
      return
    }
    this.isAdmin = localStorage.getItem('is_admin') === '1'

    // 获取标签数据
    this.getTagTreeData()
  },
  watch: {
    '$route'() {
      this.isAdmin = localStorage.getItem('is_admin') === '1'
    }
  },
  methods: {
    // 获取树状标签数据
    async getTagTreeData() {
      try {
        this.loading = true
        const res = await axios.get('/api/tags/tree', {
          headers: {
            'Authorization': localStorage.getItem('token') || ''
          }
        })

        if (res.data.code === 200) {
          this.tagTree = res.data.data.tag_tree
          this.initTagExpandState(this.tagTree)
          this.totalTagCount = this.calculateTagCount(this.tagTree)
        }
      } catch (error) {
        console.error('获取音乐风格树失败：', error)
        this.tagTree = []
      } finally {
        this.loading = false
      }
    },
    // 初始化标签展开状态
    initTagExpandState(tags) {
      if (!tags || tags.length === 0) return
      tags.forEach(tag => {
        this.$set(tag, 'expanded', false)
        if (tag.children && tag.children.length > 0) {
          this.initTagExpandState(tag.children)
        }
      })
    },
    // 计算总标签数量
    calculateTagCount(tags) {
      let count = 0
      tags.forEach(tag => {
        count++
        if (tag.children && tag.children.length > 0) {
          count += this.calculateTagCount(tag.children)
        }
      })
      return count
    },
    // 处理标签展开/收起
    handleTagToggle(tag) {
      this.$set(tag, 'expanded', !tag.expanded)
      this.$forceUpdate()
    },
    // 提取英文部分（根节点使用）
    getEnglishName(tagName) {
      const match = tagName.match(/(.*?)【/)
      return match ? match[1].trim() : tagName
    },
    // 提取中文部分（根节点使用）
    getChineseName(tagName) {
      const match = tagName.match(/【(.*?)】/)
      return match ? match[1].trim() : tagName
    },
    // 获取标签详情页URL
    getTagDetailUrl(tagName) {
      return `/tag-detail?tagName=${encodeURIComponent(tagName)}`
    },
    // 跳转到标签详情页
    navigateToTagDetail(tagName) {
      this.$router.push({
        path: '/tag-detail',
        query: { tagName: encodeURIComponent(tagName) }
      })
    },
    // 打开新增标签侧边栏
    handleOpenAddTagSidebar() {
      this.showAddTagSidebar = true
    },
    // 关闭新增标签侧边栏（核心简化）
    handleAddTagClose() {
      this.showAddTagSidebar = false
    }
  }
}
</script>

<style scoped>
.container {
  max-width: 1600px;
  margin: 0 auto;
  padding: 20px;
  position: relative;
  min-height: 600px;
}

.admin-add-tag-btn {
  display: flex;
  position: absolute;
  top: 20px;
  right: 20px;
  z-index: 999 !important;
}

.add-original-btn {
  padding: 8px 20px;
  font-size: 15px;
  background: v-bind(mainColorDark);
  color: white;
  border: none;
  border-radius: 4px;
  cursor: pointer;
  font-weight: bold;
  transition: background 0.2s;
}

.add-original-btn:hover {
  background: v-bind(mainColorDarkDouble);
}

.tag-tree-container {
  margin-top: 60px;
  font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
}

.tag-tree-header {
  margin-bottom: 20px;
  border-bottom: 2px solid v-bind(mainColorDark);
  padding-bottom: 10px;
}

.tag-tree-header h2 {
  font-size: 24px;
  color: v-bind(mainColorDark);
  margin: 0 0 5px 0;
}

.tag-count {
  color: #666;
  margin: 0;
  font-size: 14px;
}

.tag-tree-list {
  line-height: 1.8;
  background: rgba(255, 255, 255, 0.3);
  padding: 10px;
  border-radius: 8px;
  backdrop-filter: blur(2px);
}

.tag-node {
  margin: 10px 0;
}

.tag-item {
  display: flex;
  align-items: center;
  padding: 4px 8px;
  border-radius: 4px;
  transition: background 0.2s;
}

.tag-item:hover {
  background: rgba(0, 0, 0, 0.05);
}

::v-deep .expand-icon {
  display: inline-block;
  width: 18px;
  height: 18px;
  line-height: 18px;
  text-align: center;
  font-weight: bold;
  color: #666;
  margin-right: 8px;
  border-radius: 3px;
  background: #eee;
  user-select: none;
  cursor: pointer;
  transition: background 0.2s;
}

::v-deep .expand-icon:hover {
  background: #ddd;
}

::v-deep .expand-icon.expanded {
  background: v-bind(mainColorDark);
  color: white;
}

::v-deep .tag-name {
  color: v-bind(mainColorDark) !important;
  font-weight: 500;
  text-decoration: none !important;
  margin-right: 8px;
  transition: color 0.2s;
  cursor: pointer;
  /* 优化title提示的显示效果 */
  position: relative;
}

::v-deep .tag-name:hover {
  color: #007acc !important;
  text-decoration: underline !important;
}

::v-deep .tag-aka {
  color: #888;
  font-size: 14px;
  margin-right: 8px;
}

::v-deep .tag-brief {
  color: #666;
  font-size: 14px;
  flex: 1;
}

.tag-children {
  /* 由递归组件的depth控制缩进 */
}

::v-deep a {
  color: inherit;
  text-decoration: none;
}

.loading-content {
  text-align: center;
  padding: 100px 0;
  color: #666;
  font-size: 16px;
}

.empty-content {
  text-align: center;
  padding: 100px 0;
  color: #666;
}

.empty-content h3 {
  font-size: 20px;
  margin-bottom: 10px;
  color: #333;
}

.add-first-tag-btn {
  padding: 8px 20px;
  font-size: 15px;
  margin-top: 20px;
  background: v-bind(mainColorDark);
  color: white;
  border: none;
  border-radius: 4px;
  cursor: pointer;
  font-weight: bold;
}

@media (max-width: 768px) {
  .tag-item {
    flex-wrap: wrap;
  }

  ::v-deep .tag-brief {
    width: 100%;
    margin-top: 4px;
    margin-left: 26px;
  }
}
</style>