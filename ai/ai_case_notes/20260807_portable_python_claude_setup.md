# 移动硬盘项目便携化：Python虚拟环境 + Claude Code跨电脑方案

## 一、案例基本信息
- 问题场景分类：环境迁移 / 便携化
- 产生时间：2026-08-07
- 项目模块：全局（Python运行环境 + Claude Code配置）
- 相似问题判定特征：
  1. 项目在移动硬盘/U盘上，换电脑后Python环境失效
  2. `.venv` 中 `pyvenv.cfg` 的 `home` 路径指向旧电脑绝对路径
  3. 运行报错 `No Python at '"X:\Python\PythonXXX\python.exe'`
  4. Claude Code记忆文件在C盘，换电脑后丢失

## 二、原始问题描述
MusicRate项目在移动硬盘上，从公司电脑拷贝到家里电脑后：
- `.venv` 硬编码了 `D:\Python\Python310` 的绝对路径，新电脑无此路径导致Python完全不可用
- 用户不想每次换电脑都重建虚拟环境（耗时且繁琐）
- Claude Code的持久化记忆和设置存储在C盘，换电脑后丢失

核心诉求：
1. Python环境跟随项目走，插任何电脑都能用
2. Claude Code记忆和设置跟随项目走
3. 换电脑后只需一次简单配置，不需要手动重建环境

## 三、最终解决方案

### 方案：内嵌便携 Python + Claude Junction 链接

#### 1. 便携 Python（替代 .venv）
- 下载 Python Windows embeddable package（`python-3.10.11-embed-amd64.zip`）
- 解压到项目目录 `python/`，依赖直接装在 `python\Lib\site-packages\`
- 修改 `python/python310._pth`，启用 `Lib`、`site-packages` 和 `import site`
- PyCharm 直接配置 `python\python.exe` 为解释器（不使用 venv）
- 删除坏的 `.venv`

#### 2. Claude Code 便携化
- 记忆目录 `.claude/memory/` 放在项目内
- 通过 Windows Junction 链接 `C:\Users\用户\.claude\projects\X--MusicRate\memory\` → 项目 `.claude\memory\`
- 全局设置 `.claude/settings.json`（含API密钥）备份到项目目录
- 创建 `setup_claude_portable.bat` 自动配置脚本

## 四、关键代码/配置/模板

### python310._pth（修改后）
```
python310.zip
.
Lib
Lib\site-packages

# Uncomment to run site.main() automatically
import site
```

### setup_claude_portable.bat（核心逻辑）
```bat
REM 计算Claude项目目录名（路径中 : → 空，\ → --）
set "CLAUDE_DIR_NAME=%PROJECT_DIR::=%"
set "CLAUDE_DIR_NAME=%CLAUDE_DIR_NAME:\=--%"

REM 创建记忆Junction
mklink /J "%CLAUDE_PROJECT_DIR%\memory" "%MEMORY_TARGET%"

REM 复制全局设置（如不存在）
copy "%PORTABLE_SETTINGS%" "%GLOBAL_SETTINGS%"
```

### 启动方式
```bat
REM 后端启动（PyCharm或命令行）
python\python.exe backend\run.py

REM 或双击
start_backend.bat
```

## 五、踩坑点 & 注意事项

- **`_pth` 文件必须修改**：默认 embeddable Python 不启用 site-packages，必须手动添加 `Lib`、`Lib\site-packages` 和 `import site`
- **不能用 `-m` 方式启动**：`python\python.exe -m backend.run` 会报 ModuleNotFoundError，因为项目根目录不在 sys.path，应使用 `python\python.exe backend\run.py`
- **`_pth` 不能硬编码项目路径**：否则换盘符又坏了，用脚本方式运行更可靠
- **Junction 用 mklink /J 而非 mklink /D**：/J 是目录联接，不需要管理员权限；/D 是符号链接，需要管理员权限
- **`python/` 和 `.claude/` 加入 `.gitignore`**：这些是本地配置，不应入仓库

## 六、同类问题快速适配规则

下次遇到移动硬盘项目跨电脑使用的问题，只需：
- 【适配点1】更换 embeddable Python 版本：下载对应版本的 `python-X.X.X-embed-amd64.zip`，修改 `_pth` 中的 `pythonXXX` 文件名
- 【适配点2】更换项目路径：`setup_claude_portable.bat` 自动根据 `%~dp0` 计算，无需手动改
- 【适配点3】依赖变更：`python\python.exe -m pip install -r requirements.txt` 重新安装
