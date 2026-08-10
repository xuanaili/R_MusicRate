# pytest 收集误入 site-packages + MySQL 结果集键名大小写坑

## 一、案例基本信息
- 问题场景分类：测试环境排坑 / MySQL 结果集键名大小写（非 bug）
- 产生时间：2026-08-10
- 项目模块：`pytest.ini`、`backend/tests/`、`backend/utils/db.py`、`information_schema` 查询
- 来源：从 BookRate 迁移（其 `20260810_pytest_no_traceback_and_info_schema_pitfalls.md`），并合并本次 MusicRate 实际遇到的收集坑
- 相似问题判定特征：
  1. 项目根跑 `pytest` 收集到几百个 `site-packages` 里的测试并报错（如 setuptools 自带测试）
  2. 查询 `information_schema.columns` 后 `row['column_type']` 报 `KeyError`
  3. 写「查表结构/判断缺列再 ALTER」的幂等迁移
  4. 断言失败但看不到 traceback（BookRate 曾遇；MusicRate 已验证无此问题）

## 二、坑1：项目根跑 pytest 误收 site-packages 自带测试（MusicRate 实遇）
- **现象**：在项目根 `portable\python\python.exe -m pytest`，收集阶段报 **41 个 ERROR**，全来自 `portable/python/Lib/site-packages/setuptools/tests/`、`setuptools/_distutils/tests/` 等。
- **根因**：便携 Python 的 site-packages 里装着带 `test_*.py` 的包（setuptools 自带测试），pytest 默认递归收集当前目录下所有 `test_*.py`。
- **解决**：`pytest.ini` 加 `testpaths = backend/tests`，只收集自己的测试目录：
  ```ini
  [pytest]
  testpaths = backend/tests
  addopts = -m "not realdata"
  ```
- **验证**：加后 `collected 15 items`，正常。可用 `pytest --collect-only -q` 确认收集范围。

## 三、坑2：`information_schema.columns` 结果键名是大写
- **现象**：`SELECT column_type, column_default FROM information_schema.columns WHERE ...` 返回的 dict 键是 `COLUMN_TYPE`/`COLUMN_DEFAULT`（大写），`row['column_type']` 抛 `KeyError`。
- **根因**：`information_schema.columns` 表**自身的列名就是大写**（`COLUMN_NAME`/`COLUMN_TYPE`/`COLUMN_DEFAULT`…），`SELECT column_type` 无别名时，返回头沿用列元数据的大写名。而 `COUNT(*) AS c` 是别名，MySQL 保留查询里写的 `c` 小写——所以 `row['c']` 正常、`row['column_type']` 报错，看似矛盾。
- **解决**：一律用 `AS` 别名取小写键，跨 MySQL 大小写配置稳定：
  ```python
  cursor.execute(
      "SELECT column_type AS col_type, column_default AS col_default "
      "FROM information_schema.columns WHERE table_schema=%s AND table_name='users' AND column_name='avatar'",
      (MYSQL_CONFIG['db'],)
  )
  row = cursor.fetchone()
  assert 'varchar' in row['col_type'].lower()
  ```

## 四、坑3（BookRate 曾遇，MusicRate 已验证无此问题）：`--capture=no` 下断言失败不显示 traceback
- **现象**：任何断言失败都只显示 `F`/`FAILED`，无 FAILURES 段、无 traceback。
- **根因**：`--capture=no` + Windows/embeddable Python + `db.py` 顶部 `sys.stdout = io.TextIOWrapper(...)` 重包 stdout 的组合下，pytest 失败报告渲染被破坏。
- **MusicRate 实测**：`backend/utils/db.py` **未**重包 stdout，失败 traceback 显示正常（无需 `--capture=no`，pytest.ini 未加）。
- **如果未来重包 stdout**：失败无 traceback 时，测试体包 `try/except + traceback.print_exc()` 定位真实异常：
  ```python
  def test_xxx():
      try:
          ...  # 测试体
      except Exception as e:
          print('EXC:', repr(e))
          traceback.print_exc()
          raise
  ```

## 五、幂等迁移模板（加列照抄）
```python
def ensure_users_avatar_column():
    db = get_db()
    cursor = db.cursor()
    cursor.execute(
        "SELECT COUNT(*) AS c FROM information_schema.columns "
        "WHERE table_schema=%s AND table_name='users' AND column_name='avatar'",
        (MYSQL_CONFIG['db'],)
    )
    row = cursor.fetchone()
    if row['c'] == 0:
        cursor.execute("ALTER TABLE users ADD COLUMN avatar VARCHAR(255) DEFAULT '' COMMENT '头像URL'")
        db.commit()
    cursor.close()
# init_base_tables() 中 create_users() 之后调用
```

## 六、realdata 测试骨架（需 app_context 包住 get_db）
```python
@pytest.mark.realdata
class TestUserAvatarMigration:
    def test_ensure_users_avatar_column_idempotent(self):
        app = create_app()
        with app.app_context():
            db = get_db()
            ensure_users_avatar_column()
            ensure_users_avatar_column()  # 二次执行验证幂等
            ...
```

## 七、踩坑点 & 注意事项
- **MySQL 返回键大小写**：`SELECT 裸列名` 返回大写键（尤其 information_schema 系列表），`SELECT xxx AS 别名` 返回小写。判断"列是否存在/查表结构"一律加别名。
- **Windows Git Bash 下 `tail` 截断 pytest 输出**：重定向到项目内临时文件再 Read，比 `| tail` 可靠。
- **fixture 无关的探针也要放到 `backend/tests/` 下**（conftest 自动加项目根到 sys.path），`python -c` 直跑需手动 `sys.path.insert`。
- **便携 Python site-packages 混有自带测试包**：新装依赖后若 pytest 收集异常增多，先查 `testpaths` 是否限定。

## 八、同类问题快速适配规则
- 【pytest 收集到别人的测试】`pytest.ini` 加 `testpaths = backend/tests`
- 【查 information_schema 列】SQL 一律 `SELECT ... AS 小写别名`，用别名取键
- 【加列迁移】复制上方幂等模板，改表名/列名/注释，挂进 `init_base_tables()`
- 【realdata 测试】类级 `@pytest.mark.realdata`，`get_db()` 需在 `app.app_context()` 内
- 【断言无 traceback】测试体包 try/except + print（仅当重包 stdout 后出现时才需要）

---

以下为固定指令，下次新开对话直接先贴本文件 + 再贴下方指令：
请以本文档为标准案例范式，解决我接下来的同类问题。优先复用本文的分析逻辑、改造流程、代码模板和避坑规则，不要从零重新思考。根据我新问题的差异点做适配微调，输出稳定、同规范的解决方案。
