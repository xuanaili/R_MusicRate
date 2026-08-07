一、案例基本信息
- 问题场景分类：MySQL启动 / 数据库异常处理 / Windows终端编码
- 产生时间：2026-08-07
- 项目模块：后端启动（backend/run.py）、数据库工具（backend/utils/db.py）
- 相似问题判定特征：
  1. 关机/重启后运行 `python -m backend.run` 报 `Can't connect to MySQL server on 'localhost'`
  2. 异常日志中出现 `UnboundLocalError: local variable 'db' referenced before assignment`
  3. MySQL服务报告"启动成功"但端口3306不可连接
  4. Windows终端print含emoji字符时崩溃 `UnicodeEncodeError: 'gbk' codec can't encode character`
  5. MySQL安装在移动硬盘/U盘，非系统标准安装目录

二、原始问题描述
关机前手动kill掉了MySQL进程，重新开机后运行 `python -m backend.run` 报错。报错信息显示两层问题：
1. MySQL连接被拒绝（`WinError 10061 由于目标计算机积极拒绝`）
2. 连接失败后触发 `UnboundLocalError: local variable 'db' referenced before assignment`，掩盖了真正的连接错误

核心诉求：
1. 修复MySQL关机后无法自动启动的问题（移动硬盘U盘环境）
2. 修复db.rollback()在db未赋值时崩溃的代码缺陷
3. 修复Windows终端GBK编码导致emoji输出崩溃的问题

三、排查与解决过程

1. 第一步：分析MySQL启动失败原因
   - `run.py` 中 `sc query MySQL80` 检查服务状态 → 服务未注册（MySQL在移动硬盘U盘，非系统安装）
   - `sc start MySQL80` 执行后返回"启动成功"，但实际MySQL端口3306未监听
   - 原因：`sc start` 是异步的，只表示"已向服务管理器发送启动命令"，不等MySQL真正就绪
   - 且MySQL80服务本身根本未注册到Windows服务中

2. 第二步：分析UnboundLocalError
   - `create_album_comments()` 等函数中 `db = get_db()` 在 `try` 块内
   - `get_db()` 连接失败抛异常时，`db` 变量从未赋值
   - `except` 块中 `db.rollback()` 引用了未赋值的 `db` → `UnboundLocalError`
   - 这个二次异常掩盖了真正的MySQL连接错误，所有13个create_*函数都有此问题

3. 第三步：分析UnicodeEncodeError
   - `db.py` 中 `print("✅ ...")` 等emoji字符在Windows GBK终端下无法编码
   - 即使MySQL连接成功，print也会崩溃

4. 第四步：修复并验证
   - 修复后重新运行，所有表初始化成功，Flask正常启动

四、最终解决方案/改造步骤

### 1. 修复 run.py — MySQL启动逻辑重构

```python
# 改动前：sc start MySQL80 + 固定sleep(10)
# 改动后：三层启动策略

def is_mysql_port_ready():
    """检查MySQL 3306端口是否可连接"""
    try:
        sock = socket.create_connection(('localhost', 3306), timeout=1)
        sock.close()
        return True
    except (ConnectionRefusedError, socket.timeout, OSError):
        return False

def wait_mysql_ready(max_wait=60):
    """等待MySQL端口就绪，最多等max_wait秒"""
    for i in range(max_wait // 2):
        time.sleep(2)
        if is_mysql_port_ready():
            return True
    return False

# 启动流程：
# 1. 先检测端口是否已就绪 → 直接继续
# 2. 尝试Windows服务(MySQL80)启动 → 轮询端口等待就绪
# 3. 服务启动失败 → 根据项目盘符推算mysqld路径直接启动
def start_mysql_via_mysqld():
    project_drive = os.path.splitdrive(os.path.abspath(__file__))[0]
    mysqld_path = os.path.join(project_drive, os.sep, '__',
                                'app', 'MySQL', 'MySQL Server 8.0', 'bin', 'mysqld.exe')
    ini_path = os.path.join(project_drive, os.sep, '__',
                             'app', 'MySQL', 'MySQL Server 8.0', 'my.ini')
    # 以管理员权限启动mysqld
    cmd = f'powershell -Command "Start-Process cmd -ArgumentList \'/c \\"{mysqld_path}\\" --defaults-file=\\"{ini_path}\\"\' -Verb RunAs"'
    subprocess.run(cmd, shell=True, capture_output=True, text=True)
    return wait_mysql_ready()
```

### 2. 修复 db.py — 所有create_*函数的异常处理

```python
# 改动前：
def create_album_comments():
    try:
        db = get_db()
        ...
    except Exception as e:
        db.rollback()  # ← 如果get_db()失败，db未赋值，UnboundLocalError!

# 改动后：
def create_album_comments():
    db = None          # ← 在try前初始化
    try:
        db = get_db()
        ...
    except Exception as e:
        if db: db.rollback()  # ← 安全检查，db为None时跳过
```

受影响函数（共13个）：
- `check_and_create_user_album_table`
- `get_next_id`
- `create_user_album_table`
- `create_user_album_intro_table`
- `create_user_playlist_table`
- `create_user_recommend`
- `create_users`
- `create_album_pool`
- `create_album_comments`
- `create_album_tags`
- `create_album_singers`
- `create_album_lyric`
- `create_album_share`
- `init_default_admin`

### 3. 修复 run.py — Windows终端UTF-8输出

```python
# 在run.py最开头添加：
if sys.platform == 'win32':
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')
    sys.stderr.reconfigure(encoding='utf-8', errors='replace')
```

五、关键代码/配置/模板（可直接复用）

### MySQL端口就绪检测（通用）
```python
import socket

def is_mysql_port_ready(host='localhost', port=3306, timeout=1):
    """检查MySQL端口是否可连接"""
    try:
        sock = socket.create_connection((host, port), timeout=timeout)
        sock.close()
        return True
    except (ConnectionRefusedError, socket.timeout, OSError):
        return False
```

### 移动硬盘mysqld启动命令（通用）
```bash
# 根据项目所在盘符推算
"<DRIVE>:/__/app/MySQL/MySQL Server 8.0/bin/mysqld.exe" --defaults-file="<DRIVE>:/__/app/MySQL/MySQL Server 8.0/my.ini"
```

### try/except中db变量安全模式（通用）
```python
def some_db_operation():
    db = None              # ① try前初始化
    try:
        db = get_db()
        cursor = db.cursor()
        ...
        db.commit()
        cursor.close()
    except Exception as e:
        if db: db.rollback()  # ② 安全检查后再rollback
        raise e
```

六、踩坑点 & 注意事项（非常重要）
- **`sc start` 是异步的**：只表示"已发送启动命令"，不等于MySQL端口已就绪。必须轮询端口确认
- **`sc start MySQL80` 可能服务根本不存在**：移动硬盘/U盘安装的MySQL不会注册为Windows服务，`sc query` 会报"指定的服务未安装"
- **`UnboundLocalError` 会掩盖真正的错误**：`db = get_db()` 失败后，`db.rollback()` 的二次异常会让开发者误以为问题在rollback，而不是在MySQL连接
- **`for...else` 的 `else` 语义**：Python中 `for...else` 的 `else` 在循环正常完成（无break）时执行，容易误用。建议用显式标志变量替代
- **Windows GBK终端**：Python在Windows下默认用GBK编码stdout，print含emoji/特殊Unicode字符会崩溃。必须在启动时 `reconfigure(encoding='utf-8')`
- **mysqld需要管理员权限**：`Start-Process -Verb RunAs` 会触发UAC弹窗，在自动化环境中可能被阻止

七、同类问题快速适配规则
下次遇到相似问题，只需修改哪些参数/哪些模块即可快速复用本方案：
- 【适配点1】MySQL路径：如果MySQL安装到其他位置，修改 `run.py` 中 `start_mysql_via_mysqld()` 的路径推算逻辑
- 【适配点2】等待时间：如果MySQL启动特别慢，调整 `wait_mysql_ready(max_wait=60)` 的参数
- 【适配点3】端口/主机：如果MySQL使用非默认端口，修改 `is_mysql_port_ready()` 的默认参数
- 【适配点4】其他数据库操作函数：新增的 `create_*` 函数必须遵循 `db = None` + `if db: db.rollback()` 模式

---

以下为固定指令，下次新开对话直接先贴本文件 + 再贴下方指令：
请以本文档为标准案例范式，解决我接下来的同类问题。优先复用本文的分析逻辑、改造流程、代码模板和避坑规则，不要从零重新思考。根据我新问题的差异点做适配微调，输出稳定、同规范的解决方案。
