一、案例基本信息
- 问题场景分类：环境迁移 / 跨域CORS
- 产生时间：2026-08-07
- 项目模块：后端启动（backend/__init__.py、backend/run.py）、MySQL、CORS配置
- 相似问题判定特征：
  1. 换电脑/换网络后项目无法正常运行
  2. 后端日志只出现OPTIONS请求，无POST请求跟进
  3. 前端登录页面提示"服务器错误"或"连接服务器失败"
  4. MySQL服务未注册为Windows系统服务（U盘便携版）
  5. Python终端输出emoji报UnicodeEncodeError（GBK编码）

二、原始问题描述
项目从旧电脑迁移到新公司电脑（U盘便携环境），MySQL和ffmpeg都放在U盘里而非系统安装目录。运行后端和前端后，前端登录页面点击登录报"服务器错误"，后端日志只显示OPTIONS预检请求（200），无POST请求。

核心诉求：
1. 诊断新电脑环境缺失项并补全依赖
2. 解决U盘便携MySQL无法通过Windows服务启动的问题
3. 解决终端GBK编码导致emoji输出崩溃的问题
4. 解决公司网络多IP导致CORS跨域拦截的问题

三、排查与解决过程

1. 第一步：检查新电脑环境缺失项
   - Python 3.10.6 ✅、Node.js v24.18.0 ✅、npm 11.16.0 ✅ 已安装
   - Python依赖包缺失（Flask、PyMySQL、flask-cors等未安装）
   - MySQL80系统服务未注册（MySQL在U盘 U:/__/app/MySQL/）
   - ffmpeg未加入系统PATH（在 U:/MusicRate/backend/tools/ffmpeg/）
   - 解决：`pip install -r requirements.txt` 安装所有Python依赖

2. 第二步：启动U盘便携MySQL
   - MySQL数据目录和配置文件（my.ini）都已在U盘，basedir/datadir指向U盘路径
   - 无法通过 `sc start MySQL80` 启动（服务未注册）
   - 解决：直接运行mysqld.exe并指定配置文件：
     ```bash
     "U:/__/app/MySQL/MySQL Server 8.0/bin/mysqld.exe" --defaults-file="U:/__/app/MySQL/MySQL Server 8.0/my.ini"
     ```

3. 第三步：解决GBK编码崩溃
   - `run.py` → `init_base_tables()` 中的 `print("✅ ...")` 在Windows GBK终端下报 UnicodeEncodeError
   - 解决：启动时加环境变量 `PYTHONIOENCODING=utf-8`：
     ```bash
     PYTHONIOENCODING=utf-8 python -m backend.run
     ```

4. 第四步：解决CORS跨域拦截（核心问题）
   - 原CORS配置只允许 `http://localhost:8080` 和 `http://127.0.0.1:8080`
   - 公司电脑有多个网络IP（10.254.170.130、192.168.1.100等），若浏览器通过IP访问前端，origin不匹配，浏览器阻止POST请求
   - 现象：后端日志只有OPTIONS（200），无POST请求；前端显示"服务器错误"
   - 解决：将 `origins` 从固定白名单改为正则 `r".*"`，开发环境匹配任意来源

四、最终解决方案/改造步骤

### 1. 新电脑首次启动流程
```bash
# 1. 安装Python依赖
cd U:/MusicRate
pip install -r requirements.txt

# 2. 启动U盘MySQL（每次开机需手动执行一次）
"U:/__/app/MySQL/MySQL Server 8.0/bin/mysqld.exe" --defaults-file="U:/__/app/MySQL/MySQL Server 8.0/my.ini"

# 3. 启动后端（UTF-8编码）
PYTHONIOENCODING=utf-8 python -m backend.run

# 4. 启动前端
cd U:/MusicRate/frontend
npm run serve
```

### 2. CORS配置修改（backend/__init__.py）
```python
# 修改前：
origins=["http://localhost:8080", "http://127.0.0.1:8080"],

# 修改后：
origins=r".*",  # 正则匹配任意来源，开发环境用，生产环境应改为具体域名
```

五、关键代码/配置/模板（可直接复用）

### U盘MySQL便携启动命令
```bash
"U:/__/app/MySQL/MySQL Server 8.0/bin/mysqld.exe" --defaults-file="U:/__/app/MySQL/MySQL Server 8.0/my.ini"
```

### MySQL连接测试命令
```bash
"U:/__/app/MySQL/MySQL Server 8.0/bin/mysql.exe" -u music_user -p123456 -e "SELECT 1"
```

### CORS预检测试命令（curl模拟浏览器）
```bash
# 测试OPTIONS预检
curl -v -X OPTIONS http://localhost:5000/api/login \
  -H "Origin: http://10.254.170.130:8080" \
  -H "Access-Control-Request-Method: POST" \
  -H "Access-Control-Request-Headers: Content-Type,Authorization"

# 测试实际POST登录
curl -v -X POST http://localhost:5000/api/login \
  -H "Content-Type: application/json" \
  -H "Origin: http://10.254.170.130:8080" \
  -d '{"username":"admin","password":"123456"}'
```

六、踩坑点 & 注意事项（非常重要）
- **CORS只允许localhost**：公司网络IP变化后，固定白名单的origins配置会导致跨域拦截，必须用正则或动态匹配
- **Windows GBK终端**：Python在Windows下默认用GBK编码，print含emoji的字符串会崩溃，必须加 `PYTHONIOENCODING=utf-8`
- **U盘MySQL非系统服务**：`sc start MySQL80` 找不到服务，必须手动启动mysqld.exe并指定--defaults-file
- **OPTIONS 200 ≠ CORS通过**：后端日志看到OPTIONS返回200，不代表CORS配置正确。浏览器可能仍因origin不匹配而阻止POST请求
- **pydub的ffmpeg警告可忽略**：`RuntimeWarning: Couldn't find ffmpeg` 是pydub导入时的检查，项目代码在 `unlock.py` 中已通过 `AudioSegment.converter` 正确配置了ffmpeg路径
- **`origins="*"` 不能与 `supports_credentials=True` 同时使用**：CORS规范不允许，必须用正则 `r".*"` 替代

七、同类问题快速适配规则
下次遇到相似问题，只需修改哪些参数/哪些模块即可快速复用本方案：
- 【适配点1】MySQL路径：如果MySQL安装到其他位置，修改 `run.py` 中的mysqld启动路径和 `my.ini` 中的basedir/datadir
- 【适配点2】CORS来源：如果生产环境部署，将 `origins=r".*"` 改回具体域名白名单
- 【适配点3】ffmpeg路径：如果ffmpeg安装到其他位置，修改 `backend/utils/unlock.py` 中的 `FFMPEG_PATH` 和 `FFPROBE_PATH`
- 【适配点4】Python编码：如果终端编码不同（如UTF-8原生系统），可省略 `PYTHONIOENCODING=utf-8`

---

以下为固定指令，下次新开对话直接先贴本文件 + 再贴下方指令：
请以本文档为标准案例范式，解决我接下来的同类问题。优先复用本文的分析逻辑、改造流程、代码模板和避坑规则，不要从零重新思考。根据我新问题的差异点做适配微调，输出稳定、同规范的解决方案。
