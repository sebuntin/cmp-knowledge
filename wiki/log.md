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

---

## [2026-04-20] query | DragAndDrop 在 OHOS 平台的实现分析

**操作类型**: query（代码探索 → 分析页）
**描述**: 通过代码探索分析 DragAndDrop 在 OHOS 平台的完整实现，创建 1 个分析页、1 个概念页、3 个实体页。
**影响页面**: analysis-DragAndDrop在OHOS平台的实现.md, Messenger通信机制.md, ComposeSceneDragAndDropNode.md, HarmonyOSDragAndDropManager.md, DragAndDropProxy.md, index.md, log.md
**详情**:
- **分析页**：四层架构（Compose API → 事件分发 → Kotlin 平台管理 → ArkTS 原生桥接）、Messenger 5 种消息类型、完整数据流图
- **概念页**：Messenger 通信机制（Kotlin-ArkTS 双向 JSON 通道）
- **实体页**：ComposeSceneDragAndDropNode（事件分发入口）、HarmonyOSDragAndDropManager（预览图生成+状态管理）、DragAndDropProxy（OHOS dragController API 调用）
- 来源：代码探索分析（非 raw/ 源文档），基于直接阅读 Kotlin 和 ArkTS 源码

---

## [2026-04-20] ingest | LazyColumn 与 Column 原理及性能对比分析

**操作类型**: ingest
**描述**: 录入 LazyColumn 与 Column 原理及性能对比分析（11 章）。提取 6 个关键发现，创建 1 个源文档摘要页、2 个概念页。
**影响页面**: src-LazyColumn与Column原理及性能对比分析.md, SubcomposeLayout与懒组合.md, LazyColumn vs Column 选型决策.md, index.md, log.md
**详情**:
- **源文档摘要页**：6 个关键发现——LazyColumn 是组合控制器而非回收列表、SubcomposeLayout 打破阶段分离、首帧无懒加载优势、item.key 四个作用、CMP 单线程放大效应、<20 项应用 Column
- **概念页**：SubcomposeLayout 与懒组合（测量阶段触发组合的机制与代价）、LazyColumn vs Column 选型决策（决策树与首帧优化策略）

---

## [2026-04-20] lint | Wiki 内容与代码一致性检查

**操作类型**: lint
**描述**: 对 Wiki 所有实体页和概念页与当前代码进行交叉验证。
**影响页面**: SkCanvas.md, OH_Drawing命令转换.md
**详情**:
- **已修正错误 1**：`SkCanvas` 实体页中 `operator OH_Drawing_Canvas*()` 描述错误。Wiki 写的是 `return fDrawingCanvas;`（透明访问），实际代码会先调用 `initDrawingCanvas()` 确保画布就绪
- **已修正错误 2**：`OH_Drawing命令转换` 概念页中使用了不存在的函数名 `convertPaintToPen`。实际 Paint 转换通过 `attachPaint(paint)` + `detachPaint()` 实现
- **已修正错误 3**：`OH_Drawing命令转换` 概念页中转换运算符同样遗漏了 `initDrawingCanvas()` 调用
- **验证通过**：OHRenderNode（方法/成员变量准确）、SkPictureRecorder（录制流程准确）、RenderNode生命周期（状态标志准确）、ContentModifier挂载机制（决策逻辑准确）、SkPicture与脏区管理（脏区机制准确）、DragAndDrop 相关页面（5 页全部准确）、源文档摘要页（4 篇抽样全部准确）

---

## [2026-04-26] ingest | raw/ 新增文档批量录入（3 个文档）

**操作类型**: ingest
**描述**: 录入 raw/ 目录下 3 个新增文档，创建 3 个源文档摘要页、3 个概念页、2 个实体页。
**影响页面**: src-CMP帧时钟协作机制.md, src-OHOS SkiaRenderer渲染管线设计.md, src-自渲染ArkUI原生组件混排设计.md, 帧时钟协作机制.md, SkiaRenderer渲染管线.md, 三明治混排结构.md, ComposeSceneRender.md, XComponentRender.md, index.md, log.md
**详情**:
- **CMP帧时钟协作机制**：两级 BroadcastFrameClock 级联、FlushCoroutineDispatcher 双路径 dispatch、render() 六阶段流程、协程上下文组装
- **OHOS SkiaRenderer渲染管线设计**：SkiaLayer 空壳、6 个策略接口隔离、ComposeSceneRender 三种绘制模式、EGL 资源分层、尺寸通知迂回路径
- **自渲染ArkUI原生组件混排设计**：三明治五层叠放、InteropContainer 三层选择、BACK 层挖洞机制、PasteButton 免权限集成
- **新增概念页**：帧时钟协作机制、SkiaRenderer渲染管线、三明治混排结构
- **新增实体页**：ComposeSceneRender（Kotlin Skia GPU 管线）、XComponentRender（C++ EGL 上下文管理）

---

## [2026-04-27] analysis | 三篇跨文档对比分析

**操作类型**: analysis
**描述**: 基于已有概念页和源文档摘要页，创建 3 篇跨文档对比分析页。
**影响页面**: analysis-FusionRenderer与SkiaRenderer渲染路径对比.md, analysis-两种渲染路径的混排机制对比.md, analysis-帧时钟在两种渲染路径中的差异.md, index.md, log.md
**详情**:
- **渲染路径对比**：架构层、帧循环、Surface 管理、策略接口六维度全量对比，识别 FusionRenderer 拉模型 vs SkiaRenderer 推模型的本质差异
- **混排机制对比**：内嵌式混排（FusionRenderer RenderNode 直接嵌入 ArkUI 树）vs 叠层式混排（SkiaRenderer 三明治五层 Stack + 挖洞），分析挖洞的必要性和选择建议
- **帧时钟差异**：帧时钟内核（两级级联 + 双路径 dispatch + 六阶段）完全共用，外壳差异集中在帧触发方式、后台心跳、EGL 绘制包装

---

## [2026-04-27] lint | Wiki 内容整理

**操作类型**: lint
**描述**: 全量检查 Wiki 内容一致性，修复断裂 wikilink、补充缺失 frontmatter、标记未录入 raw 文件。
**影响页面**: 使用指南.md, ComposeSceneDragAndDropNode.md, src-CMP融合渲染架构设计文档.md, src-CMP鸿蒙化规范对齐模板.md, 所有 source 页 frontmatter, index.md, log.md
**详情**:
- **修复 4 个断裂 wikilink**：使用指南的 `[[CLAUDE.md]]`、src-CMP融合渲染架构设计文档的 `[[渲染模式隔离架构设计文档]]`（缺 src- 前缀）、src-CMP鸿蒙化规范对齐模板的 `[[FusionRenderer与SkiaRenderer渲染路径对比]]`（缺 analysis- 前缀）、ComposeSceneDragAndDropNode 的 `[[DragAndDropNode]]`（无对应页面，改为指向分析页）
- **修正 source 引用**：src-CMP融合渲染架构设计文档 的 source_file 标注为 docs/ 路径（原始文档未存入 raw/）
- **补充 frontmatter**：所有 15 个 source 页补充 `created` 和 `updated` 字段（取 ingested 日期）
- **标记未录入 raw 文件**：index.md 新增"待录入"节，标记 `Compose_OHOS_手势事件处理剖析.md`（~32KB）和 `MonotonicFrameClock_Injection_Chain.md`（~3KB）

---

## [2026-04-27] ingest | 2 个 raw 文档录入

**操作类型**: ingest
**描述**: 录入剩余 2 个 raw 文档，创建 2 个源文档摘要页、1 个概念页，更新相关页面交叉引用。
**影响页面**: src-MonotonicFrameClock_Injection_Chain.md, src-Compose_OHOS_手势事件处理剖析.md, 手势事件处理机制.md, 帧时钟协作机制.md, 融合渲染架构.md, index.md, log.md
**详情**:
- **MonotonicFrameClock_Injection_Chain**：分析 withFrameNanos 通过 CoroutineContext 依赖注入找到 BroadcastFrameClock 的 5 步链路，补充了帧时钟协作机制"Why"层面的理解
- **Compose_OHOS_手势事件处理剖析**：触摸事件六阶段链路（ArkTS→NAPI→Kotlin→策略分发→事件转换→Compose 处理），两种渲染路径 InputStrategy 差异、多指追踪、GC 抑制
- **新增概念页**：手势事件处理机制（六阶段链路、事件转换核心、关键优化）
- **交叉引用更新**：帧时钟协作机制添加 MonotonicFrameClock 注入链关联、融合渲染架构添加手势事件关联
- **index.md 更新**：移除待录入标记，统计更新为 12 概念 + 17 源文档 = 41 页

---

## [2026-04-27] analysis | 三篇跨主题综合分析

**操作类型**: analysis
**描述**: 识别知识库中跨多个概念/实体页但缺乏综合分析的复杂主题，创建 3 篇综合分析页。
**影响页面**: analysis-FusionRenderer渲染数据流全景.md, analysis-跨语言通信架构.md, analysis-性能优化体系.md, index.md, log.md
**详情**:
- **FusionRenderer 渲染数据流全景**：综合 5 概念页 + 3 实体页，追踪 @Composable 到像素的五次格式转换、三层脏区传递、Picture/Node 模式完整决策路径、帧循环时序对应关系
- **跨语言通信架构**：提炼三种通信机制（NAPI 直接调用 / Messenger JSON / KN cinterop）的适用场景、调用链路、选择决策和关键约束（线程安全、链接约束、导入约束）
- **性能优化体系**：按渲染管线阶段组织六项优化策略（重组跳过 94%、Picture 缓存、懒组合、脏区管理 + 节点复用、GC 抑制、applyChanges 栈回溯），分析策略间的增强和冲突关系，提供瓶颈定位指南

## [2026-04-28] ingest | Clippings 6 篇文章批量录入

**操作类型**: ingest
**描述**: 将 Clippings 目录下 6 篇 Compose 基础知识文章录入 wiki
**影响页面**: index.md, log.md, 6 个 source 页, 6 个 concept 页
**详情**:
- **源文档移动**：Clippings/ → raw/，Clippings 目录已清空删除
- **新建 6 个源文档摘要页**：src-图解协程原理、src-Compose附带效应一探究竟、src-揭秘Composable的本质、src-深入理解DrawModifier、src-深入理解LayoutModifier、src-一文看懂Compose布局流程
- **新建 6 个概念页**：图解协程原理、SideEffect机制、Composable本质、DrawModifier机制、LayoutModifier机制、布局流程
- **index.md 更新**：概念 12→18，源文档 17→23，总页数 44→56
- 每个概念页均建立了与已有 wiki 页面的交叉引用（帧时钟协作机制、融合渲染架构等）

---

## [2026-04-30] lint | Wiki 目录分类整理

**操作类型**: lint
**描述**: 对 concepts/ 和 analysis/ 目录按主题建立子目录分类。
**影响页面**: index.md, log.md, 所有 concepts/ 和 analysis/ 页面（路径变更）
**详情**:
- **concepts/ → 4 子目录**：rendering/（6 页：融合渲染架构、脏区管理、命令转换、ContentModifier、RenderNode生命周期、SkiaRenderer管线）、compose-basics/（6 页：协程、SideEffect、Composable本质、DrawModifier、LayoutModifier、布局流程）、platform/（3 页：Messenger、手势事件、三明治混排）、performance/（3 页：帧时钟、懒组合、选型决策）
- **analysis/ → 2 子目录**：rendering/（4 页：数据流全景、路径对比、性能优化、帧时钟差异）、platform/（3 页：跨语言通信、混排对比、DragAndDrop）
- **index.md 重写**：概念和分析节按子目录分组展示
- entities/ 和 sources/ 维持扁平结构不变（实体数量适中，源文档按时间排列即可）

---

## [2026-04-30] query | 同层渲染实现分析

**操作类型**: query（代码探索 → 概念页 + 更新分析页）
**描述**: 通过代码探索分析 FusionRenderer 路径的同层渲染（ExternalRenderNode）实现，创建 1 个概念页，更新 2 个已有页面。
**影响页面**: 同层渲染.md, 三明治混排结构.md, analysis-两种渲染路径的混排机制对比.md, index.md, log.md
**详情**:
- **新增概念页**：同层渲染（ExternalRenderNode 桥接、两种创建路径、InteropViewPainter 绘制基类、useStacked() 策略路由、坐标映射、ArkUIView/ArkUINativeView 实现）
- **更新三明治混排结构**：添加局限性说明，指出三明治仅适用于 SkiaRenderer，FusionRenderer 使用同层渲染
- **更新混排机制对比**：结论改为 FusionRenderer 同层渲染优先、旧设备回退叠层；FusionRenderer 架构图从内嵌式改为 ExternalRenderNode 同层渲染；混排能力对比表从 2 列扩展为 3 列（同层/叠层/SkiaRenderer）；更新通信机制对比
- **index.md 更新**：概念 18→19，总页数 56→57
- 来源：代码分析（非 raw/ 源文档），基于直接阅读 Kotlin、ArkTS 和 C++ 源码
