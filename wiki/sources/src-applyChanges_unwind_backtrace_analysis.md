---
type: source
created: 2026-04-19
updated: 2026-04-19
source_file: raw/applyChanges_unwind_backtrace_analysis.md
ingested: 2026-04-19
tags:
  - CMP
  - 调试
  - backtrace
  - applyChanges
  - 崩溃分析
related:
  - "[[融合渲染架构]]"
  - "[[OHRenderNode]]"
  - "[[RenderNode生命周期]]"
  - "[[SkCanvas]]"
---

# applyChanges 中 `_Unwind_Backtrace` 根因分析

## 摘要

基于 hiperf 对 `libkn.so` 的采样分析，`_Unwind_Backtrace` 在 `applyChanges` 调用栈中占比 155M/178M (87%)。根因是 Kotlin/Native 的异常急切栈追踪机制：每次 `LaunchedEffect` 组件随 LazyList 滑动离开 viewport 时，`onForgotten()` 调用 `job.cancel()`，而 cancel 内部 throw 触发 `_Unwind_Backtrace` 遍历 40-70 帧调用栈。这不是业务逻辑开销，而是 KN 运行时异常实现对高频 cancel 操作收取的"税"。

## 关键发现

- **Kotlin/Native 异常急切采集**：与 JVM 的懒惰采集不同，KN 每次 `throw` 立即调用 `_Unwind_Backtrace()` 遍历全部栈帧，即使后续 catch 后不使用 `stackTrace`，代价已经发生
- **LazyList 滑动是最高频触发场景**：每个离开 viewport 的 item 内的 `LaunchedEffect` 都会触发 cancel → throw → unwind，典型每帧 3-6 次
- **调用链完整路径**：`LazyList 测量 → SubcomposeLayout.dispose → applyChanges → removeCurrentGroup → onForgotten → LaunchedEffectImpl.cancel → throw LeftCompositionCancellationException → _Unwind_Backtrace`
- **关键类 `LaunchedEffectImpl`**：内部 `onForgotten()` 调用 `job?.cancel(LeftCompositionCancellationException())`，该异常类继承自 `PlatformOptimizedCancellationException`（源码 `Effects.kt:390`）
- **影响范围**：阻塞主线程、帧率压力、内存抖动（每次 cancel 分配新异常对象）、forget+remember 双倍成本

## 重要细节

### 完整调用栈

```
Snapshot.sendApplyNotifications()
  → Recomposer 调度重组
    → CompositionImpl.recompose()
      → Composer.compose() — DFS 重新执行 composable 树
        → applyChanges() → applyChangesInLocked()        [Composition.kt:1098]
          → SlotWriter.removeCurrentGroup(rememberManager) [Composer.kt:4465]
            → rememberManager.forgetting(slot)
              → RememberEventDispatcher.dispatchRememberObservers() [RememberEventDispatcher.kt:194]
                → LaunchedEffectImpl.onForgotten()        [Effects.kt:290]
                  → job?.cancel(LeftCompositionCancellationException())
                    → KN throw → ExceptionUtilsKt.captureStack()
                      → _Unwind_Backtrace()               ← hiperf 命中点
```

### 六种触发场景

| 场景 | 频率 | 说明 |
|------|------|------|
| A. LazyList 快速滑动 | 最高 | 每帧 1-3 个 item 进出 viewport |
| B. `LaunchedEffect(key)` key 变化 | 高 | Tab 切换、搜索输入、分页加载 |
| C. 含 LaunchedEffect 组件条件性移除 | 中 | 折叠面板、对话框关闭、导航返回 |
| D. `rememberCoroutineScope` 宿主移除 | 中 | 路由跳转、AnimatedContent 切换 |
| E. SubcomposeLayout key 变化 | 低 | 屏幕旋转、BoxWithConstraints 重建 |
| F. DisposableEffect onDispose 手动 cancel | 低 | 用户代码主动 cancel |

### 核心优化方案

| 优先级 | 方案 | 原理 |
|--------|------|------|
| P0 | 生产包添加 `-Xbinary=sourceInfoType=none` | 关闭 KN 急切栈追踪，**直接消除 155M 指令** |
| P0 | `SubcomposeSlotReusePolicy(5)` 配置 LazyList | item 走 reuse pool 路径不触发 cancel |
| P1 | LaunchedEffect key 改用稳定 id | 避免 item 复用时 key 变化导致不必要的 cancel+restart |
| P1 | 网络/IO 逻辑上移到 ViewModel 协程 | ViewModel scope 不依赖组合树 |
| P2 | 减少单 item 内 LaunchedEffect 数量 | 每减少 1 个少 1 次 unwind |
| P2 | `rememberUpdatedState` + `LaunchedEffect(Unit)` | key 频繁变化时不重启 effect |

### 验证方法

通过 hiperf `perf.json` 分析确认 `_Unwind_Backtrace` 的 caller 为异常路径符号（`ExceptionOps_ThrowException` / `captureStack`）而非 GC 路径（`gcSafePoint`）。若出现 GC 符号则说明还有 GC 栈根扫描叠加，需分别处理。

## 与已有知识的关联

- [[融合渲染架构]] — Fusion Renderer 路径的帧回调机制中 `applyChanges` 是主线程同步执行的关键阶段，unwind 开销直接阻塞帧回调链
- [[OHRenderNode]] — RenderNode 的 Picture 模式决策依赖稳定的帧时序，`applyChanges` 中的 unwind 阻塞会影响脏区计算与 Node/Picture 模式切换的时机
- [[RenderNode生命周期]] — RenderNode 的创建/销毁与 Compose 组合树同步，LazyList item 离开触发的 `onForgotten` 链条是 RenderNode 被回收的触发源之一
- [[SkCanvas]] — Canvas 绘制命令录制在 `applyChanges` 之后执行，unwind 阻塞延迟了 SkCanvas 的实际绘制时机

## 来源

- 原始文档：`raw/applyChanges_unwind_backtrace_analysis.md`
- 数据来源：hiperf pid=37777 libkn.so `raw-instruction-retired`，采样总量 1,642,697,537
- 关键源码文件：`Composition.kt`、`Composer.kt`、`Effects.kt`、`RememberEventDispatcher.kt`、`SubcomposeLayout.kt`
