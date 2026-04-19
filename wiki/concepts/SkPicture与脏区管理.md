---
type: concept
created: 2026-04-19
updated: 2026-04-19
sources:
  - CMP融合渲染架构设计文档.md
tags:
  - CMP
  - 融合渲染
  - 脏区
  - SkPicture
  - 性能优化
related:
  - "[[融合渲染架构]]"
  - "[[SkPictureRecorder]]"
  - "[[SkCanvas]]"
  - "[[OHRenderNode]]"
---

# SkPicture 与脏区管理

## 定义

**脏区（Dirty Region）** 是 UI 更新过程中实际发生变化的绘制区域。通过精确计算脏区，融合渲染架构只需重绘变化部分而非整个画面，从而显著提升渲染性能。

**SkPicture** 是 Skia 的绘制指令录制容器，在融合渲染中承载从 Compose 绘制到 OH_Drawing 命令的核心数据。

## 详解

### 脏区计算流程

```
绘制操作 (drawRect/drawPath/...)
  → markDrawBounds(area, paint)      — 每次绘制时实时更新
    → adjustAndMap(area, paint)       — 坐标转换 + Paint 影响
      → fDrawBounds.join(deviceArea)  — 合并边界框
  → getFinishDrawBounds()            — 完成录制时返回最终脏区
  → setRealFrame(paintArea)          — 设置到 RenderNode
```

### 核心：fDrawBounds 更新机制

`fDrawBounds` 是 `std::optional<SkRect>` 类型，在每次绘制操作时通过 `markDrawBounds()` 实时合并：

1. **坐标转换**：`adjustAndMap()` 将局部坐标转为设备坐标，考虑 Paint 影响（stroke width、blur 等）
2. **边界框合并**：使用 `join()` 将新绘制区域合并到 fDrawBounds
3. **交集检测**：检查绘制区域是否与子节点区域相交
4. **空值处理**：无法计算时设为 `std::nullopt`

### 四大优化策略

| 策略 | 原理 | 实现位置 |
|------|------|---------|
| **边界框合并** | 每次绘制实时合并，避免最后一次性计算 | `markDrawBounds()` |
| **Paint 影响计算** | 考虑 stroke/blur 扩展边界框 | `adjustAndMap()` |
| **扩展不缩小** | RenderNode 脏区只扩展不缩小，减少重建 | `setRealFrame()` |
| **无限制绘制** | 无法计算脏区时使用固定大小 (NODE_SIZE_ALIGNMENT) | `finishRecordingAsPicture()` |

### Layer 层脏区管理

RenderNodeLayer 通过 Picture 缓存的失效机制管理脏区：

- **缓存命中**：直接绘制已缓存的 Picture
- **缓存失效**：`invalidate()` 清除缓存，通知父层
- **失效触发**：层属性变化、大小变化、内容变化
- **传播机制**：子 Layer → 父 NodeCoordinator → 递归向上

### 数据流示例

```
drawRect(50,50,200,100) → fDrawBounds = (50,50,250,150)
drawRect(300,50,200,100) → fDrawBounds.join() → (50,50,500,150)
drawPath(circle 400,300 r=50 stroke=10) → fDrawBounds.join() → (50,50,500,360)
finishRecordingAsPicture() → getFinishDrawBounds() → (50,50,500,360)
  → setRealFrame((50,50,500,360), false)
  → updateNodeStatus() → updateNowFrame() → pushStatusToModify()
```

## 关键要点

- 脏区是矩形区域，通过合并所有绘制操作的边界框计算得出
- `getFinishDrawBounds()` 在完成录制时调用，返回 `std::optional<SkRect>`
- "扩展不缩小"策略避免频繁的节点重建
- Layer 层脏区与 SkPicture 脏区是两个不同层次的抽象

## 与其他概念的关系

- [[融合渲染架构]] — 脏区管理是整体架构中的关键优化环节
- [[SkPictureRecorder]] — 录制器负责调用 `getFinishDrawBounds()` 和 `setRealFrame()`
- [[OH_Drawing命令转换]] — 脏区计算与命令转换在录制阶段同时发生
- [[OHRenderNode]] — `setRealFrame()` 将脏区应用到 RenderNode

## 来源

- [[src-CMP融合渲染架构设计文档]] — 第二章：SkPicture 脏区管理机制
