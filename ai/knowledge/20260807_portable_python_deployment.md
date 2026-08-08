# Python Embeddable Package 便携部署指南

## 概述
Python 官方提供 Windows embeddable package（嵌入版），适合放在项目目录内随项目移动，无需安装、不依赖系统 Python。

## 下载地址
https://www.python.org/downloads/windows/ → 选择对应版本 → "Windows embeddable package (64-bit)"

## 部署步骤

### 1. 下载并解压
下载 `python-X.X.X-embed-amd64.zip`，解压到项目目录 `python/`。

### 2. 修改 `_pth` 文件
文件名如 `python310._pth`，默认内容：
```
python310.zip
.

# Uncomment to run site.main() automatically
#import site
```
修改为：
```
python310.zip
.
Lib
Lib\site-packages

# Uncomment to run site.main() automatically
import site
```
关键改动：
- 添加 `Lib` 和 `Lib\site-packages` 目录
- 取消注释 `import site`（启用 pip 支持）

### 3. 创建目录结构
```
python/
├── Lib/
│   └── site-packages/   ← 依赖包装在这里
├── Scripts/              ← pip 安装后自动生成
├── python.exe
├── python310._pth
└── ...
```

### 4. 安装 pip
```bash
curl -o get-pip.py https://bootstrap.pypa.io/get-pip.py
python\python.exe get-pip.py
```

### 5. 安装依赖
```bash
python\python.exe -m pip install -r requirements.txt
```

## 运行项目

### 命令行
```bash
python\python.exe backend\run.py
```

### PyCharm
Settings → Project → Python Interpreter → Add → System Interpreter → 选择 `python\python.exe`

### 注意事项
- **不要用 `-m` 方式启动**：`python\python.exe -m backend.run` 会报 ModuleNotFoundError，因为项目根目录不在 `_pth` 的搜索路径中，且不应硬编码项目路径
- **不要用 venv**：embeddable Python 本身就是隔离环境，不需要再创建虚拟环境
- **`_pth` 不要加绝对路径**：否则换电脑/换盘符又坏了
- **`python/` 加入 `.gitignore`**：本地环境不入仓库

## 与 venv 的对比

| 特性 | .venv | Embeddable Python |
|------|-------|-------------------|
| 便携性 | ❌ 硬编码绝对路径 | ✅ 相对路径，可移动 |
| 依赖 pip | ✅ | ✅（需手动启用） |
| 隔离性 | ✅ | ✅ 自身就是隔离环境 |
| PyCharm 支持 | ✅ 自动识别 | ✅ 需手动配置 System Interpreter |
| 换电脑 | ❌ 必须重建 | ✅ 直接可用 |

## Claude Code 便携配置

### 记忆目录 Junction
```powershell
New-Item -ItemType Junction -Path "$env:USERPROFILE\.claude\projects\X--ProjectName\memory" -Target "项目路径\.claude\memory"
```

### 自动配置脚本
见 `setup_claude_portable.bat`，核心逻辑：
1. 根据项目路径自动计算 Claude 项目目录名（`:` → 空，`\` → `--`）
2. 创建 Junction 链接记忆目录
3. 复制全局设置（API密钥等）
