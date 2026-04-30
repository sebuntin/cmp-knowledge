---
title: "Obsidian + GitHub + Termux 打造全平台丝滑同步工作流"
source: "https://forum-zh.obsidian.md/t/topic/60487"
author:
  - "[[AuroRa1]]"
published: 2026-04-13
created: 2026-04-28
description: "为什么需要这套方案？ 目前 Obsidian 的主流同步方式都有痛点： 官方 Sync：好用但价格昂贵。 网盘同步 (坚果云等)：容易产生文件冲突，甚至导致笔记丢失（尤其是双端同时修改时）。 移动端 Obsidian Git 插件：这个我想重点说一下，绝大多数git同"
tags:
  - "clippings"
---
## ![:bulb:](https://forum-zh.obsidian.md/images/emoji/twitter/bulb.png?v=12 ":bulb:") 为什么需要这套方案？

目前 Obsidian 的主流同步方式都有痛点：

1. **官方 Sync**：好用但价格昂贵。
2. **网盘同步 (坚果云等)**：容易产生文件冲突，甚至导致笔记丢失（尤其是双端同时修改时）。
3. **移动端 Obsidian Git 插件**：这个我想重点说一下，绝大多数git同步的教程都会讲到这一层，对于*从零开始的小型库*我也非常推荐你用这个方案。但是对于已有大仓库的同步，是有底层局限性的。由于移动端插件基于纯 JavaScript (isomorphic-git) 实现，一旦笔记数量较多，扫描文件状态时会直接无限卡死在 `It takes konger: getting status` 导致移动端无法提交修改。

**本方案的核心思路：** 电脑端正常使用原生 Git；移动端**彻底抛弃效率低下的 Git 插件**，利用底层 C 语言编写的**原生 Git (Termux)** 接管同步，并通过 **Termux:Widget** 在桌面生成一个“一键同步”小组件。上万个文件，几秒内丝滑搞定！

## 声明：

## 本方案已验证平台为PC端：win11+移动端：Android

## ![:hammer_and_wrench:](https://forum-zh.obsidian.md/images/emoji/twitter/hammer_and_wrench.png?v=12 ":hammer_and_wrench:") 准备工作：必备软件下载与避坑

1. **账号**：一个 GitHub 账号（国内gitee也可以，无需魔法，不过仓库容量上限更低，步骤基本一样，区别我会放在文末）。
2. **PC 端**：安装好 [Git 客户端 3](https://git-scm.com/downloads)。
3. **安卓端软件下载（![:warning:](https://forum-zh.obsidian.md/images/emoji/twitter/warning.png?v=12 ":warning:") 致命避坑处）**：
	- **请务必从 [F-Droid 官网 7](https://f-droid.org/) 或 GitHub Releases 下载**，你需要下载两个 App：**Termux** 和 **Termux:Widget**。
		- **为什么绝对不能从 Google Play 商店下载？** 因为 Google Play 限制了应用执行本地下载的二进制文件（安全策略 API 限制），导致 Play 商店版的 Termux 已经彻底停更并废弃。只有 F-Droid 版能正常安装完整的 Linux 环境。
		- **注意**：Termux 主程序和 Widget 插件的签名必须完全一致（必须在同一个渠道下载），否则系统会拒绝它们通信。

---

## ![:crown:](https://forum-zh.obsidian.md/images/emoji/twitter/crown.png?v=12 ":crown:") 第一阶段：获取 GitHub “通行证” (Classic Token)

2021 年起，GitHub 禁用了密码推送，必须使用 Token 替代密码。

1. 登录 GitHub 网页端，点击右上角头像进入 `Settings` → 左侧最底部 `Developer settings` → `Personal access tokens` → **`Tokens (classic)`**。（注意：不要选 Fine-grained tokens，很容易漏配权限导致 403 报错）。
2. 点击右上角 `Generate new token (classic)`。
3. **Note** 随便填（如 ObsidianSync），**Expiration** 建议选 90 天或 No expiration（永久）。
4. **【最关键的一步】Select scopes**：找到并勾选 **`repo`** 这一项（Full control of private repositories）。
5. 滑到底部生成后，立刻复制那串以 `ghp_` 开头的 Token，发送到手机备忘录备用（刷新网页后将无法再次查看）。

---

## ![:computer:](https://forum-zh.obsidian.md/images/emoji/twitter/computer.png?v=12 ":computer:") 第二阶段：PC 端建库与推送 (The Source of Truth)

为了防止 PC 端的系统垃圾文件或超大文件拖垮云端，必须配置 `.gitignore`。

#### 1\. 配置忽略清单

**执行路径：** 你的 PC 端 Obsidian 仓库根目录（例如 `D:\Documents\My_Obsidian\`）。

在该目录下新建一个名为 `.gitignore` 的文件（注意前面有个点，没有后缀名），用记事本打开并严格填入以下内容：

```Plaintext
# 忽略潜在大文件 (GitHub 限制单个文件最大 100MB 超过会导致同步失败，如果确实需要同步PDF可以考虑手动复制到其他设备)
*.pdf
*.mp4
*.zip

# 忽略操作系统自动生成的文件
.DS_Store
Thumbs.db

# 忽略 Obsidian 的缓存文件
.obsidian/cache/

# 忽略特定设备的工作区状态，这是避免多端冲突的关键！核心目标！
.obsidian/workspace.json
.obsidian/workspaces.json
.obsidian/workspace-mobile.json

# 忽略其他不建议同步的文件
.obsidian/daily-notes.json
.obsidian/facets.json
.obsidian/starred.json

# 忽略插件的缓存和数据文件(可选，但推荐)
.obsidian/plugins/some-plugin/data.json
.obsidian/plugins/recent-files-obsidian/data.json

# 忽略垃圾箱文件夹
.trash/
```

#### 2\. 在 GitHub 网页端创建一个空仓库

在 GitHub 首页点击 `New repository`，输入仓库名（如 `My_Obsidian`），设为 **Private（私有）**，否则所有人都能看到你的笔记。**不要**勾选 “Add a README file”。

#### 3\. 将本地仓库推上云端

**执行路径：** 依然在你的 PC 端 Obsidian 仓库根目录。右键选择 `Open Git Bash here`（或在地址栏输入 `cmd` 打开终端），依次执行：

```Bash
# 初始化 Git 仓库
git init

# 将所有文件添加到暂存区（根据 .gitignore 规则，大文件和缓存会被自动过滤）
git add .

# 首次提交
git commit -m "init: first sync"

# 将默认分支设为 main
git branch -M main

# 绑定远程仓库（将下面地址替换为你刚才在网页端创建的仓库 URL）
git remote add origin https://github.com/你的用户名/你的仓库名.git

# 推送上云
git push -u origin main
```

*(如果弹出 GitHub 登录框，请选择 “Token” 登录，并粘贴你的 `ghp_Token`)*

---

## ![:iphone:](https://forum-zh.obsidian.md/images/emoji/twitter/iphone.png?v=12 ":iphone:") 第三阶段：安卓端环境配置 (Termux)

这一步是将云端数据完美克隆到手机，并打通底层存储权限。

#### 0.2基础环境配置（必做，创建脚本目录 + 权限）

打开**Termux 主程序**，在终端依次执行以下命令，创建插件所需的**前台 / 后台脚本目录**（权限必须设为 0700，否则插件无法读取脚本）。

##### 1\. 创建前台脚本目录（运行后弹出 Termux 终端）

```bash
mkdir -p /data/data/com.termux/files/home/.shortcuts
chmod 700 -R /data/data/com.termux/files/home/.shortcuts
```

##### 2\. 创建后台脚本目录（后台运行，在通知栏显示状态）

```bash
mkdir -p /data/data/com.termux/files/home/.shortcuts/tasks
chmod 700 -R /data/data/com.termux/files/home/.shortcuts/tasks
```

#### 1\. 授予存储权限

**执行路径：** 手机端打开 Termux App。

```Bash
termux-setup-storage
```

*会跳转到应用权限设置，**必须点击允许**。*

#### 2\. 安装原生 Git

**执行路径：** Termux 默认主目录 `~/`。

```Bash
pkg update
pkg install git -y
```

#### 3\. 进入手机公共文档目录

**执行路径：** 切换到手机内部存储的 Documents 目录。

*(建议将仓库放在 Documents，而不是根目录，以避免安卓 11+ 严格的 Scoped Storage 沙盒限制导致软件无法读取)*

```Bash
cd ~/storage/shared/Documents
```

#### 4\. 克隆仓库

为了避免以后手机每次 Push 都报 403 错误或弹窗要密码，我们**直接把 Token 绑在 URL 里**进行克隆。

*(将 `<你的Token>` 替换为 `ghp_...`，不要带尖括号)*

```Bash
git clone https://<你的Token>@github.com/你的用户名/你的仓库名.git
```

等待进度条跑完，你的文件就完美降落到手机的 `Documents/你的仓库名` 文件夹了！此时，你就可以在手机版 Obsidian 中选择“打开文件夹作为仓库”了。

---

## ![:man_mage:](https://forum-zh.obsidian.md/images/emoji/twitter/man_mage.png?v=12 ":man_mage:") 第四阶段：制作“一键同步”桌面魔法按钮

不用每次都手动敲代码，我们写一个具备自我保护机制的智能脚本，放在桌面一键执行。

#### 1\. 创建存放快捷方式的目录

**执行路径：** Termux 任意目录。

```Bash
mkdir -p ~/.shortcuts
```

#### 2\. 编写智能同步脚本

**执行路径：** Termux 任意目录。

```Bash
nano ~/.shortcuts/sync_obsidian.sh
```

#### 3\. 填入强健版脚本代码

将以下代码粘贴进去。**注意：请务必将 `VAULT_DIR` 的值修改为你手机真实的绝对路径！**

*(泛用性提示：大多数安卓手机的内部存储根目录绝对路径为 `/storage/emulated/0/`，如果是放在 Documents 下，则为 `/storage/emulated/0/Documents/你的仓库名`)*

```Bash
#!/bin/bash

# 1. 定义你的仓库绝对路径 (⚠️ 必须使用绝对路径，不要在引号内使用 ~ )
VAULT_DIR="/storage/emulated/0/Documents/你的仓库名"

# 尝试进入目录，如果失败则拦截并退出
cd "$VAULT_DIR" || { echo "❌ 致命错误：找不到仓库目录 $VAULT_DIR"; sleep 5; exit 1; }

# 2. 自动修复安卓端 Git 的“所有权可疑”拦截报错
git config --global --add safe.directory "$VAULT_DIR"

echo "🔍 [1/4] 正在检查本地修改..."
git add .

# 3. 智能防空提交：利用 diff-index 检查是否有实际修改
if ! git diff-index --quiet HEAD --; then
    TIME=$(date "+%Y-%m-%d %H:%M:%S")
    echo "📝 发现本地有新笔记，正在 Commit..."
    git commit -m "📱 mobile sync: $TIME"
else
    echo "💤 本地无任何修改，跳过 Commit。"
fi

echo "☁️  [2/4] 正在拉取云端最新数据 (Pull)..."
# 使用 --no-rebase 采用标准的合并策略，处理两端同时修改的情况
git pull origin main --no-rebase

# 4. 冲突与网络阻断保护：捕捉上一条命令的状态码 ($?)
if [ $? -ne 0 ]; then
    echo ""
    echo "⚠️ 警告：拉取失败！检测到版本冲突或网络异常。"
    echo "👉 处理建议：打开 Obsidian 检查是否有文件出现 <<<<<<< HEAD 冲突标记，手动删除不需要的片段后再次运行同步。"
    echo "脚本已终止，保护本地数据安全。"
    sleep 8
    exit 1
fi

echo "🚀 [3/4] 正在推送到云端 (Push)..."
git push -u origin main

if [ $? -eq 0 ]; then
    echo "✅ [4/4] 完美！全平台同步成功！"
    sleep 2
else
    echo "❌ 错误：推送失败！请检查网络是否通畅，或 GitHub Token 是否过期。"
    sleep 5
    exit 1
fi
```

*(按 `Ctrl + O` 保存，回车确认文件名，按 `Ctrl + X` 退出)*

#### ![:bulb:](https://forum-zh.obsidian.md/images/emoji/twitter/bulb.png?v=12 ":bulb:") 脚本鲁棒性（Robustness）解析：

- **防呆设计 (`diff-index`)**：如果你没写新笔记就误触了同步按钮，普通脚本会因为生成空的 Commit 而报错崩溃。我们的脚本会静默跳过推送，只拉取云端更新。
- **冲突熔断机制 (`$? -ne 0`)**：如果你在电脑和手机上同时修改了同一篇笔记，Git 拉取时会产生冲突。此时上一条命令返回的状态码不为 0，脚本会立即拉起警报并**终止运行**，防止把混乱的代码强行 Push 污染云端。
- **权限自愈 (`safe.directory`)**：安卓系统的沙盒机制经常让 Git 误判文件所有权（dubious ownership），脚本每次运行都会自动给自己发放安全许可，彻底杜绝此类拦截报错。

#### 4\. 赋予执行权限与桌面绑定

**执行路径：** Termux 任意目录。

```Bash
# 如果没有这一步，桌面点击会提示 Permission Denied
chmod +x ~/.shortcuts/sync_obsidian.sh
```

**回到手机桌面**：长按空白处添加小部件（Widget），找到 **Termux:Widget** 里的 **Termux Shortcut (1x1)** 拖到桌面，在弹出的列表中选择 `sync_obsidian.sh`。

![:tada:](https://forum-zh.obsidian.md/images/emoji/twitter/tada.png?v=12 ":tada:") **大功告成！** 以后记完笔记，退回桌面点一下黑色的终端图标，万级文件的增量同步几秒钟就能跑完！彻底告别移动端的无限转圈与卡顿！

---

## ​![:globe_with_meridians:](https://forum-zh.obsidian.md/images/emoji/twitter/globe_with_meridians.png?v=12 ":globe_with_meridians:") 附录：国内免梯子极速同步方案（Gitee 码云替换法）

​如果你没有稳定的科学上网环境，执行 GitHub 同步时经常遇到 Time out 或 443 报错，强烈建议将远程仓库替换为国内的 **Gitee（码云）**。

​操作逻辑与 GitHub 完全一致，只需注意以下三处替换：

### ​1. 更严苛的 .gitignore 限制（必看！）

​Gitee 免费版限制**单文件最大 50MB，单仓库总容量 500MB**。

### 2\. 获取 Gitee 的私人令牌 (Token)

1. ​登录 Gitee 网页端，点击右上角头像 → **设置**。
2. ​在左侧菜单找到 **安全设置** → **私人令牌**。
3. ​点击右上角 **生成新令牌**。
4. ​权限选项中，勾选 **projects**（读取、列出、创建、管理项目）即可。
5. ​生成后，复制这串 Token 备用。

### ​3. URL 绑定格式的微调

​在使用 Termux 进行手机端克隆，或者 PC 端绑定远程仓库时，Gitee 的免密 URL 格式需要同时带上你的**用户名**和 **Token**：

​**标准格式：**

`https://<你的Gitee用户名>:<你的Token>@gitee.com/<你的用户名>/<你的仓库名>.git`

同步脚本修改：

只需确保你在 PC 端推送和 Termux 拉取时，使用的是这个 Gitee 的 URL 即可。我们在桌面创建的 sync\_obsidian.sh 脚本**完全不需要修改任何代码**（因为本地仓库的 origin 已经指向 Gitee 了），直接点击依然一键丝滑同步！