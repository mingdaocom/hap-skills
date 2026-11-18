# HAP AI 智能助手领域对象规范

本规范定义 HAP（明道云）应用内 **AI 智能助手（Chatbot）** 的数据结构、预设提问硬约束、系统提示词设计准则与权限连带关系。创建（`create_chatbot`）、基础属性修改（`update_chatbot`）及关联工作流 Agent 节点修订（`update_workflow_node`）共用本领域对象标准。

---

## 一、 智能助手元数据与核心属性

每个智能助手实体包含以下属性：

- **`appId`**（String，必填）：所属应用 ID。
- **`name`**（String，必填）：助手显示名称（如 `"采购助手"`、`"HR 政策咨询顾问"`）。
- **`welcomeMessage`**（String，必填）：场景化欢迎语，向用户清晰告知该助手能解决什么业务问题与能力边界。
- **`prompt`**（String，必填）：系统提示词，注入助手的专业角色定位、业务规则与交互指引（见第三节）。
- **`presetQuestions`**（String[]，必填）：预设快捷引导提问列表，接口限制为**最多 5 项**；创建时必须提供该数组。
- **`sectionId`**（String，可选）：所属应用导航分组（Section）ID。
- **`icon`**（String，可选）：助手图标文件名（如 `"sys_17_6_reddit"`、`"sys_16_6_genius"`、`"sys_1_8_online_support"`）。
- **`description`**（String，可选）：面向用户的助手功能与定位简述。
- **`remark`**（String，可选）：面向开发者/AI 的内部维护备注。

---

## 二、 平台核心限制与硬约束 (Hard Limits)

1. **预设提问数量约束 (`presetQuestions`)**：
   - 创建时数组必传，接口声明的硬上限为 **5 项**，但未声明最少 1 项；
   - 为保证入口可用性，默认设计 1 ~ 5 项；只有用户明确要求无预设问题时才使用空数组；
   - 提问内容必须结合业务实际场景生成具体问题（如 `"如何申请加急报销？"`、`"试用期转正流程是什么？"`），严禁输出“你好”、“请问有什么可以帮您”等空泛套话。
2. **系统提示词通过关联工作流修订 (`prompt`)**：
   - 当前 `update_chatbot` 接口仅支持更新名称、欢迎语、预设提问、导航分组、图标、说明与备注，**不支持更新系统提示词（`prompt`）**；
   - 底层 `chatbotId == workflowId`，已有助手直接用 `get_workflow_structure(workflow_id: chatbotId)` 读取工作流并定位 `ai_agent`，再用 `update_workflow_node.config.prompt` 原地更新；严禁删除重建。不为查找关联流程额外读取助手详情或工作流列表；nodeId 从工作流结构或节点查询取得，不能用 chatbotId 代替。更新写入草稿，按授权发布后才生效。
3. **接口参数白名单约束**：
   - 不能向 create_chatbot/update_chatbot 传入 `model`、`iconColor`、`knowledgeBases`、`worksheets` 等不存在的参数；Agent 节点的 model、tools 等按其自身 Schema 使用。
4. **角色权限连带授权规则**：
   - 新建的 AI 助手默认对普通角色不可见；
   - 若角色需要使用该助手，必须在该角色的精细权限配置中追加 `{ id: "<chatbotId>", enable: true }`。

---

## 三、 系统提示词 (`prompt`) 四段式编写规范

新建或明确要求整体重写时，系统提示词按以下四段式结构组织；局部修订保留原文无关内容、业务规则和动态引用，不为满足结构要求重写整个提示词：

### 1. 角色定位与职责边界 (Role & Scope)
明确助手的专业身份、服务对象、主要职责以及不涉及的范围（如“你是 XX 公司的采购业务顾问，负责解答员工关于采购申请、供应商准入及对账付款的流程疑问”）。

### 2. 业务规则与知识注入 (Business Rules & Knowledge)
注入当前业务系统的关键规则与判断逻辑：
- 审批层级与金额阶梯（如“采购金额 ≥ 5 万元需总监审批”）；
- 状态流转条件与前置依赖（如“必须先完成入库验收方可提交开票”）；
- 常用分类标准与对应处理路径。

### 3. 交互规范与排版要求 (Interaction & Formatting)
- 使用任务指定的应用语言，未指定时沿用助手语言；
- 复杂流程与步骤采用分点列出（1、2、3...），关键名词、金额或时间节点加粗显示；
- 语气保持专业、友善、清晰。

### 4. 安全底线与未知处理 (Safety & Fallback)
- 严禁捏造未经系统或制度明确证实的数据；
- 对超出助手知识范围或涉及高度敏感隐私的事项，明确回复无法处理，并引导用户联系对应的业务负责人或系统管理员。


## 四、关联工作流 Agent 节点能力

以下基于 2026-10-14 sandbox 实时 `update_workflow_node` Schema；执行时以当前入口为准，不把 AI Action 或普通工作流字段混入 Chatbot。

| 可用于助手修订的能力 | 字段与约束 |
|---|---|
| 角色、规则、回复格式 | `prompt`；保留合法的动态字段引用 |
| 用户输入与附件 | `input`、`file`；紧接 Chatbot 开始节点的首个 Agent 需要 input；file 只能是单个附件字段占位符，不填固定文本或拼接引用 |
| 模型与生成参数 | `model` 使用 get_app_ai_models 返回的有效模型 ID；`temperature` 为 0–2，`maxTokens` 为正整数；局部修改不清空未要求更换的模型 |
| 权限与图片理解 | `checkUserPermission`（Chatbot 默认 true）、`enableImageRecognition`；不能为解决检索失败擅自关闭权限检查 |
| 回复与结构化输出 | `switchReplyPrompt` 不能为 true 且同时配置非空 `outputs`；输出支持文本、数字、标量数组、对象数组，AI Action 不支持 outputs |
| 工具配置 | `tools` 控制启用状态、数据范围和适用的运行时用户确认；不是调用或执行这些工具 |

`switchDetail`、`switchDiscussion` 仅适用于 AI Action，不用于对话机器人。集成 API / 外部 MCP 工具目前不支持配置，不传内部 configs/auto/toolNode 或子节点 ID。

工具可选能力：

- 基础工具：`queryRecords`、`summarizeRecords`、`createRecord`、`updateRecord`、`sendNotification`、`sendEmail`、`getRecordDiscussions`。
- 查询/汇总可在每个 worksheets 项中设置 worksheetId、viewId、fields 和 filter，限定工作表、视图、返回字段与预设筛选；新增/更新的 worksheets 项仅支持 worksheetId，不能传 viewId、fields、filter 来声称已限定写入记录范围。`scope: app` 表示整个应用，`selected` 必须给出具体表；字段空数组表示全部字段，不能把省略范围误当作限制。查询筛选左值隐含当前表，不能传 `left.node`。停用工具不能携带 filter，不能为满足此限制静默丢弃受保护筛选。
- 对写记录、通知、邮件和封装流程，按 Schema 使用 `requireUserConfirmation` 配置助手运行时确认；此参数不等于当前修订任务的授权，不能擅自取消。
- `searchKnowledge`：用 get_app_knowledge_list 取得真实 knowledgeIds，启用时不能为空；可配置检索策略、内容类型和召回参数。列表为空也可能是没有应用配置权限，不能直接认定无知识库。参数组合以当前 Schema 为准，不套用 knowledge_search 工具的规则。
- `callWorkflow`：从 get_workflow_list(triggerType: "pbc", published: true) 取得已发布、已授权的封装流程；保留真实 workflowId，不将普通工作流当作 PBC，不构造循环调用。仅配置引用，不自动编辑或执行被引用流程。

修改 tools/outputs 前使用 get_workflow_node 取得当前配置；本任务已有未失效的完整节点详情时直接复用，不为遵循步骤重复读取。数组为整组替换，必须携带全部保留项，既有工具保留 toolId，既有输出（含子字段）保留 fieldId；新增项不伪造 ID。省略数组表示保持，`[]` 表示清空，`null` 被拒绝。工具类型、既有输出类型/数组元素类型不能随意改变；被下游引用的输出不能删除。存在无法按当前 Schema 无损保留的既有项时，停止该数组修改并说明缺口，不能删掉不支持的项后提交；其他已授权且独立的标量修改可继续。


## 五、新建助手的资源选择

本节供 chatbot-revision-sub-agent 与 Build 的 chatbot-config-sub-agent 按实际配置需求使用，不是每次创建的固定检查清单。创建接口本身不接收工作表/知识库绑定参数，提示词中的表名也不构成工具范围限制。已有信息直接复用，互不依赖的必要读取同轮发出；不增加与目标无关的筛选、返回字段限制、知识检索或模型切换。

- 从助手用途判断需要结构化记录查询/统计、知识检索、业务写入或封装流程调用；在原目标内选择必需能力，纯通用文案任务不强行配置数据工具。复用主 Agent 已交接的资源信息，执行器只补查缺口。
- 工作表候选复用 get_app_info 中的工作表清单，缺少时才查询，不额外调用工作表列表工具。仅指定工作表时无需读取表/视图详情；配置返回字段、预设筛选或定位视图且信息不足时，按需用 get_worksheet_structure(responseFormat: "md") 取得真实字段 ID、类型、选项值与视图概览。只有核对或复用已有视图筛选等详细配置时才 get_view_structure；已有可靠 viewId 直接引用，不为绑定视图例行读详情。明确表范围时使用工具的 scope: selected 并填写 worksheets，不能因默认 scope: app 而扩大到整个应用。只有目标本身涵盖全应用数据时才使用 app。
- 知识问答按需查询 get_app_knowledge_list；名称/描述不足以判断覆盖时用 includeKnowledgeConfig: true 核对来源，选择能够支持目标的真实 knowledgeIds 配置 searchKnowledge。无需知识的任务不例行查询；无可用结果、权限不足或必需知识缺失时说明缺口，不虚构 ID、不默认绑定全部库，也不创建知识库。只有同等满足目标的可用来源才能替代，否则将具体选择交回主 Agent。
- 任务明确只读或业务目标要求限制操作时，配置所需查询、汇总、知识等工具，并停用与目标冲突的默认写入/发送工具，不能仅靠提示词限制；不为未涉及的能力安排额外检查。业务目标明确需要写入或发送时按该目标配置相应工具、数据范围与运行时确认；保持 checkUserPermission，不能为扩大可用范围关闭权限检查。
- 新建助手需要资源绑定或工具范围配置时，取得 chatbotId 后按第四节规则读取节点，合并全部必要 tools 变更一次提交；同一工具类型不重复添加，保留原 toolId 和仍需要的完整工具项。配套绑定不改写工作表或知识库，不等于授予用户这些数据的访问权限；角色使用助手的权限仍由 role_permission 任务处理。
- 验收以实际配置与发布结果为依据：核对所需工具、工作表/知识库范围、必要的确认设置和交付状态，复用充分回执；创建回执不代表资源配置已完成，不能把未配置的能力写进欢迎语或最终报告冒充已可用。不执行真实业务工具测试。
