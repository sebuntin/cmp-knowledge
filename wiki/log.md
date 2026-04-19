# Wiki Log

本文件是 Wiki 的活动日志，按时间顺序追加记录所有操作。

---

## [2026-04-19] init | LLM Wiki 系统初始化

**操作类型**: init
**描述**: 基于 Karpathy 的 LLM Wiki 模式初始化知识库系统。创建三层架构（raw / wiki / schema），建立 index.md 和 log.md。
**影响页面**: index.md, log.md

---

## [2026-04-19] ingest | CMP融合渲染架构设计文档

**操作类型**: ingest
**描述**: 录入 CMP 融合渲染架构设计文档（~131KB，六章）。提取 6 个关键发现，创建 1 个源文档摘要页、5 个概念页、3 个实体页。
**影响页面**: src-CMP融合渲染架构设计文档.md, 融合渲染架构.md, SkPicture与脏区管理.md, OH_Drawing命令转换.md, ContentModifier挂载机制.md, RenderNode生命周期.md, OHRenderNode.md, SkPictureRecorder.md, SkCanvas.md, index.md, log.md
**详情**:
- 源文档摘要页：6 个关键发现，命令映射表，数据流全景
- 概念页：融合渲染架构（三阶段绑定、四层数据流）、脏区管理（fDrawBounds 机制、四大优化策略）、OH_Drawing 命令转换（映射表、RecordCmdUtils 生命周期）、ContentModifier 挂载（Picture/Node 双模式、决策逻辑）、RenderNode 生命周期（三级复用策略）
- 实体页：OHRenderNode（核心方法、成员变量表）、SkPictureRecorder（录制流程）、SkCanvas（命令转换、脏区跟踪）

---

## [2026-04-19] ingest | raw/ 目录批量录入（9 个文档）

**操作类型**: ingest
**描述**: 并行录入 raw/ 目录下所有 9 个 Markdown 文档，每个创建源文档摘要页，更新 index.md 和 log.md。
**影响页面**: 9 个 src- 页面, index.md, log.md
**详情**:
- **Canvas生命周期详解**：三层 Canvas 类型（录制 Canvas / JNI Canvas / 回放 Canvas）、四阶段生命周期（创建→传递→使用→回放）、五步 doRedraw 流程
- **Coil图片解码与零拷贝优化**：识别 DMA→CPU 冗余拷贝瓶颈、SkiaImageWrapper 零拷贝方案、33MB 内存节省、10-15ms 延迟消除
- **ComposeUI与ArkUI混排原理**：双层 InteropBridge 架构（Kotlin + C++）、测量回流机制、坐标同步、延迟销毁策略、绘制层嵌入
- **applyChanges_unwind_backtrace_analysis**：KN eager stack trace 捕获导致 87% CPU 开销、LazyList 滚动触发 LaunchedEffect 取消、6 种触发场景、P0 优化建议
- **coil+skia自渲染解码原理**：延迟解码设计（draw 时触发）、SkBitmapCache 机制、sk_malloc vs DiscardableMemory 内存策略
- **图解NodeCoordinator**：LayoutModifier-only Coordinator 创建、双向链表结构、Constraints 64-bit 编码、两阶段布局协议、三级坐标系
- **渲染模式隔离架构设计文档**：三层隔离（构建层/运行时策略层/ArkTS 分发层）、BackendId 全链路传递、六个策略接口、逃生通道机制
- **融合渲染全阶段拆解**：四棵树七阶段渲染管线、手势处理占 12.71% 为第二大成本、Kotlin 绘制仅占 1.79%、重组优化 94%、doMeasureAndLayout 每帧调用两次
- **融合渲染整体方案总结**：四层架构渲染管线、双模式决策逻辑、嵌套录制机制、GraphicsLayer 属性分类、五项性能优化
