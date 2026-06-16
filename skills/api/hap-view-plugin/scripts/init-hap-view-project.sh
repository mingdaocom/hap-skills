#!/bin/bash

# HAP视图插件项目初始化脚本
# 用法: ./init-hap-view-project.sh [项目名称]

set -e

echo "=== HAP视图插件项目初始化 ==="
echo ""

# 检查Node.js版本
echo "1. 检查Node.js版本..."
NODE_VERSION=$(node --version 2>/dev/null | cut -d'v' -f2)
if [ -z "$NODE_VERSION" ]; then
    echo "❌ 未检测到Node.js，请先安装Node.js 16.20或更高版本"
    exit 1
fi

REQUIRED_VERSION="16.20"
if [ "$(printf '%s\n' "$REQUIRED_VERSION" "$NODE_VERSION" | sort -V | head -n1)" != "$REQUIRED_VERSION" ]; then
    echo "❌ Node.js版本过低，当前版本: $NODE_VERSION，需要版本: $REQUIRED_VERSION 或更高"
    exit 1
fi
echo "✅ Node.js版本检查通过: $NODE_VERSION"

# 检查mdye-cli是否安装
echo ""
echo "2. 检查mdye-cli工具..."
if command -v mdye &> /dev/null; then
    # 已安装，显示版本
    MDYE_VERSION=$(mdye --version 2>/dev/null || echo "未知版本")
    echo "✅ mdye-cli已安装，版本: $MDYE_VERSION"
else
    # 未安装，询问用户是否安装
    echo "❌ mdye-cli未安装"
    echo ""
    echo "要安装mdye-cli，请执行以下命令："
    echo ""

    if [[ "$OSTYPE" == "darwin"* ]]; then
        echo "  # macOS系统"
        echo "  sudo npm install -g mdye-cli"
    else
        echo "  # Windows/Linux系统"
        echo "  npm install -g mdye-cli"
    fi

    echo ""
    echo "安装完成后，请重新运行此脚本。"
    echo ""
    echo "或者，您希望我现在为您安装吗？(y/N)"
    read -r INSTALL_CHOICE

    if [[ "$INSTALL_CHOICE" =~ ^[Yy]$ ]]; then
        echo "开始安装mdye-cli..."

        if [[ "$OSTYPE" == "darwin"* ]]; then
            echo "检测到macOS系统，使用sudo安装..."
            sudo npm install -g mdye-cli
        else
            echo "检测到其他系统，直接安装..."
            npm install -g mdye-cli
        fi

        # 验证安装
        if command -v mdye &> /dev/null; then
            MDYE_VERSION=$(mdye --version 2>/dev/null || echo "未知版本")
            echo "✅ mdye-cli安装成功，版本: $MDYE_VERSION"
        else
            echo "❌ mdye-cli安装失败"
            echo "请手动安装: npm install -g mdye-cli"
            exit 1
        fi
    else
        echo "请先安装mdye-cli，然后重新运行此脚本。"
        exit 1
    fi
fi

# 生成项目名称
echo ""
echo "3. 生成项目配置..."
if [ -n "$1" ]; then
    PROJECT_NAME="$1"
    echo "使用自定义项目名称: $PROJECT_NAME"
else
    TIMESTAMP=$(date +%Y%m%d_%H%M%S)
    RANDOM_SUFFIX=$(openssl rand -hex 3 2>/dev/null || echo $RANDOM)
    PROJECT_NAME="hap_view_${TIMESTAMP}_${RANDOM_SUFFIX}"
    echo "生成项目名称: $PROJECT_NAME"
fi

# 生成插件ID（PREFIX 请替换为你自己的 worksheet/应用 ID，可由环境变量传入）
PREFIX="${PREFIX:-你的worksheetID}"
PLUGIN_ID="${PREFIX}-$(date +%s)-$(openssl rand -hex 4 2>/dev/null || echo $RANDOM)"
echo "生成插件ID: $PLUGIN_ID"

# 创建项目
echo ""
echo "4. 创建项目..."
echo "执行命令: mdye init view --id $PLUGIN_ID --template React"
mdye init view --id "$PLUGIN_ID" --template React

# 检查项目是否创建成功
if [ ! -d "mdye_view_${PLUGIN_ID##*-}" ]; then
    echo "❌ 项目创建失败"
    exit 1
fi

PROJECT_DIR="mdye_view_${PLUGIN_ID##*-}"
echo "✅ 项目创建成功，目录: $PROJECT_DIR"

# 进入项目目录
echo ""
echo "5. 进入项目目录..."
cd "$PROJECT_DIR" || {
    echo "❌ 无法进入项目目录"
    exit 1
}
echo "当前目录: $(pwd)"

# 安装依赖
echo ""
echo "6. 安装项目依赖..."
echo "执行命令: npm i"
npm i

if [ $? -ne 0 ]; then
    echo "⚠️  依赖安装可能存在问题，请检查网络或npm配置"
    echo "建议:"
    echo "  1. 检查网络连接"
    echo "  2. 清理npm缓存: npm cache clean --force"
    echo "  3. 使用淘宝镜像: npm config set registry https://registry.npmmirror.com"
fi

# 显示项目信息
echo ""
echo "=== 项目初始化完成 ==="
echo ""
echo "📁 项目信息:"
echo "  项目名称: $PROJECT_NAME"
echo "  插件ID: $PLUGIN_ID"
echo "  项目目录: $PROJECT_DIR"
echo "  模板类型: React基础示例"
echo ""
echo "🚀 启动项目:"
echo "  cd $PROJECT_DIR"
echo "  mdye start"
echo ""
echo "🔧 常用命令:"
echo "  mdye start          # 启动开发服务器"
echo "  mdye build          # 构建项目"
echo "  npm run lint        # 代码检查"
echo "  npm test           # 运行测试"
echo ""
echo "📚 项目结构:"
echo "  src/               # 源代码目录"
echo "    index.jsx        # 插件入口"
echo "    App.jsx          # 主组件"
echo "    styles.css       # 样式文件"
echo "  public/            # 静态资源"
echo "  package.json       # 项目配置"
echo ""
echo "💡 下一步:"
echo "  1. 进入项目目录: cd $PROJECT_DIR"
echo "  2. 启动开发服务器: mdye start"
echo "  3. 在浏览器中访问开发服务器地址"
echo "  4. 开始开发你的HAP视图插件"
echo ""
echo "⚠️  注意事项:"
echo "  - 确保使用唯一的插件ID"
echo "  - 开发前请阅读明道云插件开发文档"
echo "  - 定期备份重要代码"
echo ""
echo "🎉 祝你开发顺利！"