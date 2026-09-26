#!/bin/bash
# 抖音短剧AI剪辑工具 - 启动脚本
# 自动打开浏览器可视化界面

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PYTHON="$SCRIPT_DIR/.venv/bin/python"

if [ ! -f "$PYTHON" ]; then
    echo "❌ 虚拟环境不存在"
    exit 1
fi

# 启动Web可视化界面（自动打开浏览器）
echo "🎬 正在启动短剧剪辑工作站..."
$PYTHON "$SCRIPT_DIR/server.py"
