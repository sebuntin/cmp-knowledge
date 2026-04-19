# CLAUDE.md — LLM Wiki Schema

本文件是 LLM Wiki 的核心配置文件，定义了 Wiki 的结构、约定和工作流。
它告诉 LLM Agent（Claude Code / Claudian）如何维护这个知识库。

## 设计理念

本知识库基于 Karpathy 的 LLM Wiki 模式构建，核心理念：

> **不是 RAG（每次查询都重新检索原始文档），而是让 LLM 增量构建并维护一个持久的、互联的 Wiki。**
> 知识被编译一次，然后持续更新——而不是每次查询都重新推导。

三个原则：
1. **人类策展**：你负责选取源文档、提出问题、引导分析方向
2. **LLM 维护**：LLM 负责所有"苦力活"——摘要、交叉引用、归档、一致性维护
3. **知识复利**：每次 ingest 和 query 都让 Wiki 更丰富，知识不断积累

## 三层架构

```
raw/                    ← 原始源文档层（不可变，LLM 只读）
wiki/                   ← Wiki 层（LLM 读写，人类浏览）
CLAUDE.md               ← Schema 层（本文件，LLM 的行为规范）
```

### Raw 层 (`raw/`)

- 存放原始源文档：文章、论文、截图、数据文件
- **不可变性**：LLM 读取但绝不修改原始文件
- 图片资源存放在 `raw/assets/`
- 支持格式：`.md`, `.pdf`, `.png`, `.jpg`, `.txt`

### Wiki 层 (`wiki/`)

- LLM 生成的结构化知识页面
- 由 LLM 完全拥有和操作——人类浏览，LLM 编写
- 特殊文件：
  - `wiki/index.md` — 内容目录（按分类列出所有页面）
  - `wiki/log.md` — 活动日志（按时间追加记录）

### Schema 层 (`CLAUDE.md`)

- 本文件，定义 Wiki 的规则和约定
- 由人类和 LLM 共同演化

## 目录结构

```
cmp-knowledge/                   # Vault 根目录
├── CLAUDE.md                    # Wiki Schema（本文件）
├── raw/                         # 原始源文档（不可变）
│   ├── assets/                  # 下载的图片资源
│   └── *.md / *.pdf / ...       # 源文档文件
├── wiki/                        # LLM 生成的 Wiki
│   ├── index.md                 # 内容目录
│   ├── log.md                   # 活动日志
│   ├── 使用指南.md               # 使用方法说明
│   ├── concepts/                # 概念页（核心概念、技术术语）
│   ├── entities/                # 实体页（类、组件、模块）
│   ├── sources/                 # 源文档摘要页（src- 前缀）
│   └── analysis/                # 分析页（对比、深度分析）
└── (其他现有文件可留在原位，逐步迁移到 raw/)
```

## 页面类型与命名约定

### 文件命名

- 使用 **中文或英文** 命名，与内容语言一致
- 文件名 = 页面标题
- 使用 PascalCase（英文）或自然语言（中文）
- 示例：`Fusion Renderer.md`, `渲染模式决策.md`, `SkPictureRecorder.md`

### 页面类型

| 类型 | 前缀 | 说明 | Frontmatter 字段 |
|------|------|------|-----------------|
| **概念页** | — | 核心概念、技术术语的详细解释 | `type: concept`, `related`, `sources` |
| **实体页** | — | 项目、组件、模块的档案页 | `type: entity`, `category`, `sources` |
| **源文档摘要** | `src-` | 原始文档的摘要和关键提取 | `type: source`, `source_file`, `ingested` |
| **分析页** | `analysis-` | 对比、深度分析、综合 | `type: analysis`, `related`, `sources` |
| **主题页** | — | 综合主题的门户页面 | `type: topic`, `subtopics`, `sources` |

### Frontmatter 格式

每个 Wiki 页面必须包含 YAML frontmatter：

```yaml
---
type: concept  # concept | entity | source | analysis | topic
created: 2026-04-19
updated: 2026-04-19
sources:
  - raw/某文档.md
tags:
  - 标签1
  - 标签2
related:
  - "[[其他页面]]"
---
```

### 页面结构模板

**概念页：**
```markdown
---
type: concept
created: YYYY-MM-DD
updated: YYYY-MM-DD
sources: []
tags: []
related: []
---

# 概念名称

## 定义
（一句话定义）

## 详解
（详细解释）

## 关键要点
- 要点 1
- 要点 2

## 与其他概念的关系
- [[相关概念A]] — 关系描述
- [[相关概念B]] — 关系描述

## 来源
- [[src-源文档名]] — 具体章节
```

**源文档摘要页：**
```markdown
---
type: source
source_file: raw/原文档.md
ingested: YYYY-MM-DD
tags: []
---

# 源文档标题

## 摘要
（200-300 字的核心摘要）

## 关键发现
- 发现 1
- 发现 2

## 重要细节
（值得记录的具体细节）

## 与已有知识的关联
- 更新了 [[某概念]] 的理解
- 与 [[某分析]] 形成对比

## 原文引用
> 重要原文引用（如有）
```

## 核心工作流

### 1. Ingest（录入）

当用户添加新的源文档或要求处理已有文档时：

1. **读取源文档** — 完整阅读 `raw/` 中的文档
2. **讨论要点** — 与用户讨论关键发现，确认重点
3. **创建源文档摘要页** — 在 `wiki/` 中创建 `src-文档名.md`
4. **更新/创建相关页面** — 更新或创建受影响的概念页、实体页
5. **更新 index.md** — 在对应分类中添加新页面条目
6. **追加 log.md** — 记录本次 ingest 操作

**一个源文档可能影响 10-15 个 Wiki 页面。**

### 2. Query（查询）

当用户提出问题时：

1. **搜索相关页面** — 先读 `index.md` 定位，再深入相关页面
2. **综合回答** — 跨页面综合信息，附带 `[[]]` 引用链接
3. **归档有价值的答案** — 如果答案有价值，创建新页面存入 Wiki
4. **追加 log.md** — 记录本次 query

**重要洞察：好的回答应该被保存回 Wiki，而不仅仅是留在聊天记录中。**

### 3. Lint（健康检查）

定期对 Wiki 进行健康检查：

- **矛盾检测** — 页面间的矛盾或不一致
- **过时标记** — 新源文档已取代的旧观点
- **孤儿页面** — 没有入链的页面
- **缺失概念** — 提及但未创建页面的重要概念
- **交叉引用** — 缺失的跨页面链接
- **数据缺口** — 可通过 Web 搜索补充的知识空白

每次 lint 后追加 `log.md` 记录。

## 日志格式

`log.md` 中每条记录使用以下格式：

```markdown
## [YYYY-MM-DD] 操作类型 | 简短描述

**操作类型**: ingest | query | lint | init
**描述**: 一句话描述
**影响页面**: 页面1, 页面2, ...
**详情**: （可选）更多细节
```

使用一致的格式前缀便于搜索：
- `grep "^## \[" log.md | tail -5` — 最近 5 条记录
- `grep "ingest" log.md` — 所有 ingest 操作

## 写作规范

1. **语言**：中文为主，技术术语保留英文原文
2. **链接**：使用 Wiki 链接 `[[]]` 连接相关页面，建立知识网络
3. **标签**：在 frontmatter 的 `tags` 中添加分类标签
4. **简洁**：每个页面聚焦一个主题，避免信息过载
5. **引用**：标注信息来源，指向 `raw/` 中的原始文档
6. **时效**：在 frontmatter 中维护 `updated` 日期
7. **矛盾标记**：发现矛盾时使用 `> [!warning]` callout 标记

## 扩展建议

随着知识库增长，可考虑：
- **Obsidian Web Clipper** — 浏览器扩展，快速将网页文章转为 Markdown 存入 `raw/`
- **Dataview 插件** — 基于 frontmatter 生成动态表格和列表
- **Graph View** — Obsidian 图谱视图，可视化知识网络
- **qmd** — 本地搜索引擎（当 Wiki 规模超过 index.md 管理能力时）
