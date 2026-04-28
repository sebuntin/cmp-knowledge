---
type: source
source_file: raw/带着问题学，Compose附带效应(Side Effect)一探究竟.md
ingested: 2026-04-28
tags:
  - SideEffect
  - LaunchedEffect
  - DisposableEffect
  - snapshotFlow
  - Composition生命周期
---

# src-Compose附带效应(Side Effect)一探究竟

## 摘要

以问题驱动形式系统讲解 Compose Side Effect API 体系：SideEffect、LaunchedEffect、DisposableEffect、rememberUpdatedState、produceState、snapshotFlow 等的使用场景、生命周期管理和常见陷阱。

## 关键发现

- **SideEffect**：每次成功重组后在主线程同步执行，仅适合轻量任务（日志、状态同步），不能触发状态变更否则死循环
- **LaunchedEffect**：key 驱动的协程启动器，key 变化时取消旧协程启动新协程，Composable 离开组合时自动取消；运行在 effectDispatcher 上
- **DisposableEffect**：提供进入/退出生命周期钩子，onDispose 保证清理（注销监听器、关闭资源）
- **rememberUpdatedState**：解决长运行协程中捕获值过期问题——将值包装为 MutableState，重组时自动更新引用
- **snapshotFlow**：将 Compose State 转为 Kotlin Flow，可配合 debounce/map/collectLatest 等 Flow 操作符，适用于搜索联想等场景
- **produceState**：将非 Compose 数据源（Flow、LiveData）转为 State，兼顾生命周期管理

## 与已有知识的关联

- LaunchedEffect 有一帧启动延迟（帧 K 阶段 3 投递 → 帧 K+1 阶段 1 执行），这与 [[帧时钟协作机制]] 中的 effectDispatcher 双路径机制一致
- snapshotFlow 底层使用 `Snapshot.registerApplyObserver` + `readSet` 追踪依赖
- Side Effect API 是 Recomposer 的 `effectCoroutineContext` 向开发者暴露的接口层

## 来源

- [[SideEffect机制]] — 概念页
