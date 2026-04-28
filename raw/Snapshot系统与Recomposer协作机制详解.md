# Snapshot 系统工作原理与 Recomposer 协作机制详解

## 0. 前置心智模型

### 心智模型 1：Snapshot 是"版本管理系统"

Git 给文件的每次修改创建一个 commit，你可以回到任何历史版本。Snapshot 系统做的事情非常类似：

```
mutableState.value = "A"  → 创建 StateRecord(snapshotId=1, value="A")
mutableState.value = "B"  → 创建 StateRecord(snapshotId=2, value="B")
mutableState.value = "C"  → 创建 StateRecord(snapshotId=3, value="C")
```

每个 `mutableState` 内部维护一个 **StateRecord 链表**，每个节点记录了"在哪个快照版本时，值是什么"。读取时根据当前快照的 ID 查找对应版本。

### 心智模型 2：Snapshot 是"观察者代理"

Snapshot 不仅能"看到"历史版本，还能**观察谁读了什么、谁写了什么**：

- **readObserver**：每次读取状态时回调 → 用于追踪"哪些 @Composable 函数读了哪些状态"
- **writeObserver**：每次写入状态时回调 → 用于追踪"本帧内哪些状态被改了"

### 心智模型 3：Snapshot 是"事务系统"

数据库用事务保证一致性。Snapshot 也一样：

```kotlin
val snapshot = Snapshot.takeMutableSnapshot()
snapshot.enter {
    // 在这个事务里：
    state1.value = "new1"
    state2.value = "new2"
    // 外界看不到这些修改
}
snapshot.apply()  // 原子提交，外界一次性看到所有修改
```

如果两个事务冲突（改了同一个状态），apply 会检测到并尝试合并或失败。

---

## 1. 核心数据结构

### 1.1 StateRecord —— 状态的"版本快照"

```kotlin
// Snapshot.kt:1246
public abstract class StateRecord(
    internal var snapshotId: SnapshotId  // 这个版本属于哪个快照
) {
    internal var next: StateRecord? = null  // 链表下一个节点（更旧的版本）
    public abstract fun assign(value: StateRecord)  // 从另一个 record 复制值
    public abstract fun create(): StateRecord       // 创建新的空 record
}
```

每个 `StateRecord` 就像 Git 的一个 commit：标记了"在哪个快照 ID 时，值是什么"。

**链表结构**：

```
StateObject (mutableState)
  │
  firstStateRecord → StateRecord(snapshotId=3, value="C")
                      ↓ next
                    StateRecord(snapshotId=2, value="B")
                      ↓ next
                    StateRecord(snapshotId=1, value="A")
```

新的 record 总是**插入链表头部**（`prependStateRecord`）。读取时从头部开始，找到第一个 `snapshotId` 合法的 record。

### 1.2 StateObject —— 状态对象的接口

```kotlin
// Snapshot.kt:1305
public interface StateObject {
    public val firstStateRecord: StateRecord     // 链表头
    public fun prependStateRecord(value: StateRecord)  // 插入新版本
    public fun mergeRecords(                     // 冲突合并策略
        previous: StateRecord, current: StateRecord, applied: StateRecord
    ): StateRecord?
}
```

`mutableStateOf` 创建的 `SnapshotMutableStateImpl` 就是 `StateObject` 的实现。

### 1.3 Snapshot —— 快照基类

```kotlin
// Snapshot.kt:62
public sealed class Snapshot(
    snapshotId: SnapshotId,
    internal open var invalid: SnapshotIdSet,  // 对此快照无效的其他快照 ID 集合
) {
    internal abstract val readObserver: ((Any) -> Unit)?   // 读观察者
    internal abstract val writeObserver: ((Any) -> Unit)?  // 写观察者
    internal abstract val modified: MutableScatterSet<StateObject>?  // 此快照中修改过的状态对象
}
```

### 1.4 MutableSnapshot —— 可变快照

```kotlin
// Snapshot.kt:736
public open class MutableSnapshot(
    snapshotId: SnapshotId,
    invalid: SnapshotIdSet,
    override val readObserver: ((Any) -> Unit)?,
    override val writeObserver: ((Any) -> Unit)?,
) : Snapshot(snapshotId, invalid) {
    public open fun apply(): SnapshotApplyResult  // 提交修改
}
```

### 1.5 GlobalSnapshot —— 全局快照（始终存在）

```kotlin
// Snapshot.kt:1482
internal class GlobalSnapshot(snapshotId: SnapshotId, invalid: SnapshotIdSet) :
    MutableSnapshot(
        snapshotId, invalid,
        readObserver = null,
        writeObserver = { state -> sync { globalWriteObservers.fastForEach { it(state) } } },
    )
```

全局快照是一个特殊的 `MutableSnapshot`，它**没有 readObserver**，但有一个 **writeObserver**——通知所有全局写入观察者。当你在 `mutableState.value = xxx` 这种"不在显式快照中"的代码里直接写状态时，实际上是在全局快照中写入。

---

## 2. 状态读写如何触发观察者

### 2.1 读取流程

```kotlin
// SnapshotState.kt:141-142
override var value: T
    get() = next.readable(this).value
```

`next.readable(this)` 展开的调用链：

```
StateStateRecord.readable(state: StateObject)
  → Snapshot.kt:2070
  → val snapshot = Snapshot.current          // 获取当前快照
  → snapshot.readObserver?.invoke(state)     // 🔔 通知读观察者！
  → readable(this, snapshot.snapshotId, snapshot.invalid)  // 在链表中查找合法 record
```

**关键点：每次读取 `state.value`，都会调用 `readObserver`（如果有的话）。**

`readable(r, id, invalid)` 的查找逻辑（2047-2064）：

```kotlin
private fun <T : StateRecord> readable(r: T, id: SnapshotId, invalid: SnapshotIdSet): T? {
    var current: StateRecord? = r
    var candidate: StateRecord? = null
    while (current != null) {
        if (valid(current, id, invalid)) {
            // 选 snapshotId 最大（最新）的合法 record
            candidate = if (candidate == null) current
                        else if (candidate.snapshotId < current.snapshotId) current
                        else candidate
        }
        current = current.next
    }
    return candidate
}
```

合法性判定：`candidateSnapshot <= currentSnapshot && !invalid.get(candidateSnapshot)`。

**通俗理解**：读取就像"去图书馆找最新版的书"。每个状态对象是一本有多版次的书，readObserver 是图书管理员，记录"谁借阅了哪本书"。

### 2.2 写入流程

```kotlin
// SnapshotState.kt:143-148
override var value: T
    set(value) = next.withCurrent {
        if (!policy.equivalent(it.value, value)) {
            next.overwritable(this, it) { this.value = value }
        }
    }
```

先检查策略（默认 `structuralEqualityPolicy`：值不同才算修改），然后调用 `overwritable`：

```
StateStateRecord.overwritable(state, candidate) { this.value = value }
  → Snapshot.kt:2386
  → sync {                                   // 加锁
       snapshot = Snapshot.current
       this.overwritableRecord(state, snapshot, candidate)
         .block()                            // 写入新值
     }
  → notifyWrite(snapshot, state)             // 🔔 通知写观察者！
```

`overwritableRecord` 的逻辑：
- 如果当前 record 的 `snapshotId` 等于当前快照 ID → 直接复用（同一个快照内的多次修改）
- 否则 → 创建新 StateRecord，设为新快照 ID，插入链表头部

`notifyWrite`（2329-2332）：

```kotlin
internal fun notifyWrite(snapshot: Snapshot, state: StateObject) {
    snapshot.writeCount += 1
    snapshot.writeObserver?.invoke(state)
}
```

**通俗理解**：写入就像"出新版书"。如果你是在自己的笔记本（MutableSnapshot）上改，外面看不到；等你"出版"（apply），外面才能看到。writeObserver 是出版审查员，记录"谁出了哪本书的新版"。

---

## 3. apply：提交修改并通知观察者

### 3.1 MutableSnapshot.apply() 全流程

```kotlin
// Snapshot.kt:807-897
public open fun apply(): SnapshotApplyResult {
    val modified = modified  // 本快照中修改过的所有状态对象
    val optimisticMerges = ... // 计算乐观合并策略

    sync {
        validateOpen(this)
        if (modified == null || modified.size == 0) {
            closeLocked()  // 没有修改，直接关闭
        } else {
            // 检测冲突并合并
            val result = innerApplyLocked(nextSnapshotId, modified, optimisticMerges, ...)
            if (result != SnapshotApplyResult.Success) return result
            closeLocked()
        }
        // 推进全局快照
        val previousModified = globalSnapshot.modified
        resetGlobalSnapshotLocked(globalSnapshot, emptyLambda)
    }

    // 🔔 通知所有 apply 观察者
    if (globalModified != null) {
        observers.fastForEach { it(nonNullGlobalModified, this) }
    }
    if (modified != null && modified.isNotEmpty()) {
        observers.fastForEach { it(modifiedSet, this) }
    }
}
```

**关键步骤**：
1. **检测冲突**：如果在当前快照打开期间，其他快照也修改了同一个状态对象，尝试用 `mergeRecords` 合并
2. **推进全局快照**：`resetGlobalSnapshotLocked` 递增全局快照 ID，使新快照能看到刚才的修改
3. **通知观察者**：把修改过的状态对象集合传给所有 `applyObserver`

---

## 4. Snapshot 如何与 Recomposer 协作

这是最核心的部分。整个过程分三个阶段：**读追踪 → 变更通知 → 无效化传播**。

### 4.1 阶段一：读追踪（Composition 期间）

当 Recomposer 执行重组时，它通过 `composing` 函数创建一个带观察者的 MutableSnapshot：

```kotlin
// Recomposer.kt:1505-1520
private inline fun <T> composing(
    composition: ControlledComposition,
    modifiedValues: MutableScatterSet<Any>?,
    block: () -> T,
): T {
    val snapshot = Snapshot.takeMutableSnapshot(
        readObserver = readObserverOf(composition),    // 🔑 读观察者
        writeObserver = writeObserverOf(composition, modifiedValues),  // 🔑 写观察者
    )
    try {
        return snapshot.enter(block)  // 在此快照上下文中执行 @Composable 函数
    } finally {
        applyAndCheck(snapshot)  // 提交修改
    }
}
```

**readObserverOf**（1491-1493）：

```kotlin
private fun readObserverOf(composition: ControlledComposition): (Any) -> Unit {
    return { value -> composition.recordReadOf(value) }
}
```

**writeObserverOf**（1495-1503）：

```kotlin
private fun writeObserverOf(
    composition: ControlledComposition,
    modifiedValues: MutableScatterSet<Any>?,
): (Any) -> Unit {
    return { value ->
        composition.recordWriteOf(value)
        modifiedValues?.add(value)  // 收集本帧修改过的值（用于级联重组检测）
    }
}
```

**当 `@Composable` 函数执行时，每次读取 `state.value` 都触发 `readObserver`，调用 `composition.recordReadOf(value)`**。

### 4.2 recordReadOf：建立"状态 → 重组作用域"的映射

```kotlin
// Composition.kt:1007-1039
override fun recordReadOf(value: Any) {
    if (!areChildrenComposing) {
        composer.currentRecomposeScope?.let { scope ->
            scope.used = true
            val alreadyRead = scope.recordRead(value)

            if (!alreadyRead) {
                // 标记这个状态对象被 Composition 读取过
                if (value is StateObjectImpl) {
                    value.recordReadIn(ReaderKind.Composition)
                }

                // 核心：建立 observations[value] = scope 映射
                observations.add(value, scope)

                // 处理 derivedStateOf 的依赖映射
                if (value is DerivedState<*>) {
                    val record = value.currentRecord
                    record.dependencies.forEachKey { dependency ->
                        derivedStates.add(dependency, value)
                    }
                    scope.recordDerivedStateValue(value, record.currentValue)
                }
            }
        }
    }
}
```

**核心数据结构 `observations`**：

```kotlin
// Composition.kt:493
private val observations = ScopeMap<Any, RecomposeScopeImpl>()
```

这是一个**多值映射**（一个状态对象可以被多个重组作用域观察）：

```
observations = {
    stateA → [scope1, scope3],    // scope1 和 scope3 都读了 stateA
    stateB → [scope2],           // 只有 scope2 读了 stateB
    stateC → [scope1, scope2],   // scope1 和 scope2 都读了 stateC
}
```

**通俗理解**：`observations` 就是一份"订阅表"——记录了哪些 @Composable 函数（通过 RecomposeScope 表示）依赖了哪些状态对象。

### 4.3 阶段二：变更通知（状态修改时）

当用户代码或动画修改状态时：

```
stateA.value = newValue
  → SnapshotState.kt: overwritable { this.value = newValue }
    → notifyWrite(snapshot, stateA)              // 🔔 全局写入观察者
    → GlobalSnapshot.writeObserver 被调用
      → globalWriteObservers.fastForEach { it(stateA) }
```

全局写入观察者由 Compose 注册，它的作用是**通知平台调度新帧**（`invalidate()`）。

之后，`sendApplyNotifications()` 或 `snapshot.apply()` 会通知 **apply 观察者**：

```
MutableSnapshot.apply()
  → observers.fastForEach { it(modifiedSet, this) }
    → Recomposer 注册的 applyObserver 被调用（Recomposer.kt:1131-1149）
      → changed.fastForEach { snapshotInvalidations.add(it) }
      → deriveStateLocked()
        → 如果有工作，workContinuation.resume()  // 唤醒工作协程
```

**applyObserver 做的事**：

```kotlin
// Recomposer.kt:1131-1149
Snapshot.registerApplyObserver { changed, _ ->
    synchronized(stateLock) {
        if (_state.value >= State.Idle) {
            changed.fastForEach {
                // 过滤：只关心被 Composition 读过的状态对象
                if (it is StateObjectImpl && !it.isReadIn(ReaderKind.Composition)) {
                    return@fastForEach  // 跳过从未在 Composition 中读过的状态
                }
                snapshotInvalidations.add(it)  // 加入无效化集合
            }
            deriveStateLocked()  // 推导新状态，可能唤醒工作协程
        }
    }?.resume(Unit)
}
```

### 4.4 阶段三：无效化传播（recordComposerModifications）

工作协程被唤醒后，调用 `recordComposerModifications()`（Recomposer.kt:454-489）：

```kotlin
private fun recordComposerModifications(): Boolean {
    val changes = synchronized(stateLock) {
        if (snapshotInvalidations.isEmpty()) return hasFrameWorkLocked
        // 取出所有变化的状态对象
        snapshotInvalidations.wrapIntoSet().also { snapshotInvalidations = MutableScatterSet() }
    }
    // 告诉每个组合："这些状态对象变了"
    compositions.fastForEach { composition ->
        composition.recordModificationsOf(changes)
    }
    return synchronized(stateLock) { deriveStateLocked(); hasFrameWorkLocked }
}
```

**`recordModificationsOf`**（Composition.kt:904-922）：

```kotlin
override fun recordModificationsOf(values: Set<Any>) {
    // CAS 循环：把 values 追加到 pendingModifications
    pendingModifications.compareAndSet(old, new)
    if (old == null) {
        synchronized(lock) { drainPendingModificationsLocked() }
    }
}
```

`drainPendingModificationsLocked` 会遍历 pending modifications，对每个变化的状态对象调用 `invalidateScopeOfLocked`：

```kotlin
// Composition.kt:1041-1048
private fun invalidateScopeOfLocked(value: Any) {
    // 查 observations：哪些 scope 读了这个 value
    observations.forEachScopeOf(value) { scope ->
        if (scope.invalidateForResult(value) == InvalidationResult.IMMINENT) {
            observationsProcessed.add(value, scope)
        }
    }
}
```

**这里就是"订阅表"发挥作用的时刻**——查表找出哪些 `RecomposeScope` 依赖了被修改的状态，然后**标记它们为无效**（需要重组）。

### 4.5 级联重组中的 recordWriteOf

在重组过程中，如果 @Composable 函数**写了**某个状态（比如 `derivedStateOf` 的计算结果），`writeObserver` 会触发 `recordWriteOf`：

```kotlin
// Composition.kt:1051-1058
override fun recordWriteOf(value: Any) = synchronized(lock) {
    invalidateScopeOfLocked(value)  // 无效化读了这个值的 scope

    // 如果写的是 derivedState 的依赖，还要无效化读了这个 derivedState 的 scope
    derivedStates.forEachScopeOf(value) { invalidateScopeOfLocked(it) }
}
```

这让 Recomposer 能在 `toRecompose` 循环中检测到级联无效化（上一篇文章的 8.2.3 节）。

---

## 5. 完整数据流图

```
┌─────────────────────────── 用户代码 / 动画 ────────────────────────────┐
│                                                                         │
│  stateA.value = newValue                                                │
│    │                                                                    │
│    ├── StateRecord 链表更新（创建新 record 或复用）                      │
│    │                                                                    │
│    ├── notifyWrite(snapshot, stateA)                                    │
│    │     └── writeObserver?.invoke(stateA)                              │
│    │           └── GlobalSnapshot.writeObserver                         │
│    │                 └── globalWriteObservers → invalidate() 请求帧     │
│    │                                                                    │
│    └── snapshot.apply() / sendApplyNotifications()                      │
│          │                                                              │
│          ├── 冲突检测 + 合并（innerApplyLocked）                         │
│          ├── 推进全局快照（resetGlobalSnapshotLocked）                    │
│          │                                                              │
│          └── 🔔 applyObserver 通知                                      │
│                │                                                        │
│                ▼                                                        │
├─────────────────────────── Recomposer ─────────────────────────────────┤
│                                                                         │
│  applyObserver { changed, _ ->                                          │
│    snapshotInvalidations += changed  (过滤非 Composition 读取的)        │
│    deriveStateLocked()                                                  │
│    workContinuation.resume()  → 唤醒工作协程                            │
│  }                                                                      │
│                                                                         │
│  工作协程被唤醒：                                                        │
│    │                                                                    │
│    ├── awaitWorkAvailable() 返回                                        │
│    │                                                                    │
│    ├── recordComposerModifications()                                    │
│    │     │                                                              │
│    │     ├── 取出 snapshotInvalidations → changes                       │
│    │     │                                                              │
│    │     └── 遍历所有 Composition:                                       │
│    │           composition.recordModificationsOf(changes)               │
│    │             │                                                      │
│    │             └── drainPendingModificationsLocked()                  │
│    │                   │                                                │
│    │                   └── 遍历 changes:                                 │
│    │                         invalidateScopeOfLocked(value)             │
│    │                           │                                        │
│    │                           └── observations.forEachScopeOf(value)   │
│    │                                 scope.invalidate()  → 标记无效     │
│    │                                                                    │
│    └── withFrameNanos { ... }                                           │
│          │                                                              │
│          ▼                                                              │
├─────────────────────────── 帧内重组 ───────────────────────────────────┤
│                                                                         │
│  performRecompose(composition, modifiedValues):                         │
│    │                                                                    │
│    └── composing(composition, modifiedValues) {                         │
│          val snapshot = takeMutableSnapshot(                             │
│            readObserver = { composition.recordReadOf(it) },  ← 重建订阅 │
│            writeObserver = { composition.recordWriteOf(it) }             │
│          )                                                              │
│          snapshot.enter {                                               │
│            composition.recompose()                                      │
│              │                                                          │
│              └── 执行 @Composable 函数                                   │
│                    │                                                    │
│                    ├── 读 state.value → readObserver → recordReadOf     │
│                    │     → observations.add(state, scope)  ← 更新订阅表│
│                    │                                                    │
│                    └── 写 state.value → writeObserver → recordWriteOf   │
│                          → invalidateScopeOfLocked → 可能触发级联重组   │
│          }                                                              │
│          snapshot.apply()  → 变更对外可见 + 通知 applyObserver          │
│        }                                                                │
│                                                                         │
│  applyChanges() → 更新 LayoutNode 树                                    │
│                                                                         │
└─────────────────────────────────────────────────────────────────────────┘
```

---

## 6. 关键设计点详解

### 6.1 为什么需要 Snapshot 而不是直接观察？

直接在 setter 里通知观察者有什么问题？

```
stateA.value = "new1"
stateB.value = "new2"
// 如果 setter 直接触发重组：
//   stateA 变 → 重组 → 读到 stateB 的旧值 → 重组结果不一致！
//   stateB 变 → 再重组 → 浪费
```

Snapshot 的好处：
1. **原子性**：`MutableSnapshot.enter { }` 内的所有修改在 `apply()` 之前对外不可见
2. **合并**：同一帧内多次修改同一个状态，只触发一次重组
3. **一致性**：重组时读到的所有状态来自同一个快照版本，不会"看到半个新半个旧"

### 6.2 observations（订阅表）的更新时机

订阅表在**每次重组时重建**。这是因为：

1. `if` 条件可能变了——上次读的 state 这次可能不读了
2. 重组范围可能变了——新增或移除了 @Composable 函数

重建流程：
- 重组开始前：`observations` 保持旧的订阅关系
- `composing { }` 创建带 readObserver 的快照
- 重组过程中：readObserver 对每次读取调用 `recordReadOf`，更新 `observations`
- 重组结束后：`observations` 反映最新的订阅关系

### 6.3 derivedStateOf 的依赖映射

`derivedStateOf` 是"计算派生状态"，例如：

```kotlin
val items by mutableStateOf(listOf(...))
val filteredCount by derivedStateOf { items.count { it.isActive } }
```

`derivedStateOf` 的特殊之处：它**自身**是一个状态对象，但它**依赖**其他状态对象（`items`）。Snapshot 系统需要两层映射：

```
observations: items → [scopeA, scopeB]          // 直接依赖
derivedStates: items → [filteredCount]           // 间接依赖（通过 derivedStateOf）
              filteredCount → [scopeC]           // scopeC 读了 filteredCount
```

当 `items` 变化时：
1. `invalidateScopeOfLocked(items)` → 无效化 scopeA、scopeB
2. `derivedStates.forEachScopeOf(items)` → 找到 filteredCount
3. `invalidateScopeOfLocked(filteredCount)` → 无效化 scopeC

### 6.4 recordComposerModifications 调用两次的原因

回顾 `runRecomposeAndApplyChanges` 的结构：

```
帧外: recordComposerModifications()  ← 第一次：决定要不要等帧
  ↓
withFrameNanos {
    broadcastFrameClock.sendFrame()   ← 动画执行，可能修改更多状态
    recordComposerModifications()     ← 第二次：收集动画产生的新无效化
    ... recompose ...
}
```

第一次过滤掉不需要等帧的情况（比如只有帧时钟等待者没有无效化）。第二次捕获帧内动画产生的新状态变化。两次之间可能有时间差（等帧的挂起期间），新的修改可能在期间到达。

### 6.5 notifyObjectsInitialized 的作用

```kotlin
// 在 applyChanges 之后调用
Snapshot.notifyObjectsInitialized()
```

在当前快照中创建的**新**状态对象，默认不被视为"已修改"（因为它们刚创建时就是当前值）。调用 `notifyObjectsInitialized` 后，这些对象之后如果被修改，就会出现在 modified 集合中。

**为什么需要？** 重组可能创建新的 `mutableState`（如 `remember { mutableStateOf(0) }`）。这些新状态在创建帧内不应触发无效化（值刚设好，没人读过），但从下一帧开始如果被修改就应该触发。`notifyObjectsInitialized` 画了一条线：线之前的创建不算修改，线之后的修改才算。

---

## 7. 线程安全机制

### 7.1 StateRecord 链表的并发安全

- **读取**：无锁遍历链表，通过 `snapshotId` 和 `invalid` 集合判断合法性
- **写入**：`sync { }` 块内操作（全局锁），确保同一时刻只有一个线程在修改链表结构
- **新增 record**：通过 CAS 操作 `prependStateRecord`，将新 record 的 `next` 指向旧链表头，然后原子更新链表头指针

### 7.2 observations 的并发安全

`observations`（ScopeMap）由 `CompositionImpl` 的 `lock` 保护。所有对 `observations` 的读写都在 `synchronized(lock)` 中。

### 7.3 snapshotInvalidations 的并发安全

`snapshotInvalidations` 由 Recomposer 的 `stateLock` 保护。applyObserver 在 `synchronized(stateLock)` 内添加，`recordComposerModifications` 在 `synchronized(stateLock)` 内取出。

---

## 8. 精简总结

| 组件 | 角色 | 关键数据结构 |
|------|------|------------|
| `StateRecord` 链表 | 状态的版本历史 | 每个 mutableState 一个链表 |
| `readObserver` | 追踪谁读了什么 | `observations: ScopeMap<State, Scope>` |
| `writeObserver` | 追踪谁写了什么 | `modifiedValues: MutableScatterSet` |
| `applyObserver` | 通知修改已提交 | `snapshotInvalidations: MutableScatterSet` |
| `observations` | 状态→作用域的订阅表 | 每次重组重建 |
| `derivedStates` | 派生状态的依赖映射 | 间接依赖链 |

**一句话总结协作机制**：Snapshot 系统在重组时通过 readObserver 建立订阅表（状态→作用域），状态修改时通过 applyObserver 通知 Recomposer，Recomposer 查订阅表找到受影响的作用域并标记无效，下一帧重组时重建订阅表。
