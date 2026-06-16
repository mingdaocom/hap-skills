#!/bin/bash

# 测试mdye-cli检查逻辑的演示脚本

echo "=== mdye-cli 检查演示 ==="
echo ""

# 检查mdye-cli是否安装
if command -v mdye &> /dev/null; then
    MDYE_VERSION=$(mdye --version 2>/dev/null || echo "未知版本")
    echo "✅ mdye-cli 已安装"
    echo "   版本: $MDYE_VERSION"
    echo ""
    echo "可以直接使用以下命令："
    echo "  mdye init view --id 插件ID --template React"
else
    echo "❌ mdye-cli 未安装"
    echo ""
    echo "需要先安装 mdye-cli："
    echo ""

    if [[ "$OSTYPE" == "darwin"* ]]; then
        echo "  # macOS系统"
        echo "  sudo npm install -g mdye-cli"
    else
        echo "  # Windows/Linux系统"
        echo "  npm install -g mdye-cli"
    fi

    echo ""
    echo "安装完成后，使用以下命令验证："
    echo "  mdye --version"
fi

echo ""
echo "=== 演示结束 ==="