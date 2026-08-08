# 20260808 项目结构优化：根目录清理与便携工具统一迁移

## 一、案例基本信息
- 问题场景分类：项目结构优化
- 产生时间：2026-08-08
- 项目模块：项目根目录、backend/tools/、portable/
- 相似问题判定特征：
  1. 根目录出现不属于项目核心的文件夹（如误装的 node_modules）
  2. 便携式应用散落在项目多个位置，无统一管理
  3. 代码中引用的路径因文件移动而需要批量更新
  4. .gitignore 中对便携工具的忽略规则分散

## 二、原始问题描述
1. 项目根目录下有一个 `node_modules/`，里面只有一个误装的 `date-fns`（5.8MB），项目根目录没有 `package.json`，是误操作产生的
2. 便携式工具散落在不同位置：`python/` 在根目录，`ffmpeg/` 和 `unlock/` 在 `backend/tools/` 下，结构不清晰
3. 随着项目发展可能还会加入更多便携工具（如 MySQL、Node.js），需要统一管理

## 三、核心诉求
1. 删除误装的根目录 `node_modules/`
2. 将所有便携式应用统一到 `portable/` 目录下
3. 同步更新所有源码中的路径引用
4. 更新 `.gitignore` 和文档

## 四、最终解决方案/改造步骤

### 4.1 删除根目录误装的 node_modules
```bash
rm -rf U:/MusicRate/node_modules
```
根目录无 `package.json`，`node_modules/` 里的 `date-fns` 在项目代码中无任何引用，是误操作产物。

### 4.2 便携工具迁移
```
python/                  → portable/python/
backend/tools/ffmpeg/    → portable/ffmpeg/
backend/tools/unlock/    → portable/unlock/
```

### 4.3 需要更新的源码文件

| 文件 | 修改内容 |
|------|----------|
| `backend/utils/unlock.py` | ffmpeg/ffprobe 路径：`'..', 'tools', 'ffmpeg'` → `'..', '..', 'portable', 'ffmpeg'` |
| `backend/utils/kgg_converter.py` | kgg-dec 路径：从相对路径改为基于 `__file__` 的绝对路径计算 |
| `frontend/auto-record.js` | ffmpeg 绝对路径：`backend\\tools\\ffmpeg` → `portable\\ffmpeg` |
| `.gitignore` | 合并为 `portable/` 整体忽略 |
| `CLAUDE.md` | 更新路径描述 |

### 4.4 .gitignore 变更
旧规则（分散）：
```
backend/tools/ffmpeg/*.exe
backend/tools/unlock/*.exe
backend/tools/*.exe
python/
```

新规则（统一）：
```
portable/
```

## 五、关键代码/配置/模板

### 路径计算方式（推荐：基于文件位置）
```python
# backend/utils/unlock.py — 正确方式
current_dir = os.path.dirname(os.path.abspath(__file__))
FFMPEG_PATH = os.path.abspath(os.path.join(current_dir, '..', '..', 'portable', 'ffmpeg', 'ffmpeg.exe'))
```

```python
# backend/utils/kgg_converter.py — 修复后
_current_dir = os.path.dirname(os.path.abspath(__file__))
KGG_DEC_EXE_PATH = Path(os.path.abspath(os.path.join(_current_dir, '..', '..', 'portable', 'unlock', 'kgg-dec.exe')))
```

### 不推荐的方式（相对路径，依赖工作目录）
```python
# ❌ 旧写法，运行时工作目录不对就会找不到文件
KGG_DEC_EXE_PATH = Path("portable/unlock/kgg-dec.exe")
```

## 六、踩坑点 & 注意事项
- **相对路径陷阱**：`kgg_converter.py` 原来用的 `Path("tools/unlock/kgg-dec.exe")` 是相对路径，依赖工作目录是项目根目录。移动后必须改为基于 `__file__` 的绝对路径计算，否则从其他目录启动时会找不到 exe
- **NCM 解密不受影响**：`ncm_unlock.py` 是纯 Python 实现，不依赖 `portable/unlock/` 下的 exe 文件，只有 `kgg_converter.py` 才调用 `kgg-dec.exe`
- **遗留路径清理**：`unlock.py` 的 `possible_paths` 中有旧项目 `AudioConnect` 的路径（`U:\project\python\AudioConnect\...`），应一并清理
- **`backend/tools/` 保留**：该目录仍保留业务脚本（`get-pip.py`、`setup_claude_portable.bat`），只移走了便携 exe

## 七、同类问题快速适配规则
- 【适配点1】以后新增便携工具（如 MySQL、Node.js），直接放入 `portable/` 目录，在 `.gitignore` 中无需额外配置（`portable/` 已整体忽略）
- 【适配点2】引用便携工具的路径，一律使用 `os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '..', 'portable', ...)` 方式，不要用相对路径
- 【适配点3】误装的 `node_modules/` 判断标准：该目录下无对应的 `package.json`，且包在项目代码中无引用
