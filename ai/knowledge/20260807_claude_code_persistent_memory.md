# Claude Code 持久化记忆机制 — 对话结束自动归档

## 概述
利用 Claude Code 的持久化记忆系统，实现"对话结束"关键词触发自动归档到 `./ai/` 子目录的功能。

## 记忆文件位置
```
C:\Users\20135272\.claude\projects\U--MusicRate\memory\
├── MEMORY.md                          ← 索引文件（每次新对话自动加载）
└── conversation-summary-hook.md       ← 具体指令内容
```

## 机制原理
1. **MEMORY.md** 是索引文件，每次新对话自动加载到 Claude 上下文
2. 索引中列出所有记忆文件的链接和一句话描述
3. Claude 读取索引后，根据对话内容匹配相关记忆
4. 记忆文件中的指令会被 Claude 主动遵守

## 记忆文件格式
```markdown
---
name: <短横线命名slug>
description: <一句话描述，用于召回时判断相关性>
metadata:
  type: user | feedback | project | reference
---

<正文内容，可链接其他记忆：[[name]]>
```

## 类型说明
| type | 用途 | 示例 |
|------|------|------|
| `user` | 用户角色、偏好、专业知识 | 用户是全栈开发者 |
| `feedback` | 工作方式指导、纠正 | 代码注释用中文 |
| `project` | 项目级约束、工作流 | 对话结束自动归档 |
| `reference` | 外部资源链接 | API文档地址 |

## 对话结束归档流程
1. 用户说"对话结束" → Claude 识别触发条件
2. 回顾本次对话，判断内容属于哪个 `./ai/` 子目录
3. 读取该子目录的模板文件（如 `00_template.md`）
4. 按模板格式生成总结文档，命名 `YYYYMMDD_简短英文描述.md`
5. 保存到对应子目录
6. 告知用户文件已保存

## ./ai/ 子目录说明
- `ai_case_notes/` — 典型问题解决方案、排查案例
- `knowledge/` — 知识库文档、技术参考、环境配置、代码样例
- `skill/` — 技能/操作规范、可复用工作流
- 未来新增子目录同样规则：先读模板再按模板生成

## 与 Claude Code Hook 的区别
| 方式 | 触发机制 | 持久性 | 适合场景 |
|------|----------|--------|----------|
| **settings.json Hook** | 工具调用事件（PreToolUse/PostToolUse）自动触发 | 持久，写死在配置 | 自动化脚本、权限控制 |
| **记忆文件** | AI读取上下文后主动识别关键词 | 持久，可随时编辑修改 | 行为指令、工作流约定 |

## 管理操作
- 修改指令：编辑 `memory/conversation-summary-hook.md`
- 添加新指令：在 `memory/` 下新建 `.md` 文件，在 `MEMORY.md` 加一行索引
- 删除指令：删除 `.md` 文件，从 `MEMORY.md` 移除索引行
- 查看所有指令：查看 `MEMORY.md` 索引
