# 项目介绍
## v0
用于简单的静态音乐列表画面
首页：展示音乐列表（歌曲名、评分、简短介绍）
详情页：单首音乐的评分、评论输入框
简单的评分功能：用户能给音乐打 1-10 分，页面能显示平均分
### 功能清单
#### 已完成
- 静态音乐列表页面（HTML/CSS）
- Vue实现评分/评论交互（假数据）
- 新增用户登录功能
- Flask接口对接，评论/评分存JSON
- 多用户登录
- 添加专辑页面
- 替换JSON为SQLite数据库
- 替换SQLite数据库为Mysql
- 用户id进行分表
#### 进行中


#### 待做
- 专辑封面问题，创建新专辑时复制图片代替URL
- 专辑列表的评论隐藏，放在平台评论里
- 听后感需要一个新增按钮，每次时间戳的听后感都单独保存，也可单独删除
- 音乐分类（按歌手/风格）
- 优化评分星星的样式（hover高亮）


# 文件介绍
- MusicRate/ # 项目根目录
  - frontend/ # 前端（Vue）
    - assets/ # 静态资源（图片/字体/全局CSS）
      - css/
        - global.css # 全局样式（比如重置样式、通用布局）
        - star.css # 评分星星专属样式
      - images/ # 音乐封面/图标等
    - components/ # Vue组件（复用的小模块）
      - MusicItem.vue   # 单首音乐的卡片组件（评分+评论）
      - StarRating.vue  # 评分星星组件（复用）
    - js/         # 辅助JS（请求封装/工具函数）
      - api.js  # 封装后端接口（比如获取音乐、提交评论）
      - utils.js # 工具函数（比如评分计算、时间格式化）
    - index.html  # 入口页面
    - app.js      # Vue入口（挂载实例、路由等）
  - backend/        # 后端（Flask）
    - app.py      # 入口文件（启动服务、注册路由）
    - routes/     # 接口路由拆分（按模块）
      - music.py # 音乐相关接口（获取列表、提交评分/评论）
      - user.py  # 后续加用户登录时用
    - utils/      # 后端工具函数
      - data_handler.py # JSON/数据库读写封装
      - score_calc.py   # 评分计算（比如加权平均分）
    - config.py   # 配置文件（数据库地址、端口、密钥等）
    - data/       # 数据存储（JSON/数据库文件）
      - music_data.json #这个是示例
  - .gitignore      # 忽略不需要提交的文件（venv/、node_modules/等）
  - README.md       # 项目说明（启动步骤、功能清单、待优化项）
