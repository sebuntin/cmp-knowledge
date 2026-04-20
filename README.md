# CMP Knowledge Vault

基于 [Karpathy LLM Wiki](https://gist.github.com/karpathy/442a6bf555914893e9891c11519de94f) 模式构建的 Obsidian 个人知识库，用于管理 **Compose for HarmonyOS（CMP）融合渲染架构**的结构化知识。

## 设计理念

> **不是 RAG（每次查询都重新检索原始文档），而是让 LLM 增量构建并维护一个持久的、互联的 Wiki。**
> 知识被编译一次，然后持续更新——而不是每次查询都重新推导。

三个原则：

1. **人类策展** — 选取源文档、提出问题、引导分析方向
2. **LLM 维护** — 摘要、交叉引用、归档、一致性维护
3. **知识复利** — 每次 ingest 和 query 都让 Wiki 更丰富

## 目录结构

```
cmp-knowledge/
├── CLAUDE.md                    # Wiki Schema（LLM 行为规范）
├── raw/                         # 原始源文档（不可变，LLM 只读）
│   ├── assets/                  # 图片资源
│   └── *.md                     # 源文档
├── wiki/                        # LLM 生成的 Wiki
│   ├── index.md                 # 内容目录
│   ├── log.md                   # 活动日志
│   ├── 使用指南.md               # 使用方法说明
│   ├── concepts/                # 概念页（核心概念、技术术语）
│   ├── entities/                # 实体页（类、组件、模块）
│   ├── sources/                 # 源文档摘要页（src- 前缀）
│   └── analysis/                # 分析页（对比、深度分析）
└── .obsidian/                   # Obsidian 配置
```

## 当前内容

| 类别 | 数量 | 说明 |
|------|------|------|
| 源文档 (raw) | 10 | 融合渲染架构设计、Canvas 生命周期、NodeCoordinator、混排原理等 |
| 概念页 | 5 | 融合渲染架构、脏区管理、OH_Drawing 命令转换、ContentModifier 挂载、RenderNode 生命周期 |
| 实体页 | 3 | OHRenderNode、SkPictureRecorder、SkCanvas |
| 源文档摘要 | 10 | 每篇源文档的结构化摘要 |

## 三步使用

### 1. 添加源文档

将文档放入 `raw/` 目录（Markdown、PDF、截图等）。源文档不可变，LLM 只读不写。

### 2. 录入 Wiki

在 Obsidian 中使用 Claudian 插件，说：

> "请录入 raw/xxx.md"

LLM 会阅读源文档、创建摘要页和概念页、更新交叉引用和索引。

### 3. 查询与维护

- **提问**：对 LLM 说 "Wiki 中关于 XXX 的内容是什么？"
- **健康检查**：定期说 "请 Lint Wiki"

## 覆盖的核心主题

- Fusion Renderer 统一渲染管线（基于 OHOS RenderService）
- SkiaRender 自渲染路径（基于 OpenGL ES / XComponent）
- 两种路径的策略模式隔离架构
- SkPicture 录制机制与脏区管理
- OH_Drawing 命令转换层
- ContentModifier 挂载与 Picture/Node 模式决策
- RenderNode 生命周期（创建、复用、缓存、销毁）
- ComposeUI 与 ArkUI 混排原理
- Coil 图片解码与零拷贝优化

## 工具链

- [Obsidian](https://obsidian.md) — 知识库浏览与编辑
- [Claudian](https://github.com/nicosqlity/claudian) — Obsidian 内的 AI 助手（Claude Code 集成）
- [obsidian-git](https://github.com/Vinzent03/obsidian-git) — 自动 Git 同步

## License

本知识库内容基于项目源文档整理，遵循各源文档的原始许可证。
