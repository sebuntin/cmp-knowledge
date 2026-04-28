---
title: "一文看懂 Jetapck Compose 布局流程"
source: "https://juejin.cn/post/7446007995417395234"
author:
  - "[[fundroid]]"
published: 2024-12-09
created: 2026-04-28
description: "本文用通俗易懂的语言介绍 Jeptac Compose 的布局流程，涉及到 MeasurePolicy，Modifier，Constraints， Intrinsic measurement 等概念。"
tags:
  - "clippings"
---
## 1\. 前言：从 Compose 生命周期说起

![image.png](https://p6-xtjj-sign.byteimg.com/tos-cn-i-73owjymdk6/550bfb9587864d4fbeeebe90b364e037~tplv-73owjymdk6-jj-mark-v1:0:0:0:0:5o6Y6YeR5oqA5pyv56S-5Yy6IEAgZnVuZHJvaWQ=:q75.awebp?rk3s=f64ab15b&x-expires=1777802726&x-signature=3P%2BGhbPd5OR5Oh3g%2Ba%2Bed%2Baq1q8%3D) Compose 绘制生命周期为三个阶段：

1. **Composition/组合** ：Composable 源码经过运行后生成 `LayoutNode` 的节点树，这棵树被称为 Composition。
2. **Layout/布局** ：对节点树深度遍历测量子节点的尺寸，并将其在父容器内摆放到合适的位置。
3. **Drawing/绘制** ：基于布局后拿到的尺寸和位置信息，绘制上屏。

我们与 Android 经典视图系统的生命周期（Measure，Layout，Drawing）做一个对比：组合是 Compose 的特有阶段，是其能够通过函数调用实现声明式 UI 的核心，想要深入理解 Compose 第一课就是理解这个过程。但我已经有一些文章介绍过了，不在本文讨论范围。可以参考 [深入理解 Jetpack Compose 内核：SlotTable 系统](https://juejin.cn/post/7113736450968911908 "https://juejin.cn/post/7113736450968911908")

绘制阶段与传统视图大同小异，都是通过 Android Cavas API ，底层调用 skia 实现，本文也不做讨论。

本文讨论的重点是布局阶段。Compose 的布局把 Measure 也了囊括进来，相对于 Android View 有相似性，但也有其独有的特点和优势，接下来我们进入正题。

## 2\. Compose 布局过程三步走

Compose 布局包括三个阶段，从当前 Node 出发，需要依次经历：

1. **Measure children** ： 深度遍历子节点，并测量它们的尺寸。
2. **Decide own size** ：根据收集到的子节点尺寸，决定当前节点自己的尺寸
3. **Place children** ：将子节点摆放到合理的相对位置

上面代码描述了一个卡片的布局，下面以这个布局的节点树为例，看一下布局流程

- **Step1** ：从 `Row` 开始发起测量，遵循三步走第一步，深度遍历测量其子节点 `Image` 和 `Column`
- **Step2&3** ： `Image` 发起测量，因为没有子节点需要测量了，所以只需要计算自己的尺寸，也因为没有子节点需要摆放，空实现完成 place 即可。
- **Step4** ： `Column` 发起测量，因其有子节点，继续深度遍历
- **Step5&6** ：测量 Text ，因为一个叶子节点，立即完成自己的 Size 和 Place 阶段
- **Step7&8** ：测量另一个 Text，同上
- **Step9** ：Column 拿到两个子 Text 返回的 Size 后，计算出自己的 Size，不难猜到其计算逻辑应该是 width = maxOf(child1.w, child2.w)， height = sumOf(child1.h, child2.h)。 设置自己的 width 和 height 后，对两个子 Text 进行 Place， 垂直线性摆放。

看一下代码是如何实现这三步。

所有的 Composable 最终都会调用一个公共 Layout Composable 方法，这里面创建 LayoutNode 存储在 `Composition` 节点树

以 `Column` 的实现为例，可以看到调用 `Layout` 时，传入了三个参数

```kotlin
inline fun Column(
    modifier: Modifier = Modifier,
    verticalArrangement: Arrangement.Vertical = Arrangement.Top,
    horizontalAlignment: Alignment.Horizontal = Alignment.Start,
    content: @Composable ColumnScope.() -> Unit
) {
    val measurePolicy = columnMeasurePolicy(verticalArrangement, horizontalAlignment)
    Layout(
        content = { ColumnScopeInstance.content() },
        measurePolicy = measurePolicy,
        modifier = modifier
    )
}
```
- **content** ：在这里定义子 Composable ，组合过后形成当前节点的子节点
- **measurePolicy** ：这是定义了布局的三步走核心逻辑
- **modifier** ：修饰符链，参与到布局或者绘制阶段

`measurePolicy` 和 `modifier` 会存储在当前 LayoutNode 上，等待 `measure` 的开始参与其中。下面重点分析 `MeasurePolicy` 了解三步走如何实现。

## 3\. MeasurePolicy - 测量策略

```kotlin
fun interface MeasurePolicy {

    fun MeasureScope.measure(
        measurables: List<Measurable>,
        constraints: Constraints
    ): MeasureResult

}
```

MeasurePolicy 通过 measure 方法完成测量。这里有两个重要参数：

- **measurables** ：等待测量的对象，其实就是当前节点的子节点
- **constraints** ：测量约束。节点需要基于当前的 Constaints 进行测量， 它规定了节点尺寸的上限和下限，如下：
```kotlin
class Constraints {
    val minWidth: Int
    val maxWidth: Int
    val minHeight: Int
    val maxHeight: Int
    ...
}
```

## 4\. Constraints - 测量约束

父节点通过 `Constraints` 约束子节点的测量。Constraints 非常重要，我们常说 Compose 不怕布局嵌套正是得益于它。反观 Android 原生视图，由于测量阶段的约束不明确，子 View 需要再次请求父 View 给出清楚的 `View.MeasureSpec` ，导致出现多次绘制

举几个例子理解一下 Constraints 如何设置：

对于页面的根节点， Activity 的 Window 的长宽就是其 Constraints 的最大长宽。如果是一个垂直可滚动容器的节点，那么它的 Constraints 的 height 应该是 Infinity，因为它可以跨多个屏幕存在。

此外， Modifier 的装饰能力本质也是通过修改 Constraints 完成的。例如 `fillMaxWidth` 要求被修饰的节点填充整个父容器，所以 Modifier 会在布局阶段将 `minHeight/minWidth` 对齐 max 组值。关于 Modifier 参与布局的流程，稍后介绍。

## 5\. 三步走实现 - Kotlin 语法优势的体现

举例看一下三步走代码如何实现

我们实现一个类似 Column 的布局效果，在 `measurePolicy#measure` 中实现三步走逻辑。

```kotlin
measurePolicy = { // this: MeasureScope
    // Step1：Measure each children
    val placeables = measurables.map { measurable ->
        measurable.measure(constraints)
    }

    // Step2: Deciee own size
    val height = placeables.sumOf { it.height }
    val width = placeables.maxOf { it.width }
    
    layout(width, height) { //this: Placeable.PlacementScope
    
        // Step3: Place children by changing the offset of y co-ord    
        var yPosition = 0

        placeables.forEach { placeable ->
            // Position item on the screen
            placeable.placeRelative(x = 0, y = yPosition)

            // Record the y co-ord placed up to
            yPosition += placeable.height
        }
    }
}
```
1. 每个 `measuable` 提供了参与测量的 `measure` 方法，此处会传入 Constraints ，返回的 `placeable` 中已经存储了测量后的 `widht` 和 `height` ，等待 `place`
2. 基于各个 `placeable` 的 `w` 和 `h` 计算当前节点的 Size，并通过 `layout` 方法设置。 `layout` 方法内会真正的创建 `LayoutNode` 。
3. `layout` 方法的末参是一个 lambda ，这里是第三步摆放子节点的逻辑，通过设置 `y` 轴的偏移量实现纵向布局，非常简单。

特别值得一提的是，通过 `meause` 一个方法就完成三步走，布局逻辑相对传统的 View 系统更加高效，回想传统自定义 View 你需要分别实现 `onMeasure` ， `onLayout` ， `onDraw` 等，逻辑分散，可读性差。

但是这种集中式的写法有一个弊端，需要人为保证代码顺序。试想如果把 `layout` 写在 `measure` 前面怎么办？幸好 Kotlin 强大的编译期检查能力，很好地指导大家写出正确代码：

- `measure` 方法的返回值是 `MeasureResult ` 类型， `layout ` 方法也返回此类型，所以保证了尾部一定是调用 `layout` 完成三步走。
- `Measuable#measure` 调用后返回 `Placeable` 类型，然后才能调用 `Placeable#place` ，这保证了 `place` 和 `measure` 的先后关系
- `Measuable#measure` 只能在 `MeasureScope` 中调用， `Placeable#place` 只能在 `Placeable.PlacementScope` 中调用，这确保了 `place ` 需要在 `layout` 的 lambda 中调用

通过各种返回值类型、作用域类型的约束，大家可以写出安全又一气呵成的代码，这种 API 设计理念值得推崇。

## 6\. Modifier Node

接下来介绍一下 Modifier 如何参与布局的。

Modifier 在组合之后也会成为 Node 存储在节点树上，Modifier 的调用链生成一条单向继承的子节点树，而被修饰的 Composable 会成为这条树枝的叶子结点。

比如上面例子中， `Image` 最终成为 `clip->size` 的子节点。实际上 `Image` 内部有一些内置的 Modifier，所以全部展开后 Image 所在的树枝上有一连串 `ModifierNode` 。

挂在节点树上的 `ModifierNode` 可以参与到深度遍历的绘制流程中，在 `Image` 之前对 Constraints 做出调整，完成对末端 `Image` 的装饰。

以 `Padding ` 修饰符为例，看一下源码：

```kotlin
//组合中调用 paddiung 会
fun Modifier.padding(
    start: Dp = 0.dp,
    top: Dp = 0.dp,
    end: Dp = 0.dp,
    bottom: Dp = 0.dp
) = this then PaddingElement(
    start = start,
    top = top,
    end = end,
    bottom = bottom
)

//Element 存储到链上，创建 PaddingNode
private class PaddingElement(
    ...
) : ModifierNodeElement<PaddingNode>() 

//PaddingNode 定义 measure 逻辑
private class PaddingNode(
    
    overide fun MeasureScope.measure(
        measurable: Measurable, // 注意不是list
        constraints: Constraints
    ): MeasureResult {
        ...
    }
    
) : LayoutModifierNode, Modifier.Node()
```

组合阶段， `Modifier#then` 创建 Element 加入 Modifier chain 中。Element 是无状态的，重组中会重新生成，Element 会在组合中创建有状态的 ModifierNode。 `ModifierNode` 有状态，重组中仅当状态发生变化时被更新，否则不会重新生成。 Modifier Node 是 Compose 1.5 引入的新优化，目的就是通过存储 Modifier 状态参与比较，提升重组性能。 可以参考 [Jetpack Compose 1.5 发布：全新 Modifier 系统助力性能提升](https://link.juejin.cn/?target=https%3A%2F%2Fblog.csdn.net%2Fvitaviva%2Farticle%2Fdetails%2F132797385 "https://blog.csdn.net/vitaviva/article/details/132797385")

ModifierNode 按照参与的阶段不同，分为 `LayoutModifierNode` 和 `DrawModifierNode` 。 对于前者，布局逻辑就是现在 `LayoutModifierNode#measure` 中，和 `MeasurePolicy#measure` 的功能一样，唯一的区别是接受单个 `measurable` 参数而不是 List。因为我们知道了 ModifierNode 是单向继承，所以只会有一个后续子节点。如果把 `LayoutNode` 的 `measure` 看做是自定义 ViewGroup 需要针对多个子 View 布局，那么 `LayoutModifierNode` 的 `measure` 更像是自定义 View，只对自身负责。

## 7\. Modifier.layout {}

除了自定义一个 Modifier 来改变当前节点的布局，还有一个简单的方法就是使用 `Modifier.layout {}` 方法

```kotlin
fun Modifier.layout(
    measure: MeasureScope.(Measurable, Constraints） -> MeasureResult
)
```

我们可以在 Modifier 调用链的任意位置插入 `measure` 自定义代码，对当前节点做装饰。例如下面代码中添加了一个自定义 50px 的 padding。

```kotlin
Box(Modifier
   .background(Color.Gray)
   .layout { measurable, constraints ->
       // an example modifier that adds 50 pixels of vertical padding
       val padding = 50
       val placeable = measurable.measure(constraints.offset(vertical = -padding))
       layout(placeable.width, placeable.height + padding) {
           placeable.placeRelative(0, padding)
       }
   }){ ... }
```

## 8\. Modifier 布局流程

上面代码绘制一个居中摆放 50\*50 的矩形。我们通常不会同时设置这么多 size 相关的 modifier，这个例子只是为了展示 Modifier 的布局流程:

先看一下自顶向下的测量流程：从 `fillMaxSize` 对应的 LayoutModifierNode 出发，假设当前的 Constraints 是 w:0-200，h:0-300。 `fillMaxSize` 的功能是让子节点填满当前全部剩余空间，所以会为子节点创建以下 `childConstraints `:

```kotlin
val childConstraints = Constraints (
    minWidth = outerConstraints.maxWidth,
    maxWidth = outerConstraints.maxWidth,
    minHeight = outerConstraints.maxHeight,
    maxHeight = outerConstraints.maxHeight,
)
```

来到 `warpContentSize` ，它会让子自己决定 size 不设限， min 值再次回归 0， `childConstraints` 如下：

```kotlin
val childConstraints = Constraints (
    minWidth = 0,
    maxWidth = outerConstraints.maxWidth,
    minHeight = 0,
    maxHeight = outerConstraints.maxHeight,
)
```

来到 `size(50)` ，这里自然要给一个具体的 size 约束，如下：

```kotlin
val childConstraints = Constraints (
    minWidth = 50,
    maxWidth = 50,
    minHeight = 50,
    maxHeight = 50,
)
```

以此类推 Constraints 经过不断调整传入到叶子结点 Box 对应的 `LayoutNode` ，完成三步走第一步测量

叶子节点测量完后，再自底向上进行第二三步，整个流程不做赘述了，只提一点： `wrapContentSize` 从语义上是应该跟随子节点的大小，即 50 *50，为什么实际尺寸设置了 200* 300 呢？

因为其父节点 `fillMaxSize` 传入的 Constraints 是 200 *300， `wrapContentSize` 必须填满这个空间，而由于它有一个默认参数 `align = Alignment.Center` ，所以才能出现 50* 50 矩形块居中的效果。

## 9\. Intrinsic Measurements - 固有特性测量

中文将其翻译成“固有特性”，很多人不理解“固有”到底指什么？所以放在本文最后讨论一下

Compose 要求布局过程中每个节点只被测量一次，测量总耗时只与节点数正相关，与层级无关，所以 Comopse UI 不怕嵌套过深，而传统 Android 视图系统中，某个 View 存在多次测量的情况，随着层级变多测量次数会指数级增长，所以传图视图下我们需要通过优化 View 的层级提升性能。

Compose 为了保证“每个节点只测量一次”的原则，甚至增加了编译期检查：

```kotlin
val constraints1 = ...
val constraints2 = ...
val placeable1 = measurable.measure(constraints1
val placeable2 = measurable.measure(constraints2)
```

“每个节点只测量一次” 在提升性能的同时也带来了问题。看下面官方文档的例子

```kotlin
@Composable
fun TwoTexts(modifier: Modifier = Modifier, text1: String, text2: String) {
    Row(modifier = modifier) {
        Text(
            modifier = Modifier
                .weight(1f)
                .padding(start = 4.dp)
                .wrapContentWidth(Alignment.Start),
            text = text1
        )
        Divider(
            color = Color.Black,
            modifier = Modifier.fillMaxHeight().width(1.dp)
        )
        Text(
            modifier = Modifier
                .weight(1f)
                .padding(end = 4.dp)
                .wrapContentWidth(Alignment.End),

            text = text2
        )
    }
}
```

上面代码的本意是希望打造以下的布局效果：

但实际效果不符合预期： `Divider` 的高度没有对齐左右的 `Text` ，而是撑满了容器高度

Row 为测量 Divider 传入 Constraints 时，不知道对齐 Text 高度应该设置怎样的 `maxHeight` 。传入的 `maxHeight` 值比较大导致 Divider 的 `fillMaxSize` 撑满了整个容器。

传统视图体系中类似的情况，Row 在测量了 Text 的高度后，会再测量一次 Divider 并给出更合适的 `View.MeasureSpec` ，但 Compose 中不可以，因为这样违反了“每个节点只测量一次” 的原则。

为此， Compose 引入了“固有特性测量”的机制。在当前节点正式发起深度遍历子测量节点之前的一次“预处理”，从子节点提前获取必要信息，设置更合理的 Constraints， 然后再发起正式测量。

`MeasurePolicy` 中提供了获取“固有特性”尺寸的方法： `IntrinsicMeasureScope.minIntrinsicXXX `

```kotlin
fun interface MeasurePolicy {

   fun IntrinsicMeasureScope.minIntrinsicWidth(
        measurables: List<IntrinsicMeasurable>,
        height: Int
    ): Int

   fun IntrinsicMeasureScope.minIntrinsicHeight
   fun IntrinsicMeasureScope.maxIntrinsicWidth
   fun IntrinsicMeasureScope.maxIntrinsicHeight

}
```

Text 的固有特性的 `minIntrinsicHeight` 是文本内容单行展示的高度；Divider 的 `minIntrinsicHeight` 是 0，当我们改一下例子中的代码，在 Row 的 `Modifier.height` 增加 `IntrinsicSize.Min`

```kotlin
Row(modifier = modifier.height(IntrinsicSize.Min)) {...}
```

Row 在发起子节点测量前，通过 `MeasurePolicy` 提供的固有特性相关方法，获取所有子节点的 `minIntrinsicHeight` ， 取最大的一个设为 `Constraints.maxHeight` 后发起正式测量。这样， Divider 的 `fillMaxSize` 就会跟 Text 两边高度对齐了。

看到这里相信大家理解 “固有”的含义了，其本质代表“不依赖 Constraints” 就可以获取的值，基于这些值更新 Constraints，后续测量只有一次也能正确约束。