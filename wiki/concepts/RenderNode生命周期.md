---
type: concept
created: 2026-04-19
updated: 2026-04-19
sources:
  - CMP融合渲染架构设计文档.md
tags:
  - CMP
  - 融合渲染
  - RenderNode
  - 生命周期
  - 节点复用
related:
  - "[[融合渲染架构]]"
  - "[[OHRenderNode]]"
  - "[[ContentModifier挂载机制]]"
---

# RenderNode 生命周期

## 定义

RenderNode 生命周期管理是融合渲染中 OHRenderNode 的创建、使用、复用和销毁的完整过程，通过节点复用和缓存策略优化性能。

## 详解

### 四个阶段

1. **创建阶段**：通过 `CreateNormalNode()` 创建，在 `beginRecording()` 中关联到录制器
2. **使用阶段**：三级复用策略（克隆 → 回收 → 缓存）
3. **更新阶段**：`updateNodeStatus()` 集中处理标志位驱动的增量更新
4. **销毁阶段**：Picture 析构解绑节点，OHRenderNode 析构回收子节点

### 三级复用策略

| 策略 | 机制 | 优势 |
|------|------|------|
| **克隆（makeClone）** | 克隆原始节点，复制所有状态，递归克隆子节点 | 复用节点状态，减少初始化开销 |
| **回收（fUnusedCloneNodes）** | 节点不再使用时回收到未使用列表 | 下次直接复用，避免克隆开销 |
| **缓存（fCacheCloneNodes）** | 所有克隆节点保存在缓存列表 | 便于跟踪管理和调试 |

### 状态标志

| 标志 | 含义 |
|------|------|
| `fRealFrameHasChanged` | 真实帧（脏区）已变化 |
| `fFatherMatrixHasChanged` | 父节点矩阵已变化 |
| `fClipShapeHasChanged` | 裁剪形状已变化 |
| `fContentHasChanged` | 绘制内容已变化 |
| `fNodeNeedRedraw` | 节点需要重绘 |

## 关键要点

- 三级复用策略大幅减少节点创建开销
- 标志位驱动的增量更新避免无效操作
- 缓存超过 10 个节点时发出 TRACE 警告
- Picture 销毁时解绑所有关联节点防止悬空引用

## 与其他概念的关系

- [[OHRenderNode]] — RenderNode 的 C++ 实现
- [[ContentModifier挂载机制]] — Node 模式回放时触发节点创建
- [[SkPictureRecorder]] — 录制器管理节点的创建和关联

## 来源

- [[src-CMP融合渲染架构设计文档]] — 第三章 3.5 节：RenderNode 生命周期管理
