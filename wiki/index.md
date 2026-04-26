---
updated: 2026-04-20
source_count: 11
page_count: 28
---

# Wiki Index

本文件是 Wiki 的内容目录，按分类列出所有页面。每次 ingest 或 lint 时由 LLM 自动更新。

## 概览

| 类别 | 页面数 | 说明 |
|------|--------|------|
| 概念 (Concepts) | 8 | 核心概念和技术术语 |
| 实体 (Entities) | 6 | 类、组件、模块 |
| 源文档 (Sources) | 11 | 已录入的原始文档 |
| 分析 (Analysis) | 1 | 对比分析、深度解读 |
| 主题 (Topics) | 1 | 综合主题页面（含使用指南） |

## 概念 (Concepts)

| 页面 | 一句话摘要 | 标签 |
|------|-----------|------|
| [[融合渲染架构]] | CMP 在 OHOS 上的端到端渲染管线架构 | 融合渲染, 架构, OHOS |
| [[SkPicture与脏区管理]] | 通过精确计算脏区实现增量渲染优化 | 脏区, SkPicture, 性能优化 |
| [[OH_Drawing命令转换]] | Skia 绘制命令到 OHOS 原生命令的转换机制 | OH_Drawing, 命令转换 |
| [[ContentModifier挂载机制]] | 绘制命令通过 ContentModifier 聚合到 RenderNode | ContentModifier, Picture模式, Node模式 |
| [[RenderNode生命周期]] | OHRenderNode 的创建、复用、缓存和销毁过程 | RenderNode, 生命周期, 节点复用 |
| [[Messenger通信机制]] | Kotlin 与 ArkTS 之间的双向 JSON 消息通信通道 | Messenger, JSON, 跨平台通信 |
| [[SubcomposeLayout与懒组合]] | LazyColumn 核心：在测量阶段按需触发组合的机制 | SubcomposeLayout, LazyColumn, 性能 |
| [[LazyColumn vs Column 选型决策]] | 何时选择 Column 或 LazyColumn 的决策框架 | LazyColumn, Column, 首帧性能 |

## 实体 (Entities)

| 页面 | 类别 | 一句话摘要 |
|------|------|-----------|
| [[OHRenderNode]] | C++ 类 | OHOS RenderNode 封装，管理绘制内容和节点树 |
| [[SkPictureRecorder]] | C++ 类 | 绘制指令录制器，录制 SkPicture 并计算脏区 |
| [[SkCanvas]] | C++ 类 | 绘制画布，包装 OH_Drawing_Canvas 执行命令转换 |
| [[ComposeSceneDragAndDropNode]] | Kotlin 类 | 平台拖拽事件进入 Compose 节点树的唯一入口 |
| [[HarmonyOSDragAndDropManager]] | Kotlin 类 | OHOS 平台拖拽管理器，生成预览图并与 ArkTS 通信 |
| [[DragAndDropProxy]] | ArkTS 类 | 调用 OHOS dragController API 的 ArkTS 拖拽代理 |

## 源文档 (Sources)

| 页面 | 原始文件 | 录入日期 | 关键发现数 |
|------|---------|---------|-----------|
| [[src-CMP融合渲染架构设计文档]] | CMP融合渲染架构设计文档.md | 2026-04-19 | 6 |
| [[src-Canvas生命周期详解]] | Canvas生命周期详解.md | 2026-04-19 | 6 |
| [[src-Coil图片解码与零拷贝优化方案]] | Coil图片解码与零拷贝优化方案.md | 2026-04-19 | 6 |
| [[src-ComposeUI与ArkUI混排原理]] | ComposeUI与ArkUI混排原理.md | 2026-04-19 | 5 |
| [[src-applyChanges_unwind_backtrace_analysis]] | applyChanges_unwind_backtrace_analysis.md | 2026-04-19 | 5 |
| [[src-coil+skia自渲染解码原理]] | coil+skia自渲染解码原理.md | 2026-04-19 | 5 |
| [[src-图解NodeCoordinator]] | 图解NodeCoordinator.md | 2026-04-19 | 5 |
| [[src-渲染模式隔离架构设计文档]] | 渲染模式隔离架构设计文档.md | 2026-04-19 | 6 |
| [[src-融合渲染全阶段拆解]] | 融合渲染全阶段拆解.md | 2026-04-19 | 6 |
| [[src-融合渲染整体方案总结]] | 融合渲染整体方案总结.md | 2026-04-19 | 6 |
| [[src-LazyColumn与Column原理及性能对比分析]] | LazyColumn 与 Column 原理及性能对比分析.md | 2026-04-20 | 6 |

## 分析 (Analysis)

| 页面 | 一句话摘要 | 标签 |
|------|-----------|------|
| [[analysis-DragAndDrop在OHOS平台的实现]] | DragAndDrop 功能横跨四层的完整架构分析 | DragAndDrop, OHOS, 跨平台 |

## 主题 (Topics)

| 页面 | 一句话摘要 |
|------|-----------|
| [[使用指南]] | LLM Wiki 系统的使用方法说明 |
