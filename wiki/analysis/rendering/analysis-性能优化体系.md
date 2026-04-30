---
type: analysis
created: 2026-04-27
updated: 2026-04-27
sources:
  - raw/applyChanges_unwind_backtrace_analysis.md
  - raw/融合渲染全阶段拆解.md
  - raw/LazyColumn 与 Column 原理及性能对比分析.md
  - raw/Compose_OHOS_手势事件处理剖析.md
tags:
  - 性能优化
  - 脏区管理
  - 节点复用
  - GC抑制
  - 帧时钟
  - 重组优化
related:
  - "[[SkPicture与脏区管理]]"
  - "[[RenderNode生命周期]]"
  - "[[帧时钟协作机制]]"
  - "[[手势事件处理机制]]"
  - "[[SubcomposeLayout与懒组合]]"
  - "[[LazyColumn vs Column 选型决策]]"
  - "[[analysis-FusionRenderer渲染数据流全景]]"
---

# 性能优化体系

本分析综合分散在多个概念页和源文档中的性能优化策略，按渲染管线阶段组织为完整的优化体系。

## 一、优化策略全景图

按渲染管线阶段排列，每项优化作用于不同环节：

```
@Composable → 重组 → 录制 → 回放 → 渲染合成
    │           │       │       │        │
    │      ①重组跳过   ②Picture缓存  ④脏区管理  ⑤RenderService
    │      ③懒组合     ②命令缓存    ④节点复用
    │                   ⑤GC抑制
    │
    └─ ⑥列表选型（<20项用Column）
```

## 二、六项优化策略详解

### ① 重组跳过（Recomposition Skip）

**阶段**：重组（帧时钟阶段 3）

**原理**：Compose 编译器为每个 Composable 函数生成"稳定组"（Stable Group）。当函数参数未变化时，跳过整个函数体的重新执行。

**效果**：重组优化率 **94%**——仅 6% 的 Composable 函数在实际帧中需要重新执行。

**代码层面**：
```kotlin
@Composable
fun MyButton(text: String, onClick: () -> Unit) {
    // 如果 text 和 onClick 引用未变化，跳过重组
    Button(onClick = onClick) { Text(text) }
}
```

**约束**：参数类型必须被标记为 `@Stable` 或 `@Immutable`。`List<T>`、`Map<K,V>` 等不可变集合默认不被视为稳定类型。

### ② Picture 缓存与命令缓存

**阶段**：录制（draw 阶段）

**Picture 缓存（Kotlin 层）**：

RenderNodeLayer 维护 `cachedPicture: SkPicture?`。当 Layer 未失效时，直接使用缓存的 Picture 跳过录制：

```
draw(canvas)
  → cachedPicture != null && !invalidated?
    → 直接绘制 cachedPicture（跳过录制）
    → 否则：SkPictureRecorder 重新录制 → 更新缓存
```

**命令缓存（C++ 层）**：

OHRenderNode 的三级复用策略避免 RecordCmd 重建：
- **克隆**：复制节点状态和 RecordCmd，无需重新录制
- **回收**：不再使用的节点回收到 `fUnusedCloneNodes`，下次直接复用
- **缓存**：所有克隆节点保存在 `fCacheCloneNodes` 中统一管理

**效果**：避免每帧重新录制未变化的绘制内容。

### ③ 懒组合（SubcomposeLayout）

**阶段**：组合（重组之前）

**原理**：LazyColumn 通过 SubcomposeLayout 将组合延迟到测量阶段，只组合可见范围内的 item，非可见 item 不进入组合树。

**代价**：SubcomposeLayout 打破了 Compose 的"组合/布局/绘制"阶段分离——在布局阶段触发组合。这使得：
- 首帧无懒加载优势（需要先测量才能知道可见范围）
- 每个 item 的组合是独立触发的，无法批量优化

**选型决策**：

| 场景 | 推荐 | 原因 |
|------|------|------|
| <20 项 | Column | 首帧更快，无懒组合开销 |
| 20-100 项 | 视滑动频率决定 | Column 全量组合 vs LazyColumn 懒组合 |
| >100 项 | LazyColumn | 内存优势明显 |

### ④ 脏区管理 + 节点复用

**阶段**：回放（OHRenderNode.nodeDraw）

**脏区四大策略**：

| 策略 | 机制 | 效果 |
|------|------|------|
| 边界框合并 | markDrawBounds 每次绘制实时合并 | 避免最后一次性全量计算 |
| Paint 影响计算 | adjustAndMap 考虑 stroke/blur 扩展 | 精确脏区，不多不少 |
| 扩展不缩小 | setRealFrame 只扩展不缩小 | 减少节点重建次数 |
| 无限制兜底 | 无法计算时用 NODE_SIZE_ALIGNMENT | 保证渲染正确性 |

**节点复用三级策略**：

```
首次：CreateNormalNode() → 克隆原始节点
后续：fUnusedCloneNodes 回收列表 → 直接取用（零开销）
管理：fCacheCloneNodes 缓存列表 → 统一跟踪（>10 个 TRACE 警告）
销毁：Picture 析构 → 解绑所有关联节点 → 防止悬空引用
```

**Picture/Node 模式与性能的关系**：
- **Picture 模式**：节点少、管理开销低，但脏区粗粒度（整体重绘）
- **Node 模式**：节点多、管理开销高，但脏区细粒度（局部更新）
- 系统根据内容复杂度、稳定性（delta>=3）、区域交集自动选择

### ⑤ GC 抑制 + 帧时钟效率

**GC 抑制**：

```
Press → internalStartGCSuppressor() → 抑制 KN 垃圾回收
Release/Cancel → internalStopGCSuppressor() → 恢复 GC
```

**原因**：Kotlin/Native 的 GC 会暂停所有线程。触摸事件（尤其是 Press）可能触发 GC 导致卡顿。抑制 GC 保证触摸响应流畅。

**帧时钟效率**：

FlushCoroutineDispatcher 双路径确保无帧时不浪费 vsync：
- 路径 A（帧内）：immediateTasks 同步队列，flush 消费
- 路径 B（帧间）：scope.launch via OhosUiDispatcher 异步回退

帧时钟的 `onNewAwaiters` 回调：无 awaiter 时不请求帧，系统完全空闲。

### ⑥ applyChanges 栈回溯优化

**阶段**：重组后的 applyChanges

**问题**：Kotlin/Native 在 `applyChanges()` 中执行 eager stack trace 捕获，占 **87% CPU 开销**。

**触发场景**（6 种）：
1. LazyList 滚动触发 LaunchedEffect 取消
2. CompositionLocal 值变化
3. 状态快照 apply
4. 可移动内容状态变化
5. 无效组合重试
6. 组合错误恢复

**优化方向**：延迟或禁用非必要的 stack trace 捕获。

## 三、优化策略的交互关系

各优化策略并非独立，它们之间存在增强和冲突：

```
重组跳过 ──增强──→ Picture 缓存（跳过重组 = 不触发 Layer 失效 = 缓存有效）
Picture 缓存 ──增强──→ 节点复用（缓存命中 = 不产生新 Picture = 节点可复用）
脏区管理 ──增强──→ 节点复用（精确脏区 = 减少节点扩展 = 复用更高效）

懒组合 ──冲突──→ 首帧性能（懒组合打破阶段分离，首帧反而更慢）
Picture 模式 ──冲突──→ 脏区精度（聚合减少节点但牺牲局部更新能力）
节点复用 ──冲突──→ 内存占用（缓存列表常驻内存，>10 节点需 TRACE 监控）
```

## 四、性能瓶颈定位指南

| 现象 | 可能瓶颈 | 定位方法 |
|------|---------|---------|
| 帧率下降、卡顿 | 重组范围过大 | Compose Compiler 报告查看重组次数 |
| 首帧白屏 | 懒组合 + Layer 初始化 | 检查 LazyColumn item 数量，考虑 Column |
| 内存增长 | RenderNode 缓存不释放 | TRACE 检查 fCacheCloneNodes 大小 |
| 触摸响应延迟 | GC 暂停 | 检查 suppressGCIfNeed 是否生效 |
| applyChanges CPU 高 | 栈回溯捕获 | 查看 LazyList 滚动时的 KN profile |
| 脏区过大（全屏重绘） | Picture 模式过多 | TRACE 检查模式决策日志 |

## 五、时间占比参考

基于 [[src-融合渲染全阶段拆解]] 的实测数据：

| 阶段 | 占比 | 优化空间 |
|------|------|---------|
| 手势处理 | 12.71% | GC 抑制已优化 |
| 重组 + applyChanges | 主要 | 重组跳过 94% 已优化，applyChanges 栈回溯待优化 |
| Kotlin 绘制 | 1.79% | Picture 缓存已优化 |
| C++ 录制 | 主要 | 命令缓存 + 脏区管理 |
| RenderService 合成 | 平台层 | 节点模式决策影响 |

## 来源

- [[src-applyChanges_unwind_backtrace_analysis]] — applyChanges 栈回溯 87% CPU 问题
- [[src-融合渲染全阶段拆解]] — 管线各阶段时间占比（手势 12.71%、绘制 1.79%）
- [[src-LazyColumn与Column原理及性能对比分析]] — 懒组合代价与选型决策
- [[src-Compose_OHOS_手势事件处理剖析]] — GC 抑制机制
- [[src-CMP融合渲染架构设计文档]] — 脏区四大策略、节点三级复用
