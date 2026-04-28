---
title: "深入理解 Jetpack Compose DrawModifier"
source: "https://juejin.cn/post/7324011383720263718"
author:
  - "[[bqliang]]"
published: 2024-01-15
created: 2026-04-28
description: "虽然 drawWithContent() 相比 drawBehind() 麻烦了一点点，但是换来了更高的灵活性：可以自由地在元素原有内容的前后绘制任意内容。查看源码发现......"
tags:
  - "clippings"
---
## Modifier.drawXxx & DrawModifierNode

> 注：本文源码基于：androidx.compose.ui:ui:1.5.4

## Modifier.drawXxx

日常开发中，最常见的 Modifier 修饰符有两类：Layout 修饰符与 Draw 修饰符。Layout 修饰符如 `size()` 、 `padding()` 在元素的布局阶段发挥作用，而 Draw 修饰符如 `background()` 则在元素的绘制阶段发挥作用。

![Layout 修饰符与 Draw 修饰符.jpg](https://p6-juejin.byteimg.com/tos-cn-i-k3u1fbpfcp/9ab3dc8014fc482a906a3b63855a2825~tplv-k3u1fbpfcp-jj-mark:3024:0:0:0:q75.awebp#?w=3015&h=774&s=83708&e=jpg&b=fefefe)

Compose 提供了 `Modifier.layout()` 修饰符，能对元素的测量和布局方式进行简单修改。那么类似的，是否存在 `Modifier.draw()` 修饰符，能对元素的绘制过程进行修改呢？答案是肯定的，不过，名字不叫 ~~`Modifier.draw()`~~ ，而且还是三兄弟：

### drawBehind

`Modifier.drawBehind()` 修饰符用于在元素内容后面绘制内容。

```kotlin
体验AI代码助手 代码解读复制代码/**
 * Draw into a Canvas behind the modified content.
 */
fun Modifier.drawBehind(
    onDraw: DrawScope.() -> Unit
) = this then DrawBehindElement(onDraw)
```

可以看到函数类型参数 `onDraw` 的接收者类型是 DrawScope，DrawScope 里定义了各种绘制函数：

```kotlin
体验AI代码助手 代码解读复制代码interface DrawScope : Density {
    
    fun drawLine(...)
    
    fun drawRect(...)
    
    fun drawCircle(...)
    ...
}
```

也就是说，在使用 `Modifier.drawBehind()` 修饰符时，我们可以传入一个 lambda 表达式，在 lambda 里调用各种 drawXxx 函数来绘制图形。

我们不妨试试在 Text 后面绘制圆角矩形作为背景：

```kotlin
体验AI代码助手 代码解读复制代码Text(
    text = "Hello Compose!",
    modifier = Modifier
        .drawBehind {
            drawRoundRect(color = Purple, cornerRadius = CornerRadius(10.dp.toPx()))
        }
        .padding(4.dp)
)
```
![modifier_draw_behind.png](https://p9-juejin.byteimg.com/tos-cn-i-k3u1fbpfcp/60e4787377454f17a8822806f001134c~tplv-k3u1fbpfcp-jj-mark:3024:0:0:0:q75.awebp#?w=946&h=348&s=14919&e=png&b=ffffff)

### drawWithContent

`drawBehind()` 绘制的内容会显示在元素的下面，那如果想绘制内容盖在元素上面怎么办？虽然没有 drawFront()，不过我们可以用 `drawWithContent()` ：

```kotlin
体验AI代码助手 代码解读复制代码Text(
    text = "Hello Compose!",
    modifier = Modifier
        .drawWithContent {
            // 绘制紫色圆角矩形
            drawRoundRect(color = Purple, cornerRadius = CornerRadius(10.dp.toPx()))
            // 绘制元素原有内容
            drawContent() 
            // 绘制蓝色圆角矩形
            drawRoundRect(color = Blue, size = size / 2f, cornerRadius = CornerRadius(10.dp.toPx()))
        }
        .padding(4.dp)
)
```
![modifier_draw_with_content.png](https://p3-juejin.byteimg.com/tos-cn-i-k3u1fbpfcp/a59ad5d2fa6540f893465c7dfef33ad1~tplv-k3u1fbpfcp-jj-mark:3024:0:0:0:q75.awebp#?w=946&h=348&s=14825&e=png&b=ffffff)

使用 `drawWithContent()` 的时候，需要开发者手动调用 `drawContent()` 来绘制原有的内容。drawXxx 函数和 drawContent() 被调用的前后顺序，决定了绘制内容会显示在元素原有内容的前面还是后面。

虽然 `drawWithContent()` 相比 `drawBehind()` 麻烦了一点点，但是换来了更高的灵活性：可以自由地在元素原有内容的前后绘制任意内容。

查看源码发现 `drawWithContent()` 的函数参数 `onDraw` 的接收者类型是 ContentDrawScope，一个 DrawScope 的子接口，多定义了一个 `drawContent()` 函数。原来如此~

```kotlin
体验AI代码助手 代码解读复制代码// DrawModifier.kt
/**
 * Creates a DrawModifier that allows the developer to draw before or after the layout's
 * contents. It also allows the modifier to adjust the layout's canvas.
 */
fun Modifier.drawWithContent(
    onDraw: ContentDrawScope.() -> Unit
): Modifier = this then DrawWithContentElement(onDraw)

// ContentDrawScope.kt
interface ContentDrawScope : DrawScope {
    fun drawContent()
}
```

### drawWithCache

我们都知道在自定义 View 时，不应该在 `onDraw()` 里创建对象，因为 `onDraw()` 会被频繁调用，频繁创建对象会导致频繁的 GC，影响性能。

假设我们要为 Text 绘制渐变背景，如果像下面这么写，就会在每一帧刷新时创建一个新的 Brush 对象，从而影响性能：

```kotlin
体验AI代码助手 代码解读复制代码Text(
    text = "Hello Compose!",
    modifier = Modifier
        .drawBehind {
            val brush = Brush.linearGradient(colors = listOf(Purplr, Blue)) // ⚠️
            drawRoundRect(brush = brush, cornerRadius = CornerRadius(10.dp.toPx()))
        }
        .padding(4.dp)
)
```
![modifier_draw_with_cache.png](https://p9-juejin.byteimg.com/tos-cn-i-k3u1fbpfcp/b0a32c79ffc5458e8fbfee1f3ef0e39e~tplv-k3u1fbpfcp-jj-mark:3024:0:0:0:q75.awebp#?w=946&h=348&s=63725&e=png&b=ffffff)

Compose 提供了 `Modifier.drawWithCache()` 修饰符，能缓存在其中创建的对象。只要绘制区域的大小不变，或者读取的任何状态对象都未发生变化，对象就会被缓存。

因此我们可以使用 `Modifier.drawWithCache()` 来改进上面的代码：

```kotlin
体验AI代码助手 代码解读复制代码Text(
    text = "Hello Compose!",
    modifier = Modifier
        .drawWithCache { // CacheDrawScope
            // brush 对象会被缓存
            val brush = Brush.linearGradient(colors = listOf(Purplr, Blue))
            
            onDrawBehind {
                drawRoundRect(brush = brush, cornerRadius = CornerRadius(10.dp.toPx()))
            }
            // 也可以调用 onDrawWithContent 进行绘制
        }
        .padding(4.dp)
)
```

## DrawModifierNode

> **以下内容假定你已了解 LayoutModifier 的背后实现原理，如果不了解，请先阅读 [《Jetpack Compose LayoutModifier》](https://juejin.cn/post/7320437915351334950 "https://juejin.cn/post/7320437915351334950") 再继续阅读以下内容。**

接下来我们就要深入探究 `background()` 、 `drawBehind()` 、 `drawWithContent`...这类 Draw 修饰符背后的实现原理了，它们究竟是如何影响元素绘制过程的呢？为什么 `Modifier.drawWithContent { }.background(Blue)` 会导致元素原有内容"被擦除"？而 `Modifier.background(Blue).drawWithContent { }` 又能正常显示原有内容呢？了解完实现原理，这些问题都会迎刃而解。

![drawWithContent擦除原有内容.jpg](https://p1-juejin.byteimg.com/tos-cn-i-k3u1fbpfcp/904c072d6c004fbb9c8ce529181c5131~tplv-k3u1fbpfcp-jj-mark:3024:0:0:0:q75.awebp#?w=1170&h=1122&s=55723&e=jpg&b=ffffff)

查看 `Modifier.background()` 和 `Modifier.drawWithContent()` 的源码，发现它们背后的 BackgroundElement 和 DrawWithContentElement 都继承自 `ModifierNodeElement<N : Modifier.Node>` ，而且泛型类型 BackgroundNode 和 DrawWithContentModifier 都实现了 **DrawModifierNode 接口** 。

![DrawModifierNode.jpg](https://p6-juejin.byteimg.com/tos-cn-i-k3u1fbpfcp/4f45395ba4c349e483b36d629c5d3377~tplv-k3u1fbpfcp-jj-mark:3024:0:0:0:q75.awebp#?w=3069&h=1773&s=349357&e=jpg&b=ffffff)

这个 DrawModifierNode 接口就是 Draw 修饰符的核心，它定义了 Draw 修饰符的核心逻辑：

```kotlin
体验AI代码助手 代码解读复制代码/**
 * A [Modifier.Node] that draws into the space of the layout.
 *
 * This is the [androidx.compose.ui.Modifier.Node] equivalent of
 * [androidx.compose.ui.draw.DrawModifier]
 */
interface DrawModifierNode : DelegatableNode {
    fun ContentDrawScope.draw() // 📌
    fun onMeasureResultChanged() {}
}
```

那么，我们要探究 Draw 修饰符如何影响元素绘制过程，重点就是看元素的绘制在哪用到了 DrawModifierNode，或者更准确地说，DrawModifierNode 的 `draw()` 方法在何处被调用了。

众所周知，Composable 函数在组合阶段会被调用生成 LayoutNode 对象，而 LayoutNode 对象的 `draw()` 方法就是负责元素的绘制，所以我们跟一下这个方法的源码，看看哪个地方用到了 DrawModifierNode。

```kotlin
体验AI代码助手 代码解读复制代码internal class LayoutNode(...) : ... {
    internal val outerCoordinator: NodeCoordinator
        get() = nodes.outerCoordinator
    
    internal fun draw(canvas: Canvas) = outerCoordinator.draw(canvas)
}
```

LayoutNode 的 draw() 方法直接转发调用了 outerCoordinator 的 draw，继续跟到 NodeCoordinator 的 draw() 方法：

```kotlin
体验AI代码助手 代码解读复制代码internal abstract class NodeCoordinator(override val layoutNode: LayoutNode) : ... {
    
    internal var wrapped: NodeCoordinator? = null   // 内部包含的子 NodeCoordinator
    internal var wrappedBy: NodeCoordinator? = null // 包含着自己的父 NodeCoordinator
    
    /**
     * Draws the content of the LayoutNode
     */
    fun draw(canvas: Canvas) {
        val layer = layer
        if (layer != null) {
            layer.drawLayer(canvas)
        } else {
            val x = position.x.toFloat()
            val y = position.y.toFloat()
            canvas.translate(x, y)
            drawContainedDrawModifiers(canvas) // 📌
            canvas.translate(-x, -y)
        }
    }

    private fun drawContainedDrawModifiers(canvas: Canvas) {
        val head = head(Nodes.Draw)
        if (head == null) {
            performDraw(canvas)
        } else {
            val drawScope = layoutNode.mDrawScope
            drawScope.draw(canvas, size.toSize(), this, head)
        }
    }
}
```

NodeCoordinator 的 draw() 方法里，首先判断 `if (layer != null)` ，这个 layer 的作用是将内容放在独立图层中绘制，一般情况下都是 null 的，所以我们主要关注 `drawContainedDrawModifiers(canvas)` 。

`drawContainedDrawModifiers()` 方法的第一行是 `val head = head(Nodes.Draw)` ，注意我们目前还在 NodeCoordinator 里面。

一个 NodeCoordinator 会对应一个或多个 Modifier.Node，而 `head(Nodes.Draw)` 就是获取当前 NodeCoordinator 范围内的的第一个 Draw 修饰符。

![1个NodeCoordinator对应1个或多个Modifier.Node.jpg](https://p6-juejin.byteimg.com/tos-cn-i-k3u1fbpfcp/1c14254233cd4c8580af31d1d706c4f7~tplv-k3u1fbpfcp-jj-mark:3024:0:0:0:q75.awebp#?w=3333&h=1530&s=336550&e=jpg&b=fffafa)

在 Modifier.Node 的内部会使用标志位来存储分类信息，假设第一位代表 Layout 修饰、第二位代表 Draw 修饰符，以此类推......

![标志位管理 Modifier.Node 分类.jpg](https://p6-juejin.byteimg.com/tos-cn-i-k3u1fbpfcp/8d4ab2b54b2543c3b0d928fb78912ac5~tplv-k3u1fbpfcp-jj-mark:3024:0:0:0:q75.awebp#?w=2856&h=1335&s=177608&e=jpg&b=fffefe)

为什么 Modifier.Node 要使用标志位来存储分类信息呢？直接用枚举类不好吗？这是因为在组装 Modifier.Node 双向链表时，每个节点都会包含自己及其所有子节点的分类信息。以上图中的例子，组装双向链表时，第一个修饰符 background() 是 Draw 修饰符，所以标志位是 0010；第二个修饰符 size() 是 Layout 修饰符，标志位是 0001，还要与它的子节点的标志位 0010 进行或运算，得到 0011，以此类推......头节点的标志位是 1111，代表了整条链表包含的所有修饰符类型。

```kotlin
体验AI代码助手 代码解读复制代码interface Modifier {
    abstract class Node : ... {
        // 当前节点的标志位
        internal var kindSet: Int = 0
        
        // 当前节点及其所有子节点的标志位
        internal var aggregateChildKindSet: Int = 0.inv()
    }
}
```

关于 `head(Nodes.Draw)` 的具体逻辑可以看下图：

![head(Nodes.Draw).jpg](https://p6-juejin.byteimg.com/tos-cn-i-k3u1fbpfcp/8eab91513c3f4e13b520e39c06ff6ee0~tplv-k3u1fbpfcp-jj-mark:3024:0:0:0:q75.awebp#?w=2373&h=2565&s=614553&e=jpg&b=fefefe)

了解完 `head(Nodes.Draw)` 后我们继续往下看，如果 `head(Nodes.Draw)` 为 null，则调用 `performDraw()` ，里面很简单，直接转发调用当前 NodeCoordinator 所包含的 NodeCoordinator 的 draw() 方法

```kotlin
体验AI代码助手 代码解读复制代码internal abstract class NodeCoordinator(override val layoutNode: LayoutNode) : ... {
    
    internal var wrapped: NodeCoordinator? = null   // 内部包含的子 NodeCoordinator

    fun draw(canvas: Canvas) {
        ...
        drawContainedDrawModifiers(canvas)
        ...
    }
    
    private fun drawContainedDrawModifiers(canvas: Canvas) {
        val head = head(Nodes.Draw)
        if (head == null) {
            performDraw(canvas)
        } else {
            val drawScope = layoutNode.mDrawScope
            drawScope.draw(canvas, size.toSize(), this, head)
        }
    }

    open fun performDraw(canvas: Canvas) {
        wrapped?.draw(canvas)
    }
}
```

以下图中的例子来说，如果没有写 ~~`drawBehind{}`~~ ，那么 outerCoordinator 在执行 `head(Nodes.Draw)` 时结果就是 null，然后它会调用内部 NodeCoordinator 的 draw() 方法，再次执行到 `head(Nodes.Draw)` 这行代码。

![head(Nodes.Draw) = null.jpg](https://p9-juejin.byteimg.com/tos-cn-i-k3u1fbpfcp/41962f0eff8b499ba5478e4d59dd899a~tplv-k3u1fbpfcp-jj-mark:3024:0:0:0:q75.awebp#?w=3333&h=1530&s=352346&e=jpg&b=fffbfa)

如果 NodeCoordinator 对应的一个或多个 Modifier.Node 里面，有至少一个的类型是 Nodes.Draw，那么 `head(Nodes.Draw)` 就不为 null，就会执行 `drawScope.draw(canvas, size.toSize(), this, head)` 。

```kotlin
体验AI代码助手 代码解读复制代码private fun drawContainedDrawModifiers(canvas: Canvas) {
    val head = head(Nodes.Draw)
    if (head == null) {
        performDraw(canvas)
    } else {
        val drawScope = layoutNode.mDrawScope // 类型是 LayoutNodeDrawScope
        drawScope.draw(canvas, size.toSize(), this, head) // 📌
    }
}
```

继续跟进 LayoutNodeDrawScope 的 draw() 方法：

```kotlin
体验AI代码助手 代码解读复制代码internal class LayoutNodeDrawScope(...) : ... {
    ...
    internal fun draw(
        canvas: Canvas,
        size: Size,
        coordinator: NodeCoordinator,
        drawNode: Modifier.Node, // drawNode 就是刚刚找到的类型为 Nodes.Draw 的 Modifier.Node
    ) {
        drawNode.dispatchForKind(Nodes.Draw) {
            drawDirect(canvas, size, coordinator, it)
        }
    }
}
```

里面调用了 `drawNode.dispatchForKind(Nodes.Draw){}` ，先看看这个 dispatchForKind() 方法干了啥：

```kotlin
体验AI代码助手 代码解读复制代码internal inline fun <reified T> Modifier.Node.dispatchForKind(
    kind: NodeKind<T>, // 实参 kind 是 Nodes.Draw = NodeKind<DrawModifierNode>，所以泛型 T 是 DrawModifierNode
    block: (T) -> Unit
) {
    var stack: MutableVector<Modifier.Node>? = null
    var node: Modifier.Node? = this // 赋值为 this，也就是函数调用者 drawNode，实际类型就是 DrawModifierNode
    while (node != null) {
        if (node is T) { // 这里判断为 true
            block(node) // 会执行传进来的函数 block
        } else if (node.isKind(kind) && node is DelegatingNode) { 
            ... 
        }
        node = stack.pop()
    }
}
```

其实 `drawNode.dispatchForKind(Nodes.Draw){ }` 就干了一件事，对函数调用者 drawNode 执行函数参数 block，回头看调用 dispatchForKind() 方法时传入的 lambda 表达式，继续跟踪 drawDirect() 方法

```kotlin
体验AI代码助手 代码解读复制代码internal class LayoutNodeDrawScope(...) : ... {
    private var drawNode: DrawModifierNode? = null
    ...
    internal fun draw(
        canvas: Canvas,
        size: Size,
        coordinator: NodeCoordinator,
        drawNode: Modifier.Node,
    ) {
        drawNode.dispatchForKind(Nodes.Draw) {
            drawDirect(canvas, size, coordinator, it) // 📌 it 就是 drawNode
        }
    }

    internal fun drawDirect(
        canvas: Canvas,
        size: Size,
        coordinator: NodeCoordinator,
        drawNode: DrawModifierNode,
    ) {
        // 临时设置一下 drawNode，执行完操作最后再恢复
        val previousDrawNode = this.drawNode
        this.drawNode = drawNode
        canvasDrawScope.draw(
            coordinator,
            coordinator.layoutDirection,
            canvas,
            size
        ) {
            with(drawNode) {
                this@LayoutNodeDrawScope.draw() // 📌 执行 drawNode 的绘制，也就是将 Draw 修饰符的内容绘制出来
            }
        }
        this.drawNode = previousDrawNode // 恢复 drawNode
    }
}
```

关键的一行是 `with(drawNode) { this@LayoutNodeDrawScope.draw() }` ，点进去看这个 draw() 函数，会发现它就是我们最初在 DrawModifierNode 里看见的 draw() 函数：

```kotlin
体验AI代码助手 代码解读复制代码interface DrawModifierNode : DelegatableNode {
    fun ContentDrawScope.draw() // <---
    ...
}
```

嗯~~ 终于联系起来了！

![真正绘制 Draw 修饰符的内容.jpg](https://p9-juejin.byteimg.com/tos-cn-i-k3u1fbpfcp/fbc561eadeb64fae867ae9a0a67f25fe~tplv-k3u1fbpfcp-jj-mark:3024:0:0:0:q75.awebp#?w=2508&h=2709&s=469931&e=jpg&b=ffffff)

现在我们终于找到了第一个 Draw 修饰符被绘制的地方了，可是问题来了，剩下的 Draw 修饰符以及元素自身又是怎么被绘制的呢？

![第一个 Draw 修饰符的绘制.jpg](https://p1-juejin.byteimg.com/tos-cn-i-k3u1fbpfcp/741cb94bde244c9fa01bff23cb65e6bd~tplv-k3u1fbpfcp-jj-mark:3024:0:0:0:q75.awebp#?w=3042&h=702&s=112475&e=jpg&b=fffefe)

其实 Draw 修饰符之间的连接，靠的是 `drawContent()` 方法：

```kotlin
体验AI代码助手 代码解读复制代码interface ContentDrawScope : DrawScope {
    /**
     * Causes child drawing operations to run during the \`onPaint\` lambda.
     */
    fun drawContent()
}
```

因为这是个接口方法，我们可以看一下它的实现，它只有唯一实现，就是 LayoutNodeDrawScope 的 `drawContent()` ：

```kotlin
体验AI代码助手 代码解读复制代码internal class LayoutNodeDrawScope(
    private val canvasDrawScope: CanvasDrawScope = CanvasDrawScope()
) : DrawScope by canvasDrawScope, ContentDrawScope {
    ...
    override fun drawContent() {
        drawIntoCanvas { canvas ->
            val drawNode = drawNode!!
             val nextDrawNode = drawNode.nextDrawNode() // 在当前 NodeCoordinator 范围内寻找下一个 Draw 类型的 Modifier.Node
             if (nextDrawNode != null) {
                 nextDrawNode.dispatchForKind(Nodes.Draw) {
                     it.performDraw(canvas) // 绘制下一个 Draw 修饰符
                 }
             } else { // 当前 NodeCoordinator 范围内已经没有下一个 Draw 类型的 Modifier.Node 了 
                 val coordinator = drawNode.requireCoordinator(Nodes.Draw)
                 val nextCoordinator = if (coordinator.tail === drawNode.node)
                       coordinator.wrapped!!
                     else
                       coordinator
                 nextCoordinator.performDraw(canvas)
             }
        }
    }
}
```

还是比较容易理解的，就不再具体一句句看了，流程是在当前 NodeCoordinator 范围内寻找下一个 Draw 修饰符，找得到就继续绘制，找不到就丢给下一个 NodeCoordinator，让它寻找 head(Nodes.Draw)，以此类推形成闭环。

![drawContent 连接各个 Draw 修饰符.jpg](https://p3-juejin.byteimg.com/tos-cn-i-k3u1fbpfcp/8303f9781f484a9fa2b5dc97c5c66aa9~tplv-k3u1fbpfcp-jj-mark:3024:0:0:0:q75.awebp#?w=3333&h=1917&s=396884&e=jpg&b=fffcfc)

查看几乎所有的 Draw 修饰符背后的源码，你一定会看到它们都调用了 `drawContent()` ，比如 background() 修饰符背后的 BackgroundNode：

```kotlin
体验AI代码助手 代码解读复制代码private class BackgroundNode(
    var color: Color,
    var brush: Brush?,
    var alpha: Float,
    var shape: Shape,
) : DrawModifierNode, Modifier.Node() {
    ...
    override fun ContentDrawScope.draw() {
        if (shape === RectangleShape) {
            drawRect()
        } else {
            drawOutline()
        }
        drawContent() // 📌
    }
}
```

再比如 `drawbehind()` 修饰符背后的 DrawBackgroundModifier：

```kotlin
体验AI代码助手 代码解读复制代码internal class DrawBackgroundModifier(
    var onDraw: DrawScope.() -> Unit
) : Modifier.Node(), DrawModifierNode {

    override fun ContentDrawScope.draw() {
        onDraw()
        drawContent() // 📌
    }
}
```

现在我们终于可以回答最初的问题了，为什么 `Modifier.drawWithContent { }.background(Blue)` 会导致元素原有内容"被擦除"？而 `Modifier.background(Blue).drawWithContent { }` 又能正常显示原有内容呢？

![drawWithContent擦除原有内容.jpg](https://p1-juejin.byteimg.com/tos-cn-i-k3u1fbpfcp/73a7476f161d461fb417e8ba924995b8~tplv-k3u1fbpfcp-jj-mark:3024:0:0:0:q75.awebp#?w=1170&h=1122&s=55723&e=jpg&b=ffffff)

这是因为 `Modifier.drawWithContent { }.background(Blue)` 没有在第一个 Draw 修饰符里调用 `drawContent()` ，导致绘制流程提前中断结束了，第二个 Draw 修饰符得不到执行，看起来就好像是元素原有的内容"被擦除"了。

而 `Modifier.background(Blue).drawWithContent { }` 是先执行的 `.background(Blue)` ，在绘制流程中断之前就已经绘制出了蓝色背景，所以显示没有问题。

不知道你是否有过这样的疑惑，啊你这讲的全部都是 Draw 修饰符的绘制啊，那元素本身的内容是在哪被绘制的啊？比如下面的 Text 是在哪被绘制的啊？

```kotlin
体验AI代码助手 代码解读复制代码Text(Modifier.background(Red).requiredSize(100.dp).background(Blue).requiredSize(50.dp))
```

注意了，在 Compose 里面，一切的内容都是通过修饰符 Modifier 来绘制的，根本不存在独立的元素内容绘制流程。也就是说，对于以上例子，文字的绘制就是发生在 Draw 修饰符的 draw() 方法里面。

现在的你，要理解下面的代码为什么紫色矩形绘制在文字下方，而蓝色矩形绘制在文字上方，应该是非常轻松的事情了

```
体验AI代码助手 代码解读复制代码 Text(
    text = "Hello Compose!",
    modifier = Modifier
        .drawWithContent {
            // 绘制紫色圆角矩形
            drawRoundRect(color = Purple, cornerRadius = CornerRadius(10.dp.toPx()))
            // 绘制元素原有内容
            drawContent() 
            // 绘制蓝色圆角矩形
            drawRoundRect(color = Blue, size = size / 2f, cornerRadius = CornerRadius(10.dp.toPx()))
        }
        .padding(4.dp)
)
```
![modifier_draw_with_content.png](https://p3-juejin.byteimg.com/tos-cn-i-k3u1fbpfcp/a59ad5d2fa6540f893465c7dfef33ad1~tplv-k3u1fbpfcp-jj-mark:3024:0:0:0:q75.awebp#?w=946&h=348&s=14825&e=png&b=ffffff)