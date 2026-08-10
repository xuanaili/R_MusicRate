# MusicRate 测试 skill（pytest 测试驱动工作流）

> **配对加载**：与「开发 skill」（`20260810_feature_development_workflow.md`）**必须成对使用**。
> 新需求开启新对话时，同时加载本文件 + 开发 skill，按「测试先行 → 实现 → 验证 → 提交」推进，两者互相验证修改。

## 1. 测试基础设施
- 测试统一放 **`backend/tests/`**，pytest 框架（已装入便携 Python，`pytest.ini` 在项目根）
- 运行命令（项目根目录）：
  ```bash
  portable\python\python.exe -m pytest                                  # 快速单测（默认跳过 realdata）
  portable\python\python.exe -m pytest -m realdata                      # 真实 DB/网络集成测试
  portable\python\python.exe -m pytest backend/tests/test_xxx.py -k 关键词   # 单文件/定向
  ```
- 关键配置（见 `pytest.ini`）：`testpaths = backend/tests`（避免误收 site-packages 里的 setuptools 自带测试）；`addopts = -m "not realdata"`
- `backend/tests/conftest.py`：自动把项目根加入 `sys.path`，测试内直接 `from backend.utils.xxx import ...`

## 2. 测试编写规范
- **纯逻辑函数/工具 → 单测**，零依赖（无 MySQL / 真实网络），秒级跑完，这是微调回归的主力
- **依赖真实 DB / 网络 → 加 `@pytest.mark.realdata`**，默认跳过，用 `-m realdata` 单独跑
- 命名：`test_<模块>_<场景>`，用 `class TestXxx` 分组；断言用 assert，不写死系统路径
- 测试只测**行为结果**，不 mock 到失去意义
- 现有首批单测参考：`backend/tests/test_score.py`（评分计算）、`backend/tests/test_json.py`（safe_json_loads）——新功能按同样模式补充

## 3. 测试驱动流程（与开发并行）
对每个功能点，顺序执行：
1. **测试先行**：先写测试描述预期行为 → 跑测试确认**红灯**（失败）
2. **开发实现**：按开发 skill 实现功能
3. **验证**：跑测试确认**绿灯**（全部通过）
4. **回归**：后续任何代码修改后，重跑全量测试

## 4. 与开发 skill 的互验协议（核心）
- 开发改了行为 → **必须**跑测试验证；测试是代码行为的唯一判定标准
- 测试失败 → **二选一**：改代码；或需求确实变更 → 按新需求明确更新测试（不允许静默跳过/删除测试来掩盖）
- 提交时：**代码 + 对应测试用例一起提交**，不留"没测试的代码"
- 测试失败但功能"看似正常" → 说明测试与实现不一致，优先补测试/对齐测试，不要无视
- 调试排错时：先用测试缩小范围（单测定位到函数），再动真实接口

## 5. 固定指令
新对话开发需求时：先读本文件 + 开发 skill（`20260810_feature_development_workflow.md`），按「测试先行 → 实现 → 验证 → 提交」推进。每个功能点产出 = 实现代码 + 测试用例，缺一不可。
