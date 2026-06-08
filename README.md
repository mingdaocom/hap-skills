# HAP Skills

一组面向 **明道云 HAP（MingDAO HAP）** 的 AI Agent 技能（Skill）集合。基于 `hap-cli` 命令行，让 Agent 在终端里直接操作明道云：建应用、改应用、查数据，以及收发消息、发动态、管日程等日常协作。

> 这个仓库只包含 Skill，不含 `hap-cli` 的源码。`hap-cli` 通过 `pip` 单独安装（见下方前置依赖）。

## 包含的技能

| Skill | 作用 |
| --- | --- |
| **hap-cli** | 总览与导航：介绍 `hap` 命令行能做什么、怎么登录，并在合适时把你引导到下面三个专门技能 |
| **hap-cli-app-creator** | 从一句业务需求一站式建出**真实可用、带示例数据**的明道云应用 |
| **hap-cli-app-editor** | 对**已有应用**做精确的局部修改（字段/视图/工作表/角色权限/工作流/自定义动作/页面） |
| **hap-cli-data-query** | 复杂查数：多条件 AND/OR 筛选、嵌套分组、透视聚合统计（求和/计数/平均/分组） |

## 前置依赖

这些技能都基于 `hap` 命令行工作，先装好并登录：

```bash
pip install hap-cli      # 安装命令行工具
hap auth login           # 浏览器授权登录
hap auth whoami          # 确认已登录、查看当前用户与组织
```

## 安装

### 方式一：用 `npx skills`（推荐）

一次性安装全部技能：

```bash
npx skills add mingdaocom/hap-skills
```

或按需安装其中某个技能：

```bash
npx skills add mingdaocom/hap-skills --skill hap-cli
npx skills add mingdaocom/hap-skills --skill hap-cli-app-creator
npx skills add mingdaocom/hap-skills --skill hap-cli-app-editor
npx skills add mingdaocom/hap-skills --skill hap-cli-data-query
```

### 方式二：在 AI Agent 对话里一句话安装

在 **Claude Code、Codex、Antigravity、Hermes、Open Claw** 等 Agent 的对话中直接输入：

```text
帮我安装这个skills: https://github.com/mingdaocom/hap-skills
```

Agent 会自动克隆仓库并把技能装到对应位置。

## 各技能简介

### hap-cli — 使用导航

带你把工具装好、登录、选好组织与应用，并梳理 `hap` 的一级命令地图（通讯录、聊天、动态、日程、工作表记录、工作流、审批等）。当你的需求需要整体建/改应用或复杂查数时，它会指明该切到下面哪个专门技能。

### hap-cli-app-creator — 创建应用

适合「从零搭一个完整应用」：描述业务场景（如 CRM / 库存 / 报修 / 借阅系统），它先与你确认方案（工作表、字段、角色），产出设计文档并校验，再用 `hap` 命令一次性物理搭建，最后生成并填充示例数据。

### hap-cli-app-editor — 修改应用

适合「改已有应用的某个元素」：加/改/删字段、视图重命名、停用工作流、给角色加权限、加自定义动作按钮、删表等。每次操作前读取应用实时结构，破坏性操作需显式确认。

### hap-cli-data-query — 数据查询

适合「把想要的数据查出来」：讲清筛选器的结构与运算符词表、透视的维度与聚合参数，给出可直接套用的模板，帮你写对复杂的 `--filter-json` / 透视查询。

## 验证

安装完成后，在对话中输入下面任意一句，看 Agent 是否进入对应技能：

```text
帮我用 HAP 建一个图书借阅管理应用      # → hap-cli-app-creator
在某张表里加一个字段                    # → hap-cli-app-editor
查一下某张表上个月各产品的销售额前 5    # → hap-cli-data-query
hap 命令行怎么登录、有哪些命令          # → hap-cli
```

## 目录结构

```
hap-skills/
├── README.md
├── .gitignore
└── skills/
    ├── hap-cli/
    ├── hap-cli-app-creator/
    ├── hap-cli-app-editor/
    └── hap-cli-data-query/
```

每个技能目录下的 `SKILL.md` 是入口，Agent 会自动读取。

## 许可

MIT
