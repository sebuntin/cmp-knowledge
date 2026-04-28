---
title: "深入理解 Jetpack Compose LayoutModifier"
source: "https://juejin.cn/post/7320437915351334950"
author:
  - "[[bqliang]]"
published: 2024-01-05
created: 2026-04-28
description: "LayoutModifierNode 是如何改变元素的测量与布局方式？要探究这个问题，首先得了解元素是怎么进行测量与布局的。每个 Composable 函数，经过 Compose 编译器处理后..."
tags:
  - "clippings"
---
## Modifier.layout() & LayoutModifierNode

> 注：本文源码基于：androidx.compose.ui:ui:1.5.4

### 前置知识

在 Compose 中，将数据渲染到屏幕上，一共会经历 3 个阶段：

![3个阶段.webp](https://p1-juejin.byteimg.com/tos-cn-i-k3u1fbpfcp/9810f787f96a4066814e8b17dd49d547~tplv-k3u1fbpfcp-jj-mark:3024:0:0:0:q75.awebp#?w=945&h=127&s=22929&e=png&b=fefefe)

组合（Composition）阶段，Composable 函数会被执行，输出表示界面的树形数据结构：LayoutNode 树，也叫做 UI 树，每个 Composable 函数都对应一个节点 LayoutNode。

![Compisition阶段.gif](https://p9-juejin.byteimg.com/tos-cn-i-k3u1fbpfcp/8f666c8c01d24cf58f9b4e0bf2ef8924~tplv-k3u1fbpfcp-jj-mark:3024:0:0:0:q75.awebp#?w=1080&h=608&s=2584526&e=gif&f=226&b=00ff80)

布局（Layout）阶段，树中的每个元素都会测量其子元素（如果有的话），并将它们摆放到可用的某个位置

![Layout阶段.gif](https://p1-juejin.byteimg.com/tos-cn-i-k3u1fbpfcp/a4f8f9a5aa9d43589ce4e289b01c9420~tplv-k3u1fbpfcp-jj-mark:3024:0:0:0:q75.awebp#?w=1080&h=608&s=1077537&e=gif&f=73&b=ffffff)

界面树的每个节点在布局阶段都有 3 个步骤：

1. 测量所有子项（如果有）；
2. 确定自己的尺寸；
3. 摆放其子项。

![layout-three-step-process.jpg](https://p3-juejin.byteimg.com/tos-cn-i-k3u1fbpfcp/52541badf3de4a8b8ab5e30b90369a53~tplv-k3u1fbpfcp-jj-mark:3024:0:0:0:q75.awebp#?w=1569&h=921&s=68932&e=jpg&b=ffffff)

一般来说，我们会将布局阶段的 3 个 步骤看作是 2 个过程：1.测量过程；2.布局（摆放）过程

![测量过程和摆放过程.jpg](https://p3-juejin.byteimg.com/tos-cn-i-k3u1fbpfcp/4bb37687d6564a91a36faafd0743eda2~tplv-k3u1fbpfcp-jj-mark:3024:0:0:0:q75.awebp#?w=1569&h=1020&s=100089&e=jpg&b=fefefe)

最后一个阶段——绘制（Drawing）阶段，树中的每个节点会在屏幕上绘制像素：

![Drawing阶段.gif](https://p9-juejin.byteimg.com/tos-cn-i-k3u1fbpfcp/fe401baf249a4841a425d659000e3217~tplv-k3u1fbpfcp-jj-mark:3024:0:0:0:q75.awebp#?w=1080&h=608&s=1244616&e=gif&f=58&b=fefbfb)

### Modifier.layout()

Compose 里面有一个 `layout()` 修饰符，可用于修改元素的测量和布局方式，从而影响元素的尺寸和位置。

```kotlin
体验AI代码助手 代码解读复制代码// LayoutModifier.kt
fun Modifier.layout(
    measure: MeasureScope.(Measurable, Constraints) -> MeasureResult
) = this then LayoutElement(measure)
```

`layout()` 修饰符有一个函数类型参数 `measure` ：

- 接收者类型是 MeasureScope；
- 接受两个参数，类型分别为 Measurable 和 Constraints；
- 返回类型为 MeasureResult。
```kotlin
体验AI代码助手 代码解读复制代码Image(
    painter = painterResource(id = R.drawable.android), 
    contentDescription = null,
    modifier = Modifier.layout { measurable, constraints ->
        // 在这里修改元素的测量和布局过程
        // 最后需要返回 MeasureResult
    }
)
```

先来看看 lambda 表达式里的两个参数，第一个参数 Measurable，"可被测量的"，它就是被 `layout()` 修饰符所修饰的元素，对于上面的例子来说，这个 measurable 其实就是 Image 元素。

```kotlin
体验AI代码助手 代码解读复制代码// Measurable.kt
interface Measurable : IntrinsicMeasurable {
    fun measure(constraints: Constraints): Placeable
}
```

可以看到 Measurable 只有一个 `measure()` 方法，参数的类型是 Constraints。恰好，lambda 表达式的第二个参数就是 Constraints，它是父元素对当前元素的约束条件：

![Constraints.jpg](https://p9-juejin.byteimg.com/tos-cn-i-k3u1fbpfcp/687befacd1744984bd636bc71edef7e6~tplv-k3u1fbpfcp-jj-mark:3024:0:0:0:q75.awebp#?w=505&h=309&s=126202&e=jpg&b=f2f5fa)

最后，lambda 表达式要求返回类型为 MeasureResult，这又是什么？从它的名字就可以看出来，这是“测量结果”，里面保存了宽高和对齐线，还有一个 `placeChildren()` 方法，用于在布局过程被调用。

```kotlin
体验AI代码助手 代码解读复制代码// MeasureResult.kt
interface MeasureResult {
    val width: Int
    val height: Int
    val alignmentLines: Map<AlignmentLine, Int>
    fun placeChildren()
}
```

说了这么多，这个 `layout()` 修饰符到底怎么使用啊？先看一下最简单的使用方式，即不修改元素原本的测量和布局方式：

```kotlin
体验AI代码助手 代码解读复制代码Image(
    painter = painterResource(id = R.drawable.android), 
    contentDescription = null,
    modifier = Modifier.layout { /* 拥有 MeasureScope 上下文 */ 
        measurable, constraints ->
        val placeable = measurable.measure(constraints)
        layout(placeable.width, placeable.height) {
0

        }
    }
)
```
- 首先，调用 `measurable.measure(constraints)` 来测量当前元素，也就是让 Image 元素进行自我测量，得到一个 Placeable 实例。
- 然后使用 MeasureScope 的 `layout()` 函数来保存元素的尺寸，这里传入了 `placeable.width` 和 `placeable.height` ，也就是使用了自我测量得到的尺寸。另外，还传入了一个 lambda 表达式，在里面调用 `placeable.placeRelative(0, 0)` ，将元素内容摆放到 `(0, 0)` 位置。
	MeasureScope 的 `layout()` 函数返回值类型就是我们需要的 MeasureResult：
	```kotlin
	体验AI代码助手 代码解读复制代码MeasureeScope.kt
	interface MeasureeScope {
	    fun layout(
	        width: Int,
	        height: Int,
	        alignmentLines: Map<AlignmentLine, Int> = emptyMap(),
	        placementBlock: Placeable.PlacementScope.() -> Unit
	    ) = object : MeasureResult { ... }
	}
	```
	![不干预测量和布局.jpg](https://p9-juejin.byteimg.com/tos-cn-i-k3u1fbpfcp/2d578ad3fc774b90aa976a34aaa3adb1~tplv-k3u1fbpfcp-jj-mark:3024:0:0:0:q75.awebp#?w=1080&h=750&s=71641&e=jpg&b=092e41)

#### 修改测量过程

如果要创建一个总是显示为正方形的自定义 Image 组件，可以在 Image 完成自我测量后，从长和宽中取最小值作为正方形的边长，保存为尺寸：

```kotlin
体验AI代码助手 代码解读复制代码@Composable
fun SquareImage(painter: Painter) {
    Image(
        painter = painter,
        contentDescription = null,
        modifier = Modifier.layout { measurable, constraints ->
            val placeable = measurable.measure(constraints)
            val size = min(placeable.width, placeable.height)
            layout(size, size) {
0

            }
        }
    )
}
```
![正方形 Image.jpg](https://p6-juejin.byteimg.com/tos-cn-i-k3u1fbpfcp/df584ece7a1c4f839a3d5a0ce50079ee~tplv-k3u1fbpfcp-jj-mark:3024:0:0:0:q75.awebp#?w=1080&h=750&s=37763&e=jpg&b=fafafa)

可以看到，虽然我们的图片是长方形，但由于使用了 `Modifier.layout()` 对 Image 自我测量的结果进行修改，最终显示出来的是正方形图像。

在传统 View 里面，等效的写法，需要继承 ImageView，重写 `onMeasure()` 方法：

```kotlin
体验AI代码助手 代码解读复制代码class SquareImageView @JvmOverloads constructor(
    context: Context,
    attrs: AttributeSet? = null,
    defStyleAttr: Int = 0
) : AppCompatImageView(context, attrs, defStyleAttr) {

    override fun onMeasure(widthMeasureSpec: Int, heightMeasureSpec: Int) {
        super.onMeasure(widthMeasureSpec, heightMeasureSpec) // 先让 ImageView 自我测量
        val size = min(measuredWidth, measuredHeight) // 取长宽最小值
        setMeasuredDimension(size, size) // 保存尺寸
    }
}
```

这里只是针对提出的简单场景，对比 Compose 和 View 的写法。Compose 的 `Modifier.layout()` 并不等价于 View 里面的 `onMeasure()` 。对于元素的测量过程而言， `Modifier.layout()` 只能修改"测量前的约束条件"或"测量后得到的尺寸"。它不能 100% 修改元素测量过程，也不能像 `onMeasure()` 那样测量子元素（子 View），只能对元素自身的测量过程进行简单的修改（修饰）。

#### 修改布局过程

`Modifier.layout()` 除了能修改元素的测量方式，还能修改元素的布局方式。比如将元素内容向右偏移 20 dp：

```kotlin
体验AI代码助手 代码解读复制代码Text(
    text = "Hello Android!",
    fontSize = 38.sp,
    modifier = Modifier
        .background(Color.Yellow)
        .layout { measurable, constraints ->
            val placeable = measurable.measure(constraints)
            layout(placeable.width, placeable.height) {
                placeable.placeRelative(20.dp.roundToPx(), 0)
                // 其实这里使用 placeable.place() 也是可以的，
                // 只是 placeable.placeRelative() 支持 RTL 布局
            }
    }
)
```
![layout修饰符向右偏移20dp.jpg](https://p6-juejin.byteimg.com/tos-cn-i-k3u1fbpfcp/ef987e8ae22b4137bc2b9c6b80a69f33~tplv-k3u1fbpfcp-jj-mark:3024:0:0:0:q75.awebp#?w=1080&h=400&s=64767&e=jpg&b=e5e5e5)

不知道你是否发现，刚才说的是“对 **元素内容** 进行偏移”，而不是“对元素进行偏移”，注意二者的区别。

元素内容偏移，参照物是元素本身；而元素偏移，参照物是父元素。

![元素偏移 VS 元素内容偏移.jpg](https://p3-juejin.byteimg.com/tos-cn-i-k3u1fbpfcp/6fcc0a19c48d4039ac5711113ea56096~tplv-k3u1fbpfcp-jj-mark:3024:0:0:0:q75.awebp#?w=2460&h=600&s=219544&e=jpg&b=f0f0f0)

为什么 `placeable.placeRelative()` 摆放的不是元素自身，而是元素内容呢？我们换个角度思考，一个元素的摆放是由它的父元素决定的，而我们现在用的是 `Modifier.layout()` ，Modifier 是用于修改被修饰元素的外观和行为的，不应该干预父元素的行为，这样看事情似乎就变得合理了。

#### 小结

`Modifier.layout()` 修饰符，只适用于需要对元素自身测量过程和布局过程进行简单修改的场景。简单来说，你对某个元素的测量和布局方式没有大刀阔斧修改的需求，只想微调一下尺寸，挪挪位置，那么 `Modifier.layout()` 修饰符就能派上用场了。

#### Sample

现在我们使用 `layout()` 修饰符来自定义一个功能类似 `padding()` 的修饰符，用于为元素添加内边距。

```kotlin
体验AI代码助手 代码解读复制代码fun Modifier.spacing(spacing: Dp): Modifier = layout { measurable, constraints ->
    val spacingInPx = spacing.roundToPx()
    val placeable = measurable.measure(constraints.copy(
        maxWidth = constraints.maxWidth - spacingInPx * 2,
        maxHeight = constraints.maxHeight - spacingInPx * 2
    ))
    val width = placeable.width + spacingInPx * 2
    val height = placeable.height + spacingInPx * 2
    layout(width, height) {
        placeable.placeRelative(spacingInPx, spacingInPx)
    }
}
```

首先，在元素进行自我测量前，需要修改约束条件，最大可用高度和宽度，需要减去内边距 \* 2，因为对于元素实际内容来说，它可用空间变小了。

其次，让元素进行自我测量，将得到的长和宽都加上内边距 \* 2，再保存为尺寸，因为内边距也是算在尺寸里面的。

最后，在摆放元素内容时，向右下偏移。That's all，就这么简单！

测试一下：

```kotlin
体验AI代码助手 代码解读复制代码Text(
    text = "Hello, Compose!",
    fontSize = 38.sp,
    modifier = Modifier
        .background(Color.Yellow)
        .spacing(20.dp)
)
```
![spacing.jpg](https://p1-juejin.byteimg.com/tos-cn-i-k3u1fbpfcp/42e043ff22f940a48dfb7d2bd939c8cd~tplv-k3u1fbpfcp-jj-mark:3024:0:0:0:q75.awebp#?w=1080&h=500&s=84362&e=jpg&b=e4e4e4)  

### LayoutModifierNode

```kotlin
体验AI代码助手 代码解读复制代码// LayoutNodofoer.kt
fun Modifier.layout(
    measure: MeasureScope.(Measurable, Constraints) -> MeasureResult
) = this then LayoutElement(measure)
```

`layout()` 修饰符背后使用了 LayoutElement，与 `size()` 修饰符、 `padding()` 修饰符背后的 SizeElemrnt、PaddingElement 对比，会发现它们都继承了 `ModifierNodeElement<N : Modifier.Node>` ，这个类的泛型类型 上界是 Modifier.Node。

![修饰符size、padding、layout共同之处.jpg](https://p9-juejin.byteimg.com/tos-cn-i-k3u1fbpfcp/f9916dd6015c4aacb73ef4316d8ae9ac~tplv-k3u1fbpfcp-jj-mark:3024:0:0:0:q75.awebp#?w=2604&h=1998&s=267233&e=jpg&b=fefcfc)

Modifier.Node 是什么？我们都知道，代码 `Modifier.size(100.dp).padding(10.dp)` 会创建出一条 Modifier 链，每个节点都是一个 Modifier。这个 Modifier 链条被真正使用前，会被遍历处理，生成另外一条 Modifier.Node 的双向链条，每个节点都是一个 Modifier.Node。

不过我们也看到，SizeNode、PaddingNode...除了继承自 Modifier.Node，还实现了 LayoutModifierNode 接口，这个接口又是什么？查看它的注释：

```kotlin
体验AI代码助手 代码解读复制代码/**
 * A [Modifier.Node] that changes how its wrapped content is measured and laid out.
 * It has the same measurement and layout functionality as the [androidx.compose.ui.layout.Layout]
 * component, while wrapping exactly one layout due to it being a modifier. In contrast,
 * the [androidx.compose.ui.layout.Layout] component is used to define the layout behavior of
 * multiple children.
 *
 * This is the [androidx.compose.ui.Modifier.Node] equivalent of
 * [androidx.compose.ui.layout.LayoutModifier]
 */
interface LayoutModifierNode : DelegatableNode { ... }
```

大概意思就是，LayoutModifierNode 代表这个 Modifier.Node 能改变其包装内容的测量和布局方式。它与 `Layout()` 函数具有相同的测量和布局功能，不过它终究只是一个 Modifier，所以只能封装一个布局，而 `Layout()` 函数可用于定义多个子元素的布局测量方式。另外，文档里提到，这个 LayoutModifierNode 和 LayoutModifier 是等价的，LayoutModifier 是 1.0.0 版本就有的，后来因为要做性能优化，Compose 团队就对 Modifier 的代码进行逐步重构，1.3.0 版本后就有了 LayoutModifierNode，它俩的功能是一样的。

到这里就不得不提一嘴 Modifier 修饰符的分类了：

![Modifier分类.jpg](https://p6-juejin.byteimg.com/tos-cn-i-k3u1fbpfcp/43072f9174ff483aa72ba7c73c1e5c64~tplv-k3u1fbpfcp-jj-mark:3024:0:0:0:q75.awebp#?w=1650&h=1629&s=134279&e=jpg&b=ffffff)

Modifier 修饰符有很多，不过我们可以按功能来分类：影响元素的测量与布局过程的修饰符，像 `size()` 、 `padding()` 、 `layout()`... 它们都是基于 LayoutModifier 实现的（新版本基于 LayoutModifierNode）；而影响元素绘制流程的修饰符，像 `background()` 、 `border()` 则基于 DrawModifier 实现（新版本基于 DrawModifierNode）。我们最常用的 Modifier 修饰符基本都属于前面的两个分类，此外还有很多其他种类。

#### LayoutNode 的测量流程

LayoutModifierNode 是如何改变元素的测量与布局方式的呢？要探究这个问题，首先得了解元素是怎么进行测量与布局的。每个 Composable 函数，经过 Compose 编译器处理后，都会生成对应的 LayoutNode 对象，LayoutNode 的 `remeasure()` & `replace()` 方法做的就是测量 & 布局工作。

下面来扒一下 LayoutNode 的 `remeasure()` 关键源码：

![LayoutNode的remeasure方法跟源码-1.jpg](https://p3-juejin.byteimg.com/tos-cn-i-k3u1fbpfcp/8d534ab5c5c44126ab5632705ece571b~tplv-k3u1fbpfcp-jj-mark:3024:0:0:0:q75.awebp#?w=1716&h=2826&s=1023139&e=jpg&b=ffffff)

LayoutNode 的 `remeasure()` 方法里，调用了 measurePassDelegate 的 `remeasure()` 方法，而这个 measurePassDelegate 的类型是 LayoutNodeLayoutDelegate.MeasurePassDelegate，所以我们应该跟踪到 LayoutNodeLayoutDelegate.MeasurePassDelegate 的 `remeasure()` 方法。

LayoutNodeLayoutDelegate.MeasurePassDelegate 的 `remeasure()` 方法里，调用了外部类 LayoutNodeLayoutDelegate 的 `performMeasure()` 方法。

LayoutNodeLayoutDelegate 的 `performMeasure()` 里，调用了 `outerCoordinator.measure()` ，outerCoordinator 是谁？是 layoutNode.nodes.outerCoordinator，这时候我们得回头找 LayoutNode 的 nodes，找到 nodes 再继续看它里面的 outerCoordinator，因为上一步就是调用了这个 outerCoordinator 的 `measure()` 方法。

![LayoutNode的remeasure方法跟源码-2.jpg](https://p9-juejin.byteimg.com/tos-cn-i-k3u1fbpfcp/ab97da67aa7c479899d6c64a7db0f37a~tplv-k3u1fbpfcp-jj-mark:3024:0:0:0:q75.awebp#?w=3486&h=2976&s=1824832&e=jpg&b=ffffff)

LayoutNode 的 `nodes` 属性，类型是 NodeChain，继续深入，找到 NodeChain 里面的 `outerCoordinator` ，发现 outerCoordinator 实际上指向了 `innerCoordinator` ，innerCoordinator 的实际类型是 InnerCoordinator，至此终于找到了上一步执行的 `measure()` 方法，它就是 InnerCoordinator 里的 `measure()` 方法，在这个方法里，调用了 `MeasureScope.measure()` 方法，得到了 MeasureResult。

山路十八弯，兜兜转转，我们从 LayoutNode 的 `remeasure()` 方法，一路跟踪，最后发现是调用了 InnerCoordinator 的 `measure()` 方法，在这里面做最终的、实际的测量，从而得到 MeasureResult。

也许你对 InnerCoordinator 的 `measure()` 方法还有很多疑惑，不过现在你只需知道：Compose 组件例如 Text 组件，它的内部定义了具体的测量算法，当使用 Text 组件时，Compose 会生成对应的 LayoutNode 对象，里面自然也包含了测量的具体算法。在测量阶段， LayoutNode 对象的 `remeasure()` 方法就会被执行，里面会调用 InnerNodeCoordinator 的 `measure()` 方法，在这个方法里会执行组件的实际测量算法。

#### LayoutModifierNode 如何影响测量流程

虽然我们简单了解了 LayoutNode 测量流程，但在此过程中，似乎并没有看到哪里和“LayoutModifierNode 改变元素的测量与布局方式”有关系，甚至连 Modifier 的影子都没见着。

让我们换个角度，我们都知道 Composable 函数会生成 LayoutNode 对象，而 LayoutNode 里面有一个 `modifier` 变量，存储的就是修饰 Composable 函数的 Modifier。

![LayoutNode的modifier属性.jpg](https://p1-juejin.byteimg.com/tos-cn-i-k3u1fbpfcp/8b4c2f038ad94032892ac90d362e8d22~tplv-k3u1fbpfcp-jj-mark:3024:0:0:0:q75.awebp#?w=2751&h=693&s=119278&e=jpg&b=fff5f2)

我们不妨从 LayoutNode 的 `modifier` 属性入手，看一看这个 modifier 的 set 方法，如果它被设置为 `Modifier.size(100.dp)` ，将在哪个地方影响到元素的测量与布局。

```kotlin
体验AI代码助手 代码解读复制代码internal class LayoutNode(...) : ... {
    
    internal val nodes = NodeChain(this)
    
    override var modifier: Modifier = Modifier
        set(value) {
            ...
            nodes.updateFrom(value) // 📌 重点
            ...
        }
}
```

我们主要看 set 方法里面的 `nodes.updateFrom(value)` ，这个 nodes 是一个 NodeChain 实例， `NodeChain.updateFrom(modifier)` 就是根据所设置的 Modifier 链来更新 NodeChain。

NodeChain 其实就是存储 Modifier.Node 的双向链表。也就是前面提到的，Modifier 链会被用于生成 Modifier.Node 双向链，所谓的 Modifier.Node 双向链就是 NodeChain。

![Code-Modifier链-Modifier.Node链.jpg](https://p6-juejin.byteimg.com/tos-cn-i-k3u1fbpfcp/ba85ea119c104e368fdf912bf010c0f6~tplv-k3u1fbpfcp-jj-mark:3024:0:0:0:q75.awebp#?w=3099&h=1329&s=228007&e=jpg&b=fdfafa)

```kotlin
体验AI代码助手 代码解读复制代码// NodeChain.kt
internal class NodeChain(val layoutNode: LayoutNode) {
    internal val innerCoordinator = InnerNodeCoordinator(layoutNode)
    internal var outerCoordinator: NodeCoordinator = innerCoordinator
    
    internal val tail: Modifier.Node = innerCoordinator.tail
    internal var head: Modifier.Node = tail
}
```

从源码里看到，这个双向链表 NodeChain 除了头尾节点 `head` 和 `tail` ，还有两个 NodeCoordinator： `innerCoordinator` 和 `outerCoordinator` ，NodeCoordinator 又是啥？

其实每一个 Modifier.Node 都有一个对应的 NodeCoordinator 辅助对象，用于分层测量。

```kotlin
体验AI代码助手 代码解读复制代码// Modifier.kt
interface Modifier {
    abstract class Node : DelegatableNode {
        internal var parent: Node? = null                 // 父节点
        internal var child: Node? = null                  // 子节点
        internal var coordinator: NodeCoordinator? = null // 对应的 NodeCoordinator

        internal open fun updateCoordinator(coordinator: NodeCoordinator?) {
            this.coordinator = coordinator
        }
    }
}

// NodeCoordinator.kt
internal abstract class NodeCoordinator(
    override val layoutNode: LayoutNode,
) : Measurable, ... {
    abstract val tail: Modifier.Node

    internal var wrapped: NodeCoordinator? = null   // 内层 NodeCoordinator
    internal var wrappedBy: NodeCoordinator? = null // 外层 NodeCoordinator

}
```

![Modifier.Node链里面的NodeCoordinator.jpg](https://p6-juejin.byteimg.com/tos-cn-i-k3u1fbpfcp/a9d903aef9454a948ae32f8bb60770c5~tplv-k3u1fbpfcp-jj-mark:3024:0:0:0:q75.awebp#?w=2592&h=2466&s=389460&e=jpg&b=fdf9f9)

在测量过程中，Compose 会遍历 Modifier.Node 链中的每个 NodeCoordinator，调用 NodeCoordinator 的 `measure()` 方法，从而影响元素的测量。同理，在布局过程则遍历调用 NodeCoordinator 的 `placeAt()` 方法。

上图中的例子里，外三层的 NodeCoordinator 负责对应 LayoutModifier 修饰符的测量工作，而最里层的 InnerNodeCoordinator 则负责元素 Box 的测量。

明白了这些，再来看 NodeChain 的 `updateFrom(modifier)` 方法就很清晰了：

```kotlin
体验AI代码助手 代码解读复制代码internal class NodeChain(val layoutNode: LayoutNode) {
    internal val innerCoordinator = InnerNodeCoordinator(layoutNode)
    internal var outerCoordinator: NodeCoordinator = innerCoordinator
    internal val tail: Modifier.Node = innerCoordinator.tail
    internal var head: Modifier.Node = tail

    internal fun updateFrom(m: Modifier) {
        var coordinatorSyncNeeded = false
        val paddedHead = padChain()
        var before = current
        val beforeSize = before?.size ?: 0
        // 📌 Modifier.fillVector() 会将 Modifier 展平
        val after = m.fillVector(buffer ?: mutableVectorOf())
        var i = 0
        if (after.size == beforeSize) { // 检测更新差异
            ...
        } else if (!layoutNode.isAttached && beforeSize == 0) { // 第一次组装 Modifier.Node 双向链表
            coordinatorSyncNeeded = true
            var node = paddedHead
            while (i < after.size) { // 遍历 after 组装 Modifier.Node 双向链表
                val next = after[i]
                val parent = node
                node = createAndInsertNodeAsChild(next, parent)
                logger?.nodeInserted(0, i, next, parent, node)
                i++
            }
            syncAggregateChildKindSet()
        } else if (after.size == 0) { // 删除所有 modifier
            checkNotNull(before) { "expected prior modifier list to be non-empty" }
            var node = paddedHead.child
            while (node != null && i < before.size) {
                logger?.nodeRemoved(i, before[i], node)
                node = detachAndRemoveNode(node).child
                i++
            }
            innerCoordinator.wrappedBy = layoutNode.parent?.innerCoordinator
            outerCoordinator = innerCoordinator
        } else { ... }
        current = after
        buffer = before?.also { it.clear() }
        head = trimChain(paddedHead) // 更新头节点
        if (coordinatorSyncNeeded) {
            syncCoordinators() // 📌 关联 Modifier.Node 和 NodeCoordinator
        }
    }

    fun syncCoordinators() {
        var coordinator: NodeCoordinator = innerCoordinator
        var node: Modifier.Node? = tail.parent
        while (node != null) { // 尾 -> 头，遍历 Modifier.Node 双向链表
            val layoutmod = node.asLayoutModifierNode()
            if (layoutmod != null) { // 如果 Modifier.Node 属于 LayoutModifierNode
                val next = if (node.coordinator != null) { // LayoutModifierNode 已经有对应的 NodeCoordinator 了
                    val c = node.coordinator as LayoutModifierNodeCoordinator
                    val prevNode = c.layoutModifierNode
                    c.layoutModifierNode = layoutmod
                    if (prevNode !== node) c.onLayoutModifierNodeChanged()
                    c
                } else { // LayoutModifierNode 还没有对应的 NodeCoordinator
                    // 创建一个 LayoutModifierNodeCoordinator 与 LayoutModifierNode 关联
                    val c = LayoutModifierNodeCoordinator(layoutNode, layoutmod)
                    node.updateCoordinator(c)
                    c
                }
                // 将当前 LayoutModifierNode 对应的 NodeCoordinator 与上一个 NodeCoordinator 串起来
                coordinator.wrappedBy = next
                next.wrapped = coordinator
                coordinator = next
            } else { // Modifier.Node 不属于 LayoutModifierNode
                // 直接和上一个 NodeCoordinator 关联
                node.updateCoordinator(coordinator)
            }
            node = node.parent
        }
        // 链条所有节点都和对应的 NodeCoordinator 关联完成，最后更新 outerCoordinator
        coordinator.wrappedBy = layoutNode.parent?.innerCoordinator
        outerCoordinator = coordinator
    }
}
```

![3种 Modifier.Node 与 NodeCoordinator 对应情况.jpg](https://p9-juejin.byteimg.com/tos-cn-i-k3u1fbpfcp/cd019ffa57334b6fb4a46c50eaf9ac5b~tplv-k3u1fbpfcp-jj-mark:3024:0:0:0:q75.awebp#?w=4983&h=2850&s=703346&e=jpg&b=fdfdfd)

上图中展示了 3 种情况下 Modifier.Node 与 NodeCoordinator 对应的场景：

1. 不设置 Modifier：只有 InnerNodeCoordinator 用于测量元素自身；
2. 设置的 Modifier 全部都是 LayoutModifier 修饰符：除了 InnerNodeCoordinator 用于测量元素自身，每一个 LayoutModifierNode 都有一个对应的 LayoutModifierNodeCoordinator，用于测量 LayoutModifier 修饰符；
3. 设置的 Modifier 里面既有 Layout 修饰符，也有 Draw 修饰符：Draw 修饰符会和右侧邻近的 Layout 修饰符共用同一个 LayoutModifierNodeCoordinator。

那么，现在思考一个问题，下面代码里蓝色区域的大小是多少呢，100 dp 还是 50 dp？

```kotlin
体验AI代码助手 代码解读复制代码Box(modifier = Modifier
        .size(100.dp)
        .background(blue)
        .size(50.dp)
)
```

在 `syncCoordinators()` 方法里，遍历 Modifier.Node 双向链表绑定对应的 NodeCoordinator 时，是从尾部开始遍历，Draw 修饰符 `.background(blue)` 和它右侧 Layout 修饰符 `.size(50.dp)` 共用同一个 NodeCoordinator。换句话说，Draw 修饰符比如 `.background()` 、`.border()` 的绘制尺寸是受右侧的 Layout 修饰符所影响的，或者说是受对应的 Modifier.Node 的 NodeCoordinator 影响。

![.size(100.dp).background(blue).size(50.dp).jpg](https://p6-juejin.byteimg.com/tos-cn-i-k3u1fbpfcp/45c4bc36e8a34338b2c2aad2afd7db0f~tplv-k3u1fbpfcp-jj-mark:3024:0:0:0:q75.awebp#?w=2658&h=900&s=185440&e=jpg&b=ffffff)

那么按前面的分析来说，蓝色区域的大小应该是 50 dp 才对，因为 `.background()` 的右侧就是 `.size(50.dp)` ，但实际上蓝色区域大小为 100 dp，这又是为什么呢？难道分析错了？

我们的分析没错，Draw 修饰符的绘制尺寸确实是受右侧的 Layout 修饰符所影响，只不过 Layout Modifier 会将尺寸约束会从左边往右传递，在这个例子里， `size(100.dp)` 把约束信息向右传给 `size(50.dp)` ，这导致后者不起作用。

初学 Compose 时，你肯定写过这样的代码： `Modifier.size(100.dp).background(blue)` ，这句代码看上去给人的直觉就是：Draw 修饰符 `background(blue)` 的绘制尺寸是直接受左侧 Layout 修饰符 `.size(100.dp)` 的影响，但其实不然！实际上是约束条件 `.size(100.dp)` 会先影响测量元素的 InnerNodeCoordinator，而由于 `background(blue)` 的绘制区域尺寸就是由（右侧）InnerNodeCoordinator 决定的，所以最后才画出了 100 dp 的蓝色矩形。

#### Modifier 链顺序

我们都知道先调用的 Layout 修饰符会影响后调用的 Layout 修饰符，具体是如何影响的呢？

回顾前面 LayoutNode 的测量流程，LayoutNode 的 `remeasure(constraints)` 方法，最后会调用最外层的 outerCoordinator 的 `measure(constraints)` 方法，在里面做实际测量。

![Modifier链顺序.jpg](https://p1-juejin.byteimg.com/tos-cn-i-k3u1fbpfcp/02b7f252533c4655a041169dcb3c0b98~tplv-k3u1fbpfcp-jj-mark:3024:0:0:0:q75.awebp#?w=2721&h=1683&s=288856&e=jpg&b=fdfafa)

结合图不难看出：约束条件会从外层 NodeCoordinator 往内层更新传递。对于代码 `Modifier.size().padding().padding()` 而言，约束条件则是从左往右更新传递，换而言之，右边的修饰符会受到左边修饰符传递过来的约束限制。

写在最后的 modifier 修饰符反而在最内侧，距离元素最近。

![约束向传递，尺寸向左传递.png](https://p6-xtjj-sign.byteimg.com/tos-cn-i-73owjymdk6/8b12391641a543c3af6a7e94e0bc37b9~tplv-73owjymdk6-jj-mark-v1:0:0:0:0:5o6Y6YeR5oqA5pyv56S-5Yy6IEAgYnFsaWFuZw==:q75.awebp?rk3s=f64ab15b&x-expires=1777841890&x-signature=jlNpVt8IvjqpLv1PDkCFKyro5Uo%3D)

修饰符从左往右更新传递约束条件，然后从右往左传递返回确定的尺寸。

现在思考一个问题，以下两个 Box 最终大小分别是多少？

```kotlin
体验AI代码助手 代码解读复制代码Box(Modifier.size(100.dp).size(200.dp))
Box(Modifier.size(200.dp).size(100.dp))
```

3

2

1

答案揭晓：

```kotlin
体验AI代码助手 代码解读复制代码Box(Modifier.size(100.dp).size(200.dp)) // 最终大小 100 dp
Box(Modifier.size(200.dp).size(100.dp)) // 最终大小 200 dp
```

为什么呢？因为约束条件从左往右传递，右边 Layout 修饰符的测量会受到左边 Layout 修饰符传递过来的约束限制，最终负责测量 Box 的 InnerNodeCoordinator 拿到的约束条件，就是左边 Layout 修饰符传递过来的。

再来看一个例子：

```kotlin
体验AI代码助手 代码解读复制代码Box(
    modifier = Modifier
        .size(100.dp)
        .background(Blue)
        .size(50.dp)
        .background(Origin)
)
```

这个 Box 最终效果是？

A. 100 dp 的蓝色方块盖着 50 dp 的橙色方块；

B. 100 dp 的橙色方块盖着 50 dp 的蓝色方块；

C. 50 dp 的蓝色方块盖着 100 dp 的橙色方块；

D. 50 dp 的橙色方块盖着 100 dp 的蓝色方块.

3

2

1

答案是 E. 100 dp 橙色方块盖着 100 dp 的蓝色方块。

![100 dp橙色方块盖着 100 dp 蓝色方块.jpg](https://p3-juejin.byteimg.com/tos-cn-i-k3u1fbpfcp/3db1561baded4da1b801845a170229cd~tplv-k3u1fbpfcp-jj-mark:3024:0:0:0:q75.awebp#?w=753&h=547&s=43064&e=jpg&b=f4f4f4)
```kotlin
体验AI代码助手 代码解读复制代码Box(
    modifier = Modifier
        .size(100.dp)        // LayoutModifierNodeCoordinator 2  -->  100 dp
        .background(Blue)   //  LayoutModifierNodeCoordinator 1  -->  100 dp
        .size(50.dp)        // LayoutModifierNodeCoordinator 1  -->  100 dp
        .background(Origin) // InnerNodeCoordinator  -->  100 dp
)
```

首先，两个 Draw 修饰符，先 `background(Blue)` 再 `background(Origin)` ，先画蓝再画橙，那么自然是橙色盖着蓝色。然后再看尺寸，所有 Modifier.Node 对应的 NodeCoordinator 都受到最左侧 Layout 修饰符 `.size(100.dp)` 的约束限制。最终的结果就是 100 dp 橙色方块盖着 100 dp 的蓝色方块了。

##### required modifiers

有没有什么办法让右边的 Layout 修饰符不受左边 Layout 修饰符的约束限制？还真有办法，那就是 required modifiers 修饰符。

日常使用的 `width()` 、 `height()` 、 `size()` 修饰符它们都会考虑左边传递过来的约束，而 `requiredWidth()` 、 `requiredHeight()` 、 `requiredSize()` 则会无视左边的约束，它们只会考虑自己的尺寸要求。

```kotlin
体验AI代码助手 代码解读复制代码val columnWidth = 200.dp
Column(
    modifier = Modifier
    .width(columnWidth)
    .border(1.dp, red)
) {
    Text(
        text = "width = parent + 50",
        modifier = Modifier
        .width(columnWidth + 50.dp)
        .background(Color.LightGray)
    )
    Text(
        text = "requiredWidth = parent + 50",
        modifier = Modifier
        .requiredWidth(columnWidth + 50.dp)
        .background(Color.LightGray)
    )
}
```
![突破最大限制.jpg](https://p9-juejin.byteimg.com/tos-cn-i-k3u1fbpfcp/42013928b42449d0996d03edfe92e4dc~tplv-k3u1fbpfcp-jj-mark:3024:0:0:0:q75.awebp#?w=804&h=101&s=27793&e=jpg&b=dbdbdb)

Column 的宽度被设置为 200 dp，那么它的所有子项都会接收到限制：喂，记得测量的时候，宽别超过 200 dp，不然爸爸要撑死啦；

第一个 Text 子项想要 250 dp 宽测量自己，但是听说上级要求最多 200 dp，好吧，那就只要 200 dp 吧；

第二个子项用 `requiredWidth()` 要求用 250 dp 测量自己，什么？最大 200 dp，我才不管，我就要 250 dp。

实际显示到屏幕上，看到的就是：

![突破最大限制-实际效果.png](https://p9-juejin.byteimg.com/tos-cn-i-k3u1fbpfcp/9215c67801f7455a87376ada01cdd77d~tplv-k3u1fbpfcp-jj-mark:3024:0:0:0:q75.awebp#?w=536&h=101&s=12349&e=png&b=cbcbcb)

注意第二个子项，它自认为拥有了 250 dp 宽，所以把内容按照 250 dp 宽的规格来画，但实际上只是掩耳盗，200 dp 范围外的内容都是别人看不见的。

以上例子使用 `requiredWidth()` 修饰符突破了最大尺寸限制，再来看一个突破最小尺寸限制的例子：

```kotlin
体验AI代码助手 代码解读复制代码val min = 150.dp
val max = 200.dp
Column {
    Text(
        text = "width = minWidth",
        modifier = Modifier
        .border(.5.dp, blue)
        .width(min)
        .background(Color.LightGray)
    )
    Text(
        text = "width = minWidth - 50",
        modifier = Modifier
        .border(.5.dp, blue)
        .widthIn(min, max)
        .width(min - 50.dp)
        .background(Color.LightGray)
    )

    Text(
        text = "requiredWidth = minWidth - 50",
        modifier = Modifier
        .border(.5.dp, blue)
        .widthIn(min, max)
        .requiredWidth(min - 50.dp)
        .background(Color.LightGray)
    )
}
```
![突破最小尺寸限制.jpg](https://p3-juejin.byteimg.com/tos-cn-i-k3u1fbpfcp/437e4a60d236446589ef88450026e1cd~tplv-k3u1fbpfcp-jj-mark:3024:0:0:0:q75.awebp#?w=402&h=195&s=36878&e=jpg&b=d5d5d5)

第一行文本，没有宽高约束，将宽设置为最小尺寸 150 dp，OK；

第二行文本，宽约束为 \[150 dp, 200 dp\]， `width()` 要求 100 dp 宽来测量自己，但因为受到约束（最低限制 150 dp），所以最终还是以 150 dp 宽来自我测量；

第三行文本， 宽约束为 \[150 dp, 200 dp\]， `requiredWidth()` 要求 100 dp 宽来测量自己，无视约束（最低限制 150 dp），所以最终以 100 dp 宽来自我测量。

同理，这里要注意的是，第三个 Text 只是在测量时，自认为自己仅拥有 100 dp，所以内容按照 100 dp 宽的规格来画，但在屏幕上这个组件实际所占的宽就是 150 dp。有点像电影里面演的 *创伤后应激障碍（PTSD）* ，主角以为自己瘸了走不了路，但实际上他行动并无问题。

![突破最小尺寸限制-实际效果.jpg](https://p6-juejin.byteimg.com/tos-cn-i-k3u1fbpfcp/8fb32e6df08242b180ef64b519af1059~tplv-k3u1fbpfcp-jj-mark:3024:0:0:0:q75.awebp#?w=402&h=195&s=23060&e=png&b=dacbc5)  
  

到这里，你可以思考一下，怎么利用 required modifier 画出：50 dp 的橙色方块盖着 100 dp 的蓝色方块：

```kotlin
体验AI代码助手 代码解读复制代码Box(
    modifier = Modifier
    .background(Blue)     // LayoutModifierNodeCoordinator 2
    .requiredSize(100.dp) // LayoutModifierNodeCoordinator 2
    .background(Origin)   // LayoutModifierNodeCoordinator 1
    .requiredSize(50.dp)  // LayoutModifierNodeCoordinator 1
)
```

注意， `background(Blue)` 和 `requiredSize(100.dp)` 的顺序不能调换：

```kotlin
体验AI代码助手 代码解读复制代码Box(
    modifier = Modifier
    .requiredSize(100.dp) // LayoutModifierNodeCoordinator 2
    .background(Blue)     // LayoutModifierNodeCoordinator 1
    .background(Origin)   // LayoutModifierNodeCoordinator 1
    .requiredSize(50.dp)  // LayoutModifierNodeCoordinator 1
)
```

具体原因相信不用再解释一遍了。

---

参考：

[Jetpack Compose中的Modifier——川峰](https://link.juejin.cn/?target=https%3A%2F%2Fblog.csdn.net%2Flyabc123456%2Farticle%2Fdetails%2F128324256 "https://blog.csdn.net/lyabc123456/article/details/128324256")

[Compose：LayoutModifier](https://link.juejin.cn/?target=https%3A%2F%2Fblog.csdn.net%2Fqq_31339141%2Farticle%2Fdetails%2F129573217 "https://blog.csdn.net/qq_31339141/article/details/129573217")

[How Jetpack Compose Measuring Works](https://link.juejin.cn/?target=https%3A%2F%2Fdeveloper.squareup.com%2Fblog%2Fhow-jetpack-compose-measuring-works%2F "https://developer.squareup.com/blog/how-jetpack-compose-measuring-works/")

[Custom layouts](https://link.juejin.cn/?target=https%3A%2F%2Fdeveloper.android.com%2Fjetpack%2Fcompose%2Flayouts%2Fcustom "https://developer.android.com/jetpack/compose/layouts/custom")

[Jetpack Compose - Order of Modifiers](https://link.juejin.cn/?target=https%3A%2F%2Fstackoverflow.com%2Fquestions%2F64206648%2Fjetpack-compose-order-of-modifiers "https://stackoverflow.com/questions/64206648/jetpack-compose-order-of-modifiers")

[Android Jetpack Compose width / height / size modifier vs requiredWidth / requiredHeight / requiredSize](https://link.juejin.cn/?target=https%3A%2F%2Fstackoverflow.com%2Fquestions%2F65779226%2Fandroid-jetpack-compose-width-height-size-modifier-vs-requiredwidth-requir "https://stackoverflow.com/questions/65779226/android-jetpack-compose-width-height-size-modifier-vs-requiredwidth-requir")