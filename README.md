# HAP Skills

一组面向 **HAP** 的 AI Agent 技能（Skill）集合，覆盖三种操作 HAP 的方式：

- **CLI** — 基于 `hap` 命令行，让 Agent 在终端里直接建应用、改应用、查数据；
- **MCP** — 基于 HAP MCP 服务，对话式全自动搭建应用（方案设计 → 确认 → 物理搭建）；
- **API** — 基于 HAP REST API，对接前端 / 对外网站（当前为占位草稿）。

技能按场景分目录存放（`skills/cli/`、`skills/mcp/`、`skills/api/`），可以整组安装，也可以单装。

> 这个仓库只包含 Skill，不含 `hap-cli` 的源码；`hap-cli` 通过 `pip` 单独安装（见下方前置依赖）。

## 包含的技能

| 场景 | Skill | 作用 |
| --- | --- | --- |
| CLI | **hap-cli** | 总览与导航：介绍 `hap` 命令行能做什么、怎么登录，并在合适时把你引导到下面几个专门技能 |
| CLI | **hap-cli-app-creator** | 从一句业务需求一站式建出**真实可用、带示例数据**的 HAP 应用 |
| CLI | **hap-cli-app-editor** | 对**已有应用**做精确的局部修改（字段/视图/工作表/角色权限/工作流/自定义动作/页面） |
| CLI | **hap-cli-data-query** | 复杂查数：多条件 AND/OR 筛选、嵌套分组、透视聚合统计（求和/计数/平均/分组） |
| CLI | **hap-cli-environments** | 多环境/多账号操作守则：授权了多个 HAP 环境或账号时，决定在哪个环境/账号上执行，破坏性操作前先确认 |
| MCP | **hap-mcp-app-builder** | 全自动一站式应用构建器：方案设计（Plan）→ 确认 → 自动物理搭建（Build），支持中断后一键续建 |
| API | **hap-api-website** | 基于 HAP REST API 搭建网站 / 对接前端（占位草稿，工作流待补全） |

## 前置依赖

不同场景依赖不同，按你要用的场景准备：

**CLI 场景** —— 基于 `hap` 命令行，先装好并登录：

```bash
pip install hap-cli      # 安装命令行工具
hap auth login           # 浏览器授权登录
hap auth whoami          # 确认已登录、查看当前用户与组织
```

**MCP 场景** —— 在你的 Agent 客户端里配置 HAP MCP 服务（`api1.mingdao.com/mcp` 或 `api2.mingdao.com/mcp`）后即可调用。

**API 场景** —— 准备好目标 HAP 应用的 REST API 鉴权密钥（Appkey / Sign）。

## 安装

### 方式一：用 `npx skills`（推荐）

一次性安装全部技能：

```bash
npx skills add mingdaocom/hap-skills
```

按场景整组安装（只装你需要的那一类）：

```bash
# CLI 场景
npx skills add https://github.com/mingdaocom/hap-skills/tree/main/skills/cli
# MCP 场景
npx skills add https://github.com/mingdaocom/hap-skills/tree/main/skills/mcp
# API 场景
npx skills add https://github.com/mingdaocom/hap-skills/tree/main/skills/api
```

或按需安装其中某个技能：

```bash
# CLI
npx skills add mingdaocom/hap-skills --skill hap-cli
npx skills add mingdaocom/hap-skills --skill hap-cli-app-creator
npx skills add mingdaocom/hap-skills --skill hap-cli-app-editor
npx skills add mingdaocom/hap-skills --skill hap-cli-data-query
npx skills add mingdaocom/hap-skills --skill hap-cli-environments
# MCP
npx skills add mingdaocom/hap-skills --skill hap-mcp-app-builder
# API
npx skills add mingdaocom/hap-skills --skill hap-api-website
```

### 方式二：在 AI Agent 对话里一句话安装

在 **Claude Code、Codex、Antigravity、Hermes、Open Claw** 等 Agent 的对话中直接输入：

```text
帮我安装这个skills: https://github.com/mingdaocom/hap-skills
```

只想装某一类场景，把场景目录说清楚即可，例如：

```text
帮我安装 https://github.com/mingdaocom/hap-skills/tree/main/skills/cli 下的所有 skills
```

Agent 会自动克隆仓库并把技能装到对应位置。

## 各技能简介

### CLI 场景（基于 `hap` 命令行）

#### hap-cli — 使用导航

带你把工具装好、登录、选好组织与应用，并梳理 `hap` 的一级命令地图（通讯录、聊天、动态、日程、工作表记录、工作流、审批等）。当你的需求需要整体建/改应用或复杂查数时，它会指明该切到下面哪个专门技能。

#### hap-cli-app-creator — 创建应用

适合「从零搭一个完整应用」：描述业务场景（如 CRM / 库存 / 报修 / 借阅系统），它先与你确认方案（工作表、字段、角色），产出设计文档并校验，再用 `hap` 命令一次性物理搭建，最后生成并填充示例数据。

#### hap-cli-app-editor — 修改应用

适合「改已有应用的某个元素」：加/改/删字段、视图重命名、停用工作流、给角色加权限、加自定义动作按钮、删表等。每次操作前读取应用实时结构，破坏性操作需显式确认。

#### hap-cli-data-query — 数据查询

适合「把想要的数据查出来」：讲清筛选器的结构与运算符词表、透视的维度与聚合参数，给出可直接套用的模板，帮你写对复杂的 `--filter-json` / 透视查询。

#### hap-cli-environments — 多环境 / 多账号

当你授权了多个 HAP 环境或账号（MingDAO SaaS、Nocoly、私有部署，或同一环境下多个账号）时，帮你决定「在哪个环境、用哪个账号执行」：把你的措辞匹配到具体环境/账号，破坏性操作（删除、发布、改权限）若环境不明确就先停下来确认，避免在不该动的环境上造成不可逆后果。

### MCP 场景（基于 MCP 服务）

#### hap-mcp-app-builder — 全自动应用构建器

适合「一句话全自动建应用」：从业务方案设计（Plan）开始，与你确认后自动进入物理搭建（Build）；若方案已存在，可直接一键续建/恢复。通过 `/hap-builder` 或直接用对话描述系统诉求（如「帮我搭建一个客户管理应用」）触发。与 CLI 的 `hap-cli-app-creator` 解决同类问题，区别在于它走 MCP 服务而非命令行。

### API 场景（基于 HAP REST API）

#### hap-api-website — API 建站助手（占位草稿）

适合「把对外网站或前端直接对接 HAP API」：在 HAP REST API 之上搭建网站。**当前为占位骨架，鉴权方式与建站工作流待补全。**

## 验证

安装完成后，在对话中输入下面任意一句，看 Agent 是否进入对应技能：

```text
帮我用 HAP 建一个图书借阅管理应用          # → hap-cli-app-creator
在某张表里加一个字段                        # → hap-cli-app-editor
查一下某张表上个月各产品的销售额前 5        # → hap-cli-data-query
切到我测试用的那个环境再操作                # → hap-cli-environments
hap 命令行怎么登录、有哪些命令              # → hap-cli
帮我全自动搭建一个客户管理应用              # → hap-mcp-app-builder
用 HAP API 做一个对外网站                    # → hap-api-website
```

## 目录结构

```
hap-skills/
├── README.md
├── .gitignore
└── skills/
    ├── cli/                     # CLI 场景：基于 hap 命令行
    │   ├── hap-cli/
    │   ├── hap-cli-app-creator/
    │   ├── hap-cli-app-editor/
    │   ├── hap-cli-data-query/
    │   └── hap-cli-environments/
    ├── mcp/                     # MCP 场景：基于 MCP 服务
    │   └── hap-mcp-app-builder/
    └── api/                     # API 场景：基于 HAP REST API
        └── hap-api-website/
```

每个技能目录下的 `SKILL.md` 是入口，Agent 会自动读取。

## 许可

MIT
