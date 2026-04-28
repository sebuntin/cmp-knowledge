---
type: source
created: 2026-04-19
updated: 2026-04-19
source_file: raw/融合渲染全阶段拆解.md
ingested: 2026-04-19
tags:
  - CMP
  - 融合渲染
  - 全阶段
  - 渲染流程
---

# src-融合渲染全阶段拆解

## 摘要

本文档是 FusionRenderer 渲染管线的全阶段性能分析文档，以"四棵树"（Composition Tree → LayoutNode Tree → Kotlin Layer Tree → C++ OHRenderNode Tree）为主线，按初始化、帧调度、手势处理、重组、测量、布局、绘制七个阶段逐层拆解执行流程、数据形态转换和负载分布。文档附带 hiperf 实测数据（主线程 1.64B 指令），给出了各阶段的 TOP-N 热点函数和优化机会，可直接用于 Profile Perf 采样定位。

## 关键发现

1. **四棵树之间传递的并非节点实例，而是逐层收紧的结果形态**：Composition 产出结构补丁（ChangeList），LayoutNode 产出绘制边界（coordinator 链 + createLayer 决策），Layer 产出 picture 录制结果（SkOHPicture + hash + originNode），OHRenderNode 产出批量节点操作（NodeModifyInfo → doModify batchCtx）。每一跳都在换一种更接近平台消费的数据形态。

2. **手势处理是第二大独立成本中心（12.71%/208M subEvents），此前常被忽略**：`FlushTouchEvents` 在 `FlushVsync` 内占 55.6%，包含 MMI 跨进程投递、ACE-NG 批量分发、C++ Bridge 转发、Kotlin 三趟命中测试（Initial/Main/Final）和手势识别叶子函数。滑动场景下与重组量级相当。

3. **真实 Kotlin 绘制仅占 1.79%**：`CanvasLayersComposeSceneImpl#draw` 开销远低于直觉；C++ 侧 RenderNode 状态更新（`updateNodeStatus` 2.15%）和批量提交（`doModify` 1.07%）才是绘制瓶颈。绘制阶段 8 层缓存/跳过机制将理论 150K 条指令/帧压缩到 ~12K。

4. **重组优化幅度达 94%**：`$changed` 参数传播（57%）+ Key 快速路径（29%）+ Gap Buffer O(1) 插入（5.6%）+ applyChanges 批量（1.4%）将理论 ~50K/帧压缩到 ~3K。但 `Pending.getNext()` 的 O(n) 线性搜索仍是已知热点。

5. **CRenderNode/JsRenderNode 选择受设备能力和生命周期时机双重约束**：`capiRenderNodeSupported` 管能不能用（API>60000 或 API=60000&&build>=45），`capiRenderNodeFixed` 管用起来稳不稳（build>=107）。即使设备支持 C API，若 `NodeContent` 尚未挂载也必须回退到 JsRenderNode。

6. **`doMeasureAndLayout()` 每帧被调用两次**：`BaseComposeScene.render()` 中第二轮处理 Snapshot 通知可能引入的新脏标记，大多数帧第二轮无新脏节点但仍有函数调用开销。

## 重要细节

### 初始化三阶段绑定

- **子阶段 A（Kotlin 容器创建）**：`ComposeArkUIViewContainer` 构造时仅保存 content lambda 和配置，6 个策略接口均为 lazy 属性，内存占用极小（~200 条指令）
- **子阶段 B（ArkTS aboutToAppear）**：创建 `NodeContent` + `RenderFrameManager`，通过 NAPI 调用 `initFusionRendererNode()` 创建 CRenderNode/JsRenderNode 并挂载到 ArkUI 节点树。CRenderNode 必须在已挂载的 `NodeContent` 上创建，否则 `GetNodeContentFromNapiValue failed: 401`
- **子阶段 C（onAreaChange → onSurfaceChanged）**：首次尺寸就绪后创建 `ComposeSceneMediator` + `ComposeScene`，延迟执行 `setContent()` 避免空转

### 帧调度链路

`displaySync/VSync → ArkUIViewController.onFrame() → ChoreographerManager → FusionRendererFrameDispatcher.onFrame() → FusionRendererContext.notifyRedraw() → CRenderNode/JsRenderNode → OHRenderNode.doRedraw() → fCallbackC → BaseComposeScene.render()`

CRenderNode 路径通过 `fHasPendingAsyncTask` 去重，防止状态抖动放大为多次 draw。

### 手势处理特殊机制

- **GC 抑制**：`suppressGCIfNeed` 在 Press 时启动 GC 抑制，Release/Cancel 时停止，Move 保持抑制状态不变
- **触摸取消短路**：`rawTouchType==3` 时直接 `cancelPointerInput()`，不走命中测试
- **两层守卫**：`isActive()` 为 false 时事件直接消费，不传递给 Compose

### 重组五子阶段

1. **Snapshot 状态检测**（帧间异步）：写入不立即重组，标记失效等待下一帧批量处理
2. **帧调度触发**：`performScheduledEffects` → `performScheduledRecomposerTasks` → `frameClock.sendFrame()`，三步完成后才进入真正重组
3. **Composer Diff**：`$changed` 位标记参数全部不变时 `skipCurrentGroup()` 仅 3 条指令；key 不匹配时惰性创建 `Pending` 做 O(n) 搜索
4. **applyChanges**：所有变更在 `slotTable.write{}` 块内批量执行，通过 `UiApplier` 落成 LayoutNode 树操作
5. **副作用分发**：`SideEffect{}` 同步执行，`LaunchedEffect`/`DisposableEffect` 提交到协程队列下帧处理

### 测量五子阶段

- **脏节点调度**：`DepthSortedSet` 深度优先队列保证父节点先于子节点处理，父节点测量时递归包含子节点，子节点后续 `measurePending=false` 直接跳过
- **约束传播**：`Constraints` 打包为 64-bit Long（4 个 13-bit 字段），比较仅需 1 次 64-bit 等值判断
- **文本测量是最大热点**：`ParagraphImpl::layout()` 含字体匹配、Unicode 断行、行布局三个 CPU 密集型子步骤；`MultiParagraphLayoutCache` 缓存命中时几乎零开销
- **forceMeasureTheSubtree**：`wrapContent` 等非线性布局依赖场景下的顺序修正机制

### 布局五子阶段

- **placeBlock 延迟执行**：`MeasurePolicy.measure()` 返回的 `placeChildren` lambda 延迟到布局阶段执行，是测量与布局解耦的核心
- **mutatedFields 位检查**：属性未变时不重算矩阵，约 5 条指令退出；只有实际变化的属性触发 `updateMatrix()`
- **矩阵构建固定顺序**：translate(pivot) → rotateX/Y/Z → scale → translate(-pivot) → translate(translation)
- **NodeStatusModify 批量提交**：50 个节点各 3 个属性变更 = 150 次 NAPI 调用合并为 1 次 `doModify()`
- **onGloballyPositioned** 是布局最后一步，滥用会随节点数线性增长

### 绘制六子阶段

1. **脏 Layer 预处理**：清理上帧积累的 `dirtyLayers`
2. **NodeCoordinator 绘制链**：layer 有值走 `drawLayer()`，无值沿 `DrawModifierNode` 链递归到 `InnerNodeCoordinator.performDraw()`
3. **RenderNodeLayer 双层录制**：缓存命中时 5 条指令（save/concat/translate/drawPicture/restore）；未命中走 `beginRecording → drawBlock → finishRecordingAsPicture`
4. **C++ 命令转换**：每条 draw 命令同步维护录制边界、overlap 标记和 64-bit FNV hash
5. **OHRenderNode 树状态更新**：静态子树早返回（~3 条指令）、hash 比较跳过、Picture/Node 模式动态决策
6. **RasterCache 状态机**：四道安全检查（溢出/缩放/saveLayer/offscreen）+ 稳定性计数（>=3帧）+ 开销模型判断（gpuCost*2 > rcCost && cpuCost >= 10）

### 全阶段负载矩阵（滑动场景）

| 阶段 | subEvents | 占主线程% |
|------|----------:|----------:|
| L1-手势 | 208,839,222 | 12.71% |
| L1-0 帧调度本体 | 167,005,669 | 10.17% |
| L1-2 重组 | 235,361,531 | 14.33% |
| L1-3/4 测量+布局 | 115,011,070 | 7.00% |
| L1-5 绘制 | 64,626,144 | 3.93% |
| 初始化(首帧) | 22,778,727 | — |

### 潜在优化机会

| # | 机会 | 阶段 | 预估收益 |
|---|------|------|----------|
| 1 | `Pending.getNext` O(n)→O(1) HashMap 索引 | 重组 | 大列表 10-15% |
| 2 | `doMeasureAndLayout` 第二轮条件执行 | 测量 | ~20-50 条/帧 |
| 3 | `updatePictureTreeHash` XOR 增量 | 绘制 | O(children)→O(1) |
| 4 | PictureTreeCmdCache 分片缓存 | 绘制 | 滑动 15-25% |
| 5 | Kotlin↔C++ 批量绘制（100 layer→1 次 JNI） | 绘制 | 80% 跨边界开销 |
| 6 | NodeStatusModify 操作合并（POS+SIZE+TRANSFORM→单次 API） | 布局/绘制 | 30% API 调用减少 |
| 7 | LazyList 预估高度（同类 item 缓存历史测量） | 测量 | 30-50% 首帧测量 |
| 8 | 录制矩形缩减（±2^30 → 实际尺寸 + padding） | 绘制 | 减少内存分配 |

### Trace Marker 体系

文档提供了完整的 37 个 Trace Section Name 速查表，覆盖 Kotlin 层（`OhosTrace.traceSync`）和 C++ 层（`TRACE_EVENT0/1/2`），按 L1-0 帧调度、L1-1 初始化、L1-2 重组、L1-3 测量布局、L1-5 绘制排列，可直接用于 HiTrace/Profile Perf 采样。并标注了 6 个缺失覆盖区域（Skiko 适配层、SnapshotStateObserver、RenderNodeLayer.drawLayer 等）。

## 与已有知识的关联

- **四棵树数据流**补充了 [[融合渲染架构]] 中描述的渲染管线总览，增加了每跳传递的具体数据形态（ChangeList → coordinator 链 → SkOHPicture → batchCtx）
- **初始化三阶段绑定**细化了 [[RenderNode生命周期]] 中 CRenderNode/JsRenderNode 的创建时机和选择逻辑
- **绘制阶段 8 层缓存机制**与 [[SkPicture与脏区管理]] 互补，增加了 Kotlin 层 SkPicture 缓存、C++ DrawingHash 去重、PictureTreeCmdCache、RasterCache 四层缓存分析
- **C++ 命令转换流程**与 [[OH_Drawing命令转换]] 对应，补充了 hash 累加、overlap 标记等录制期同步维护机制
- **OHRenderNode 树更新**细化了 [[OHRenderNode]] 中 `traverseAndUpdateStatus` 的完整分支（静态子树早返回 → 自身重录 → 子节点递归 → 模式决策 → 缓存判断）
- **批量提交流程**与 [[ContentModifier挂载机制]] 对应，补充了 `NodeStatusModify::doModify()` 的 CRenderNode/JsRenderNode 两条路径差异
- **SkPictureRecorder 录制**与 [[SkPictureRecorder]] 对应，增加了 beginRecording→drawBlock→finishRecordingAsPicture 的 Kotlin/C++ 跨边界流程

## 来源

- 原始文档：`raw/融合渲染全阶段拆解.md`（~213KB，3443 行）
- hiperf 数据来源：pid=37777，主线程总指令 1,642,697,537，事件类型 `raw-instruction-retired`
- 测试场景：图文混排长列表滑动（10-20 可见 item，每帧 1-2 item 进出 viewport）
