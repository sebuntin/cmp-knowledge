---
updated: 2026-04-28
source_count: 23
page_count: 56
---

# Wiki Index

本文件是 Wiki 的内容目录，按分类列出所有页面。每次 ingest 或 lint 时由 LLM 自动更新。

## 概览

| 类别 | 页面数 | 说明 |
|------|--------|------|
| 概念 (Concepts) | 18 | 核心概念和技术术语 |
| 实体 (Entities) | 8 | 类、组件、模块 |
| 源文档 (Sources) | 23 | 已录入的原始文档 |
| 分析 (Analysis) | 7 | 对比分析、深度解读 |
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
| [[帧时钟协作机制]] | VSync 周期内按正确时序调度三类工作的协程调度系统 | 帧时钟, BroadcastFrameClock, VSync |
| [[SkiaRenderer渲染管线]] | 自渲染路径通过 XComponent + EGL + OpenGL ES 的完整渲染管线 | SkiaRenderer, EGL, XComponent |
| [[三明治混排结构]] | 自渲染路径中 Compose UI 与 ArkUI 原生组件的混合布局方案 | 三明治结构, InteropContainer, 挖洞 |
| [[手势事件处理机制]] | 触摸事件从 OHOS 到 Compose 的六阶段跨语言传递与处理 | 手势事件, InputStrategy, 命中测试 |
| [[图解协程原理]] | Kotlin 协程通过 CPS 变换和状态机实现轻量级异步并发 | 协程, CPS, Continuation, 状态机 |
| [[SideEffect机制]] | Compose Side Effect API 体系：在 Composable 生命周期内安全执行非纯 UI 操作 | SideEffect, LaunchedEffect, snapshotFlow |
| [[Composable本质]] | @Composable 编译器插件注入 Composer 参数，使函数具备重组能力 | Composable, Composer, Recomposition, Snapshot |
| [[DrawModifier机制]] | 通过 DrawModifierNode 接口和 NodeCoordinator 链实现绘制遍历 | DrawModifier, drawContent, NodeCoordinator |
| [[LayoutModifier机制]] | 通过 LayoutModifierNode 和 NodeChain 双向链表实现分层测量 | LayoutModifier, NodeChain, Constraints |
| [[布局流程]] | MeasurePolicy 三步合一测量，单次测量保证 O(n)，Intrinsic Measurement 协商尺寸 | MeasurePolicy, Constraints, IntrinsicMeasurement |

## 实体 (Entities)

| 页面 | 类别 | 一句话摘要 |
|------|------|-----------|
| [[OHRenderNode]] | C++ 类 | OHOS RenderNode 封装，管理绘制内容和节点树 |
| [[SkPictureRecorder]] | C++ 类 | 绘制指令录制器，录制 SkPicture 并计算脏区 |
| [[SkCanvas]] | C++ 类 | 绘制画布，包装 OH_Drawing_Canvas 执行命令转换 |
| [[ComposeSceneRender]] | Kotlin 类 | 自渲染路径 Skia GPU 渲染管线管理 |
| [[XComponentRender]] | C++ 类 | EGL 渲染上下文管理，VSync 帧回调注册 |
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
| [[src-CMP帧时钟协作机制]] | CMP帧时钟协作机制.md | 2026-04-26 | 6 |
| [[src-OHOS SkiaRenderer渲染管线设计]] | OHOS SkiaRenderer渲染管线设计.md | 2026-04-26 | 5 |
| [[src-自渲染ArkUI原生组件混排设计]] | 自渲染ArkUI原生组件混排设计.md | 2026-04-26 | 5 |
| [[src-CMP鸿蒙化规范对齐模板]] | 工程规范整理.xlsx + 合作对齐硬规范 + 关键模块分析 + 源码 | 2026-04-27 | 12 |
| [[src-MonotonicFrameClock_Injection_Chain]] | MonotonicFrameClock_Injection_Chain.md | 2026-04-27 | 4 |
| [[src-Compose_OHOS_手势事件处理剖析]] | Compose_OHOS_手势事件处理剖析.md | 2026-04-27 | 6 |
| [[src-图解协程原理]] | Kotlin Jetpack 实战 09. 图解协程原理.md | 2026-04-28 | 6 |
| [[src-Compose附带效应一探究竟]] | 带着问题学，Compose附带效应(Side Effect)一探究竟.md | 2026-04-28 | 6 |
| [[src-揭秘Composable的本质]] | 揭秘 Compose 原理：图解 Composable 的本质.md | 2026-04-28 | 6 |
| [[src-深入理解DrawModifier]] | 深入理解 Jetpack Compose DrawModifier.md | 2026-04-28 | 6 |
| [[src-深入理解LayoutModifier]] | 深入理解 Jetpack Compose LayoutModifier.md | 2026-04-28 | 6 |
| [[src-一文看懂Compose布局流程]] | 一文看懂 Jetapck Compose 布局流程.md | 2026-04-28 | 6 |

## 分析 (Analysis)

| 页面 | 一句话摘要 | 标签 |
|------|-----------|------|
| [[analysis-DragAndDrop在OHOS平台的实现]] | DragAndDrop 功能横跨四层的完整架构分析 | DragAndDrop, OHOS, 跨平台 |
| [[analysis-FusionRenderer与SkiaRenderer渲染路径对比]] | 两种渲染路径的架构、帧循环、Surface 管理全维度对比 | FusionRenderer, SkiaRenderer, 渲染路径 |
| [[analysis-两种渲染路径的混排机制对比]] | 内嵌式混排 vs 叠层式混排的架构理念与能力差异 | 混排, 三明治结构, 挖洞 |
| [[analysis-帧时钟在两种渲染路径中的差异]] | 帧时钟内核共用，外壳差异：帧触发、后台心跳、EGL 包装 | 帧时钟, VSync, 帧循环 |
| [[analysis-FusionRenderer渲染数据流全景]] | @Composable 到像素的完整管线：五次格式转换、三层脏区传递、Picture/Node 模式决策 | 融合渲染, 渲染数据流, 管线架构 |
| [[analysis-跨语言通信架构]] | NAPI 直接调用 / Messenger JSON / KN cinterop 三种机制的选择决策与约束 | 跨语言, NAPI, Messenger |
| [[analysis-性能优化体系]] | 六项优化策略（重组跳过、Picture缓存、懒组合、脏区管理、GC抑制、栈回溯优化）的交互关系 | 性能优化, 脏区, 节点复用 |

## 主题 (Topics)

| 页面 | 一句话摘要 |
|------|-----------|
| [[使用指南]] | LLM Wiki 系统的使用方法说明 |
