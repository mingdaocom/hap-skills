# HAP App Copilot（明道云应用与数据全生命周期智能助手）

基于明道云（HAP）MCP 工具链的一站式应用与数据智能助手 Skill，完整覆盖**方案设计（Plan）、自动搭建（Build）、存量修订（Modify）与日常数据/审批操作（Data）**。

## 功能概述

本 Skill 支持三大核心场景（四路工作流闭环）：

- **场景 A：修改已有应用（Modify）** — 面向线上存量应用的 12 大业务域（应用与导航、工作表与字段、视图与自定义动作、业务规则、工作流与审批、角色权限、自定义页面与统计图、AI 对话机器人、公开表单、外部门户、打印模板、结构伴随数据迁移）提供外科手术式增量修订与配置排查。主 Agent 按需读取跨模块影响地图、领域操作手册与底层 Spec 原文，`scripts/resolve_context.py` 辅助定位，严格执行实时摸底、连带影响分析、二元风险门禁（`low`/`high`）、最小写入与按需核验。验证与异常防重以 [安全规则第五节](modify/safety-rules.md#五-效率优先验证与异常防重纪律)为准。
- **场景 B：从零新建与断点恢复（Plan & Build）** — 从**业务方案设计（Plan）**到**物理并发搭建（Build）**的全自动流水线：
  1. **Plan 阶段** — 主 Agent 交互式生成并联动修订结构化方案（`overview.md` + `hap-plan.json`），支持多语言锁定与草案局部修订（`APPLY`/`CONSULT`/`CLARIFY`）。
  2. **Build 阶段** — 基于薄调度器 `scripts/build_runtime.py` 管理 DAG 依赖、分片并发派发独立 Subagent 与落盘验收，自动完成 Step 1 ~ Step 11 全套物理资产创建与构建总结。
- **场景 C：日常业务数据操作与审批流转（Data）** — 支持条件检索、服务端透视聚合（`get_record_pivot_data`）、日常记录增删改、跨应用个人审批待办查询与决断（同意/驳回/退回/催办/撤回/终止）以及触发封装业务流程（PBP）；内置视图平铺与防静默 0 行取数准则、多值防覆盖保护与分级确认门禁，并兼容非全量个人版 MCP。

## 使用依赖

- **Python 3.10+**：运行随包提供的脚本；这些脚本只使用 Python 标准库。
- **已连接并授权的 HAP MCP 服务**：应用搭建与修订要求目标服务满足 `tools_count >= 170` 全量工具门禁；纯日常数据查询与审批操作（Data）按实际所需工具放行（兼容个人版 MCP）；服务名称不限。
- **本地宿主能力**：能够读取 Skill 文件、执行 Python 命令并保存工作区文件；工具发现与提问方式见 [宿主适配](HOST_ADAPTER.md)。
- **Build 子代理**：物理搭建的重资产步骤需要真实独立子代理及所选 HAP MCP 的访问能力；宿主不支持时无法执行 Build，Plan、常规 Modify 和 Data 不以此为前提。
- **文件打印任务**：新建或替换 Word/Excel 模板时，宿主需具备相应文件的读取、编辑和校验能力；具体要求见 [打印模板文件规程](modify/print-template-file.md)。

尚未连接 HAP MCP 时，可让 Agent 按 [MCP 接入指南](MCP_SETUP.md) 引导获取个人访问令牌、协助配置当前宿主，并在连接验证通过后继续任务。

## 核心亮点与高级能力

- 🧭 **12 域全覆盖存量修订与跨模块联动** — 内置 `modify/impact-map.md` 与 `modify/modify_guide.md`，对删改字段、状态合并、页面图表增量同步（`patch_custom_page_components`）、公开表单（`public_form`）和外部门户（`external_portal`）实现精准联动治理。
- 🛡️ **二元风险门禁与 14 类删除/关闭直通** — 对齐线上安全模型，常规可逆操作与用户点名的 14 类删除/关闭指令高效直通，破坏性变更（删表、删核心字段、删非空记录、改线上主干工作流）强制确认并支持一键备份。
- 📄 **Word / Excel / 系统 / 二维码 / 条形码打印模板** — 支持系统打印、二维码/条码打印，以及本地 Python 生成 `.docx` / `.xlsx`（Base64 / URL）上传绑定视图的全链路闭环。
- 🎨 **自定义字段（CustomField）与 AI 对话机器人（Chatbot）** — 支持自由字段前端组件注入，以及 Chatbot 外壳创建 + 底层 `ai_agent` 节点提示词、模型与工具授权两步闭环配置。
- ⚡ **原文按需读取** — Agent 按任务读取共享规范；`scripts/resolve_context.py` 提供文件与章节导航，也保留可选原文摘取。构建任务提供完整计划入口，支持跨领域排查与继续执行。

## 目录结构

```text
hap-mcp-app-builder/
├── SKILL.md                                    # 单一公开入口：环境能力探针校验 + 四路场景路由
├── README.md                                   # 项目说明与架构导览
├── LICENSE                                     # MIT 许可证
├── version.json                                # 唯一版本元数据（含版本号、工具门禁与公开库升级路径）
├── HOST_ADAPTER.md                              # 宿主工具、文件读取与交互适配
├── MCP_SETUP.md                                 # 缺少服务时按需读取的接入与配置指南
├── workflows/                                  # 四大核心工作流
│   ├── plan.md                                 # Plan 阶段：交互式方案设计与草案联动修订
│   ├── build.md                                # Build 阶段：薄调度器并发物理搭建与总结
│   ├── modify.md                               # Modify 阶段：12 域渐进加载、风险门禁与按需核验
│   └── data.md                                 # Data 阶段：日常业务数据查询统计、增删改、审批与流程触发
├── plan/                                       # Plan 阶段专属规范
│   ├── 1a_plan_overview.md                     # 面向用户的方案概览模板与多语言规则
│   └── 1b_plan_schema.md                       # hap-plan.json 严格 Schema 与设计约束
├── build/                                      # Build 阶段上下文契约与原子步骤 SOP
│   ├── CONTEXT.md                              # Subagent 最小上下文协议
│   ├── OUTPUT_CONTRACT.md                      # 统一 JSON 结果回执契约
│   ├── PROGRESS.md                             # 用户侧阶段进度播报规范
│   └── steps/                                  # 12 个原子构建步骤 SOP（轻重分离，工作流设计创建二合一）
│       ├── 1_create_app.md                     # 主调度器内联：建应用壳、分组与页面空壳
│       ├── 1b_update_app_desc.md               # 主调度器内联：更新应用简介与 HTML 使用手册
│       ├── 2a_create_worksheets.md
│       ├── 2b_create_relations.md
│       ├── 3_create_actions_views_rules.md
│       ├── 4_create_chatbots.md                # 含 4a 创建外壳 + 4b 配置 ai_agent 并发布
│       ├── 5_create_sample_data.md
│       ├── 6_create_pages.md
│       ├── 7_sort_app_items.md                 # 主调度器内联：各分组内应用项智能排序
│       ├── 8_create_roles.md
│       ├── 10_create_workflows.md              # 单条系统工作流设计 + 创建 + 校验发布一体化
│       └── 11_create_action_workflows.md       # 单个动作工作流设计 + 注入 + 校验发布一体化
├── modify/                                     # Modify 专属治理体系与本地文件规程
│   ├── impact-map.md                           # 跨模块连带影响地图与读前必查矩阵
│   ├── modify_guide.md                         # 12 大业务域修改手册与本地实操适配（第 1~13 章）
│   ├── safety-rules.md                         # 二元风险模型（low/high）、14 类删除直通与回读纪律
│   ├── execution-boundaries.md                 # 自动闭环、备份协同、人工引导与硬阻断边界
│   └── print-template-file.md                  # Word/Excel 本地制作、HAP 占位符与交付检查
├── references/                                 # 19 份 HAP 设计指南与领域规范
│   ├── hap-app-design-guide.md                 # 应用建模、导航、门户与架构设计总纲
│   ├── hap-workflow-design-guide.md            # 工作流联动设计与防死循环指南
│   ├── hap-chart-design-guide.md               # 统计图类型选型、xaxes/yaxisList 与配色规范
│   ├── hap-icon-palette.md                     # 受控图标库与主题色板
│   ├── hap-sample-data-spec.md                 # 仿真示例数据与静态图片资源规范
│   ├── hap-domain-app-spec.md                  # 应用基础属性、导航分组与应用项管理规范
│   ├── hap-domain-worksheet-spec.md            # 工作表、字段类型、排版、表单设置与筛选器规范
│   ├── hap-domain-view-spec.md                 # 8 大视图类型、筛选排序与快捷操作规范
│   ├── hap-domain-custom-action-spec.md        # 自定义动作按钮、交互输入与工作流绑定规范
│   ├── hap-domain-business-rule-spec.md        # 业务规则条件语法与前后端校验动作规范
│   ├── hap-domain-workflow-spec.md             # 工作流与审批流程节点 Schema 及发布规范
│   ├── hap-domain-custom-page-spec.md          # 自定义页面 48 栅格布局与增量组件同步规范
│   ├── hap-domain-worksheet-chart-spec.md      # 工作表统计面板图表创建、修改与排序规范
│   ├── hap-domain-role-spec.md                 # 角色权限模型、数据范围与字段级权限规范
│   ├── hap-domain-chatbot-spec.md              # AI 对话机器人与 ai_agent 节点配置规范
│   ├── hap-domain-external-portal-spec.md      # 外部门户状态、注册登录与外部角色分段配置规范
│   ├── hap-domain-worksheet-index-spec.md      # 工作表物理索引与唯一索引性能规范
│   ├── hap-domain-custom-field-spec.md         # 自定义字段（CustomField）前端组件注入规范
│   └── hap-domain-record-data-spec.md          # 业务记录查询、透视统计与受控批量写改规范
└── scripts/                                    # 5 个核心运行时脚本
    ├── skill_update.py                         # 技能版本检查、SHA256 校验、软链原子更新与回滚
    ├── resolve_context.py                      # Modify/Build/Data 原文索引与可选章节提取器
    ├── build_runtime.py                        # Build DAG 状态机、分片任务编排与输出契约校验器
    ├── merge_worksheet_context.py              # 合并生成全保真 worksheetContext.json（含选项 key）
    └── scan_apps.py                            # 扫描工作区已有应用工程状态
```

## 核心职责边界

| 模块 / 文件 | 唯一职责 |
|---|---|
| `SKILL.md` | 不限服务名的 HAP MCP 识别、`>=170` 全量工具硬门禁、URL 一键直达与四路场景路由 |
| `workflows/plan.md` + `plan/` | 交互式方案设计、语言锁定与草案阶段联动修改（`APPLY`/`CONSULT`/`CLARIFY`/`CREATE`） |
| `workflows/build.md` + `build/` | 轻重分离（1/1b/7 内联 + 重资产独立 Subagent 并发 + 工作流设计创建二合一）物理搭建与总结 |
| `workflows/modify.md` + `modify/` | 存量应用 12 大业务域实时摸底、影响地图联动、二元风险确认、最小写入与按需核验 |
| `workflows/data.md` | 日常业务数据条件查询、透视统计、增删改、审批待办流转与封装业务流程触发 |
| `references/hap-*.md` | HAP 各领域底层参数结构、约束红线与标准范例 |
| `scripts/resolve_context.py` | 按 `--mode modify/build/data --json` 定位原文件，或用 `--file ... --section ...` 辅助阅读 |

## 来源说明

本 Skill 的设计指南、领域规范及部分构建/修订流程参考明道云 `MDAgentService`，并适配本地 Agent 与 HAP MCP 的使用方式。相关文件中的 `SOURCE` 注释用于标识参考来源。

## 许可证

[MIT License](LICENSE)。发布包包含本目录的运行文件与许可证，排除 `.DS_Store`、Python 缓存及本地运行产物。
