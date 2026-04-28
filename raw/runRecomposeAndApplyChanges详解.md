# runRecomposeAndApplyChanges 逐行详解

## 0. 前置心智模型

在逐行阅读之前，先建立三个核心心智模型。

### 心智模型 1：Recomposer 是"施工队调度中心"

```
状态变化（如 mutableState.value = xxx）
  → 某个 @Composable 函数"脏了"（invalidated）
  → 需要重新执行（recompose）
  → 结果应用到 UI 树（applyChanges）
```

Recomposer 就是这个流程的调度中心。`runRecomposeAndApplyChanges` 是它的**主循环**——一个永不停止的 while 循环，每帧执行一次"检查谁脏了 → 重组 → 应用变更"。

### 心智模型 2：帧对齐

Recomposer 的主循环不是无脑循环，而是**对齐到 VSync 帧**。每次循环都要等下一帧到来才执行工作。这样做的好处：

- 多个状态变化发生在同一帧内（比如两个 mutableState 同时改），会**合并**成一次重组
- 不会重组比屏幕刷新更频繁——重组了也看不到

### 心智模型 3：两级帧时钟

```
平台 VSync
  → BaseComposeScene.frameClock.sendFrame()    ← 第一级：平台驱动
    → Recomposer 拿到帧信号，执行 onFrame 回调
      → broadcastFrameClock.sendFrame()         ← 第二级：Recomposer 自己的帧时钟
        → 用户动画/Effect 拿到帧信号
```

Recomposer 既是一级帧时钟的**消费者**（等帧），又是二级帧时钟的**生产者**（发帧给动画协程）。

---

## 1. 代码结构总览

```
runRecomposeAndApplyChanges() (537-762)
  │
  ├── recompositionRunner { ... }  ← 外壳：注册为工作协程、设置 Snapshot 观察者
  │     │
  │     └── 以下全在 recompositionRunner 提供的协程上下文中运行
  │
  ├── [539-576] 初始化局部变量 + 错误清理函数
  │
  └── while (shouldKeepRecomposing) { ... }  ← 主循环
        │
        ├── [587] awaitWorkAvailable()        ← 挂起，等有活干
        ├── [590] recordComposerModifications() ← 检查谁脏了，没活就 continue
        └── [598] parentFrameClock.withFrameNanos { ... }  ← 等下一帧，然后执行：
              │
              ├── [601-609] broadcastFrameClock.sendFrame()  ← 驱动动画
              ├── [612-685] recompose 主逻辑                 ← 重组
              ├── [691-743] applyChanges                     ← 应用变更
              └── [746-756] 收尾                             ← 通知 + 清理
```

---

## 2. 入口：recompositionRunner 外壳（1118-1171）

```kotlin
public suspend fun runRecomposeAndApplyChanges(): Unit =
    recompositionRunner { parentFrameClock ->
```

`recompositionRunner` 是 `runRecomposeAndApplyChanges` 的包装器，做三件准备工作：

### 2.1 捕获父帧时钟

```kotlin
// Recomposer.kt:1121
val parentFrameClock = coroutineContext.monotonicFrameClock
```

从协程上下文中取出 `MonotonicFrameClock`。在 CMP 中，这就是 `BaseComposeScene.frameClock`（由 `ComposeSceneRecomposer` 启动时注入：`launch(recomposeDispatcher + frameClock)`）。后面用它来 `withFrameNanos` 挂起等待帧信号。

### 2.2 替换协程上下文中的帧时钟

```kotlin
// Recomposer.kt:1122
withContext(broadcastFrameClock) {
```

把协程上下文中的 `MonotonicFrameClock` 替换为 Recomposer 自己的 `broadcastFrameClock`。这样，在这个上下文中启动的子协程（LaunchedEffect 等）调用 `withFrameNanos` 时，挂起在 `broadcastFrameClock` 上而非平台帧时钟上。

**为什么要替换？** 因为 Recomposer 要控制何时向子协程发帧——只有自己在处理帧时才发，否则子协程会越过 Recomposer 直接拿帧。

### 2.3 注册为工作协程 + Snapshot 观察者

```kotlin
// Recomposer.kt:1124-1125
val callingJob = coroutineContext.job
registerRunnerJob(callingJob)  // 记录为 runnerJob
```

将自己注册为当前 Recomposer 的工作协程。同一个 Recomposer 同时只能有一个工作协程运行（互斥保证）。

```kotlin
// Recomposer.kt:1131-1149
val unregisterApplyObserver =
    Snapshot.registerApplyObserver { changed, _ ->
        synchronized(stateLock) {
            if (_state.value >= State.Idle) {
                changed.fastForEach { ... snapshotInvalidations.add(it) }
                deriveStateLocked()
            }
        }?.resume(Unit)
    }
```

注册一个 Snapshot 观察者。当任何 `mutableState` 被修改并 apply 时，这个回调被触发，把变化的状态对象记入 `snapshotInvalidations`，然后调用 `deriveStateLocked()` 计算新状态——如果有待处理的工作，就唤醒工作协程（`workContinuation.resume()`）。

---

## 3. 局部变量初始化（539-576）

```kotlin
// 需要重组的组合列表
val toRecompose = mutableListOf<ControlledComposition>() 
// 需要插入的可移动内容
val toInsert = mutableListOf<MovableContentStateReference>() 
// 重组成功、待应用变更的列表
val toApply = mutableListOf<ControlledComposition>() 
// 延迟应用变更的列表
val toLateApply = mutableScatterSetOf<ControlledComposition>()
// 已应用、待确认完成的列表
val toComplete = mutableScatterSetOf<ControlledComposition>() 
// 本帧被修改的状态值集合
val modifiedValues = MutableScatterSet<Any>()      
// 包装成 Set（用于查询）           
val modifiedValuesSet = modifiedValues.wrapIntoSet()       
// 本帧已重组过的组合   
val alreadyComposed = mutableScatterSetOf<ControlledComposition>() 
```

这些是工作台上的"篮子"，每帧循环中用来分拣不同状态的组合：

```
toRecompose ──→ 重组 ──→ toApply ──→ applyChanges ──→ toComplete ──→ changesApplied
                                    ↑
                               toLateApply（延迟应用，移动内容用）
```

### clearRecompositionState()（548-576）

错误时调用的清理函数：放弃所有待处理的变更（`abandonChanges`），将失败的组合记入 `failedCompositions`，清空所有篮子。相当于"推倒重来"。

### fillToInsert()（578-584）

从 `movableContentAwaitingInsert`（线程安全的待插入队列）取出所有待插入的可移动内容引用，放入 `toInsert`。

---

## 4. 主循环开始（586）

```kotlin
while (shouldKeepRecomposing) {
```

`shouldKeepRecomposing` 检查 Recomposer 是否还活着（未被关闭且 effectJob 还有活跃子协程）。只要活着就一直循环。

---

## 5. 等待工作（587）

```kotlin
awaitWorkAvailable()
```

```kotlin
// Recomposer.kt:1098-1115
private suspend fun awaitWorkAvailable() {
    if (!hasSchedulingWork) {
        suspendCancellableCoroutine<Unit> { co ->
            synchronized(stateLock) {
                if (hasSchedulingWork) {
                    co  // 刚好有活了，直接返回 co
                } else {
                    workContinuation = co  // 把续体存起来
                    null
                }
            }?.resume(Unit)  // 如果有活，立即恢复
        }
    }
}
```

**做了什么：**
- `hasSchedulingWork` 检查三个条件：有 snapshot 无效化？有组合无效化？有帧时钟等待者？
- 如果有活：直接跳过，不挂起
- 如果没活：把当前协程的续体（continuation）存到 `workContinuation`，然后**挂起**

**何时被唤醒：** 当状态变化时（如 `mutableState.value = xxx`），Snapshot 观察者回调调用 `deriveStateLocked()`，发现状态变为 `PendingWork`，取出 `workContinuation` 并 `resume(Unit)`。这会将 resume 任务 dispatch 到 `recomposeDispatcher`，在下一帧的 Phase 2 或帧间的 Path B 中执行。

---

## 6. 记录无效化（590）

```kotlin
if (!recordComposerModifications()) continue
```

`recordComposerModifications()` 的核心逻辑（454-489）：

```
1. 从 stateLock 中取出 snapshotInvalidations（哪些状态对象变了）
2. 清空 snapshotInvalidations（为下次收集做准备）
3. 遍历所有已知组合，告诉每个组合："这些状态对象变了，看看你是不是需要重组"
   → composition.recordModificationsOf(changes)
4. 返回 hasFrameWorkLocked（是否有帧内工作要做）
```

**如果返回 false**：说明虽然被唤醒了，但实际上没有需要重组的活（可能只有帧时钟等待者）。`continue` 跳过本轮，回到 `awaitWorkAvailable()`。

**如果返回 true**：继续往下，等帧信号。

---

## 7. 等待帧信号（598）

```kotlin
parentFrameClock.withFrameNanos { frameTime ->
```

在 `parentFrameClock`（即 `BaseComposeScene.frameClock`）上注册等待下一帧。协程**挂起**在这里。

**何时恢复：** 当 `render()` 执行到阶段 3（`frameClock.sendFrame(nanoTime)`）时，`BroadcastFrameClock` 同步恢复所有 awaiter，`withFrameNanos` 的 lambda 开始同步执行。

恢复后 `frameTime` 就是当前帧的纳秒时间戳。

---

## 8. 帧内工作：三大阶段

以下代码**全部在 withFrameNanos 的 lambda 内同步执行**。也就是说，`render()` 的 `sendFrame` 调用不会返回，直到这里的所有工作完成。

### 8.1 阶段 A：驱动动画（601-609）

```kotlin
if (hasBroadcastFrameClockAwaiters) {
    trace("Recomposer:animation") {
        broadcastFrameClock.sendFrame(frameTime)
        Snapshot.sendApplyNotifications()
    }
}
```

**条件检查**：`hasBroadcastFrameClockAwaiters` 判断是否有动画/Effect 协程在等待帧信号。如果没有（没有动画在跑），跳过这一步节省开销。

**发帧**：调用 `broadcastFrameClock.sendFrame(frameTime)`。这会**同步**恢复所有等待在 `broadcastFrameClock` 上的动画协程，执行它们的 `onFrame` 回调。典型场景：

```
animateFloatAsState 的协程:
  withFrameNanos { frameTime ->      ← 挂起在这里
    val newValue = animationValue(frameTime)  ← onFrame 同步执行
    state.value = newValue      ← 更新动画值 → 产生 snapshot invalidation
  }
```

所有动画的 `onFrame` **同步**执行完毕后，`sendFrame` 才返回。

**sendApplyNotifications**：动画修改了 `mutableState`，调用 `Snapshot.sendApplyNotifications()` 让这些修改被 Snapshot 系统感知，这样下一步就能收集到这些无效化。

**为什么动画要先于重组？** 设计意图：先让动画值更新到最新，这样重组时 `@Composable` 函数读到的是最新动画值，用户看到的画面才是正确的。

### 8.2 阶段 B：重组（612-685）

#### 8.2.1 收集待重组列表

```kotlin
recordComposerModifications()
synchronized(stateLock) {
    compositionInvalidations.forEach { toRecompose += it }
    compositionInvalidations.clear()
}
```

再次调用 `recordComposerModifications()`——这次会收集到刚才动画产生的无效化。然后从 `compositionInvalidations` 取出所有需要重组的组合，放入 `toRecompose`。

> 注意：`recordComposerModifications` 可能被调用两次——第一次在帧外（590行）决定是否需要等帧，第二次在帧内（615行）收集动画产生的新无效化。

#### 8.2.2 重组循环

```kotlin
while (toRecompose.isNotEmpty() || toInsert.isNotEmpty()) {
    // 第一轮：重组所有无效化组合
    toRecompose.fastForEach { composition ->
        performRecompose(composition, modifiedValues)?.let {
            toApply += it  // 重组成功的放入待应用列表
        }
        alreadyComposed.add(composition)  // 标记为已重组
    }
    toRecompose.clear()
```

**performRecompose 做了什么**（1353-1378）：

```kotlin
private fun performRecompose(
    composition: ControlledComposition,
    modifiedValues: MutableScatterSet<Any>?,
): ControlledComposition? {
    // 跳过正在组合中、已销毁、已移除的组合
    if (composition.isComposing || composition.isDisposed || ...) return null

    // 调用 composition.recompose() —— 真正执行 @Composable 函数
    // 如果 recompose 产生了变更，返回 composition 本身
    return if (composing(composition, modifiedValues) {
        composition.recompose()
    }) composition else null
}
```

`composition.recompose()` 是真正执行 `@Composable` 函数的地方。它对比新旧组合结果，如果 UI 树有变化，返回 `true`。

**为什么用 while 循环？** 因为重组可能导致级联无效化：

#### 8.2.3 级联重组检测

```kotlin
// 重组可能导致新的无效化。比如：
// - 父 Composable 改了一个 CompositionLocal
// - 子 Composable 读了这个 CompositionLocal，但之前不在 toRecompose 中

if (modifiedValues.isNotEmpty() || compositionInvalidations.isNotEmpty()) {
    synchronized(stateLock) {
        knownCompositionsLocked().fastForEach { value ->
            if (value !in alreadyComposed && value.observesAnyOf(modifiedValuesSet)) {
                toRecompose += value  // 发现新的受害者，加入重组列表
            }
        }
        compositionInvalidations.removeIf { value ->
            if (value !in alreadyComposed && value !in toRecompose) {
                toRecompose += value
                true
            } else false
        }
    }
}
```

**级联重组的场景举例**：

```
父 @Composable 中:
  val theme by mutableStateOf(Theme.Dark)  // 改了这个值
  CompositionLocalProvider(LocalTheme provides theme) {
    Child()  // 子组件读了 LocalTheme
  }

第一次重组：父组件进入 toRecompose，重组后 theme 的值变了
级联检测：发现 Child 观察了 theme（通过 modifiedValues），把 Child 也加入 toRecompose
第二次循环：Child 被重组，使用新的 theme 值
```

循环直到 `toRecompose` 和 `toInsert` 都为空。

#### 8.2.4 可移动内容插入

```kotlin
if (toRecompose.isEmpty()) {
    fillToInsert()
    while (toInsert.isNotEmpty()) {
        toLateApply += performInsertValues(toInsert, modifiedValues)
        fillToInsert()
    }
}
```

处理 `movableContent`（可在不同位置之间移动的 Composable 内容，如 `key {}` 中的内容在列表重排时移动）。这是 Compose 高级特性，在 `toRecompose` 清空后才处理，因为移动内容依赖于重组的结果。

### 8.3 阶段 C：应用变更（691-743）

重组只是计算出"UI 树应该长什么样"，但还没有真正修改 UI 树。这一步把变更应用上去。

```kotlin
withTransparentSnapshot {
```

使用透明快照——这是优化：避免每次 `apply` 中的 `observeChanges` 都创建新的 Snapshot 对象。

#### 8.3.1 applyChanges

```kotlin
if (toApply.isNotEmpty()) {
    changeCount++  // 统计：这是第几次 apply

    toApply.fastForEach { composition -> toComplete.add(composition) }
    toApply.fastForEach { composition -> composition.applyChanges() }
    toApply.clear()
}
```

`composition.applyChanges()` 把重组产生的变更（新增/删除/移动 LayoutNode，修改 Modifier 等）**真正应用到 LayoutNode 树上**。执行完后，UI 树就更新了。

先全部加入 `toComplete`，再逐一 `applyChanges`，最后统一清空 `toApply`。这样做是因为 `applyChanges` 可能抛异常，`finally` 块需要清理 `toApply`。

#### 8.3.2 applyLateChanges

```kotlin
if (toLateApply.isNotEmpty()) {
    toComplete += toLateApply
    toLateApply.forEach { composition -> composition.applyLateChanges() }
    toLateApply.clear()
}
```

延迟变更——来自可移动内容插入的变更。和上面类似，但是"晚一步"应用，因为移动内容可能需要等其他变更先落地。

#### 8.3.3 changesApplied

```kotlin
if (toComplete.isNotEmpty()) {
    toComplete.forEach { composition -> composition.changesApplied() }
    toComplete.clear()
}
```

通知每个组合："变更已应用完毕"。组合可以做清理工作，比如更新内部状态。

---

## 9. 收尾（746-760）

```kotlin
                    synchronized(stateLock) { deriveStateLocked() }
```

在帧内工作结束后，重新推导 Recomposer 状态。如果在重组过程中产生了新的无效化（比如 `LaunchedEffect` 首次进入），`deriveStateLocked()` 会把状态设为 `PendingWork`，返回 `workContinuation`。不过这里是在 `withFrameNanos` lambda 内部，返回值被忽略了——因为当前帧还没结束，不需要再 resume 自己。

```kotlin
                    Snapshot.notifyObjectsInitialized()
                    alreadyComposed.clear()
                    modifiedValues.clear()
                    compositionsRemoved = null
```

- `Snapshot.notifyObjectsInitialized()`：确保本帧创建的 state 对象也被标记为"已改变"，让依赖它们的观察者能收到通知
- 清空所有工作篮子，为下一帧做准备

### 9.1 可移动内容清理（760）

```kotlin
                discardUnusedMovableContentState()
```

清理没有被任何组合引用的可移动内容状态。比如一个 `movableContent` 被移走了，旧位置的状态不再需要，就在这里丢弃。

---

## 10. withFrameNanos 之后：回到循环顶部

`withFrameNanos` lambda 执行完毕后，协程的 continuation 被 dispatch 到 `recomposeDispatcher`（产出 1 个任务给下一帧的 Phase 2）。然后控制流回到 `while` 循环顶部，进入下一轮 `awaitWorkAvailable()`。

---

## 11. 完整帧内时序图

```
render() 被平台 VSync 调用
  │
  ├── Phase 1: flush effectDispatcher
  │     (执行上一帧产出的动画/Effect continuation)
  │
  ├── Phase 2: flush recomposeDispatcher
  │     (resume recomposer 协程，它从 awaitWorkAvailable 返回)
  │
  ├── Phase 3: frameClock.sendFrame(nanoTime)
  │     │
  │     └── withFrameNanos lambda 同步执行：
  │           │
  │           ├── A. broadcastFrameClock.sendFrame()
  │           │     (同步执行所有动画的 onFrame → 动画值更新)
  │           │
  │           ├── B. 重组循环
  │           │     ├── 收集 toRecompose
  │           │     ├── performRecompose × N
  │           │     ├── 级联重组检测 → 可能追加更多 toRecompose
  │           │     └── 可移动内容插入
  │           │
  │           ├── C. applyChanges + applyLateChanges + changesApplied
  │           │
  │           └── 收尾：deriveStateLocked + 清理
  │
  ├── Phase 4-5: measure + layout
  │     (使用 C 步骤更新后的 LayoutNode 树)
  │
  └── Phase 6: draw
        (绘制到 Canvas)

→ continuation 被 dispatch 到 recomposeDispatcher (1 task for next frame)
→ 动画 continuation 被 dispatch 到 effectDispatcher (N tasks for next frame)
```

---

## 12. 关键设计总结

### 12.1 为什么 awaitWorkAvailable 要和 withFrameNanos 分开？

```
awaitWorkAvailable()   ← 等有活（可能在帧间任意时刻）
  → recordComposerModifications()  ← 检查是否真的有帧内工作
    → withFrameNanos { }           ← 等帧（对齐到 VSync）
```

不是每次被唤醒都需要等帧。比如只有帧时钟等待者而没有无效化，`recordComposerModifications` 返回 false，直接 continue 不等帧。这避免了不必要的帧等待。

### 12.2 为什么 recordComposerModifications 调用了两次？

- **第一次（590行）**：在帧外，决定"这一轮有没有需要等帧的工作"
- **第二次（615行）**：在帧内，收集动画产生的**新**无效化

中间隔了 `withFrameNanos` 的挂起和恢复，期间动画可能修改了更多状态。

### 12.3 为什么错误处理这么密集？

几乎每个步骤都有 `try-catch` + `clearRecompositionState()` + `return@withFrameNanos`。因为：

1. 重组是用户代码（`@Composable` 函数），可能抛任何异常
2. 一个组合失败不应影响其他组合
3. `return@withFrameNanos` 跳出整个帧处理，避免在错误状态下继续 apply

### 12.4 为什么动画要先于重组？

如果先重组再更新动画值，重组读到的是**上一帧**的动画值，画面就会延迟一帧。先更新动画值再重组，重组读到的是**当前帧**的值，保证视觉同步。
