# HAP 前后端项目搭建指南

> 适用于独立页面动态展示数据的场景

## 目录

- [项目概述](#项目概述)
- [⚠️ 前端 × MCP × HAP 的职责关系(AI 必须理解)](#️-前端--mcp--hap-的职责关系ai-必须理解)
- [🎯 AI 开发目标与原则(必须遵守)](#-ai-开发目标与原则必须遵守)
- [架构说明](#架构说明)
- [快速开始](#快速开始)
- [详细步骤](#详细步骤)
  - [1. HAP 后台配置](#1-hap-后台配置)
  - [2. 前端项目搭建](#2-前端项目搭建)
  - [3. 根据用户需求读取应用结构(必须)](#3-根据用户需求读取应用结构必须)
  - [4. API 集成](#4-api-集成)
  - [5. 业务逻辑实现](#5-业务逻辑实现)
  - [6. 数据渲染](#6-数据渲染)
- [核心概念](#核心概念)
- [最佳实践](#最佳实践)
- [常见问题](#常见问题)
- [示例项目](#示例项目)

---

> ## 🔴 AI 开发者必读：两大硬性要求！
>
> ### 1. 附件字段必须填充 URL
> **在创建示例数据时，附件字段（图片、文件）必须填充 URL，绝不允许为空！**
>
> - ✅ 每条示例数据的附件字段都必须有完整的图片 URL
> - ✅ 使用文档第 1.3 节提供的 8 个测试图片 URL
> - ❌ 绝不允许附件字段为空数组 `[]` 或空字符串 `''`
> - ⚠️ 没有图片的产品/案例/新闻展示效果会非常差，用户体验极差！
>
> ### 2. SingleSelect/MultipleSelect 筛选必须使用 key（UUID）
> **这是 AI 最容易犯的错误！在筛选查询中必须使用选项的 key，不能使用显示文本！**
>
> - ❌ **错误**：`value: ['现代简约']` → 筛选失败，返回空数据
> - ✅ **正确**：`value: ['uuid-xxxx-xxxx']` → 使用选项的 key（UUID）
> - ⚠️ 使用显示文本会导致筛选功能完全失效！
> - 💡 **解决方案**：先调用 `get_worksheet_structure` 获取选项的 key，再用于筛选
>
> **详见：**
> - [1.3 填充示例数据](#13-填充示例数据)
> - [2.4 筛选查询](#24-筛选查询)

---

## 项目概述

本指南介绍如何使用**明道云 HAP（高级应用平台）**作为后台内容管理系统，搭建一个完整的前后端分离项目。

### 适用场景

- ✅ 企业官网（产品展示、新闻资讯、案例展示）
- ✅ 内容管理网站（博客、文档库、知识库）
- ✅ 数据展示平台（数据看板、报表展示）
- ✅ 表单收集系统（在线预约、问卷调查、询价订单）
- ✅ 营销落地页（活动页面、促销页面）

### 技术栈

- **后端**:  HAP（零代码/低代码平台）
- **API**: HAP 应用公开 API V3
- **前端**: HTML5 + CSS3 + JavaScript (ES6+)
- **部署**: 静态网站托管（GitHub Pages、Vercel、Netlify 等）

---

## ⚠️ 前端 × MCP × HAP 的职责关系（AI 必须理解）

**这是最容易混淆的概念，AI 必须在开始工作前明确理解！**

在本项目中，前端与 HAP 的职责分工明确，通过 API 建立数据交互链路：

### 职责划分

#### 1. 前端项目（HTML/CSS/JS）
**职责：** 页面呈现与用户交互
- ✅ 负责页面布局和样式
- ✅ 通过 HAP API V3 实时读取数据
- ✅ 动态渲染页面内容
- ✅ 处理用户交互（表单提交等）
- ❌ 不存储业务数据
- ❌ 不直接使用 @mdfe/view SDK（那是视图插件的）

#### 2. HAP（明道云后台管理系统）
**职责：** 官网所有动态内容的存储、维护、更新
- ✅ 作为官网的唯一数据源
- ✅ 存储产品、案例、新闻等业务数据
- ✅ 提供可视化的数据管理界面
- ✅ 通过 API V3 暴露数据给前端
- ❌ 不负责前端页面渲染
- ❌ 不是视图插件运行环境

#### 3. MCP/API（数据通信桥梁）
**职责：** 前端项目与 HAP 的数据交互
- ✅ **HAP-MCP**: 直接管理应用结构与数据（AI 开发时使用）
  - 创建/修改工作表
  - 批量添加示例数据
  - 查询数据结构
- ✅ **HAP API V3**: 前端项目调用的接口（前端代码使用）
  - 查询数据列表
  - 提交表单数据
  - 获取单条记录详情

### 工作流程示例

```
┌─────────────────────────────────────────────────────────────┐
│ AI 开发阶段                                                  │
├─────────────────────────────────────────────────────────────┤
│ 1. AI 通过 MCP 读取 HAP 应用结构                            │
│ 2. AI 判断是否需要新增工作表/字段                           │
│ 3. AI 通过 MCP 创建工作表并添加示例数据（5条+）             │
│ 4. AI 编写前端代码,调用 HAP API V3                          │
└─────────────────────────────────────────────────────────────┘
                            ↓
┌─────────────────────────────────────────────────────────────┐
│ 前端运行阶段                                                │
├─────────────────────────────────────────────────────────────┤
│ 1. 用户访问网站（静态 HTML/CSS/JS）                         │
│ 2. JS 通过 fetch 调用 HAP API V3                            │
│ 3. API 返回 HAP 中的数据                                    │
│ 4. JS 动态渲染页面内容                                      │
└─────────────────────────────────────────────────────────────┘
                            ↓
┌─────────────────────────────────────────────────────────────┐
│ 内容更新阶段                                                │
├─────────────────────────────────────────────────────────────┤
│ 1. 业务人员登录 HAP 后台                                    │
│ 2. 在工作表中修改数据（添加产品、修改价格等）               │
│ 3. 前端网站自动显示最新数据（无需重新部署）                 │
└─────────────────────────────────────────────────────────────┘
```

### 常见错误（AI 必须避免）

❌ **错误 1**: 在前端代码中使用 MCP
```javascript
// ❌ 错误：前端不能调用 MCP
mcp__hap_mcp____get_record_list(...)
```

✅ **正确做法**: 前端使用 fetch 调用 API V3
```javascript
// ✅ 正确：前端调用 API V3
fetch('https://api.mingdao.com/v3/app/worksheets/{id}/rows/list', {
    method: 'POST',
    headers: {
        'HAP-Appkey': 'xxx',
        'HAP-Sign': 'xxx'
    }
})
```

❌ **错误 2**: 在前端代码中使用视图插件 SDK
```javascript
// ❌ 错误：这是视图插件的 SDK
import { useData } from '@mdfe/view';
```

✅ **正确做法**: 前端使用原生 fetch
```javascript
// ✅ 正确：独立网站使用原生 API 调用
const data = await fetchProducts();
```

❌ **错误 3**: 在前端代码中写死数据
```javascript
// ❌ 错误：数据写死在代码里
const products = [
    { name: '产品1', price: 1000 },
    { name: '产品2', price: 2000 }
];
```

✅ **正确做法**: 通过 API 动态获取
```javascript
// ✅ 正确：从 HAP 动态获取数据
const products = await API.getProducts();
```

---

## 🎯 AI 开发目标与原则（必须遵守）

### 项目交付标准

你是一名**资深全栈工程师 + 低代码架构师**。你需要基于 **HAP（明道云）作为唯一业务数据源**，完成：

**「前端项目 + HAP 后台管理能力」的可运行交付**

#### 必须交付的内容

- ✅ 可直接部署上线的静态前端项目（HTML / CSS / JS）
- ✅ HAP 后台已配置好数据结构（工作表、字段）
- ✅ HAP 中已有示例数据（每表至少 5 条）
- ✅ 前端通过 CORS 实时拉取 HAP 数据的逻辑
- ✅ 必要的配置说明（API 凭证、部署步骤）
- ✅ **自动启动本地开发服务器并提供访问地址（用户可立即预览）**

#### 最终目标

交付一个 **不写死业务数据**、**通过 API 实时拉取 HAP 数据** 的前端项目，并 **自动启动本地服务供用户预览**。

### 核心原则（必须贯彻）

#### 1. 数据来源原则（必须动态）

✅ **允许静态的内容：**
- 导航菜单文案（"首页"、"产品中心"、"关于我们"）
- 页脚信息（版权声明、备案号）
- 无业务含义的 UI 占位文本（"请输入关键词"）
- 固定的展示标题（"产品展示"、"案例中心"）

❌ **禁止静态的内容（必须从 HAP 获取）：**
- 产品列表和详情
- 案例展示
- 新闻资讯
- 轮播图内容
- 价格信息
- 任何业务相关的展示数据

**判断标准：**
```
如果这个内容需要业务人员在后台修改 → 必须从 HAP 获取
如果这个内容是固定的 UI 文案 → 可以写在前端代码里
```

#### 2. 空应用 / 已有结构兼容原则（必须判断）

你的执行必须兼容两种情况：
1. **应用是空的**（无工作表 / 无字段）
2. **应用已有结构与数据**

**⚠️ 强制要求：**
```
步骤 1: 通过 MCP 读取应用当前结构
步骤 2: 判断是否需要新增工作表/字段
步骤 3: 根据判断结果决定后续行为
```

**示例判断逻辑：**
```javascript
// 1. 读取应用结构
const structure = await mcp__hap_mcp____get_app_worksheets_list({
    responseFormat: 'md'
});

// 2. 判断是否存在"产品表"
if (!structure.includes('产品表')) {
    // 3a. 不存在 → 创建新表
    await mcp__hap_mcp____create_worksheet({
        name: '产品表',
        fields: [...]
    });
} else {
    // 3b. 已存在 → 检查是否需要补充字段
    const worksheet = await mcp__hap_mcp____get_worksheet_structure({
        worksheet_id: 'xxx'
    });

    // 判断缺少哪些字段，只新增缺失的
}
```

#### 3. 结构补齐策略：只增不删（红线）

**✅ 允许的操作：**
- 新增工作表
- 新增字段（补充缺失的字段）
- 新增示例数据

**❌ 严禁的操作：**
- 删除任何已有工作表
- 删除任何已有字段
- 修改已有字段的别名（除非用户明确要求）
- 修改已有数据（除非用户明确要求）

**原因：**
- 用户可能已经在使用这些数据
- 删除操作可能导致数据丢失
- 只增不删保证了向后兼容

#### 4. 示例数据强制要求（必须执行）

**⚠️ 硬性要求：**
- 每个新增的工作表 → 必须至少添加 **5 条示例数据**
- 示例数据必须符合字段类型
- 示例数据必须可直接用于前端预览
- **🔴 附件字段必须填充图片 URL（最重要！）**

**示例数据质量标准：**
```javascript
// ❌ 错误：数据质量差（没有图片）
{
    name: '测试1',
    image: '',  // ❌ 空的附件字段会导致页面无图片！
    price: 0
}

// ✅ 正确：真实、可用的示例数据
{
    name: '现代简约沙发',
    image: [{
        name: 'sofa.jpg',
        url: 'https://你的图片URL/示例.png'
    }],
    price: 3999,
    category: '客厅',
    description: '北欧风格，舒适透气，适合现代家居',
    isPublished: '1',
    isRecommended: '1',
    sort: 1
}
```

**为什么必须有示例数据：**
1. 前端页面需要数据才能看到效果
2. 用户可以直接看到最终样式
3. 避免空白页面，提升交付质量
4. **附件字段是最关键的视觉元素 - 没有图片的产品/案例/新闻展示效果会非常差！**

**🎯 附件字段填充规范：**
- ✅ 使用文档第 1.3 节提供的测试图片 URL
- ✅ 每条记录的附件字段都必须有图片
- ✅ 图片 URL 必须完整（包含所有参数）
- ❌ 绝不允许附件字段为空数组 `[]`
- ❌ 绝不允许附件字段为空字符串 `''`

---

## 架构说明

```
┌─────────────────┐         ┌──────────────────┐         ┌─────────────────┐
│                 │         │                  │         │                 │
│   前端页面      │ ◄─────► │  HAP API V3     │ ◄─────► │   HAP 后台      │
│  (HTML/CSS/JS)  │  HTTPS  │  (REST API)     │         │  (数据管理)     │
│                 │         │                  │         │                 │
└─────────────────┘         └──────────────────┘         └─────────────────┘
      用户访问                  数据接口                    管理员操作
```

### 架构优势

1. **前后端分离**: 前端专注展示，后端专注数据管理
2. **零后端开发**: 使用 HAP 可视化配置数据结构，无需编写后端代码
3. **内容可管理**: 业务人员可在 HAP 后台直接管理内容，无需技术支持
4. **快速迭代**: 数据结构调整无需重新部署，实时生效
5. **成本低廉**: 无需购买服务器，静态托管免费

---

## 快速开始

### 前置要求

1. **明道云账号**: 注册地址 https://www.mingdao.com
2. **HAP 应用**: 在明道云创建一个应用
3. **API 凭证**: 获取 HAP-Appkey 和 HAP-Sign

### 5 分钟快速上手

```bash
# 1. 创建项目目录
mkdir my-hap-website
cd my-hap-website

# 2. 创建文件结构
mkdir css js
touch index.html css/style.css js/config.js js/api.js js/main.js

# 3. 启动本地服务器
python -m http.server 8000
# 或
npx serve

# 4. 访问网站
# 浏览器打开 http://localhost:8000
```

### ⚠️ AI 必须执行：自动启动开发服务器

**在完成前端项目搭建后，AI 必须自动启动本地开发服务器，并向用户提供访问地址。**

#### 启动方式（按优先级选择）

**方式 1：Python HTTP Server（推荐，最通用）**
```bash
python -m http.server 8000
# 或 Python 2
python -m SimpleHTTPServer 8000
```
- ✅ 无需安装依赖
- ✅ 适用于所有操作系统
- ✅ 访问地址：`http://localhost:8000`

**方式 2：npx serve（如果有 Node.js）**
```bash
npx serve -p 8000
```
- ✅ 支持 CORS
- ✅ 更友好的 CLI 界面
- ✅ 访问地址：`http://localhost:8000`

**方式 3：PHP 内置服务器（如果有 PHP）**
```bash
php -S localhost:8000
```
- ✅ 支持 PHP 环境
- ✅ 访问地址：`http://localhost:8000`

#### AI 执行流程

1. **创建项目文件后**，使用 Bash 工具启动服务器
2. **使用 `run_in_background: true`** 参数，避免阻塞
3. **立即向用户输出访问地址**

**示例代码：**
```javascript
// 在完成所有文件创建后
await Bash({
    command: 'cd /path/to/project && python -m http.server 8000',
    description: '启动本地开发服务器',
    run_in_background: true
});

// 向用户输出
console.log('✅ 项目搭建完成！');
console.log('🚀 本地服务器已启动');
console.log('📍 访问地址: http://localhost:8000');
console.log('💡 提示: 在浏览器中打开上述地址即可预览网站');
```

#### 注意事项

- ⚠️ 端口 8000 被占用时，尝试 8001、8080、3000 等端口
- ⚠️ 确保在项目根目录启动服务器
- ⚠️ Windows 系统可能需要用 `python` 或 `py` 命令
- ✅ 服务器启动后，用户可直接在浏览器预览效果

---

## 详细步骤

## 1. HAP 后台配置

### 1.1 创建应用

1. 登录明道云 → 点击「创建应用」
2. 选择「从空白创建」
3. 输入应用名称（如：企业官网）
4. 点击「确定」创建

### 1.2 设计数据表

在应用中创建工作表（Worksheet），设计数据结构。

**示例：产品表**

| 字段名称 | 字段类型 | 说明 | 必填 |
|---------|---------|------|------|
| 产品名称 | 文本 | 标题字段 | ✅ |
| 产品图片 | 附件 | 支持上传图片 | ✅ |
| 产品分类 | 单选 | 客厅/卧室/餐厅等 | - |
| 参考价格 | 数值 | 保留2位小数 | - |
| 产品描述 | 文本 | 多行文本 | - |
| 是否上架 | 检查框 | 控制是否显示 | ✅ |
| 是否推荐 | 检查框 | 首页推荐标识 | - |
| 排序 | 数值 | 显示顺序 | ✅ |

### 1.3 填充示例数据

在工作表中添加几条测试数据，用于前端调试。

> **⚠️ 重要提示（AI 必读）**
> **附件字段是示例数据中最关键的部分！** 没有图片的产品/案例/新闻展示效果会非常差。
> 当通过 MCP 创建示例数据时，**必须为附件字段填充测试图片 URL**。

#### 示例图片资源

> **说明**：以下示例图片 URL 仅作格式示意，实际使用时请替换为你自己上传到 HAP 的有效附件 URL（HAP 附件 URL 带有时效 token，过期后无法访问）。

如果没有合适的图片，请上传图片到 HAP 后获取附件 URL，格式如下（占位示意）：

```
https://你的图片URL/示例.png
```

#### 使用方式

**方式一：在 HAP 后台手动添加（适合人工操作）**

1. 打开工作表
2. 新建记录
3. 在附件字段中，直接粘贴上述任意一个 URL
4. 保存记录

**方式二：通过 MCP API 批量创建（AI 开发者必读）**

当通过 MCP 创建示例数据时，附件字段的 `value` 必须是以下格式的数组：

```javascript
// ✅ 正确的附件字段格式
{
    id: '附件字段ID',
    value: [
        {
            name: 'product-image.png',  // 文件名（可自定义）
            url: 'https://你的图片URL/示例.png'  // 完整的图片 URL（替换为你自己上传到 HAP 的有效附件 URL）
        }
    ]
}
```

**完整示例：创建带图片的产品记录**

```javascript
// 通过 MCP 批量创建产品示例数据
await mcp__hap_mcp____batch_create_records({
    worksheet_id: '产品表ID',
    rows: [
        {
            fields: [
                {
                    id: '产品名称字段ID',
                    value: '现代简约沙发'
                },
                {
                    id: '产品图片字段ID',  // ⚠️ 附件字段（最重要）
                    value: [
                        {
                            name: 'sofa.png',
                            url: 'https://你的图片URL/示例.png'
                        }
                    ]
                },
                {
                    id: '参考价格字段ID',
                    value: 5999
                },
                {
                    id: '产品描述字段ID',
                    value: '北欧风格设计，舒适透气面料，适合现代家居'
                },
                {
                    id: '是否上架字段ID',
                    value: '1'
                },
                {
                    id: '排序字段ID',
                    value: 1
                }
            ]
        },
        {
            fields: [
                {
                    id: '产品名称字段ID',
                    value: '实木餐桌'
                },
                {
                    id: '产品图片字段ID',
                    value: [
                        {
                            name: 'table.png',
                            url: 'https://你的图片URL/示例.png'
                        }
                    ]
                },
                {
                    id: '参考价格字段ID',
                    value: 3299
                },
                {
                    id: '产品描述字段ID',
                    value: '优质实木材质，经典设计，结实耐用'
                },
                {
                    id: '是否上架字段ID',
                    value: '1'
                },
                {
                    id: '排序字段ID',
                    value: 2
                }
            ]
        }
        // ... 更多记录（建议至少 5 条）
    ],
    triggerWorkflow: false,
    ai_description: '工作表: 产品表'
});
```

#### 关键要点

**✅ 必须做的：**
- 每条示例数据的附件字段都要填充图片 URL
- 使用上面提供的 8 个测试图片 URL（已验证可用）
- 确保 URL 完整（包含所有参数）
- 文件名（`name`）可以自定义，但要有扩展名（如 `.png`）

**❌ 常见错误：**
```javascript
// ❌ 错误 1：value 不是数组
{
    id: '附件字段ID',
    value: 'https://...'  // 错误！必须是数组
}

// ❌ 错误 2：缺少 name 属性
{
    id: '附件字段ID',
    value: [
        {
            url: 'https://...'  // 错误！缺少 name 属性
        }
    ]
}

// ❌ 错误 3：附件字段为空（最严重的错误）
{
    id: '附件字段ID',
    value: []  // ❌ 错误！会导致页面无图片，严重影响用户体验！
}

// ❌ 错误 4：附件字段被完全忽略（AI 最常犯的错误）
{
    id: '产品名称字段ID',
    value: '现代简约沙发'
},
{
    id: '价格字段ID',
    value: 5999
}
// ❌ 完全没有提供附件字段！导致所有记录都没有图片！

// ✅ 正确做法
{
    id: '产品名称字段ID',
    value: '现代简约沙发'
},
{
    id: '产品图片字段ID',  // ✅ 必须包含附件字段
    value: [{
        name: 'sofa.png',
        url: 'https://你的图片URL/示例.png'
    }]
},
{
    id: '价格字段ID',
    value: 5999
}
```

**❌ 错误 5：SingleSelect/MultipleSelect 筛选使用显示文本而非 key（AI 常犯错误）**

```javascript
// ❌ 错误：使用选项的显示文本（value）进行筛选
const result = await API.getRows(CONFIG.WORKSHEETS.PRODUCTS, {
    filter: {
        type: 'group',
        logic: 'AND',
        children: [{
            type: 'condition',
            field: '风格字段ID',
            operator: 'eq',
            value: ['现代简约']  // ❌ 错误！这是显示文本，不是 key
        }]
    }
});
// 结果：筛选失败，返回空数据或全部数据

// ✅ 正确：使用选项的 key（UUID）进行筛选
const result = await API.getRows(CONFIG.WORKSHEETS.PRODUCTS, {
    filter: {
        type: 'group',
        logic: 'AND',
        children: [{
            type: 'condition',
            field: '风格字段ID',
            operator: 'eq',
            value: ['a1b2c3d4-e5f6-7890-abcd-ef1234567890']  // ✅ 正确！使用 key
        }]
    }
});

// 🔴 关键原则：
// - 显示时使用 option.value（显示文本）→ "现代简约"
// - 筛选时使用 option.key（UUID）→ "a1b2c3d4-e5f6-7890-abcd-ef1234567890"
// - 如果不知道 key，需要先调用 get_worksheet_structure 获取字段的 options 列表

// 正确的流程示例：
// 1. 获取工作表结构，找到选项的 key
const structure = await mcp__hap_mcp____get_worksheet_structure({
    worksheet_id: '工作表ID',
    ai_description: '工作表: 产品表'
});
// 从返回的字段结构中找到：options: [{key: 'xxx', value: '现代简约'}, ...]

// 2. 使用 key 进行筛选
const modernProducts = await API.getRows(CONFIG.WORKSHEETS.PRODUCTS, {
    filter: {
        type: 'group',
        logic: 'AND',
        children: [{
            type: 'condition',
            field: '风格字段ID',
            operator: 'eq',
            value: ['xxx']  // 使用从结构中获取的 key
        }]
    }
});
```

**提示：**
- ✅ 这些图片已经过 HAP CDN 加速，访问速度快
- ✅ URL 中的 `imageView2/2/w/200/q/100` 参数可以调整图片尺寸和质量
- ✅ 8 个 URL 足够创建丰富的示例数据（产品、案例、新闻等）
- ⚠️ 仅用于测试和演示，生产环境请使用自己的图片资源

### 1.4 获取 API 凭证

#### 方法一：通过 MCP 配置提取（推荐）

如果应用已配置 HAP MCP Server，可以从配置中直接提取 API 凭证：

```json
{
  "mcpServers": {
    "hap-mcp-API测试": {
      "url": "https://api.mingdao.com/mcp?HAP-Appkey=你的Appkey&HAP-Sign=你的Sign"
    }
  }
}
```

从 URL 参数中提取：
- **HAP-Appkey**: `你的Appkey`
- **HAP-Sign**: `你的Sign`

这些凭证可以直接用于前端代码中的 API 调用。

#### 方法二：手动获取

1. **获取 HAP-Appkey 和 HAP-Sign**
   - 进入应用 → 设置 → API 密钥
   - 复制 Appkey 和 Sign

2. **获取工作表 ID**
   - 打开工作表
   - 查看浏览器地址栏 URL
   - 格式：`https://xxx.mingdao.com/app/{appId}/worksheet/{worksheetId}`

3. **获取字段 ID**
   - 方式 1：通过 API 查询工作表结构
   - 方式 2：通过 MCP Server 调用 `get_worksheet_structure`

---

## 2. 前端项目搭建

### 2.1 项目结构

**核心原则：** 结构清晰、职责分离、易于维护

AI 需要创建合理的项目结构，包括但不限于：
- 主页面文件（HTML）
- 样式文件（CSS）
- 配置文件（HAP API 凭证）
- API 封装文件（数据请求逻辑）
- 业务逻辑文件（页面交互）
- 静态资源目录（图片、字体等）

**要求：**
- ✅ 文件命名清晰、语义化
- ✅ 代码分层合理（配置、API、业务逻辑分离）
- ✅ 便于后续扩展和维护

### 2.2 HTML 结构设计原则

**核心原则：** 语义化、可访问性、SEO 友好

AI 需要构建符合现代 Web 标准的 HTML 结构：

**基本要求：**
- ✅ 使用语义化标签（header, nav, main, section, article, footer 等）
- ✅ 合理的文档结构（导航、内容区、底部）
- ✅ 响应式设计支持（viewport meta 标签）
- ✅ SEO 优化（title, meta description, alt 属性等）
- ✅ 可访问性（ARIA 属性、键盘导航支持）

**交互体验要求：**
- ✅ 加载状态提示（骨架屏或加载动画）
- ✅ 错误状态处理（友好的错误提示）
- ✅ 空状态设计（无数据时的提示）
- ✅ 平滑的内容过渡动画

**禁止事项：**
- ❌ 过度使用 div 嵌套
- ❌ 内联样式（应使用 CSS 类）
- ❌ 硬编码业务数据

### 2.3 CSS 样式设计原则

**核心原则：** 美观、专业、用户友好

AI 需要运用设计师的审美标准创建高质量的样式：

**视觉设计要求：**
- ✅ **配色方案**：协调的主题色系，符合品牌调性
- ✅ **排版美学**：合理的字体层级、行高、字间距
- ✅ **空间布局**：恰当的留白、间距、对齐方式
- ✅ **视觉层次**：清晰的信息优先级和焦点引导
- ✅ **一致性**：统一的设计语言和组件风格

**交互体验要求：**
- ✅ **响应式设计**：完美适配桌面、平板、手机
- ✅ **微交互**：悬停效果、点击反馈、过渡动画
- ✅ **加载状态**：优雅的骨架屏或加载动画
- ✅ **错误提示**：友好的错误信息展示
- ✅ **无障碍**：足够的对比度、可点击区域大小

**性能优化要求：**
- ✅ 使用现代 CSS（Flexbox、Grid）
- ✅ 减少不必要的重绘和重排
- ✅ 合理使用 CSS 动画（transform、opacity）
- ✅ 响应式图片和懒加载

**设计风格建议：**
- 现代简约风格（推荐）
- 扁平化设计
- 柔和的阴影和圆角
- 流畅的动画过渡（0.2s - 0.3s）
- 适当的视觉层次（卡片、悬浮效果）

**禁止事项：**
- ❌ 过度装饰和花哨效果
- ❌ 不考虑响应式的固定宽度
- ❌ 过度使用动画导致性能问题
- ❌ 色彩搭配混乱、对比度不足
- ❌ 不一致的设计风格

---

## 3. 根据用户需求读取应用结构(必须)

### 核心原则

在准备通过 MCP 搭建应用创建数据时,AI 必须作为**顶级架构师**站在全局视角进行系统性规划。这不是简单的功能实现,而是需要:

- ✅ **理解业务需求**:深入理解用户的真实业务场景
- ✅ **评估现有资源**:充分利用已有的应用结构
- ✅ **避免重复建设**:识别可复用的工作表和字段
- ✅ **只增不删原则**:保护用户已有数据,绝不删除
- ✅ **用户确认机制**:任何结构变更必须征得用户同意

---

### 3.1 读取应用真实结构

通过 **HAP-MCP** 获取应用的完整结构信息:

**必须获取的信息:**
- ✅ 工作表列表(含 name 和 alias)
- ✅ 字段结构(name、alias、type)
- ✅ 视图信息(如需要)
- ✅ 现有数据量概况

**使用工具:**

```javascript
// 获取应用工作表列表(推荐使用 Markdown 格式)
mcp__hap_mcp____get_app_worksheets_list({
    responseFormat: 'md'  // 返回易读的 Markdown 格式
})

// 获取特定工作表的详细结构
mcp__hap_mcp____get_worksheet_structure({
    worksheet_id: '工作表ID',
    responseFormat: 'md',
    ai_description: '工作表: <工作表名称>'
})
```

**输出结构摘要:**
AI 必须输出清晰的摘要,包括:
- 📋 现有工作表清单(名称 + 用途推测)
- 🏷️ 关键字段清单(按工作表分组)
- ⚠️ 关键缺失点(业务需求 vs 现有结构的差距)

---

### 3.2 结构差距评估与补齐决策模块(强制)

本模块用于在**已成功读取应用真实结构**后,基于用户的业务需求,对当前 HAP 应用结构进行一次**"是否满足前端展示需求"**的系统性判断。

该模块分为两个阶段:
1️⃣ **结构差距评估**(分析阶段)
2️⃣ **结构补齐决策**(用户确认阶段)

---

#### 3.2.1 结构差距评估(分析阶段,必须执行)

AI 必须基于以下信息进行评估:
- 通过 MCP 获取的**真实应用结构**
- 用户描述的业务需求

**评估内容必须覆盖:**

**(1) 页面 → 业务对象映射(只描述业务,不臆造字段)**

示例:
```
用户需求: 企业官网需要展示产品、案例、新闻
业务对象识别:
  - 产品展示 → 需要产品信息(名称、图片、价格、描述等)
  - 案例展示 → 需要案例信息(标题、封面图、客户名称、详情等)
  - 新闻资讯 → 需要新闻信息(标题、发布时间、内容、作者等)
```

**(2) 现有结构可复用性判断**

检查当前应用中是否已存在:
- ✅ 可复用的工作表(语义匹配)
- ✅ 可复用的字段(类型和用途匹配)
- ✅ 可通过已有字段组合满足需求
- ✅ 现有别名是否可直接使用

示例:
```
现有结构评估:
  ✅ 发现工作表"产品管理"(alias: products)
     - 包含字段:产品名称、产品图片、价格、详情
     - 评估:可直接用于产品展示页面

  ⚠️ 发现工作表"客户案例"(alias: cases)
     - 包含字段:案例标题、客户名称
     - 评估:缺少封面图和详情字段,需补充

  ❌ 未发现新闻相关工作表
     - 评估:需新建"新闻资讯"工作表
```

**(3) 差距识别(只增不删)**

明确指出以下三类结果之一(必须给出结论):

- ✅ **结构完全满足**:无需新增任何工作表或字段
- ⚠️ **结构部分满足**:可复用现有结构 + 少量补充字段
- ❌ **结构不足**:需要新增工作表

---

#### 3.2.2 结构差距评估输出(必须给出)

AI 必须输出一份清晰的评估结果摘要:

**📊 评估结果示例:**

```markdown
## HAP 应用结构评估报告

### ✅ 可复用结构

**工作表:**
- "产品管理"(products) → 可直接用于产品展示页面
  - 已有字段:产品名称、产品图片、价格、规格、详情
  - 数据量:12 条产品记录

**字段:**
- 产品名称(Text)、产品图片(Attachment)、价格(Number)等
  可满足产品卡片展示需求

---

### ➕ 建议新增内容

**1. 补充"客户案例"工作表字段**
   - 建议新增:封面图(附件字段)
   - 建议新增:案例详情(多行文本)
   - 用途:完善案例展示页面

**2. 新建"新闻资讯"工作表**
   - 建议字段:
     - 标题(文本,标题字段)
     - 封面图(附件)
     - 发布时间(日期)
     - 内容(富文本)
     - 是否发布(检查框)
   - 用途:支持新闻列表和详情页展示

**3. 示例数据需求**
   - "新闻资讯"表需要至少 5 条示例新闻
   - "客户案例"表需要补充封面图数据

---

### 🚫 不执行的操作

此阶段**仅做分析,不得执行任何新增操作**,包括:
- ❌ 不创建新工作表
- ❌ 不添加新字段
- ❌ 不写入示例数据
- ❌ 不修改现有结构

---

### 📋 结论

**结构满足度:** ⚠️ 部分满足

**下一步行动:**
需要进入"结构补齐决策"阶段,请求用户确认以下操作:
1. 补充"客户案例"工作表字段
2. 新建"新闻资讯"工作表
3. 添加示例数据
```

---

### 3.3 结构补齐决策（🔴 强制用户确认，硬阻塞）

**⚠️ 红线警告：本阶段是强制执行的用户确认机制，违反将导致严重后果！**

当且仅当**3.2.2 的结论为「结构部分满足」或「结构不足」**时，必须进入本阶段。

---

#### 3.3.1 触发用户确认的条件（必须）

**以下任一情况出现时，AI 必须立即停止，使用 `AskUserQuestion` 工具请求用户明确同意：**

- 🔴 需要新增工作表
- 🔴 需要新增字段到现有工作表
- 🔴 需要写入示例数据
- 🔴 需要修改现有字段配置
- 🔴 页面展示依赖的数据在当前应用中不存在

**核心原则：**
```
未经用户明确同意 = 禁止执行任何写操作（创建、修改、删除）
```

---

#### 3.3.2 用户确认方式

使用 `AskUserQuestion` 工具,清晰列出建议的操作:

**示例 1:需要新增工作表**

```javascript
AskUserQuestion({
    questions: [{
        question: "根据业务需求分析,当前应用缺少「新闻资讯」相关数据表。是否允许创建新的工作表?",
        header: "新增工作表",
        multiSelect: false,
        options: [
            {
                label: "同意创建(推荐)",
                description: "创建「新闻资讯」工作表,包含标题、封面图、发布时间、内容等字段,并添加 5 条示例数据"
            },
            {
                label: "仅创建表结构",
                description: "只创建工作表和字段,不添加示例数据。前端页面可能显示为空"
            },
            {
                label: "暂不创建",
                description: "跳过此工作表,使用现有数据完成开发。新闻模块将无法展示"
            }
        ]
    }]
})
```

**示例 2:需要补充字段**

```javascript
AskUserQuestion({
    questions: [{
        question: "现有「客户案例」工作表缺少展示所需的封面图和详情字段。是否允许补充这些字段?",
        header: "补充字段",
        multiSelect: false,
        options: [
            {
                label: "同意补充(推荐)",
                description: "在「客户案例」表中新增:封面图(附件)、案例详情(多行文本)字段"
            },
            {
                label: "使用现有字段",
                description: "尝试用现有字段替代,可能影响展示效果"
            },
            {
                label: "暂不补充",
                description: "保持现状,案例展示功能可能不完整"
            }
        ]
    }]
})
```

**示例 3:需要添加示例数据**

```javascript
AskUserQuestion({
    questions: [{
        question: "新建的「新闻资讯」工作表需要示例数据以便前端页面预览效果。⚠️ 特别注意：附件字段必须填充图片 URL，否则页面将无法显示图片。是否允许添加示例数据?",
        header: "示例数据",
        multiSelect: false,
        options: [
            {
                label: "添加完整示例数据(推荐)",
                description: "添加 5 条真实的新闻示例，包含标题、封面图（必须有图片 URL）、内容等，便于查看页面效果"
            },
            {
                label: "添加最少数据",
                description: "仅添加 1-2 条简单示例，但附件字段仍会填充图片，节省创建时间"
            },
            {
                label: "不添加数据",
                description: "工作表为空，前端页面将显示空状态提示（不推荐，无法预览效果）"
            }
        ]
    }]
})
```

---

#### 3.3.3 禁止行为（🚫 红线，不可逾越）

**以下行为严格禁止，违反将导致用户数据损坏、业务中断等严重后果：**

---

**🚫 禁止 1：未确认即新增工作表**

```javascript
// ❌ 严重错误：未经用户同意直接创建工作表
await mcp__hap_mcp____create_worksheet({
    name: '新闻资讯',
    fields: [...]
})
// 后果：用户应用中突然出现未知的工作表，可能影响现有业务流程
```

✅ **正确做法：先询问，得到明确同意后再执行**
```javascript
// 1. 先询问用户
const answer = await AskUserQuestion({
    questions: [{
        question: "是否允许创建新的「新闻资讯」工作表？",
        header: "新增工作表",
        multiSelect: false,
        options: [
            { label: "同意创建(推荐)", description: "创建工作表及字段..." },
            { label: "暂不创建", description: "使用现有数据..." }
        ]
    }]
})

// 2. 仅在用户明确同意后才执行
if (answer.includes('同意创建')) {
    await mcp__hap_mcp____create_worksheet({
        name: '新闻资讯',
        fields: [...]
    })
} else {
    // 用户拒绝，调整开发方案
    console.log('用户拒绝创建新表，使用现有结构')
}
```

---

**🚫 禁止 2：未确认即新增字段**

```javascript
// ❌ 严重错误：未经用户同意直接添加字段
await mcp__hap_mcp____update_worksheet({
    worksheet_id: 'xxx',
    addFields: [
        { name: '封面图', type: 'Attachment' }
    ]
})
// 后果：现有工作表结构被修改，可能影响用户已有的视图、工作流、权限配置
```

✅ **正确做法：详细说明拟新增的字段，得到用户同意**
```javascript
const answer = await AskUserQuestion({
    questions: [{
        question: "是否允许在「客户案例」表中新增封面图字段？",
        header: "补充字段",
        options: [...]
    }]
})

if (answer.includes('同意')) {
    await mcp__hap_mcp____update_worksheet({
        worksheet_id: 'xxx',
        addFields: [...]
    })
}
```

---

**🚫 禁止 3：未确认即写入示例数据**

```javascript
// ❌ 严重错误：未经用户同意直接写入数据
await mcp__hap_mcp____batch_create_records({
    worksheet_id: 'xxx',
    rows: [...]
})
// 后果：用户的生产数据中混入测试数据，可能导致数据混乱
```

✅ **正确做法：说明示例数据的用途和内容**
```javascript
const answer = await AskUserQuestion({
    questions: [{
        question: "是否允许添加 5 条示例数据以便预览效果？",
        header: "示例数据",
        options: [...]
    }]
})

if (answer.includes('添加')) {
    await mcp__hap_mcp____batch_create_records({
        worksheet_id: 'xxx',
        rows: [...]
    })
}
```

---

**🚫 禁止 4：假设用户意图（最危险）**

```javascript
// ❌ 严重错误：自作主张，假设用户需要
// "用户说要做官网，肯定需要新闻表，我直接创建吧"
await mcp__hap_mcp____create_worksheet({ name: '新闻资讯' })
// 后果：用户可能已有新闻表，或不需要该功能，造成混乱
```

✅ **正确做法：读取现有结构，分析需求，询问用户**
```javascript
// 1. 读取应用结构
const structure = await mcp__hap_mcp____get_app_worksheets_list()

// 2. 判断是否需要新增
if (!structure.includes('新闻')) {
    // 3. 询问用户
    const answer = await AskUserQuestion({...})

    // 4. 根据用户回答执行
    if (answer.includes('同意')) {
        await mcp__hap_mcp____create_worksheet({...})
    }
}
```

---

**🚫 禁止 5：批量操作前未确认**

```javascript
// ❌ 严重错误：一次性创建多个表/字段/数据，未分别确认
for (const table of ['产品', '案例', '新闻']) {
    await mcp__hap_mcp____create_worksheet({ name: table })  // 未确认！
}
// 后果：用户可能只需要其中一部分，导致冗余表的创建
```

✅ **正确做法：逐项确认或一次性展示完整计划**
```javascript
// 方案 1：逐项确认
for (const table of needCreate) {
    const answer = await AskUserQuestion({
        question: `是否创建「${table}」表？`,
        ...
    })
    if (answer.includes('同意')) {
        await mcp__hap_mcp____create_worksheet({...})
    }
}

// 方案 2：一次性展示完整计划（推荐）
const answer = await AskUserQuestion({
    question: "建议创建以下工作表：产品、案例、新闻。是否全部创建？",
    options: [
        { label: "全部创建", description: "..." },
        { label: "部分创建", description: "..." },
        { label: "不创建", description: "..." }
    ]
})
```

---

#### 3.3.4 用户确认后的执行

**仅在用户明确同意后**,才可执行相应操作:

**执行顺序:**
1. 创建新工作表(如需要)
2. 补充字段到现有工作表(如需要)
3. 添加示例数据(如需要)
4. 验证结构是否完整

**执行示例:**

```javascript
// 1. 用户确认后创建工作表
if (userConfirmed) {
    const result = await mcp__hap_mcp____create_worksheet({
        name: '新闻资讯',
        alias: 'news',
        fields: [
            { name: '标题', type: 'Text', isTitle: true, required: true },
            { name: '封面图', type: 'Attachment', required: false },
            { name: '发布时间', type: 'Date', required: false },
            { name: '内容', type: 'Text', required: false },
            { name: '是否发布', type: 'Checkbox', required: false }
        ],
        ai_description: '工作表:新闻资讯'
    });

    // 2. 添加示例数据（必须包含图片）
    await mcp__hap_mcp____batch_create_records({
        worksheet_id: result.worksheetId,
        rows: [
            {
                fields: [
                    { id: '标题字段ID', value: '公司荣获年度最佳创新奖' },
                    // 🔴 重要：附件字段必须填充完整的图片 URL
                    { id: '封面图字段ID', value: [{
                        name: 'award.jpg',
                        url: 'https://你的图片URL/示例.png'
                    }] },
                    { id: '发布时间字段ID', value: '2024-12-01' },
                    { id: '内容字段ID', value: '在今年的行业评选中...' },
                    { id: '是否发布字段ID', value: '1' }
                ]
            },
            // ... 至少 5 条示例数据，每条都必须包含图片
        ],
        ai_description: '工作表:新闻资讯'
    });
}
```

---

### 3.4 完整流程示例

以下是一个完整的标准流程:

```
┌─────────────────────────────────────────────────────────────┐
│ 阶段 1: 读取应用结构                                        │
├─────────────────────────────────────────────────────────────┤
│ 1. 调用 get_app_worksheets_list 获取工作表列表             │
│ 2. 调用 get_worksheet_structure 获取关键表的字段结构       │
│ 3. 整理现有结构摘要                                         │
└─────────────────────────────────────────────────────────────┘
                            ↓
┌─────────────────────────────────────────────────────────────┐
│ 阶段 2: 结构差距评估(分析阶段)                             │
├─────────────────────────────────────────────────────────────┤
│ 1. 识别业务对象                                             │
│ 2. 判断现有结构可复用性                                     │
│ 3. 识别差距(完全满足/部分满足/不足)                         │
│ 4. 输出评估报告                                             │
│ 🚫 不执行任何新增操作                                       │
└─────────────────────────────────────────────────────────────┘
                            ↓
        ┌─────────────────────────────────┐
        │ 结构完全满足?                   │
        └─────────────────────────────────┘
                 /              \
               是                否
                ↓                ↓
    ┌───────────────┐    ┌─────────────────────────┐
    │ 直接开发前端   │    │ 阶段 3: 结构补齐决策    │
    │ 使用现有结构   │    │ (用户确认阶段)          │
    └───────────────┘    └─────────────────────────┘
                                    ↓
                         ┌───────────────────────┐
                         │ 使用 AskUserQuestion  │
                         │ 列出建议操作          │
                         │ - 新增工作表?         │
                         │ - 补充字段?           │
                         │ - 添加示例数据?       │
                         └───────────────────────┘
                                    ↓
                         ┌───────────────────────┐
                         │ 用户确认同意?         │
                         └───────────────────────┘
                                 /        \
                              同意        拒绝
                                ↓          ↓
                    ┌──────────────────┐  ┌────────────────┐
                    │ 执行确认的操作   │  │ 使用现有结构   │
                    │ 1. 创建工作表    │  │ 调整开发方案   │
                    │ 2. 补充字段      │  │ 降低功能预期   │
                    │ 3. 添加示例数据  │  └────────────────┘
                    └──────────────────┘
                                ↓
                    ┌──────────────────┐
                    │ 验证结构完整性   │
                    │ 开始前端开发     │
                    └──────────────────┘
```

---

### 3.5 关键原则总结

**🎯 核心原则：**

**1. 先读取，后评估，再确认，最后执行（🔴 强制流程）**
   - ✅ 必须先读取应用现有结构
   - ✅ 必须评估是否满足需求
   - ✅ 必须在执行前得到用户明确确认
   - ❌ 绝不可跳过任何阶段
   - ❌ 绝不可在未确认的情况下执行写操作

**2. 只增不删（🔴 硬性规则）**
   - ✅ 可以新增工作表（需确认）
   - ✅ 可以新增字段（需确认）
   - ✅ 可以新增数据（需确认）
   - ❌ 绝不删除现有工作表
   - ❌ 绝不删除现有字段
   - ❌ 绝不修改已有数据（除非用户明确要求）

**3. 用户确认是硬阻塞（🔴 最高优先级）**
   - ✅ 任何结构变更必须征得用户同意
   - ✅ 使用 `AskUserQuestion` 工具提供清晰的选项
   - ✅ 详细说明每个选项的后果和影响
   - ❌ 不可假设用户意图
   - ❌ 不可因为"觉得用户需要"就擅自执行
   - ❌ 不可省略确认步骤

**4. 优先复用现有结构（避免冗余）**
   - ✅ 能用现有表就不新建
   - ✅ 能用现有字段就不新增
   - ✅ 充分利用已有数据
   - ✅ 识别语义相近的工作表/字段

**5. 透明化决策过程（建立信任）**
   - ✅ 清晰解释为什么需要新增
   - ✅ 说明新增内容的用途和必要性
   - ✅ 给出不新增的影响和替代方案
   - ✅ 让用户完全理解每个选择的后果

**6. 附件字段必须填充（🔴 视觉质量保证）**
   - ✅ 每条示例数据的附件字段都必须有图片 URL
   - ✅ 使用文档提供的测试图片 URL
   - ❌ 绝不允许附件字段为空

**7. SingleSelect/MultipleSelect 筛选必须使用 key（🔴 功能正确性保证）**
   - ✅ 筛选时必须使用选项的 key（UUID），不能使用显示文本
   - ✅ 先调用 `get_worksheet_structure` 获取选项列表和 key
   - ✅ 在筛选条件中使用 `value: [optionKey]`
   - ❌ 绝不使用显示文本进行筛选（如 `value: ['现代简约']`）
   - ⚠️ 使用显示文本会导致筛选完全失效

---

**🚨 违反上述原则的后果：**

| 违规行为 | 严重程度 | 后果 |
|---------|---------|------|
| 未确认即创建工作表 | 🔴 严重 | 用户应用结构被污染，业务流程被打乱 |
| 未确认即添加字段 | 🔴 严重 | 现有视图/工作流/权限配置可能失效 |
| 未确认即写入数据 | 🔴 严重 | 生产数据中混入测试数据，数据混乱 |
| 删除现有工作表/字段 | ⛔ 致命 | 用户数据永久丢失，业务完全中断 |
| 附件字段为空 | ⚠️ 中等 | 页面无图片，用户体验极差 |
| 筛选时使用显示文本 | 🔴 严重 | 筛选功能完全失效，用户无法按分类查询数据 |

---

## 4. API 集成

### 4.0 CORS 跨域请求与分页详解

#### 4.0.1 CORS 跨域配置

HAP API V3 已经配置了 CORS 支持,可以直接从前端发起跨域请求。

**关键要点:**
- ✅ HAP API 允许跨域请求,无需配置代理
- ✅ 必须在请求头中携带 `HAP-Appkey` 和 `HAP-Sign`
- ✅ 使用 `Content-Type: application/json`
- ⚠️ 生产环境建议使用后端代理保护密钥

**示例 1: 基础 CORS 请求**

```javascript
// 直接从浏览器调用 HAP API
async function fetchHAPData() {
    const response = await fetch('https://api.mingdao.com/v3/app/worksheets/{worksheetId}/rows/list', {
        method: 'POST',
        headers: {
            'HAP-Appkey': 'your_appkey',
            'HAP-Sign': 'your_sign',
            'Content-Type': 'application/json'
        },
        body: JSON.stringify({
            pageSize: 20,
            pageIndex: 1,
            useFieldIdAsKey: true
        })
    });

    const data = await response.json();
    return data;
}
```

**示例 2: 处理 CORS 错误**

```javascript
async function safeFetchHAPData() {
    try {
        const response = await fetch('https://api.mingdao.com/v3/app/worksheets/{worksheetId}/rows/list', {
            method: 'POST',
            headers: {
                'HAP-Appkey': CONFIG.HAP_APPKEY,
                'HAP-Sign': CONFIG.HAP_SIGN,
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({
                pageSize: 20,
                pageIndex: 1
            })
        });

        // 检查响应状态
        if (!response.ok) {
            throw new Error(`HTTP error! status: ${response.status}`);
        }

        const data = await response.json();

        // 检查业务状态
        if (!data.success) {
            throw new Error(data.error_msg || 'API 请求失败');
        }

        return data;

    } catch (error) {
        // CORS 错误
        if (error.message.includes('CORS')) {
            console.error('跨域错误: 请检查 API 配置');
        }
        // 认证错误
        else if (error.message.includes('401')) {
            console.error('认证失败: 请检查 HAP-Appkey 和 HAP-Sign');
        }
        // 其他错误
        else {
            console.error('请求失败:', error.message);
        }

        throw error;
    }
}
```

#### 4.0.2 分页逻辑实现

HAP API 支持分页查询,推荐使用以下参数:

**分页参数说明:**
- `pageSize`: 每页数据量 (1-1000,推荐 20-50)
- `pageIndex`: 页码 (从 1 开始)
- `includeTotalCount`: 是否返回总数 (true/false)

**示例 3: 基础分页**

```javascript
// 简单分页查询
async function getProductsPage(pageIndex = 1, pageSize = 20) {
    const response = await API.getRows(CONFIG.WORKSHEETS.PRODUCTS, {
        pageSize: pageSize,
        pageIndex: pageIndex,
        includeTotalCount: true,  // 获取总记录数
        sorts: [{
            field: CONFIG.PRODUCT_FIELDS.SORT,
            isAsc: true
        }]
    });

    return {
        rows: response.rows || [],
        total: response.total || 0,
        pageIndex: pageIndex,
        pageSize: pageSize,
        totalPages: Math.ceil(response.total / pageSize)
    };
}

// 使用示例
const page1 = await getProductsPage(1, 20);
console.log(`共 ${page1.total} 条记录, 第 1/${page1.totalPages} 页`);
```

**示例 4: 完整分页器组件**

```javascript
// 分页管理器
class PaginationManager {
    constructor(options = {}) {
        this.pageSize = options.pageSize || 20;
        this.currentPage = 1;
        this.totalPages = 0;
        this.totalCount = 0;
        this.data = [];
        this.onPageChange = options.onPageChange || null;
    }

    // 加载指定页
    async loadPage(pageIndex) {
        try {
            const result = await API.getRows(CONFIG.WORKSHEETS.PRODUCTS, {
                pageSize: this.pageSize,
                pageIndex: pageIndex,
                includeTotalCount: true,
                filter: {
                    type: 'group',
                    logic: 'AND',
                    children: [{
                        type: 'condition',
                        field: CONFIG.PRODUCT_FIELDS.PUBLISHED,
                        operator: 'eq',
                        value: ['1']
                    }]
                },
                sorts: [{
                    field: CONFIG.PRODUCT_FIELDS.SORT,
                    isAsc: true
                }]
            });

            this.data = result.rows || [];
            this.totalCount = result.total || 0;
            this.totalPages = Math.ceil(this.totalCount / this.pageSize);
            this.currentPage = pageIndex;

            // 触发回调
            if (this.onPageChange) {
                this.onPageChange(this.data, this);
            }

            return this.data;
        } catch (error) {
            console.error('加载分页数据失败:', error);
            throw error;
        }
    }

    // 下一页
    async nextPage() {
        if (this.currentPage < this.totalPages) {
            return await this.loadPage(this.currentPage + 1);
        }
        return this.data;
    }

    // 上一页
    async prevPage() {
        if (this.currentPage > 1) {
            return await this.loadPage(this.currentPage - 1);
        }
        return this.data;
    }

    // 跳转到指定页
    async goToPage(pageIndex) {
        if (pageIndex >= 1 && pageIndex <= this.totalPages) {
            return await this.loadPage(pageIndex);
        }
        throw new Error('页码超出范围');
    }

    // 获取分页信息
    getPaginationInfo() {
        return {
            currentPage: this.currentPage,
            totalPages: this.totalPages,
            pageSize: this.pageSize,
            totalCount: this.totalCount,
            hasNext: this.currentPage < this.totalPages,
            hasPrev: this.currentPage > 1
        };
    }
}

// 使用示例
const pagination = new PaginationManager({
    pageSize: 20,
    onPageChange: (data, pager) => {
        console.log(`加载第 ${pager.currentPage}/${pager.totalPages} 页`);
        renderProducts(data);
        renderPagination(pager);
    }
});

// 初始化加载
await pagination.loadPage(1);
```

**示例 5: 无限滚动加载**

```javascript
// 无限滚动分页
class InfiniteScroll {
    constructor(options = {}) {
        this.pageSize = options.pageSize || 20;
        this.currentPage = 0;
        this.isLoading = false;
        this.hasMore = true;
        this.allData = [];
        this.container = options.container;
        this.onDataLoad = options.onDataLoad || null;

        // 监听滚动事件
        this.initScrollListener();
    }

    initScrollListener() {
        window.addEventListener('scroll', () => {
            // 检查是否滚动到底部
            const scrollTop = window.pageYOffset || document.documentElement.scrollTop;
            const scrollHeight = document.documentElement.scrollHeight;
            const clientHeight = window.innerHeight;

            if (scrollTop + clientHeight >= scrollHeight - 200) {
                // 距离底部 200px 时加载
                this.loadMore();
            }
        });
    }

    async loadMore() {
        if (this.isLoading || !this.hasMore) return;

        this.isLoading = true;
        this.currentPage++;

        try {
            const result = await API.getRows(CONFIG.WORKSHEETS.PRODUCTS, {
                pageSize: this.pageSize,
                pageIndex: this.currentPage,
                includeTotalCount: true,
                filter: {
                    type: 'group',
                    logic: 'AND',
                    children: [{
                        type: 'condition',
                        field: CONFIG.PRODUCT_FIELDS.PUBLISHED,
                        operator: 'eq',
                        value: ['1']
                    }]
                }
            });

            const newData = result.rows || [];
            this.allData = [...this.allData, ...newData];

            // 检查是否还有更多数据
            this.hasMore = newData.length === this.pageSize;

            // 触发回调
            if (this.onDataLoad) {
                this.onDataLoad(newData, this.allData);
            }

            // 渲染新数据
            this.appendData(newData);

        } catch (error) {
            console.error('加载更多数据失败:', error);
        } finally {
            this.isLoading = false;
        }
    }

    appendData(data) {
        const container = document.getElementById(this.container);
        if (!container) return;

        data.forEach(item => {
            const element = this.createProductElement(item);
            container.appendChild(element);
        });
    }

    createProductElement(product) {
        const div = document.createElement('div');
        div.className = 'product-card';

        const name = API.getFieldValue(product, CONFIG.PRODUCT_FIELDS.NAME);
        const image = API.getFieldValue(product, CONFIG.PRODUCT_FIELDS.IMAGE);
        const price = API.getFieldValue(product, CONFIG.PRODUCT_FIELDS.PRICE);

        div.innerHTML = `
            <img src="${image}" alt="${name}">
            <h3>${name}</h3>
            <p class="price">¥${price}</p>
        `;

        return div;
    }

    reset() {
        this.currentPage = 0;
        this.hasMore = true;
        this.allData = [];
        document.getElementById(this.container).innerHTML = '';
    }
}

// 使用示例
const infiniteScroll = new InfiniteScroll({
    container: 'productsList',
    pageSize: 20,
    onDataLoad: (newData, allData) => {
        console.log(`已加载 ${allData.length} 条数据`);
    }
});

// 初始化加载
infiniteScroll.loadMore();
```

**示例 6: 带过滤的分页**

```javascript
// 分页 + 筛选 + 搜索
class FilterablePagination {
    constructor() {
        this.pagination = new PaginationManager({ pageSize: 20 });
        this.filters = {
            category: null,      // 分类筛选
            priceRange: null,    // 价格区间
            keyword: null        // 关键词搜索
        };
    }

    // 构建筛选条件
    buildFilter() {
        const conditions = [];

        // 必须是已上架的
        conditions.push({
            type: 'condition',
            field: CONFIG.PRODUCT_FIELDS.PUBLISHED,
            operator: 'eq',
            value: ['1']
        });

        // 分类筛选
        if (this.filters.category) {
            conditions.push({
                type: 'condition',
                field: CONFIG.PRODUCT_FIELDS.CATEGORY,
                operator: 'eq',
                value: [this.filters.category]
            });
        }

        // 价格区间筛选
        if (this.filters.priceRange) {
            conditions.push({
                type: 'condition',
                field: CONFIG.PRODUCT_FIELDS.PRICE,
                operator: 'between',
                value: this.filters.priceRange
            });
        }

        return {
            type: 'group',
            logic: 'AND',
            children: conditions
        };
    }

    // 应用筛选并重新加载
    async applyFilters(filters) {
        this.filters = { ...this.filters, ...filters };

        const result = await API.getRows(CONFIG.WORKSHEETS.PRODUCTS, {
            pageSize: this.pagination.pageSize,
            pageIndex: 1,  // 重新从第一页开始
            includeTotalCount: true,
            filter: this.buildFilter(),
            search: this.filters.keyword || '',
            sorts: [{
                field: CONFIG.PRODUCT_FIELDS.SORT,
                isAsc: true
            }]
        });

        this.pagination.data = result.rows || [];
        this.pagination.totalCount = result.total || 0;
        this.pagination.totalPages = Math.ceil(result.total / this.pagination.pageSize);
        this.pagination.currentPage = 1;

        return this.pagination.data;
    }

    // 切换分类
    async filterByCategory(category) {
        return await this.applyFilters({ category });
    }

    // 设置价格区间
    async filterByPrice(min, max) {
        return await this.applyFilters({
            priceRange: [String(min), String(max)]
        });
    }

    // 搜索
    async search(keyword) {
        return await this.applyFilters({ keyword });
    }

    // 清除筛选
    async clearFilters() {
        this.filters = {
            category: null,
            priceRange: null,
            keyword: null
        };
        return await this.applyFilters({});
    }
}

// 使用示例
const filterPager = new FilterablePagination();

// 按分类筛选
await filterPager.filterByCategory('沙发');

// 按价格筛选
await filterPager.filterByPrice(1000, 5000);

// 搜索
await filterPager.search('真皮');

// 清除筛选
await filterPager.clearFilters();
```

**性能优化建议:**

1. **合理设置 pageSize**
   - 移动端: 10-20 条
   - PC 端: 20-50 条
   - 不建议超过 100 条

2. **使用字段筛选**
   ```javascript
   fields: [
       CONFIG.PRODUCT_FIELDS.NAME,
       CONFIG.PRODUCT_FIELDS.IMAGE,
       CONFIG.PRODUCT_FIELDS.PRICE
   ]  // 只获取需要的字段
   ```

3. **启用数据缓存**
   ```javascript
   const cache = new Map();

   async function getCachedData(key, fetcher, ttl = 5 * 60 * 1000) {
       const cached = cache.get(key);
       if (cached && Date.now() - cached.timestamp < ttl) {
           return cached.data;
       }

       const data = await fetcher();
       cache.set(key, { data, timestamp: Date.now() });
       return data;
   }
   ```

4. **防抖处理搜索**
   ```javascript
   function debounce(fn, delay = 500) {
       let timer;
       return function(...args) {
           clearTimeout(timer);
           timer = setTimeout(() => fn.apply(this, args), delay);
       };
   }

   const debouncedSearch = debounce(async (keyword) => {
       const results = await filterPager.search(keyword);
       renderProducts(results);
   }, 500);
   ```

### 4.1 配置文件

创建 `js/config.js`：

```javascript
// HAP API 配置
const CONFIG = {
    // HAP 应用公开 API V3 基础 URL
    API_BASE_URL: 'https://api.mingdao.com',

    // HAP 应用认证信息（从 HAP 后台获取）
    HAP_APPKEY: '你的HAP_APPKEY',
    HAP_SIGN: '你的HAP_SIGN',

    // 工作表 ID（从 HAP 后台或 MCP 获取）
    WORKSHEETS: {
        PRODUCTS: '你的产品表ID',
        ORDERS: '你的订单表ID'
    },

    // 字段 ID 映射（从 HAP 后台或 MCP 获取）
    PRODUCT_FIELDS: {
        NAME: '产品名称字段ID',
        IMAGE: '产品图片字段ID',
        PRICE: '参考价格字段ID',
        DESC: '产品描述字段ID',
        PUBLISHED: '是否上架字段ID',
        RECOMMENDED: '是否推荐字段ID',
        SORT: '排序字段ID'
    }
};
```

---

### 4.2 API 使用规范

**重要提示：** 关于 HAP API V3 的详细使用方法，请参考：

📖 **[HAP-API-Usage-Guide.md](HAP-API-Usage-Guide.md)** - HAP API V3 完整使用指南

该文档包含：
- ✅ API 端点和鉴权配置
- ✅ 筛选器（Filter）语法详解
- ✅ 字段类型处理和数据格式转换
- ✅ 分页、排序、搜索的使用方法
- ✅ 完整的代码示例和最佳实践

**本指南重点：** 专注于如何将 HAP 作为数据库搭建独立网站的整体架构和设计原则。

---

## 5. 业务逻辑实现

### 5.1 数据加载与渲染
}
```

**示例 2：多条件筛选**

```javascript
// 筛选已上架且推荐的产品
filter: {
    type: 'group',
    logic: 'AND',
    children: [
        {
            type: 'condition',
            field: CONFIG.PRODUCT_FIELDS.PUBLISHED,
            operator: 'eq',
            value: ['1']
        },
        {
            type: 'condition',
            field: CONFIG.PRODUCT_FIELDS.RECOMMENDED,
            operator: 'eq',
            value: ['1']
        }
    ]
}
```

**示例 3：嵌套筛选**

```javascript
// 筛选已上架且（价格>1000 或 推荐）的产品
filter: {
    type: 'group',
    logic: 'AND',
    children: [
        {
            type: 'condition',
            field: CONFIG.PRODUCT_FIELDS.PUBLISHED,
            operator: 'eq',
            value: ['1']
        },
        {
            type: 'group',
            logic: 'OR',
            children: [
                {
                    type: 'condition',
                    field: CONFIG.PRODUCT_FIELDS.PRICE,
                    operator: 'gt',
                    value: ['1000']
                },
                {
                    type: 'condition',
                    field: CONFIG.PRODUCT_FIELDS.RECOMMENDED,
                    operator: 'eq',
                    value: ['1']
                }
            ]
        }
    ]
}
```

---

## 6. 数据渲染

### 6.1 主应用逻辑设计原则

**核心原则：** 清晰的应用架构和数据流管理

**应用初始化要求：**
- ✅ 页面加载完成后再初始化应用（DOMContentLoaded 事件）
- ✅ 显示加载状态，提升用户体验
- ✅ 异步加载数据，避免阻塞
- ✅ 完善的错误处理和用户提示
- ✅ 优雅降级（数据加载失败时的备选方案）

**数据渲染要求：**
- ✅ 动态生成 DOM，使用模板字符串或模板引擎
- ✅ 处理空数据状态（友好的提示信息）
- ✅ 图片加载失败时的占位图处理
- ✅ 数据格式化（价格、日期等）
- ✅ 响应式图片和内容布局
- ✅ 无障碍访问支持（alt 属性、语义化标签）

**状态管理要求：**
- ✅ 统一的加载状态管理
- ✅ 错误状态的友好展示
- ✅ 成功状态的反馈提示
- ✅ 避免全局变量污染
- ✅ 模块化和可维护性

### 6.2 表单提交

```javascript
// 在 App 对象中添加表单处理方法
setupForm() {
    const form = document.getElementById('orderForm');

    form.addEventListener('submit', async (e) => {
        e.preventDefault();

        const formData = {
            name: form.name.value,
            phone: form.phone.value,
            product: form.product.value
        };

        this.showLoading();

        try {
            await API.submitOrder(formData);
            alert('提交成功！我们会尽快联系您。');
            form.reset();
        } catch (error) {
            console.error('提交失败:', error);
            alert('提交失败，请稍后重试');
        } finally {
            this.hideLoading();
        }
    });
}
```

---

## 核心概念

### 1. 字段类型与值格式（重要）

#### 1.1 常见字段类型及其返回格式

| HAP 字段类型 | API 返回格式 | 解析方式 | 示例值 |
|-------------|------------|---------|-------|
| 文本 | 字符串 | 直接使用 | `"产品名称"` |
| 数值 | 数字 | 直接使用 | `1999.00` |
| 检查框 | 字符串 "1" 或 "0" | 转换为布尔值 | `"1"` |
| 单选 | 对象数组 | **提取 value** | `[{key: "xxx", value: "客厅"}]` |
| 多选 | 对象数组 | **提取所有 value** | `[{key: "1", value: "现代"}, {key: "2", value: "简约"}]` |
| 附件 | 对象数组 | **使用 downloadUrl** | `[{fileName: "图片.png", downloadUrl: "https://..."}]` |
| 日期 | 字符串 | 直接使用 | `"2024-01-01"` |
| 关联记录 | 对象数组 | 提取 name | `[{sid: "xxx", name: "关联项"}]` |

#### 1.2 重要提醒

**⚠️ 附件字段**
- HAP API V3 返回的附件字段包含 `downloadUrl` 而非 `url`
- 正确：`value[0].downloadUrl`
- 错误：~~`value[0].url`~~

```javascript
// ❌ 错误示例
if (value[0].url) {
    return value[0].url;  // 这会失败！
}

// ✅ 正确示例
if (value[0].downloadUrl) {
    return value[0].downloadUrl;  // 正确获取附件 URL
}
```

**⚠️ 选项字段（单选/多选）**
- 单选和多选字段返回的是 **对象数组**，每个对象包含 `key` 和 `value`
- 需要提取 `value` 属性才能显示正确的选项文本
- 正确：`value.map(item => item.value).join(', ')`
- 错误：~~`value.join(', ')`~~

```javascript
// 实际返回数据
{
    "示例控件ID": [
        {
            "key": "2eeadddf-8e90-44a0-a063-4182f1f8b969",
            "value": "美式风格"
        }
    ]
}

// ❌ 错误解析
const style = value.join(', ');
// 结果: "[object Object]"

// ✅ 正确解析
const style = value.map(item => item.value).join(', ');
// 结果: "美式风格"
```

#### 1.3 完整的字段值解析函数

参考上文 [js/api.js](#32-api-封装) 中的 `getFieldValue` 函数，它已经正确处理了所有字段类型。

### 2. 分页加载

```javascript
// 分页获取数据
async loadPage(pageIndex) {
    const data = await API.getRows(CONFIG.WORKSHEETS.PRODUCTS, {
        pageSize: 20,
        pageIndex: pageIndex,
        includeTotalCount: true  // 获取总数
    });

    console.log(`总记录数: ${data.total}`);
    console.log(`当前页数据: ${data.rows.length}`);

    return data;
}
```

### 3. 排序

```javascript
// 多字段排序
sorts: [
    {
        field: CONFIG.PRODUCT_FIELDS.SORT,
        isAsc: true  // 排序字段升序
    },
    {
        field: CONFIG.PRODUCT_FIELDS.PRICE,
        isAsc: false  // 价格降序
    }
]
```

### 4. 关键字搜索

```javascript
// 搜索产品名称包含"沙发"的记录
const data = await API.getRows(CONFIG.WORKSHEETS.PRODUCTS, {
    search: '沙发'  // 会在所有文本字段中搜索
});
```

---

## 最佳实践

### 1. 错误处理

```javascript
async loadData() {
    try {
        this.showLoading();
        const data = await API.getProducts();
        this.renderProducts(data);
    } catch (error) {
        console.error('加载失败:', error);

        // 友好的错误提示
        if (error.message.includes('401')) {
            alert('认证失败，请检查 API 密钥');
        } else if (error.message.includes('404')) {
            alert('未找到数据表，请检查工作表 ID');
        } else {
            alert('加载失败，请刷新页面重试');
        }
    } finally {
        this.hideLoading();
    }
}
```

### 2. 图片优化

```javascript
// 生成缩略图 URL（HAP 支持）
function getThumbnail(imageUrl, width = 300) {
    if (!imageUrl) return '';

    // HAP 图片服务支持参数
    return `${imageUrl}?imageView2/2/w/${width}`;
}
```

### 3. 数据缓存

```javascript
// 简单的内存缓存
const DataCache = {
    cache: {},
    ttl: 5 * 60 * 1000,  // 5分钟

    set(key, data) {
        this.cache[key] = {
            data,
            timestamp: Date.now()
        };
    },

    get(key) {
        const item = this.cache[key];
        if (!item) return null;

        // 检查是否过期
        if (Date.now() - item.timestamp > this.ttl) {
            delete this.cache[key];
            return null;
        }

        return item.data;
    }
};

// 使用缓存
async getProducts() {
    const cacheKey = 'products';
    const cached = DataCache.get(cacheKey);

    if (cached) {
        return cached;
    }

    const data = await API.getProducts();
    DataCache.set(cacheKey, data);

    return data;
}
```

### 4. 环境配置

```javascript
// config.js 中区分环境
const ENV = {
    development: {
        API_BASE_URL: 'https://api.mingdao.com',
        HAP_APPKEY: '开发环境的key',
        HAP_SIGN: '开发环境的sign'
    },
    production: {
        API_BASE_URL: 'https://api.mingdao.com',
        HAP_APPKEY: '生产环境的key',
        HAP_SIGN: '生产环境的sign'
    }
};

// 根据域名判断环境
const isDev = window.location.hostname === 'localhost';
const CONFIG = {
    ...(isDev ? ENV.development : ENV.production),
    WORKSHEETS: { /* ... */ }
};
```

### 5. 防抖与节流

```javascript
// 搜索框防抖
function debounce(func, wait) {
    let timeout;
    return function(...args) {
        clearTimeout(timeout);
        timeout = setTimeout(() => func.apply(this, args), wait);
    };
}

// 使用
const searchInput = document.getElementById('search');
searchInput.addEventListener('input', debounce(async (e) => {
    const keyword = e.target.value;
    const results = await API.getRows(CONFIG.WORKSHEETS.PRODUCTS, {
        search: keyword
    });
    renderProducts(results.rows);
}, 500));
```

---

## 常见问题

### Q1: CORS 跨域问题？

**A:** HAP API V3 已配置允许跨域，确保请求头包含正确的认证信息即可。如仍有问题，检查：
- 是否使用 HTTPS（本地开发可用 HTTP）
- 请求头是否包含 `HAP-Appkey` 和 `HAP-Sign`

### Q2: 如何调试 API 请求？

**A:**
```javascript
// 在 api.js 的 request 方法中添加日志
async request(url, options = {}) {
    console.log('请求URL:', url);
    console.log('请求参数:', options);

    const response = await fetch(url, options);
    const data = await response.json();

    console.log('响应数据:', data);

    return data;
}
```

或使用浏览器开发者工具的 Network 面板查看请求详情。

### Q3: 字段 ID 如何获取？

**A:** 三种方式：
1. **MCP Server**（推荐）：
   ```javascript
   mcp__hap_mcp_API____get_worksheet_structure({
       worksheet_id: '工作表ID',
       responseFormat: 'md'
   })
   ```

2. **API 查询**：
   ```javascript
   // 通过浏览器控制台调用
   fetch('https://api.mingdao.com/v3/app/worksheets/{worksheetId}/structure', {
       headers: {
           'HAP-Appkey': 'xxx',
           'HAP-Sign': 'xxx'
       }
   }).then(r => r.json()).then(console.log)
   ```

3. **浏览器审查元素**：
   - 打开 HAP 工作表
   - 右键检查元素
   - 查找 `data-controlid` 属性

### Q4: 如何处理附件上传？

**A:** HAP API V3 目前不支持直接通过 API 上传附件。解决方案：
- 方案 1：在 HAP 后台手动上传
- 方案 2：使用第三方图床（如七牛云、阿里云 OSS），在 HAP 中存储图片 URL
- 方案 3：使用 HAP 工作流结合第三方服务

### Q5: 数据量大时如何优化性能？

**A:**
1. **分页加载**: 设置合理的 pageSize（建议 20-50）
2. **字段筛选**: 只获取需要的字段
   ```javascript
   fields: [CONFIG.PRODUCT_FIELDS.NAME, CONFIG.PRODUCT_FIELDS.IMAGE]
   ```
3. **视图优化**: 在 HAP 中创建视图，通过 `viewId` 参数使用
4. **前端缓存**: 使用 localStorage 或内存缓存
5. **懒加载**: 滚动到底部时加载更多

### Q6: 如何保护 API 密钥安全？

**A:**
- **开发环境**: 可直接使用（localhost 不会泄露）
- **生产环境**:
  - 方案 1：使用后端代理（Node.js、PHP 等）
  - 方案 2：使用 Cloudflare Workers / Vercel Serverless Functions
  - 方案 3：限制 HAP API 密钥权限（只读权限）

示例（Vercel Serverless Function）：
```javascript
// api/hap.js
export default async function handler(req, res) {
    const response = await fetch('https://api.mingdao.com/v3/...', {
        headers: {
            'HAP-Appkey': process.env.HAP_APPKEY,  // 存储在环境变量
            'HAP-Sign': process.env.HAP_SIGN
        },
        body: JSON.stringify(req.body)
    });

    const data = await response.json();
    res.json(data);
}
```

### Q7: 复选框字段如何处理？

**A:** 复选框字段返回字符串 `"1"` (选中) 或 `"0"` (未选中)：

```javascript
const isPublished = API.getFieldValue(product, CONFIG.PRODUCT_FIELDS.PUBLISHED);

// 判断是否选中
if (isPublished === '1') {
    console.log('已上架');
}

// 或转换为布尔值
const published = isPublished === '1';
```

### Q8: 如何实现实时更新？

**A:** HAP API V3 不支持 WebSocket，可使用轮询：

```javascript
// 每 30 秒刷新一次数据
setInterval(async () => {
    const data = await API.getProducts();
    this.renderProducts(data.rows);
}, 30000);
```

或使用 HAP 工作流触发 Webhook 通知前端刷新。

---

## HAP 特殊字段使用规范

### 概述

HAP API V3 返回的字段值格式因字段类型而异。正确解析这些字段值是前端开发的关键。本章节详细说明所有特殊字段类型的使用规范。

---

### 1. 附件字段（Attachment）

#### 1.1 字段特征
- **字段类型 ID**: `14`
- **返回格式**: 对象数组
- **关键属性**: `downloadUrl`, `fileName`, `fileSize`, `fileExt`

#### 1.2 数据结构

```javascript
// API 返回的附件字段数据
{
    "fieldId": [
        {
            "fileName": "产品图片.png",
            "downloadUrl": "https://p1.mingdaoyun.cn/.../image.png",
            "fileSize": 245678,
            "fileExt": ".png"
        },
        {
            "fileName": "说明文档.pdf",
            "downloadUrl": "https://p1.mingdaoyun.cn/.../doc.pdf",
            "fileSize": 1024567,
            "fileExt": ".pdf"
        }
    ]
}
```

#### 1.3 解析方法

```javascript
// ✅ 正确：使用 downloadUrl
const getAttachmentUrl = (row, fieldId) => {
    const attachments = row[fieldId];
    if (!Array.isArray(attachments) || attachments.length === 0) {
        return '';
    }
    return attachments[0].downloadUrl;  // 获取第一个附件的下载链接
};

// 获取所有附件
const getAllAttachments = (row, fieldId) => {
    const attachments = row[fieldId];
    if (!Array.isArray(attachments)) return [];

    return attachments.map(file => ({
        url: file.downloadUrl,
        name: file.fileName,
        size: file.fileSize,
        ext: file.fileExt
    }));
};

// ❌ 错误：使用 url（旧版本字段名）
const wrongUrl = attachments[0].url;  // undefined!
```

#### 1.4 图片优化

HAP 支持图片 CDN 参数，可对图片进行裁剪、压缩：

```javascript
// 生成缩略图
const getThumbnail = (imageUrl, width = 300) => {
    if (!imageUrl) return '';
    return `${imageUrl}?imageView2/2/w/${width}/q/90`;
};

// 使用示例
const originalUrl = attachments[0].downloadUrl;
const thumbnail = getThumbnail(originalUrl, 200);  // 200px 宽度缩略图

// 常用参数
// ?imageView2/2/w/300        - 宽度 300px
// ?imageView2/2/w/300/q/90   - 宽度 300px，质量 90%
// ?imageView2/1/w/300/h/200  - 固定宽高 300x200
```

#### 1.5 完整示例

```javascript
// 在产品卡片中展示图片
const renderProductCard = (product) => {
    const image = API.getFieldValue(product, CONFIG.PRODUCT_FIELDS.IMAGE);
    const thumbnail = image ? `${image}?imageView2/2/w/280/q/85` : 'placeholder.png';

    return `
        <div class="product-card">
            <img src="${thumbnail}"
                 alt="产品图片"
                 onerror="this.src='placeholder.png'">
        </div>
    `;
};
```

---

### 2. 选项字段（Single/Multiple Select）

#### 2.1 字段特征
- **单选字段类型 ID**: `11`
- **多选字段类型 ID**: `10`
- **返回格式**: 对象数组
- **关键属性**: `key`, `value`

#### 2.2 数据结构

```javascript
// 单选字段返回数据
{
    "styleField": [
        {
            "key": "2eeadddf-8e90-44a0-a063-4182f1f8b969",
            "value": "美式风格"
        }
    ]
}

// 多选字段返回数据
{
    "tagsField": [
        {
            "key": "key-1",
            "value": "现代"
        },
        {
            "key": "key-2",
            "value": "简约"
        },
        {
            "key": "key-3",
            "value": "时尚"
        }
    ]
}
```

#### 2.3 解析方法

```javascript
// ✅ 正确：提取 value 属性
const getSingleSelectValue = (row, fieldId) => {
    const options = row[fieldId];
    if (!Array.isArray(options) || options.length === 0) {
        return '';
    }
    return options[0].value;  // 单选只取第一个
};

const getMultiSelectValue = (row, fieldId) => {
    const options = row[fieldId];
    if (!Array.isArray(options) || options.length === 0) {
        return '';
    }
    return options.map(opt => opt.value).join(', ');  // 多选用逗号连接
};

// ❌ 错误：直接 join 数组
const wrongValue = options.join(', ');
// 结果: "[object Object], [object Object]"
```

#### 2.4 筛选查询

> ## 🔴 重要警告：SingleSelect/MultipleSelect 筛选必须使用 key（UUID），绝不能使用显示文本！
>
> **这是 AI 最容易犯的错误之一！**
>
> - ❌ **错误做法**：使用显示文本筛选 `value: ['现代简约']` → 筛选失败
> - ✅ **正确做法**：使用选项 key 筛选 `value: ['uuid-xxxx-xxxx']` → 筛选成功
> - ⚠️ **后果**：使用显示文本会导致筛选功能完全失效，用户无法按分类/标签筛选数据

在筛选查询中，需要使用选项的 `key` 值（UUID），而不是显示文本：

```javascript
// ❌ 错误：使用显示文本进行筛选（最常见的错误！）
const wrongFilter = async () => {
    const data = await API.getRows(CONFIG.WORKSHEETS.PRODUCTS, {
        filter: {
            type: 'group',
            logic: 'AND',
            children: [{
                type: 'condition',
                field: CONFIG.PRODUCT_FIELDS.STYLE,
                operator: 'eq',
                value: ['现代简约']  // ❌ 这是显示文本，不是 key！筛选会失败！
            }]
        }
    });
    return data.rows;  // 返回空数据或全部数据
};

// ✅ 正确：使用选项 key 进行筛选
const filterByStyle = async (styleKey) => {
    const data = await API.getRows(CONFIG.WORKSHEETS.PRODUCTS, {
        filter: {
            type: 'group',
            logic: 'AND',
            children: [{
                type: 'condition',
                field: CONFIG.PRODUCT_FIELDS.STYLE,
                operator: 'eq',
                value: [styleKey]  // ✅ 使用 key（UUID）而非 value（显示文本）
            }]
        }
    });
    return data.rows;
};

// 如何获取选项的 key？需要先获取工作表结构
const getStyleOptionKey = async (styleName) => {
    // 1. 获取工作表结构
    const structure = await mcp__hap_mcp____get_worksheet_structure({
        worksheet_id: CONFIG.WORKSHEETS.PRODUCTS,
        ai_description: '工作表: 产品表'
    });

    // 2. 找到风格字段
    const styleField = structure.fields.find(f => f.id === CONFIG.PRODUCT_FIELDS.STYLE);

    // 3. 在 options 中查找匹配的选项，返回 key
    const option = styleField.options.find(opt => opt.value === styleName);
    return option ? option.key : null;
};

// 完整的使用流程
const filterByStyleName = async (styleName) => {
    // 先获取 key
    const styleKey = await getStyleOptionKey(styleName);
    if (!styleKey) {
        console.error(`未找到风格选项：${styleName}`);
        return [];
    }

    // 再用 key 进行筛选
    return await filterByStyle(styleKey);
};

// 使用示例
const modernProducts = await filterByStyleName('现代简约');
```

**🔴 关键原则总结：**

| 场景 | 使用什么 | 示例 |
|------|---------|------|
| **显示选项文本** | `option.value` | "现代简约" |
| **筛选查询条件** | `option.key` | "a1b2c3d4-e5f6-7890-abcd-ef1234567890" |
| **创建/更新记录** | `option.value` 数组 | `["现代简约", "北欧风格"]` |
| **获取选项列表** | `get_worksheet_structure` | 返回 `{key, value}` 对象 |

**⚠️ 常见错误后果：**
- 使用显示文本筛选 → 筛选失败，返回空数据或全部数据
- 用户点击分类按钮 → 页面无反应或显示错误数据
- 多选筛选 → 完全失效

#### 2.5 完整示例

```javascript
// 显示产品风格
const renderProductStyle = (product) => {
    const style = API.getFieldValue(product, CONFIG.PRODUCT_FIELDS.STYLE);
    // 结果: "美式风格" (而不是 "[object Object]")

    return `<span class="style-tag">${style}</span>`;
};

// 显示产品标签（多选）
const renderProductTags = (product) => {
    const tags = API.getFieldValue(product, CONFIG.PRODUCT_FIELDS.TAGS);
    // 结果: "现代, 简约, 时尚"

    return tags.split(', ').map(tag =>
        `<span class="tag">${tag}</span>`
    ).join('');
};
```

---

### 3. 关联记录字段（Relation）

#### 3.1 字段特征
- **字段类型 ID**: `29`
- **返回格式**: 对象数组
- **关键属性**: `sid`, `name`, 其他字段

#### 3.2 数据结构

```javascript
// 关联记录字段返回数据（实际示例）
{
    "示例控件ID": [
        {
            "sid": "9dd9272b-e7e5-40d5-8a6d-d2403d1e45c2",  // 关联记录的 ID
            "name": "实木衣柜"  // 关联记录的标题字段值
        }
    ]
}

// 多个关联记录
{
    "categoryField": [
        {
            "sid": "示例行ID1",
            "name": "客厅家具"
        },
        {
            "sid": "示例行ID2",
            "name": "卧室家具"
        }
    ]
}
```

**重要说明:**
- `sid`: 关联记录的唯一标识符（记录 ID）
- `name`: 关联记录的标题字段值
- 如果需要展示关联表的详细信息，需要：
  1. 找到该字段关联的工作表 ID
  2. 使用 `sid` 去查询对应的完整记录数据

#### 3.3 解析方法

```javascript
// ✅ 正确：获取关联记录名称（基础用法）
const getRelationName = (row, fieldId) => {
    const relations = row[fieldId];
    if (!Array.isArray(relations) || relations.length === 0) {
        return '';
    }
    return relations.map(rel => rel.name).join(', ');
};

// 使用示例
const productCategory = getRelationName(product, CONFIG.PRODUCT_FIELDS.CATEGORY);
// 结果: "实木衣柜" 或 "客厅家具, 卧室家具"

// 获取关联记录 ID（用于进一步查询）
const getRelationIds = (row, fieldId) => {
    const relations = row[fieldId];
    if (!Array.isArray(relations)) return [];
    return relations.map(rel => rel.sid);
};

// 使用示例
const relatedIds = getRelationIds(product, CONFIG.PRODUCT_FIELDS.CATEGORY);
// 结果: ["9dd9272b-e7e5-40d5-8a6d-d2403d1e45c2"]
```

#### 3.4 深度查询关联记录

如果需要显示关联记录的更多字段信息（不仅仅是 name），需要进行深度查询：

```javascript
// 方法 1: 通过记录 ID 查询完整信息
const getRelatedRecordDetails = async (relatedIds, relatedWorksheetId) => {
    // 使用关联记录的 sid 查询完整数据
    const data = await API.getRows(relatedWorksheetId, {
        filter: {
            type: 'group',
            logic: 'AND',
            children: [{
                type: 'condition',
                field: 'rowid',  // 系统字段 rowid
                operator: 'in',
                value: relatedIds  // 传入 sid 数组
            }]
        }
    });
    return data.rows;
};

// 使用示例：查询产品的完整分类信息
const product = /* 从 API 获取的产品数据 */;
const categoryIds = getRelationIds(product, CONFIG.PRODUCT_FIELDS.CATEGORY);

// 假设分类表 ID 是 CONFIG.WORKSHEETS.CATEGORIES
const categoryDetails = await getRelatedRecordDetails(
    categoryIds,
    CONFIG.WORKSHEETS.CATEGORIES
);

console.log(categoryDetails);
// [
//     {
//         rowid: "9dd9272b-e7e5-40d5-8a6d-d2403d1e45c2",
//         name: "实木衣柜",
//         description: "高品质实木材质",
//         image: "https://...",
//         sort: 1
//     }
// ]
```

#### 3.5 关联记录字段筛选

在筛选查询中使用关联记录：

```javascript
// 筛选指定分类的产品
const filterByCategory = async (categoryId) => {
    const data = await API.getRows(CONFIG.WORKSHEETS.PRODUCTS, {
        filter: {
            type: 'group',
            logic: 'AND',
            children: [{
                type: 'condition',
                field: CONFIG.PRODUCT_FIELDS.CATEGORY,
                operator: 'contains',  // 关联字段用 contains
                value: [categoryId]  // 传入关联记录的 sid
            }]
        }
    });
    return data.rows;
};

// 使用示例
const furnitureProducts = await filterByCategory('9dd9272b-e7e5-40d5-8a6d-d2403d1e45c2');
```

---

### 4. 日期时间字段（Date/DateTime/Time）

#### 4.1 字段特征
- **日期字段类型 ID**: `15`
- **日期时间字段类型 ID**: `16`
- **时间字段类型 ID**: `46`
- **返回格式**: 字符串或数字（时间戳）

#### 4.2 数据格式

```javascript
// 日期字段
"2024-12-01"

// 日期时间字段
"2024-12-01 14:30:00"

// 时间字段
"14:30"

// 有时返回时间戳（毫秒）
1733049600000
```

#### 4.3 解析方法

```javascript
// 格式化日期
const formatDate = (dateValue) => {
    if (!dateValue) return '';

    // 如果是时间戳
    if (typeof dateValue === 'number') {
        const date = new Date(dateValue);
        return date.toLocaleDateString('zh-CN');
    }

    // 如果是字符串，直接返回或格式化
    return dateValue.split(' ')[0];  // 只取日期部分
};

// 格式化日期时间
const formatDateTime = (dateTimeValue) => {
    if (!dateTimeValue) return '';

    if (typeof dateTimeValue === 'number') {
        const date = new Date(dateTimeValue);
        return date.toLocaleString('zh-CN');
    }

    return dateTimeValue;
};

// 相对时间（如：3天前）
const getRelativeTime = (dateValue) => {
    const date = typeof dateValue === 'number'
        ? new Date(dateValue)
        : new Date(dateValue);

    const now = new Date();
    const diff = now - date;
    const days = Math.floor(diff / (1000 * 60 * 60 * 24));

    if (days === 0) return '今天';
    if (days === 1) return '昨天';
    if (days < 7) return `${days}天前`;
    if (days < 30) return `${Math.floor(days / 7)}周前`;
    return date.toLocaleDateString('zh-CN');
};
```

---

### 5. 成员字段（Collaborator）

#### 5.1 字段特征
- **字段类型 ID**: `26`
- **返回格式**: 对象数组
- **关键属性**: `accountId`, `fullname`, `avatar`

#### 5.2 数据结构

```javascript
{
    "assigneeField": [
        {
            "accountId": "user-id-123",
            "fullname": "张三",
            "avatar": "https://avatars.mingdao.com/xxx.jpg"
        }
    ]
}
```

#### 5.3 解析方法

```javascript
// 获取成员姓名
const getCollaboratorNames = (row, fieldId) => {
    const collaborators = row[fieldId];
    if (!Array.isArray(collaborators)) return '';
    return collaborators.map(user => user.fullname).join(', ');
};

// 渲染成员头像
const renderCollaborators = (row, fieldId) => {
    const collaborators = row[fieldId];
    if (!Array.isArray(collaborators)) return '';

    return collaborators.map(user => `
        <div class="user-avatar" title="${user.fullname}">
            <img src="${user.avatar}" alt="${user.fullname}">
        </div>
    `).join('');
};
```

---

### 6. 检查框字段（Checkbox）

#### 6.1 字段特征
- **字段类型 ID**: `36`
- **返回格式**: 字符串 `"1"` 或 `"0"`

#### 6.2 解析方法

```javascript
// 转换为布尔值
const isChecked = (row, fieldId) => {
    return row[fieldId] === '1';
};

// 使用示例
const published = isChecked(product, CONFIG.PRODUCT_FIELDS.PUBLISHED);
if (published) {
    console.log('产品已上架');
}

// 在筛选中使用
filter: {
    type: 'condition',
    field: CONFIG.PRODUCT_FIELDS.PUBLISHED,
    operator: 'eq',
    value: ['1']  // 选中
}
```

---

### 7. 地区字段（Region）

#### 7.1 字段特征
- **字段类型 ID**: `19`
- **返回格式**: 字符串（地区编码）或对象

#### 7.2 数据格式

```javascript
// 返回地区编码
"310100"  // 上海市

// 或返回对象
{
    "code": "310100",
    "name": "上海市/市辖区"
}
```

#### 7.3 解析方法

```javascript
// 获取地区名称
const getRegionName = (row, fieldId) => {
    const region = row[fieldId];
    if (!region) return '';

    if (typeof region === 'object') {
        return region.name;
    }

    // 如果只返回编码，需要查询地区信息
    return region;
};
```

---

### 8. 子表字段（SubTable）

#### 8.1 字段特征
- **字段类型 ID**: `34`
- **返回格式**: 对象数组
- **包含**: 子表的多行记录数据

#### 8.2 数据结构

```javascript
{
    "itemsField": [
        {
            "rowid": "sub-row-1",
            "subField1": "值1",
            "subField2": "值2"
        },
        {
            "rowid": "sub-row-2",
            "subField1": "值3",
            "subField2": "值4"
        }
    ]
}
```

#### 8.3 解析方法

```javascript
// 获取子表数据
const getSubTableData = (row, fieldId) => {
    const subRows = row[fieldId];
    if (!Array.isArray(subRows)) return [];
    return subRows;
};

// 渲染子表
const renderSubTable = (row, fieldId, subFieldConfig) => {
    const subRows = getSubTableData(row, fieldId);

    return `
        <table class="sub-table">
            <thead>
                <tr>
                    ${Object.keys(subFieldConfig).map(key =>
                        `<th>${subFieldConfig[key].label}</th>`
                    ).join('')}
                </tr>
            </thead>
            <tbody>
                ${subRows.map(subRow => `
                    <tr>
                        ${Object.keys(subFieldConfig).map(key => `
                            <td>${subRow[subFieldConfig[key].fieldId] || ''}</td>
                        `).join('')}
                    </tr>
                `).join('')}
            </tbody>
        </table>
    `;
};
```

---

### 9. 完整的通用解析函数

综合以上所有字段类型，这是一个完整的通用解析函数：

```javascript
/**
 * 通用字段值解析函数
 * 支持所有 HAP 字段类型
 */
const getFieldValue = (row, fieldId, options = {}) => {
    if (!row || !fieldId) return '';

    const value = row[fieldId];
    if (value === undefined || value === null) return '';

    // 1. 基本类型：字符串、数字、布尔值
    if (typeof value === 'string' || typeof value === 'number' || typeof value === 'boolean') {
        return value;
    }

    // 2. 数组类型
    if (Array.isArray(value)) {
        if (value.length === 0) return '';

        const firstItem = value[0];
        if (typeof firstItem !== 'object') {
            return value.join(', ');
        }

        // 2.1 附件字段：优先使用 downloadUrl
        if (firstItem.downloadUrl) {
            const url = firstItem.downloadUrl;
            // 如果指定了图片宽度，添加 CDN 参数
            if (options.imageWidth) {
                return `${url}?imageView2/2/w/${options.imageWidth}/q/${options.imageQuality || 90}`;
            }
            return url;
        }

        // 2.2 旧版附件字段：使用 url
        if (firstItem.url) {
            return firstItem.url;
        }

        // 2.3 选项字段：提取 value
        if (firstItem.value !== undefined) {
            const values = value.map(item => item.value);
            return options.separator ? values.join(options.separator) : values.join(', ');
        }

        // 2.4 关联记录/成员字段：提取 name
        if (firstItem.name || firstItem.fullname) {
            const names = value.map(item => item.name || item.fullname);
            return names.join(', ');
        }

        // 2.5 其他数组
        return value.join(', ');
    }

    // 3. 对象类型
    if (typeof value === 'object') {
        // 地区字段
        if (value.name) return value.name;
        // 选项字段（单个对象）
        if (value.value !== undefined) return value.value;
    }

    return String(value);
};

// 使用示例
const image = getFieldValue(product, CONFIG.PRODUCT_FIELDS.IMAGE, {
    imageWidth: 300,
    imageQuality: 85
});

const tags = getFieldValue(product, CONFIG.PRODUCT_FIELDS.TAGS, {
    separator: ' | '
});
// 结果: "现代 | 简约 | 时尚"
```

---

### 10. 最佳实践建议

#### 10.1 统一封装

建议在 `api.js` 中统一封装字段解析逻辑：

```javascript
// js/api.js
const API = {
    // ... 其他方法

    // 通用字段值获取
    getFieldValue: getFieldValue,  // 使用上面的完整函数

    // 特定类型快捷方法
    getImageUrl: (row, fieldId, width = 300) => {
        return getFieldValue(row, fieldId, { imageWidth: width });
    },

    getSelectValue: (row, fieldId) => {
        return getFieldValue(row, fieldId);
    },

    isChecked: (row, fieldId) => {
        return row[fieldId] === '1';
    }
};
```

#### 10.2 类型安全

在 TypeScript 项目中，建议定义字段类型：

```typescript
interface AttachmentField {
    fileName: string;
    downloadUrl: string;
    fileSize: number;
    fileExt: string;
}

interface SelectOption {
    key: string;
    value: string;
}

interface RelationRecord {
    sid: string;
    name: string;
    [key: string]: any;
}

type FieldValue =
    | string
    | number
    | boolean
    | AttachmentField[]
    | SelectOption[]
    | RelationRecord[];
```

#### 10.3 错误处理

```javascript
// 安全的字段值获取
const safeGetFieldValue = (row, fieldId, defaultValue = '') => {
    try {
        return getFieldValue(row, fieldId) || defaultValue;
    } catch (error) {
        console.error(`解析字段 ${fieldId} 失败:`, error);
        return defaultValue;
    }
};
```

#### 10.4 性能优化

```javascript
// 批量解析字段（避免重复调用）
const parseRecord = (row, fieldConfig) => {
    const result = {};
    for (const [key, fieldId] of Object.entries(fieldConfig)) {
        result[key] = getFieldValue(row, fieldId);
    }
    return result;
};

// 使用示例
const productData = parseRecord(product, {
    name: CONFIG.PRODUCT_FIELDS.NAME,
    image: CONFIG.PRODUCT_FIELDS.IMAGE,
    price: CONFIG.PRODUCT_FIELDS.PRICE,
    category: CONFIG.PRODUCT_FIELDS.CATEGORY
});

console.log(productData);
// {
//     name: "实木沙发",
//     image: "https://...",
//     price: 5999,
//     category: "客厅家具"
// }
```

---

### 11. 常见问题排查

#### 问题 1: 图片不显示

```javascript
// ❌ 错误
const image = row[fieldId][0].url;  // url 不存在

// ✅ 正确
const image = row[fieldId][0].downloadUrl;
```

#### 问题 2: 选项显示 [object Object]

```javascript
// ❌ 错误
const category = row[fieldId].join(', ');

// ✅ 正确
const category = row[fieldId].map(opt => opt.value).join(', ');
```

#### 问题 3: 检查框判断错误

```javascript
// ❌ 错误（字符串 "0" 在 JS 中是 truthy）
if (row[fieldId]) { ... }

// ✅ 正确
if (row[fieldId] === '1') { ... }
```

#### 问题 4: 日期格式不统一

```javascript
// ✅ 统一处理
const formatDate = (value) => {
    if (typeof value === 'number') {
        return new Date(value).toLocaleDateString('zh-CN');
    }
    return value.split(' ')[0];  // 去除时间部分
};
```

---

### 12. 字段类型速查表

| 字段类型 | Type ID | 返回格式 | 关键属性 | 解析方式 |
|---------|---------|---------|---------|---------|
| 文本 | 2 | String | - | 直接使用 |
| 数值 | 6 | Number | - | 直接使用 |
| 金额 | 8 | Number | - | 直接使用 |
| 检查框 | 36 | String | - | `=== '1'` |
| 单选 | 11 | Array | `key`, `value` | `[0].value` |
| 多选 | 10 | Array | `key`, `value` | `map(v).join()` |
| 附件 | 14 | Array | `downloadUrl`, `fileName` | `[0].downloadUrl` |
| 日期 | 15 | String/Number | - | 格式化 |
| 日期时间 | 16 | String/Number | - | 格式化 |
| 时间 | 46 | String | - | 直接使用 |
| 关联记录 | 29 | Array | `sid`, `name` | `map(r.name)` |
| 成员 | 26 | Array | `accountId`, `fullname` | `map(u.fullname)` |
| 部门 | 27 | Array | `departmentId`, `departmentName` | `map(d.name)` |
| 地区 | 19 | String/Object | `code`, `name` | `.name` 或直接用 |
| 子表 | 34 | Array | 子表字段 | 遍历子行 |

---

## 总结

通过本指南，您已经掌握了：

1. ✅ HAP 后台数据表设计
2. ✅ 获取 API 凭证和字段 ID
3. ✅ 前端项目结构搭建
4. ✅ HAP API V3 集成与调用
5. ✅ 数据筛选、排序、分页
6. ✅ 表单数据提交
7. ✅ 项目部署上线

**核心要点：**
- 使用官方 HAP API V3 端点（`/v3/app/worksheets/{worksheet_id}/rows/list`）
- 正确配置筛选器结构（type、logic、children、operator、value）
- 使用字段 ID（而非字段名）进行数据操作
- 处理不同字段类型的返回值格式
- 添加错误处理和加载状态

**下一步：**
- 查看 [HAP 官方文档](https://api.mingdao.com/docs)
- 参考示例项目进行定制开发
- 加入明道云社区交流经验

---

## 附录

### A. 字段类型对照表

| 字段类型 | type 值 | 说明 |
|---------|--------|------|
| 文本 | 2 | 单行文本 |
| 文本 | 41 | 多行文本 |
| 数值 | 6 | 数字 |
| 金额 | 8 | 货币 |
| 日期 | 15 | 日期 |
| 日期时间 | 16 | 日期+时间 |
| 单选 | 11 | 单选下拉 |
| 多选 | 10 | 多选下拉 |
| 检查框 | 36 | 复选框 |
| 附件 | 14 | 文件/图片 |
| 关联记录 | 29 | 关联其他表 |
| 人员 | 26 | 协作者 |
| 部门 | 27 | 部门 |

### B. 常用过滤器示例

```javascript
// 1. 文本包含
{
    type: 'condition',
    field: 'fieldId',
    operator: 'contains',
    value: ['关键词']
}

// 2. 数值范围
{
    type: 'condition',
    field: 'fieldId',
    operator: 'between',
    value: ['1000', '5000']
}

// 3. 日期范围
{
    type: 'condition',
    field: 'fieldId',
    operator: 'between',
    value: ['2024-01-01', '2024-12-31']
}

// 4. 多选包含某项
{
    type: 'condition',
    field: 'fieldId',
    operator: 'contains',
    value: ['选项1']
}

// 5. 字段不为空
{
    type: 'condition',
    field: 'fieldId',
    operator: 'isnotempty',
    value: []  // 空数组
}
```

### C. 参考链接

- [HAP 官方网站](https://www.mingdao.com)
- [HAP API 文档](https://api.mingdao.com/docs)
- [明道云帮助中心](https://help.mingdao.com)
- [明道云社区](https://bbs.mingdao.com)

---

## 总结与反思

### 核心价值

通过本指南,我们实现了一个**前后端完全分离**的开发模式:

**前端侧:**
- ✅ 纯静态页面,可部署到任何静态托管平台(Vercel、GitHub Pages、Netlify)
- ✅ 零后端开发成本,专注于用户体验和界面设计
- ✅ 直接调用 HAP API,无需编写服务端代码

**后端侧:**
- ✅ 使用 HAP 零代码/低代码平台管理数据
- ✅ 可视化设计数据表结构,业务人员也能操作
- ✅ 实时更新数据,无需重新部署前端

### 关键技术要点

#### 1. CORS 跨域请求

HAP API V3 原生支持 CORS,前端可直接调用:

```javascript
// 核心配置
headers: {
    'HAP-Appkey': 'your_appkey',
    'HAP-Sign': 'your_sign',
    'Content-Type': 'application/json'
}
```

**要点总结:**
- ✅ 无需配置代理或后端中转
- ✅ 使用 fetch API 即可直接调用
- ⚠️ 生产环境建议使用后端代理保护密钥

#### 2. 分页逻辑实现

提供三种分页模式,适应不同场景:

| 分页模式 | 适用场景 | 用户体验 |
|---------|---------|---------|
| 传统分页 | 数据量大,需精确翻页 | 经典,可控性强 |
| 无限滚动 | 移动端、瀑布流展示 | 流畅,适合浏览 |
| 带筛选分页 | 需要多条件查询 | 灵活,查询精准 |

**性能优化建议:**
- 移动端: pageSize = 10-20
- PC 端: pageSize = 20-50
- 启用字段筛选,只获取必要字段
- 使用数据缓存减少重复请求
- 搜索框使用防抖(debounce)处理

#### 3. 筛选器(Filter)设计

HAP 使用嵌套结构的筛选器:

```javascript
// 基础结构
filter: {
    type: 'group',      // 组
    logic: 'AND',       // 逻辑关系
    children: [         // 子条件
        {
            type: 'condition',
            field: '字段ID',
            operator: 'eq',
            value: ['值']
        }
    ]
}
```

**设计原则:**
- 最多两层嵌套(group → group → condition)
- 同一组内的 children 类型必须一致
- 合理使用 AND/OR 逻辑组合

### 最佳实践总结

#### 1. 项目结构

```
my-website/
├── index.html          # 主页面
├── css/
│   └── style.css       # 样式文件
├── js/
│   ├── config.js       # HAP 配置(Appkey、Sign、字段映射)
│   ├── api.js          # API 封装(请求、分页、筛选)
│   └── main.js         # 应用逻辑(渲染、事件处理)
└── images/             # 图片资源
```

**关键原则:**
- 配置与逻辑分离
- API 层统一封装
- 使用 ES6+ 语法提升代码可读性

#### 2. 错误处理

```javascript
// 完善的错误处理机制
try {
    const data = await API.getProducts();
    renderProducts(data);
} catch (error) {
    // 认证错误
    if (error.message.includes('401')) {
        alert('API 密钥错误,请检查配置');
    }
    // 网络错误
    else if (error.message.includes('Network')) {
        alert('网络连接失败,请检查网络');
    }
    // 其他错误
    else {
        alert('加载失败,请刷新重试');
    }
}
```

#### 3. 用户体验优化

- **加载动画**: 数据请求时显示 loading 状态
- **错误提示**: 友好的错误消息,避免技术术语
- **图片优化**: 使用 HAP CDN 参数压缩图片
- **响应式设计**: 适配移动端和 PC 端
- **防抖节流**: 搜索、滚动等高频操作优化

#### 4. 安全性考虑

**开发环境:**
```javascript
// 可直接在前端配置
HAP_APPKEY: 'dev_key',
HAP_SIGN: 'dev_sign'
```

**生产环境(推荐):**
```javascript
// 方案 1: 使用后端代理
// 前端 → 自己的后端 → HAP API
// 密钥存储在服务器环境变量

// 方案 2: Serverless Functions (Vercel/Netlify)
// api/hap.js
export default async function(req, res) {
    const response = await fetch('https://api.mingdao.com/v3/...', {
        headers: {
            'HAP-Appkey': process.env.HAP_APPKEY,
            'HAP-Sign': process.env.HAP_SIGN
        }
    });
    res.json(await response.json());
}
```

**方案 3: 只读权限**
- 在 HAP 后台创建只读 API 密钥
- 即使泄露也只能读取数据,无法修改

### 常见问题与解决方案

#### Q1: 如何获取字段 ID?

**方法 1: 使用 MCP Server**
```javascript
mcp__hap_mcp_API____get_worksheet_structure({
    worksheet_id: '工作表ID',
    responseFormat: 'md',
    ai_description: '获取工作表结构'
})
```

**方法 2: API 查询**
```javascript
fetch('https://api.mingdao.com/v3/app/worksheets/{worksheetId}/structure', {
    headers: {
        'HAP-Appkey': 'xxx',
        'HAP-Sign': 'xxx'
    }
})
```

**方法 3: 浏览器审查元素**
- 打开 HAP 工作表
- F12 检查元素
- 查找 `data-controlid` 属性

#### Q2: 如何处理附件字段?

```javascript
// 附件字段返回格式
const attachments = row[fieldId]; // Array
// [{url: 'https://...', name: '图片.jpg', size: 12345}]

// 获取第一个附件 URL
const imageUrl = attachments[0]?.url || '';

// 使用 HAP CDN 参数优化
const thumbnailUrl = `${imageUrl}?imageView2/2/w/300`;
```

#### Q3: 数据实时更新怎么做?

**方案 1: 轮询**
```javascript
// 每 30 秒刷新一次
setInterval(async () => {
    const data = await API.getProducts();
    renderProducts(data);
}, 30000);
```

**方案 2: HAP 工作流 + Webhook**
- 在 HAP 中配置工作流
- 数据变更时触发 Webhook
- 通知前端刷新数据

### 适用场景建议

| 场景类型 | 是否适合 | 说明 |
|---------|---------|------|
| 企业官网 | ✅ 非常适合 | 产品展示、新闻资讯、案例展示 |
| 内容管理 | ✅ 非常适合 | 博客、文档库、知识库 |
| 表单收集 | ✅ 非常适合 | 在线预约、问卷调查、询价订单 |
| 数据看板 | ✅ 适合 | 数据展示、报表展示(只读) |
| 电商平台 | ⚠️ 部分适合 | 简单商品展示可以,复杂交易流程建议传统后端 |
| 实时聊天 | ❌ 不适合 | HAP API 不支持 WebSocket |
| 高并发应用 | ❌ 不适合 | HAP API 有频率限制 |

### 性能基准参考

基于测试环境的性能数据:

- **API 响应时间**: 100-300ms (国内)
- **分页查询(50条)**: ~200ms
- **带筛选查询**: ~250ms
- **并发限制**: 建议每秒不超过 10 次请求

**优化建议:**
- 使用前端缓存减少请求
- 合理设置 pageSize
- 避免短时间内大量请求

### 未来扩展方向

1. **渐进式 Web 应用(PWA)**
   - 添加 Service Worker
   - 支持离线访问
   - 缓存数据本地存储

2. **与前端框架集成**
   - Vue.js / React 组件化
   - 状态管理(Vuex / Redux)
   - 路由管理(Vue Router / React Router)

3. **高级功能**
   - 用户认证系统
   - 权限控制
   - 多语言支持
   - 主题切换

4. **性能监控**
   - 接入 Google Analytics
   - 错误监控(Sentry)
   - 性能分析(Lighthouse)

### 总结

本指南展示了如何使用 HAP 平台快速搭建前后端分离的 Web 应用:

**核心优势:**
- 🚀 **快速上线**: 无需搭建后端,专注前端开发
- 💰 **成本低廉**: 静态托管免费,HAP 有免费版
- 👥 **易于维护**: 业务人员可直接在 HAP 管理内容
- 🔧 **灵活扩展**: 支持自定义开发,满足个性化需求

**适合人群:**
- 前端开发者(想快速上线项目)
- 创业团队(预算有限)
- 内容运营人员(需要自主管理内容)
- 企业数字化转型(快速验证想法)

**核心要点回顾:**
1. 使用 HAP API V3 直接 CORS 请求
2. 合理设计分页和筛选逻辑
3. 注意 API 密钥安全
4. 优化性能和用户体验
5. 选择合适的应用场景

---

**文档版本**: v2.0
**最后更新**: 2026-01-11
**作者**: Claude Code
**许可证**: MIT
