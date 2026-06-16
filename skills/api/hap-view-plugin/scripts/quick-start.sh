#!/bin/bash

# HAP视图插件快速启动脚本
# 用法: ./quick-start.sh [项目目录]

set -e

echo "=== HAP视图插件快速启动 ==="
echo ""

if [ -z "$1" ]; then
    # 如果没有指定项目目录，查找当前目录下的项目
    PROJECT_DIR=$(find . -maxdepth 1 -type d -name "mdye_view_*" | head -1)

    if [ -z "$PROJECT_DIR" ]; then
        echo "❌ 未找到HAP视图插件项目"
        echo ""
        echo "请先创建项目或指定项目目录:"
        echo "  ./quick-start.sh 项目目录"
        echo ""
        echo "或者使用完整初始化:"
        echo "  ./init-hap-view-project.sh"
        exit 1
    fi
else
    PROJECT_DIR="$1"
fi

# 检查项目目录是否存在
if [ ! -d "$PROJECT_DIR" ]; then
    echo "❌ 项目目录不存在: $PROJECT_DIR"
    exit 1
fi

echo "📁 项目目录: $PROJECT_DIR"

# 检查项目结构
echo ""
echo "1. 检查项目结构..."
if [ ! -f "$PROJECT_DIR/package.json" ]; then
    echo "❌ 项目目录中未找到package.json文件"
    exit 1
fi

if [ ! -d "$PROJECT_DIR/src" ]; then
    echo "❌ 项目目录中未找到src目录"
    exit 1
fi

echo "✅ 项目结构检查通过"

# 检查依赖是否安装
echo ""
echo "2. 检查项目依赖..."
cd "$PROJECT_DIR" || {
    echo "❌ 无法进入项目目录"
    exit 1
}

if [ ! -d "node_modules" ]; then
    echo "⚠️  未找到node_modules目录，开始安装依赖..."
    npm i

    if [ $? -ne 0 ]; then
        echo "❌ 依赖安装失败"
        exit 1
    fi
    echo "✅ 依赖安装完成"
else
    echo "✅ 依赖已安装"
fi

# 启动开发服务器
echo ""
echo "3. 启动开发服务器..."
echo "执行命令: mdye start"
echo ""
echo "🚀 开发服务器正在启动..."
echo "📱 请稍后在浏览器中访问开发服务器地址"
echo "🔄 支持热重载和实时预览"
echo ""

# 启动mdye开发服务器
mdye start

# 如果mdye start失败，显示错误信息
if [ $? -ne 0 ]; then
    echo ""
    echo "❌ 开发服务器启动失败"
    echo ""
    echo "🔧 故障排除建议:"
    echo "  1. 检查端口是否被占用"
    echo "  2. 检查依赖是否完整: npm i"
    echo "  3. 检查mdye-cli版本: mdye --version"
    echo "  4. 查看详细错误日志"
    exit 1
fi