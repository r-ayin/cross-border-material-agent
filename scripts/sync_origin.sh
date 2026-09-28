#!/bin/bash
# 把当前 main（中性作者，github 版）重签为企业作者单提交推 origin（内网 push rule 要求真实邮箱）
# 用法: scripts/sync_origin.sh   （历史已 squash，两远端树内容一致、作者身份按各自平台要求）
set -e
cd "$(dirname "$0")/.."
TREE=$(git rev-parse 'main^{tree}')
MSG=$(git log -1 --format=%s main)
SHA=$(git commit-tree "$TREE" -m "$MSG")
git update-ref refs/heads/origin-main "$SHA"
git push --force origin origin-main:main
echo "origin synced: $SHA (tree == main tree: $(git rev-parse 'main^{tree}' | cut -c1-7))"
