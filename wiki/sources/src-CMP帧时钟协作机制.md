---
type: source
created: 2026-04-26
updated: 2026-04-26
source_file: raw/CMP帧时钟协作机制.md
ingested: 2026-04-26
tags:
  - 帧时钟
  - BroadcastFrameClock
  - FlushCoroutineDispatcher
  - OhosUiDispatcher
  - Recomposer
  - 协程
  - VSync
related:
  - "[[融合渲染架构]]"
  - "[[Messenger通信机制]]"
---

# CMP 帧时钟协作机制

## 摘要

本文档详细梳理了 CMP 中 OhosUiDispatcher、BroadcastFrameClock 和两个 FlushCoroutineDispatcher（recomposeDispatcher / effectDispatcher）的帧时钟协作机制。核心问题是如何在一个 VSync 周期内按正确顺序调度 Recomposition、Animation/Effect、Measure/Layout/Draw 三类工作，确保时序正确。

## 关键发现

- **两级 BroadcastFrameClock 级联**：BaseComposeScene.frameClock → Recomposer → Recomposer.broadcastFrameClock → 用户 effect 协程，控制权分层
- **FlushCoroutineDispatcher 双路径 dispatch**：路径 A（immediateTasks 同步队列，flush 消费）+ 路径 B（scope.launch via OhosUiDispatcher 异步回退），通过 runLock 互斥
- **recomposeDispatcher 最多 1 个任务**：只有一个 recomposer 协程运行其上，同一 continuation 只能 resume 一次
- **effectDispatcher 可有 N 个任务**：每个 LaunchedEffect / 动画都是独立协程
- **sendFrame 内全部同步执行**：onFrame 在 sendFrame 中同步运行，然后 continuation.resumeWith 投递到 dispatcher
- **LaunchedEffect 有一帧启动延迟**：帧 K 阶段 3 投递，帧 K+1 阶段 1 执行

## 重要细节

### render() 六阶段

1. flush effectDispatcher（处理上帧产出的 effect 任务）
2. flush recomposeDispatcher（处理 continuation resume）
3. frameClock.sendFrame（级联触发 recomposer → 用户 effect → recompose → applyChanges）
4. measure + layout
5. pointer events + Snapshot 通知
6. draw

### 路径 B 的自举作用

状态变化通过路径 B 驱动 recomposer 到达 withFrameNanos 挂起点，进而通过 onNewAwaiters 触发帧请求，启动 render() 循环。

### 协程上下文组装

| Coroutine | Dispatcher | MonotonicFrameClock |
|-----------|-----------|-------------------|
| Recomposer main loop | recomposeDispatcher | BaseComposeScene.frameClock |
| LaunchedEffect | effectDispatcher | Recomposer.broadcastFrameClock |
| rememberCoroutineScope.launch | effectDispatcher | Recomposer.broadcastFrameClock |

## 与已有知识的关联

- 补充了 [[融合渲染架构]] 中帧循环的具体调度细节
- 与 [[Messenger通信机制]] 共享 OhosUiDispatcher 作为底层调度通道
- OhosUiDispatcher 的 MonotonicFrameClock 接口在 CMP 中实际无调用者，由 BroadcastFrameClock 承担帧时钟功能
