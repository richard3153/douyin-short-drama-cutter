#!/bin/bash
# 抖音短剧AI自动剪辑工具 - 启动脚本
# 使用方法: bash run.sh

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PYTHON="$SCRIPT_DIR/.venv/bin/python"

if [ ! -f "$PYTHON" ]; then
    echo "❌ 虚拟环境不存在，请先运行: uv venv .venv && uv pip install ..."
    exit 1
fi

echo "🐉 启动抖音短剧AI自动剪辑工具..."
echo ""

$PYTHON "$SCRIPT_DIR/ai_short_video_cutter_pro.py" "$@"
