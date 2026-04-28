---
type: analysis
created: 2026-04-27
updated: 2026-04-27
sources:
  - raw/CMP融合渲染架构设计文档.md
  - raw/融合渲染全阶段拆解.md
  - raw/融合渲染整体方案总结.md
  - raw/Canvas生命周期详解.md
tags:
  - 融合渲染
  - 渲染数据流
  - 管线架构
  - Picture录制
  - 命令转换
  - 脏区管理
related:
  - "[[融合渲染架构]]"
  - "[[SkPicture与脏区管理]]"
  - "[[OH_Drawing命令转换]]"
  - "[[ContentModifier挂载机制]]"
  - "[[RenderNode生命周期]]"
  - "[[OHRenderNode]]"
  - "[[SkPictureRecorder]]"
  - "[[SkCanvas]]"
  - "[[帧时钟协作机制]]"
---

# Fusion Renderer 渲染数据流全景

本分析将 5 个概念页和 3 个实体页的知识综合为一条完整的渲染数据流：从 `@Composable` 函数声明到屏幕像素输出，逐层追踪数据如何穿越 Kotlin → C++ → OH_Drawing → RenderService。

## 一、完整管线总览

```
@Composable 函数
    │  Compose 编译器生成组合树
    ▼
Recomposition（帧时钟阶段 3）
    │  frameClock.sendFrame → performRecompose → applyChanges
    │  更新 LayoutNode 树
    ▼
RenderNodeLayer.invalidate()
    │  Picture 缓存失效 → 触发重新录制
    ▼
SkPictureRecorder.beginRecording()
    │  创建 OH_Drawing_RecordCmdUtils + OH_Drawing_Canvas
    ▼
SkCanvas 绘制操作（逐条实时转换）
    │  drawRect → attachPaint → OH_Drawing_CanvasDrawRect → detachPaint → markDrawBounds
    │  drawPath → attachPaint → OH_Drawing_CanvasDrawPath → detachPaint → markDrawBounds
    │  ... 每条绘制命令同时完成：命令转换 + 脏区累计
    ▼
SkPictureRecorder.finishRecordingAsPicture()
    │  getFinishDrawBounds() → 计算最终脏区
    │  setRealFrame(paintArea) → 设置到 RenderNode
    │  生成 SkOHPicture（持有 OH_Drawing_RecordCmd）
    ▼
OHRenderNode.nodeDraw() / doRedraw()
    │  Picture vs Node 模式决策
    ▼
┌─────────────────────────────────────┐
│ Picture 模式                         │  Node 模式
│ OH_Drawing_CanvasDrawRecordCmdNesting │  generateNewNode()
│ 命令直接聚合到父节点 ContentModifier   │  appendChild → ContentModifier 挂载
│ Canvas = 当前录制 Canvas              │  Canvas = ContentModifier 执行上下文
└─────────────────────────────────────┘
    │
    ▼
OHOS RenderService 硬件加速渲染
    │  RenderNode 树遍历 → ContentModifier 执行 → 光栅化 → 显示
    ▼
屏幕像素输出
```

## 二、逐层数据格式变化

数据在管线中经历了 5 次格式转换，每一层都改变了数据的表示形式：

| 层 | 输入格式 | 处理 | 输出格式 | 负责组件 |
|----|---------|------|---------|---------|
| Compose | `@Composable` DSL | 重组 + applyChanges | LayoutNode 树 | Recomposer |
| Layer | LayoutNode 绘制请求 | PictureRecorder 录制 | SkPicture | RenderNodeLayer |
| 录制 | Skia 绘制 API | 实时命令转换 + 脏区累计 | OH_Drawing_RecordCmd + SkRect | SkCanvas |
| 回放 | RecordCmd + 脏区 | Picture/Node 模式决策 | ContentModifier 挂载 | OHRenderNode |
| 渲染 | ContentModifier 内容 | 硬件加速执行 | 像素 | RenderService |

**核心洞察**：录制层（SkCanvas）是唯一同时完成两个任务的层——命令格式转换（Skia→OH_Drawing）和脏区累计（markDrawBounds）。这种"边录制边转换"的设计避免了后处理开销。

## 三、脏区在管线中的三层传递

脏区信息在三个不同层次中流动，每一层有不同的语义：

### 3.1 Layer 层：Picture 缓存失效

```
RenderNodeLayer.invalidate()
  → cachedPicture = null
  → 通知父 NodeCoordinator → 递归向上
```

语义：**"这个区域的内容需要重新录制"**。粒度为整个 Picture，不做部分更新。

### 3.2 录制层：fDrawBounds 累计

```
每次 drawXxx → markDrawBounds(area, paint) → fDrawBounds.join(deviceArea)
finishRecording → getFinishDrawBounds() → SkRect
```

语义：**"录制期间所有绘制操作的设备坐标并集"**。实时计算，考虑 Paint 影响（stroke width、blur）。

### 3.3 RenderNode 层：paintArea 管理

```
setRealFrame(paintArea) → fRealFrame
updateNodeStatus() → 标志位驱动增量更新
"扩展不缩小"策略 → 避免频繁节点重建
```

语义：**"这个 RenderNode 需要覆盖的屏幕区域"**。只扩展不缩小，确保视觉正确性。

### 三层脏区的协作

```
Layer 失效（需要重录）
  → 录制器累计 fDrawBounds（录制期间的脏区）
  → setRealFrame 传递给 RenderNode（最终脏区）
  → RenderNode 根据 dirty 标志决定是否请求下一帧
```

## 四、Picture 模式 vs Node 模式的完整决策路径

模式选择发生在 `OHRenderNode.nodeDraw()` 中，决定了命令如何到达 RenderService：

```
nodeDraw(canvas)
│
├─ 强制 Picture 模式（4 种情况）
│  ├─ 无父节点（canvas_node == nullptr）→ 无处挂载子节点
│  ├─ isForceDrawInPicture → 上层指令
│  ├─ isInSaveLayer → SaveLayer 内需保持透明度合成
│  └─ 无 origin 节点 → 无挂载点
│
├─ Node 模式（5 种情况）
│  ├─ 绘制区域与父节点子节点相交 → 需独立脏区避免重叠
│  ├─ 矩阵变化 → 需独立变换
│  ├─ 高频回放 → 独立节点缓存优化
│  ├─ 内容稳定（delta >= 3）→ 稳定内容值得独立缓存
│  └─ 有兄弟节点 → 可能需要独立管理
│
└─ Picture 模式（默认回退）
   └─ 安全合并到父节点，内容无交集
```

**性能影响**：

| 维度 | Picture 模式 | Node 模式 |
|------|-------------|----------|
| 节点数量 | 少（聚合到父节点） | 多（每个独立节点） |
| 脏区精度 | 粗粒度（父节点级别） | 细粒度（独立脏区） |
| 缓存效率 | 低（整体重绘） | 高（局部更新） |
| 节点管理开销 | 低 | 高（创建/复用/销毁） |
| 适用 | 简单静态内容 | 复杂动态内容 |

## 五、帧循环中的渲染时序

渲染数据流与帧时钟六阶段的对应关系：

| 帧阶段 | 操作 | 对渲染管线的意义 |
|--------|------|----------------|
| 阶段 1: flush effect | 执行上帧动画协程 | 动画值更新可能触发 Layer 失效 |
| 阶段 2: flush recompose | Recomposer 恢复 | Recomposer 挂起在 frameClock |
| 阶段 3: sendFrame | 重组 + applyChanges | **LayoutNode 树更新，产生录制需求** |
| 阶段 4: measure+layout | 布局 | 确定组件大小和位置 |
| 阶段 5: snapshot 通知 | 刷新快照 | 处理残留状态变化 |
| 阶段 6: draw | **执行录制→回放→渲染** | **完整管线在此执行** |

阶段 6 的 `draw(canvas)` 内部：
```
draw(canvas)
  → RenderNodeLayer.updatePicture() → SkPictureRecorder 录制 → 生成 SkOHPicture
  → OHRenderNode.doRedraw() → Picture/Node 模式决策 → ContentModifier 挂载
  → RenderNode 树标记完成 → 等待 RenderService 下一次合成
```

## 六、三阶段绑定的时序保证

| 绑定阶段 | 时机 | 保证的约束 |
|---------|------|-----------|
| 编译时 | 编译期 | Composable 函数结构正确 |
| ArkTS 运行时 | aboutToAppear | NodeContainer + CanvasNodeController 就绪，RenderNode 可创建 |
| Compose 运行时 | 首次 onSurfaceChanged 后 | ComposeSceneMediator.setContent → 内容绑定延迟到尺寸就绪 |

**关键约束**：renderNode 必须延迟到 `aboutToAppear` 内创建（已挂载到组件树的 NodeContent），否则会因 `GetNodeContentFromNapiValue failed: 401` 崩溃。这解释了为什么 Compose 运行时绑定必须在 ArkTS 运行时绑定之后。

## 七、性能关键路径

从数据流角度，性能热点集中在三个环节：

| 热点 | 位置 | 原因 | 优化策略 |
|------|------|------|---------|
| 重组 | 阶段 3 | 大范围状态变化触发重组 | 重组优化 94%（稳定标记跳过） |
| 录制 | 阶段 6 draw | 每条命令实时转换 | Picture 缓存避免重复录制 |
| 脏区扩大 | setRealFrame | "扩展不缩小"导致脏区增长 | RenderNode 三级复用减少重建 |

数据流中的 Kotlin 绘制仅占总时间的 **1.79%**，主要开销在 C++ 录制层和 RenderService 合成层。

## 来源

- [[src-CMP融合渲染架构设计文档]] — 整体架构与四层数据流
- [[src-融合渲染全阶段拆解]] — 管线各阶段时间占比
- [[src-融合渲染整体方案总结]] — 双模式决策与优化策略
- [[src-Canvas生命周期详解]] — Canvas 三层类型与录制流程
- [[src-渲染模式隔离架构设计文档]] — 策略隔离架构
