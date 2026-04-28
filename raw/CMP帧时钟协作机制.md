# CMP 帧时钟协作机制

本文档梳理 CMP (Compose for HarmonyOS) 中 OhosUiDispatcher、BroadcastFrameClock 和两个 FlushCoroutineDispatcher（recomposeDispatcher / effectDispatcher）的帧时钟协作机制，涵盖完整的帧循环数据流、任务投递路径和时序约束。

---

## 1. 这个系统在解决什么问题

Compose 的 UI 更新由三类工作驱动：

| Type | Example | Characteristic |
|------|---------|---------------|
| **Recomposition** | `mutableState` change triggers `@Composable` re-execution | Framework logic, must align with frames |
| **Animation / Effect** | `animate*AsState`, `LaunchedEffect`, `delay` | User code, needs per-frame advancement |
| **Measure / Layout / Draw** | `measure` -> `layout` -> `draw` | Depends on recomposition result, same frame |

这三类工作之间有严格的**时序依赖**：动画值必须先于重组更新，重组必须先于布局，布局必须先于绘制。如果时序错乱，用户会看到画面撕裂或闪烁。

帧时钟系统的核心任务是：**在一个 VSync 周期内，按正确顺序调度这些工作，并确保帧间也能推进协程。**

## 2. 全局架构一张图

```
+------------------- Platform VSync -------------------+
|  ChoreographerManager.onVsync                         |
|    -> ComposeSceneMediator.onDraw()                   |
|    -> BaseComposeScene.render(canvas, nanoTime)       |
|                                                       |
|  +-- render() internals ---------------------------+  |
|  |                                                  | |
|  |  Phase 1       Phase 2        Phase 3            | |
|  |  flush         flush          sendFrame          | |
|  |  effectDisp    recomposeDisp  |                  | |
|  |  +--------+    +-----------+  BaseComposeScene   | |
|  |  |anim   |    | recomposer |  .frameClock        | |
|  |  |effect |--->| main loop  |  .sendFrame()       | |
|  |  |resume |    | ->suspend  |    |                | |
|  |  |run    |    +-----------+  onFrame sync run:   | |
|  |  |->suspend|                 |- Recomposer       | |
|  |  +--------+                  |  .broadcastFC     | |
|  |                              |  .sendFrame()     | |
|  |                              |   |-animA onFrame | |
|  |                              |   |-animB onFrame | | sync
|  |                              |   +-...           | | exec
|  |                              |- performRecompose | |
|  |                              +- applyChanges     | |
|  |                                    |             | |
|  |                              +--------------+    | |
|  |  yield effect tasks (N) <----|two dispatchers|   | | yield recompose task (1) <-
|  |  for next frame Phase 1      | each +1 task |    | | for next frame Phase 2
|  |                              +--------------+    | |
|  |                                                  | |
|  |  Phase 4-6: measure -> layout -> pointer -> draw | |
|  +--------------------------------------------------+ |
+-------------------------------------------------------+
```

**关键认知**：
- `render()` 由平台 VSync 驱动，每帧调用一次
- 阶段 1-2 处理**上一帧产出**的任务，阶段 3 **产出本帧**的任务给下一帧
- `sendFrame` 是帧时钟级联的入口，内部所有工作都是**同步**执行的

## 3. 走一遍完整流程

### 3.1 从 "用户点击按钮" 开始

假设用户点击了一个按钮，按钮的点击回调修改了一个 `mutableState`：

```
mutableState.value = newValue
  -> Snapshot.apply()
    -> Recomposer applyObserver callback
      -> snapshotInvalidations.add(state)
      -> deriveStateLocked() -> state = PendingWork
      -> workContinuation.resume()  <- resume dispatched to recomposeDispatcher
  -> updateInvalidations()
    -> invalidate()                  <- request platform to schedule new frame
```

此时：
- `recomposeDispatcher.immediateTasks` 中有 **1 个任务**（recomposer continuation）
- 平台已收到帧请求，下一个 VSync 会调用 `render()`

### 3.2 render() 的六个阶段

#### 阶段 1：flush effectDispatcher

```kotlin
recomposer.performScheduledEffects()  // -> effectDispatcher.flush()
```

处理上一帧阶段 3 产出的 effect 任务。假设上一帧没有动画在跑，`immediateTasks` 为空 -> **无事可做**。

但如果上一帧有动画，这里会执行：
- 动画协程从 `withFrameNanos` 返回
- 判断是否继续动画 -> 如果继续，再次 `withFrameNanos` 挂起
- 动画值可能被更新 -> 产生 snapshot invalidations

**设计意图**：先让 effect 跑一轮，产出的状态变化可以在阶段 2 被同帧的重组处理。

#### 阶段 2：flush recomposeDispatcher

```kotlin
recomposer.performScheduledRecomposerTasks()  // -> recomposeDispatcher.flush()
```

处理 3.1 中投递的 1 个任务。这个任务是 recomposer 协程的 continuation resume：

```
recomposer coroutine resumes from awaitWorkAvailable()
  -> recordComposerModifications()
    -> process snapshotInvalidations (including those from Phase 1 effects)
    -> collect compositions that need recomposition
    -> return true (has work to do)
  -> parentFrameClock.withFrameNanos { frameTime -> ... }
    -> suspend, register awaiter on BaseComposeScene.frameClock
    -> onNewAwaiters callback fires (but isInvalidationDisabled=true, no frame request)
```

flush 返回，`immediateTasks` 为空。

#### 阶段 3：sendFrame

```kotlin
frameClock.sendFrame(nanoTime)
```

这是整个帧循环的**核心**。所有实际工作都在这里**同步**发生：

**第一跳：BaseComposeScene.frameClock -> Recomposer**

`frameClock` 上有 1 个 awaiter（阶段 2 注册的 recomposer）。`sendFrame` 恢复它：

```kotlin
// BroadcastFrameClock.FrameAwaiter.resume
fun resume(timeNanos: Long) {
    continuation?.resumeWith(runCatching { onFrame(timeNanos) })
    //                        ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
    //                        onFrame runs synchronously!
}
```

recomposer 的 `onFrame` 同步执行（即 `withFrameNanos { frameTime -> ... }` 中的 lambda）：

```
onFrame(nanoTime) executes synchronously:

  (1) broadcastFrameClock.sendFrame(frameTime)
       |
       v  Second hop: Recomposer.broadcastFrameClock -> user effect coroutines
       Resumes N animation/effect coroutines
         -> each coroutine's onFrame runs synchronously (update animation values, etc.)
         -> each coroutine's continuation.resumeWith -> dispatch to effectDispatcher
       Yield: effectDispatcher.immediateTasks += N tasks (for next frame Phase 1)

  (2) recordComposerModifications()
       -> collect new snapshot invalidations from animations

  (3) performRecompose()
       -> execute @Composable function recomposition (with latest animation values)

  (4) applyChanges()
       -> apply recomposition results to LayoutNode tree

  (5) deriveStateLocked()
```

`onFrame` 执行完毕后，`continuation.resumeWith(result)` 将 recomposer continuation dispatch 到 `recomposeDispatcher`：

```
Yield: recomposeDispatcher.immediateTasks += 1 task (for next frame Phase 2)
```

#### 阶段 4-6：measure / layout / draw

```
doMeasureAndLayout()                          // use Node tree updated in Phase 3(4)
if (needUpdatePointerPosition) scheduleAsEffect { updatePointerPosition() }
Snapshot.sendApplyNotifications()
doMeasureAndLayout()                          // second layout pass
draw(canvas)                                  // draw to Canvas
```

`render()` 返回后，`postponeInvalidation` 的 finally 块调用 `updateInvalidations()`：
- 如果 `frameClock.hasAwaiters`（recomposer 已注册等待下一帧）-> `invalidate()` -> 请求下一帧
- 如果没有 -> 系统空闲

### 3.3 多帧循环的节奏

连续动画运行时的帧序列：

```
Frame 1: flush(empty) -> flush(empty) -> sendFrame -> recompose + anim onFrame -> yield 1+N tasks
Frame 2: flush(N effect) -> flush(1 recompose) -> sendFrame -> recompose + anim onFrame -> yield 1+N tasks
Frame 3: flush(N effect) -> flush(1 recompose) -> sendFrame -> recompose + anim onFrame -> yield 1+N tasks
...until animation ends
```

## 4. 逐个组件深入

理解了整体流程后，现在可以深入每个组件。

### 4.1 两个 BroadcastFrameClock 的级联

系统中存在两个独立的 `BroadcastFrameClock`，形成两级帧传播：

| Instance                       | Created at                   | Consumer                                     | Who calls sendFrame  |
| ------------------------------ | ---------------------------- | -------------------------------------------- | -------------------- |
| BaseComposeScene.frameClock    | BaseComposeScene.skiko.kt:73 | Recomposer's parentFrameClock.withFrameNanos | render() Phase 3     |
| Recomposer.broadcastFrameClock | Recomposer.kt:167            | User effect coroutine's withFrameNanos       | Recomposer's onFrame |

为什么需要两级？因为**控制权不同**：
- BaseComposeScene.frameClock 的 `sendFrame` 由 `render()` 调用，**只在有 VSync 帧时触发**
- Recomposer.broadcastFrameClock 的 `sendFrame` 由 recomposer 在帧内调用，**可以决定是否传播**

recomposer 可以检查 `hasBroadcastFrameClockAwaiters`：如果没有用户 effect 在等帧，就跳过 `broadcastFrameClock.sendFrame`，节省开销。

`onNewAwaiters` 回调的作用：

```kotlin
// BaseComposeScene.frameClock
private val frameClock = BroadcastFrameClock(onNewAwaiters = ::updateInvalidations)
// Recomposer.broadcastFrameClock
private val broadcastFrameClock = BroadcastFrameClock { deriveStateLocked()?.resume(Unit) }
```

当 awaiter 数量从 0->1 时，回调通知系统"有新的帧需求"，触发帧请求或 recomposer 唤醒。

### 4.2 两个 FlushCoroutineDispatcher 的分工

两者都是 `FlushCoroutineDispatcher` 的实例，但职责截然不同：

| Dimension | recomposeDispatcher | effectDispatcher |
|-----------|--------------------|--------------------|
| Coroutine count | 1 (recomposer main loop) | N (one per LaunchedEffect / rememberCoroutineScope) |
| Frame clock used | BaseComposeScene.frameClock | Recomposer.broadcastFrameClock |
| Code executed | Framework internal recomposition pipeline | User code (LaunchedEffect block, animation logic) |
| immediateTasks upper bound | <=1 | <=N |
| flush entry point | performScheduledRecomposerTasks() | performScheduledEffects() |

**为什么 recomposeDispatcher 最多只有 1 个任务？**

只有一个协程运行在上面。单个协程同一时刻只有一个 pending continuation。`continuation.resume()` 对同一 continuation 只能调用一次。因此 `immediateTasks` 始终 <= 1。

**effectDispatcher 可以有多个任务**，因为每个 LaunchedEffect、每个动画都是独立的协程，每个都可能有一个 pending continuation。

### 4.3 dispatch 的双路径机制

`FlushCoroutineDispatcher.dispatch()` 存在两条执行路径：

```kotlin
override fun dispatch(context: CoroutineContext, block: Runnable) {
    synchronized(immediateTasksLock) {
        immediateTasks.add(block)       // Path A: synchronous queue
    }
    scope.launch {                       // Path B: async fallback
        performRun {
            val isTaskAlive = synchronized(immediateTasksLock) {
                immediateTasks.remove(block)
            }
            if (isTaskAlive) { block.run() }
        }
    }
}
```

其中 `scope` 底层是 `OhosUiDispatcher`：

```kotlin
private val scope = CoroutineScope(incomingScope.coroutineContext.minusKey(Job))
// result = CoroutineScope(OhosUiDispatcher)
```

#### 为什么需要路径 B

`flush()` 只在 `render()` 执行时调用。但协程挂起/恢复不限于帧内 -- `delay` 到期、后台状态变化等可以在任意时刻发生。路径 B 确保这些任务**始终能被最终执行**，即使没有 `render()` 发生。

#### 互斥保证

路径 A 和 B 通过 `runLock` 和 `immediateTasks.remove` 实现互斥：

- **flush 先执行**：flush drain 了 `immediateTasks` -> 路径 B 的 `remove(block)` 返回 `false` -> 路径 B 跳过
- **路径 B 先执行**：`remove(block)` 返回 `true` -> 路径 B 执行 -> flush 检查 `immediateTasks` 为空 -> 无事可做

#### 在帧循环中的角色

| Timing                      | Dominant path | Reason                                                               |
| --------------------------- | ------------- | -------------------------------------------------------------------- |
| In-frame (render() running) | Path A        | flush() executes synchronously, Path B blocked by runLock then skips |
| Between frames (no render)  | Path B        | Tasks execute via OhosUiDispatcher on main thread                    |

帧间路径 B 的典型场景：

| Scenario | Trigger chain | Path B role |
|----------|-------------|------------|
| delay expires | scheduleResumeAfterDelay -> continuation.resume -> dispatch() | Advance effect coroutine on main thread |
| Background state change | invalidate() -> workContinuation.resume() -> recomposeDispatcher.dispatch() | Resume recomposer -> reach withFrameNanos -> onNewAwaiters triggers frame request |
| Background pulse (no render) | Effect completion -> continuation resume | Advance effect coroutine |

**路径 B 对 recomposeDispatcher 的特殊意义**：它是一条"自举"路径 -- 状态变化通过路径 B 驱动 recomposer 到达 `withFrameNanos` 挂起点，进而通过 `onNewAwaiters` 触发帧请求，从而启动 `render()` 循环。

### 4.4 OhosUiDispatcher 的角色

**文件**：`compose/ui/ui/src/ohosArm64Main/kotlin/.../platform/OhosUiDispatcher.kt`

```kotlin
class OhosUiDispatcher(choreographer: Choreographer, handler: Handler)
    : CoroutineDispatcher(), MonotonicFrameClock
```

在帧时钟系统中有两个身份：

1. **底层调度器**：`FlushCoroutineDispatcher` 的 `scope` 使用它，作为路径 B 的执行通道。当 `flush()` 不可用时，任务通过 `OhosUiDispatcher` 的 `Handler.post` / `Choreographer.postFrameCallback` 双通道在主线程执行。

2. **空转的 MonotonicFrameClock**：从 Android 的 `AndroidUiDispatcher + AndroidUiFrameClock` 合并移植而来。其 `withFrameNanos` 能直接注册 VSync 回调，但在 CMP 架构中**没有直接调用者** -- 帧时钟功能由 `BroadcastFrameClock` 承担。保留此接口是为了与 Android 原版结构对称。

## 5. 协程上下文组装

组件之间的关系通过协程上下文串联。完整的传递链：

```
MainDispatcherFactory.getDispatcher() = OhosUiDispatcher.Main

ComposeArkUIViewContainer
  -> ComposeSceneMediator(coroutineContext = OhosUiDispatcher.Main)
    -> BaseComposeScene(coroutineContext, invalidate)
      -> frameClock = BroadcastFrameClock(onNewAwaiters = ::updateInvalidations)
      -> ComposeSceneRecomposer(coroutineContext, frameClock)
```

`ComposeSceneRecomposer` 内部的关键组装：

```kotlin
private val job = Job()
private val coroutineScope = CoroutineScope(OhosUiDispatcher + job)
private val effectDispatcher = FlushCoroutineDispatcher(coroutineScope)
private val recomposeDispatcher = FlushCoroutineDispatcher(coroutineScope)
private val recomposer = Recomposer(OhosUiDispatcher + job + effectDispatcher)

init {
    // recomposer coroutine runs on recomposeDispatcher
    // BaseComposeScene.frameClock injected as MonotonicFrameClock
    coroutineScope.launch(recomposeDispatcher + frameClock, UNDISPATCHED) {
        recomposer.runRecomposeAndApplyChanges()
    }
}
```

`Recomposer` 内部再加工上下文：

```kotlin
// Context exposed to Composition (used by LaunchedEffect / rememberCoroutineScope)
override val effectCoroutineContext =
    (OhosUiDispatcher + CSR.job + effectDispatcher) + broadcastFrameClock + effectJob

// In recompositionRunner:
val parentFrameClock = coroutineContext.monotonicFrameClock  // = BaseComposeScene.frameClock
withContext(broadcastFrameClock) {  // replace MonotonicFrameClock in context
    coroutineScope { block(parentFrameClock) }
}
```

最终分配：

| Coroutine | Dispatcher | MonotonicFrameClock |
|-----------|-----------|-------------------|
| Recomposer main loop | recomposeDispatcher | BaseComposeScene.frameClock (as parentFrameClock) |
| LaunchedEffect | effectDispatcher | Recomposer.broadcastFrameClock |
| rememberCoroutineScope.launch | effectDispatcher | Recomposer.broadcastFrameClock |

## 6. 特殊场景

### 6.1 LaunchedEffect 的生命周期时序

```
Frame K, Phase 3: performRecompose
  -> LaunchedEffect first enters composition
  -> LaunchedEffectImpl.onRemembered()
    -> scope.launch { block } -> effectDispatcher.dispatch()    <- enqueue initial coroutine body

Frame K+1, Phase 1: flush effectDispatcher
  -> execute LaunchedEffect initial coroutine body
  -> if withFrameNanos -> suspend on broadcastFrameClock

Frame K+1, Phase 3: broadcastFrameClock.sendFrame
  -> resume LaunchedEffect -> onFrame sync exec -> continuation -> effectDispatcher

Frame K+2, Phase 1: flush -> coroutine continues -> loop -> withFrameNanos -> suspend
Frame K+2, Phase 3: sendFrame -> resume -> ...
...loop until LaunchedEffect exits
```

**从进入到实际执行有 1 帧延迟**：帧 K 的阶段 3 投递，帧 K+1 的阶段 1 执行。

### 6.2 空闲时被唤醒

系统空闲时 recomposer 挂起在 `awaitWorkAvailable()`。用户交互触发状态变化：

```
mutableState.value = newValue
  -> Snapshot.apply() -> applyObserver
    -> snapshotInvalidations.add(state)
    -> deriveStateLocked() -> workContinuation.resume()
      -> recomposeDispatcher.dispatch()  // 1 task (executed via Path B)
  -> recomposer Path B executes continuation:
    -> recordComposerModifications() -> withFrameNanos -> suspend
    -> onNewAwaiters -> updateInvalidations() -> invalidate() -> request frame
  -> next frame render() is called
```

### 6.3 后台帧脉冲

页面不可见时没有 VSync 驱动，但 effect 可能仍需推进。使用 `sendFrameWithoutDraw`：

```kotlin
internal fun sendFrameWithoutDraw(nanoTime: Long) {
    postponeInvalidation {
        recomposer.performScheduledEffects()          // Phase 1
        recomposer.performScheduledRecomposerTasks()  // Phase 2
        frameClock.sendFrame(nanoTime)                // Phase 3 (no measure/layout/draw)
        Snapshot.sendApplyNotifications()
    }
}
```

以及更轻量的 `runBackgroundEffectsTick`（不发送帧，只 flush + snapshot 通知）：

```kotlin
internal fun runBackgroundEffectsTick() {
    postponeInvalidation {
        recomposer.performScheduledEffects()
        recomposer.performScheduledRecomposerTasks()
        Snapshot.sendApplyNotifications()
    }
}
```

## 7. 关键代码索引

| File | Lines | Content |
|------|-------|---------|
| OhosUiDispatcher.kt | 45-48 | Class def: CoroutineDispatcher + MonotonicFrameClock |
| OhosUiDispatcher.kt | 67-76 | withFrameNanos impl (via Choreographer VSync) |
| BroadcastFrameClock.kt | 43 | Class definition |
| BroadcastFrameClock.kt | 79-94 | sendFrame (sync resume all awaiters) |
| BroadcastFrameClock.kt | 96-130 | withFrameNanos (register awaiter + onNewAwaiters) |
| FlushCoroutineDispatcher.skiko.kt | 42 | scope construction (OhosUiDispatcher) |
| FlushCoroutineDispatcher.skiko.kt | 52-66 | dispatch (Path A: immediateTasks + Path B: scope.launch) |
| FlushCoroutineDispatcher.skiko.kt | 83-99 | flush (sync drain loop) |
| FlushCoroutineDispatcher.skiko.kt | 102-109 | performRun (runLock mutual exclusion) |
| ComposeSceneRecomposer.skiko.kt | 40-76 | Two dispatchers + Recomposer creation + coroutine launch |
| BaseComposeScene.skiko.kt | 73 | frameClock creation |
| BaseComposeScene.skiko.kt | 106-112 | updateInvalidations (frame request decision) |
| BaseComposeScene.skiko.kt | 162-201 | render() full flow |
| BaseComposeScene.skiko.kt | 207-215 | sendFrameWithoutDraw |
| BaseComposeScene.skiko.kt | 221-228 | runBackgroundEffectsTick |
| Recomposer.kt | 167-178 | Recomposer's broadcastFrameClock |
| Recomposer.kt | 308-309 | effectCoroutineContext assembly |
| Recomposer.kt | 454-490 | recordComposerModifications |
| Recomposer.kt | 537-762 | runRecomposeAndApplyChanges main loop |
| Recomposer.kt | 1098-1115 | awaitWorkAvailable |
| Recomposer.kt | 1117-1171 | recompositionRunner (parentFrameClock capture + withContext) |
| Effects.kt | 269-311 | LaunchedEffectImpl |
| Effects.kt | 559-577 | createCompositionCoroutineScope |
| Composer.kt | 1495-1496 | applyCoroutineContext |
