---
type: source
created: 2026-04-27
updated: 2026-04-27
source_file: raw/Compose_OHOS_手势事件处理剖析.md
ingested: 2026-04-27
tags:
  - 手势事件
  - 触摸事件
  - InputStrategy
  - 跨语言传递
  - 命中测试
  - 事件转换
related:
  - "[[手势事件处理机制]]"
  - "[[融合渲染架构]]"
  - "[[Messenger通信机制]]"
---

# Compose for OHOS 手势事件处理机制剖析

## 摘要

详细剖析 CMP 中触摸事件从 OHOS 系统到 Compose 手势识别的完整六阶段链路：ArkTS 捕获 → 坐标变换（互操作视图） → NAPI 跨语言传递 → 策略分发 → 事件转换（OHOS→Compose） → Compose 内部处理（命中测试+分发+手势识别）。涵盖两种渲染路径的差异、多指触控追踪、GC 抑制优化、Cancel 事件处理等关键机制。

## 关键发现

- **六阶段链路**：触摸事件经历 ArkTS 捕获 → 坐标变换 → NAPI 桥接 → InputStrategy 分发 → ComposeSceneMediator 转换 → PointerInputEventProcessor 处理
- **两种渲染路径的输入策略差异**：Fusion Renderer 只检查 `isActive()`，SkiaRender 还需等待 `isEglReady()`
- **事件转换核心**：ComposeSceneMediator 负责 OHOS TouchType → Compose PointerEventType 映射、vp→dp 坐标缩放、多指触控追踪（activeChangedPointers 字典）
- **GC 抑制优化**：Press 时抑制 Kotlin/Native GC，Release/Cancel 时恢复，避免触摸处理期间的暂停卡顿
- **Cancel 事件特殊性**：系统取消时必须清空所有追踪指针并通知 Compose 取消所有进行中的手势
- **历史触摸点**：OHOS 采样率高于帧率时，单次回调携带多个历史点，用于提升手势速度计算精度

## 重要细节

### 跨语言传递路径

```
ArkTS .onTouch() → controller.dispatchTouchEvent() → NAPI → C++ arkui_view_controller.cpp:245 → Kotlin ComposeArkUIViewContainer.dispatchTouchEvent()
```

### 事件消费回传

Compose 返回 Boolean（是否消费）→ NAPI 回传 → OHOS 系统决定是否继续向上传递

### 关键代码索引

| 文件 | 职责 |
|------|------|
| `skiarender/Compose.ets:113` | SkiaRender 触摸入口 |
| `fusionRenderer/Compose.ets:126` | Fusion Renderer 触摸入口 |
| `ArkUIView.ets:83` | 互操作视图坐标变换 |
| `arkui_view_controller.cpp:245` | C++ NAPI 桥接 |
| `ComposeArkUIViewContainer.kt:384` | Kotlin 策略分发入口 |
| `ComposeSceneMediator.ohos.kt:303` | 事件转换核心 |
| `PointerInputEventProcessor.kt` | Compose 标准处理流程 |

## 与已有知识的关联

- 新增 [[手势事件处理机制]] 概念页，补充了 [[融合渲染架构]] 中事件处理的完整细节
- 与 [[Messenger通信机制]] 共享 NAPI 跨语言桥接通道
- InputStrategy 策略分发是渲染模式隔离架构的具体体现
