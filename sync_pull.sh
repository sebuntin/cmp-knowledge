#!/bin/bash

# 仓库绝对路径
VAULT_DIR="/storage/emulated/0/Documents/cmp-knowledge"

cd "$VAULT_DIR" || { echo "❌ 致命错误：找不到仓库目录 $VAULT_DIR"; sleep 5; exit 1; }

git config --global --add safe.directory "$VAULT_DIR"

echo "🗑️ [1/2] 丢弃本地所有修改..."
git checkout -- .
git clean -fd

echo "☁️ [2/2] 拉取远端最新数据..."
git pull origin main

if [ $? -eq 0 ]; then
    echo "✅ 同步完成！本地已与远端一致。"
else
    echo "❌ 拉取失败，请检查网络。"
    sleep 5
    exit 1
fi
