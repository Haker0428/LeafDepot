#!/bin/bash
# Git 历史清理脚本 - 仅清理 .git 目录，不影响工作目录文件
# ⚠️ 警告：此操作会重写 Git 历史，需要强制推送
# ✅ 安全：只清理 .git 历史记录，工作目录文件不受影响

set -e

echo "🧹 开始清理 Git 历史中的大文件..."
echo "⚠️  注意：此操作会重写 Git 历史，请确保已备份！"
echo "✅ 安全：只清理 .git 目录，工作目录文件不受影响"
echo ""

# 颜色定义
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# 检查是否有未提交的更改
if [ -n "$(git status --porcelain)" ]; then
    echo -e "${YELLOW}⚠️  发现未提交的更改，请先提交或暂存${NC}"
    echo "当前未提交的文件："
    git status --short
    echo ""
    read -p "是否继续？(y/N): " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        echo "已取消操作"
        exit 1
    fi
fi

# 备份当前分支
BACKUP_BRANCH="backup-before-clean-$(date +%Y%m%d-%H%M%S)"
echo -e "${GREEN}📦 创建备份分支: ${BACKUP_BRANCH}${NC}"
git branch "$BACKUP_BRANCH"

echo ""
echo -e "${YELLOW}🔍 分析需要移除的文件...${NC}"
echo ""

# 查找所有大文件（>10MB）
echo "查找大于 10MB 的文件："
git rev-list --objects --all | \
    git cat-file --batch-check='%(objecttype) %(objectname) %(objectsize) %(rest)' | \
    awk '/^blob/ {size=$3; if (size > 10485760) print size/1048576 " MB " substr($0,6)}' | \
    sort --numeric-sort --key=1 --reverse | head -20

echo ""
read -p "是否继续清理？(y/N): " -n 1 -r
echo
if [[ ! $REPLY =~ ^[Yy]$ ]]; then
    echo "已取消操作"
    exit 1
fi

# 使用 git filter-branch 移除大文件（只影响 .git 历史，不影响工作目录）
# 注意：git rm --cached 只从 Git 索引中移除，不会删除工作目录文件
echo ""
echo -e "${GREEN}🗑️  开始从 Git 历史中移除大文件...${NC}"
echo -e "${YELLOW}   （工作目录文件不会被删除）${NC}"

# 定义要从历史中移除的目录和文件（只影响 .git，不影响工作目录）
REMOVE_PATHS=(
    "archive/Yolo2BarCode/BarcodeReaderCLI/bin/lib"
    "BarcodeDetection/datasets/barcode/images/train"
    "Intergration/app/cam_sys/build"
    "Intergration/app/cam_sys/lib"
    "Intergration/output"
    "Yolo2BarCode/output"
)

echo "将移除以下目录的历史记录："
for path in "${REMOVE_PATHS[@]}"; do
    echo "  - $path"
done
echo ""

# 使用 git filter-branch 从历史中移除这些路径
# --index-filter 只影响 Git 索引和历史，不影响工作目录
# 注意：这会重写整个 Git 历史，可能需要一些时间
git filter-branch --force --index-filter '
    git rm --cached --ignore-unmatch -r \
        archive/Yolo2BarCode/BarcodeReaderCLI/bin/lib \
        BarcodeDetection/datasets/barcode/images/train \
        Intergration/app/cam_sys/build \
        Intergration/app/cam_sys/lib \
        Intergration/output \
        Yolo2BarCode/output 2>/dev/null || true
' --prune-empty --tag-name-filter cat -- --all

# 清理引用
echo ""
echo -e "${YELLOW}🧹 清理引用和临时文件...${NC}"
rm -rf .git/refs/original/
git reflog expire --expire=now --all
git gc --prune=now --aggressive

# 显示清理后的仓库大小
echo ""
echo -e "${GREEN}✅ 清理完成！${NC}"
echo ""
echo "清理后的仓库大小："
du -sh .git

echo ""
echo -e "${YELLOW}📋 下一步操作：${NC}"
echo "1. 检查清理结果: git log --all --oneline"
echo "2. 如果需要强制推送到远程: git push --force --all"
echo "3. 如果出现问题，可以恢复: git checkout ${BACKUP_BRANCH}"
echo ""
echo -e "${RED}⚠️  强制推送会影响所有协作者，请谨慎操作！${NC}"

