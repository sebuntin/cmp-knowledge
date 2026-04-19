---
type: entity
category: C++ 类
created: 2026-04-19
updated: 2026-04-19
sources:
  - CMP融合渲染架构设计文档.md
tags:
  - CMP
  - C++
  - OHRender
  - RenderNode
related:
  - "[[融合渲染架构]]"
  - "[[RenderNode生命周期]]"
  - "[[ContentModifier挂载机制]]"
  - "[[SkPictureRecorder]]"
---

# OHRenderNode

## 定义

OHRenderNode 是 OHOS RenderNode 的 C++ 封装类，负责管理 RenderNode 的生命周期、绘制内容、父子关系和状态更新。它是融合渲染架构中连接 OHRender 层与 OHOS RenderService 的核心桥梁。

## 基本信息

| 属性 | 值 |
|------|-----|
| **语言** | C++ |
| **位置** | `OHRender/OHRender/src/oh/OHRenderNode.cpp` |
| **头文件** | `OHRender/OHRender/include/oh/OHRenderNode.h` |
| **命名风格** | Skia 风格（成员变量 `f` 前缀） |

## 核心方法

### 绘制相关

| 方法 | 说明 |
|------|------|
| `nodeDraw(OH_Drawing_Canvas*)` | 在 ContentModifier 中执行绘制命令 |
| `pictureDraw(OH_Drawing_Canvas*, bool)` | 在 Picture 模式中回放绘制命令（递归子节点） |
| `doRedraw()` | 触发 Compose 重新绘制 |

### 状态管理

| 方法 | 说明 |
|------|------|
| `setRealFrame(SkRect&, bool)` | 设置脏区（扩展不缩小策略） |
| `updateNodeStatus()` | 集中更新节点状态 |
| `updateNowFrame()` | 更新当前帧大小 |
| `pushStatusToModify()` | 将状态推送到 JS RenderNode |

### 节点关系

| 方法 | 说明 |
|------|------|
| `appendChild(shared_ptr<OHRenderNode>)` | 追加子节点 |
| `setParent(OHRenderNode*)` | 设置父节点 |
| `makeClone()` | 克隆节点（递归克隆子节点） |
| `generateNewNode()` | 生成新节点或复用（通过 SkOHPicture） |

### 内容管理

| 方法 | 说明 |
|------|------|
| `updatePicture(SkPicture*)` | 挂载/更新绘制命令 |
| `updateFatherMatrix(SkMatrix)` | 更新父节点矩阵 |
| `setPaintArea(SkRect)` | 设置绘制区域 |
| `updateClipArea(variant)` | 更新裁剪区域 |

## 关键成员变量

| 变量 | 类型 | 说明 |
|------|------|------|
| `fPictureCmd` | `OH_Drawing_RecordCmd*` | 存储的绘制命令 |
| `fRealFrame` | `SkRect` | 真实帧（脏区） |
| `fNowFrame` | `SkRect` | 当前帧 |
| `fFatherMatrix` | `SkMatrix` | 父节点变换矩阵 |
| `fChildList` | `vector<shared_ptr<OHRenderNode>>` | 子节点列表 |
| `fNoLimitSize` | `bool` | 是否无限制绘制 |
| `fNodeNeedRedraw` | `bool` | 是否需要重绘 |

## 工作模式

OHRenderNode 在两种模式下工作：

- **nodeDraw 模式**：帧回调时被调用，在 ContentModifier 上下文中执行命令
- **pictureDraw 模式**：在 Picture 模式回放中被调用，递归执行子节点命令

## 与其他实体的关系

- [[SkPictureRecorder]] — 创建并管理 OHRenderNode
- [[SkCanvas]] — 使用 OHRenderNode 进行脏区跟踪

## 来源

- [[src-CMP融合渲染架构设计文档]] — 第一章 1.3 节、第二章、第三章
