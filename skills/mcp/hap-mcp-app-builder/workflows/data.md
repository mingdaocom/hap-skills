# HAP 日常业务数据操作与审批流转工作流

<!-- SOURCE: app-query-agent.yaml; skills/hap-data-agent-rules/SKILL.md -->

本文件定义日常业务视角下的**数据检索、透视统计、记录增删改、审批待办处理与封装业务流程（PBP）触发**执行规范。主 Agent 在当前会话内直接闭环执行，无需拆分子代理。

> [!IMPORTANT]
> **与结构修订数据迁移（`Modify -> record_data`）的边界铁律**：
> - **本工作流（`Data`，业务使用视角）**：处理日常查数统计、录单改单、删单、办审批与触发业务流程；记录写操作**默认保持 `triggerWorkflow: true`（或省略以沿用默认值）**，确保线上业务工作流与审批流正常联动，并兼容非管理员成员权限。
> - **应用修订（`workflows/modify.md`，架构师/DBA 视角）**：配合改表、拆表、合字段执行的存量历史数据批量初始化、字典转换与跨表结转（强制 `triggerWorkflow: false` 静默迁移），统一走 `workflows/modify.md`。

---

## 一、 目标定位与跨应用审批直达

1. **个人跨应用审批免 `appId` 直达**：
   - 当用户查询或处理本人相关的审批任务（“我有哪些待审批单据”“把张三的请假单批了”“催办我刚提的报销”）时，`get_approve_list`、`get_approve_details`、`batch_process_approves`、`return_approve`、`revoke_approve`、`terminate_approve`、`urge_approve` **均不强制要求 `appId`**（仅当用户明确限定某应用时才在 `get_approve_list` 中附加 `appId`），可直接跨应用查询与处理，无需先反问目标应用。
2. **应用内数据、知识库与流程触发定位（必传 `appId`）**：
   - 记录读写（`get_record_*` / `create_record` / `update_record` / `delete_record` / `batch_*_records`）、记录级审批历史（`get_approval_list_by_row` / `get_approval_detail`）、应用知识库（`get_app_knowledge_list` / `knowledge_search`）及封装业务流程（`get_hooks_workflows` / `get_hooks_workflow_details` / `trigger_workflow`）调用时**必须显式传入 `appId`**。
   - 若用户发送明道云链接（如 `/app/{appId}/{sectionId}/{worksheetId}/{viewId}/row/{rowId}`），直接提取 `appId`、`worksheetId`、`viewId` 与 `rowId` 精准直达，不重复拉取列表；目标应用或重名工作表存在歧义时，通过宿主提问工具请用户点选澄清。

---

## 二、 数据取数与统计防坑准则（同源 `hap-data-agent-rules`）

### 1. 结构先行与视图基准
- **复用真实表结构**：构造筛选条件、投影字段或写入记录前，上下文必须已有目标表的真实结构；未知时先调一次 `get_worksheet_structure(appId, worksheet_id, responseFormat: "md")` 并在本会话复用。
  - **剥离 `(isTitle)` 标记**：Markdown 表结构中标题字段附带的 `(isTitle)` 仅为显示标记，传入 `fields`、`filter`、`rows/columns/values` 时**必须去掉 `(isTitle)`，只传纯 24 位十六进制字段 ID**（严禁猜测或拼造 `_widget_*` 占位 ID）。
- **选准 `viewId` 与平铺形态**：
  - 用户指定“当前视图”时用对应 `viewId`；查全表范围时选用无过滤或覆盖全范围的通用视图 `viewId`（视图过滤是基准，`filter` 只能叠加收窄，找不回被视图本身排除的记录）；
  - 调用 `get_record_list` 读取或定位记录时，**显式传 `tableView: true`**（布尔值），并使用返回行的 `rowId` 作为记录唯一标识（禁把看板/层级分组容器当业务记录）。

### 2. 降维聚合优先（严禁拉全表进上下文手算）
- **统计 / 分组 / 求和 / 均值 / 趋势** ➔ 必须优先调用 **`get_record_pivot_data`** 由服务端聚合（必传 `appId`、`worksheet_id`、`viewId`、`values`；统计记录行数时 `values` 传 `{"field": "rowid", "aggregation": "COUNT"}`，日期或省市区按日/周/月或省/市/区汇总时设置 `granularity: 1|2|3`）。
- **仅查命中总条数** ➔ 调用 `get_record_list(includeTotalCount: true, tableView: true, responseFormat: "json", pageSize: 1, pageIndex: 1)` 直接读取 `total`（`md` 格式可能不含总数，切勿分页拉明细数行数）。
- **按条件查子集与最小字段投影**：
  - `fields` 仅传标题字段 + 本次问答与筛选涉及字段的 24 位 ID（涉及创建人、创建时间、最近修改时间、拥有者等系统字段时，显式设 `includeSystemFields: true`）；`pageSize` 默认 `20`，按需翻页；
  - 查关联记录明细用 `get_record_relations`，查变更审计日志用 `get_record_logs`，查评论讨论用 `get_record_discussions`，查应用文档知识用 `knowledge_search`。

### 3. `filter` 构造与静默 0 行复核
- **`filter` 结构硬约束**：**根节点必须始终是 `"type": "group"` 且显式带 `"logic": "AND" | "OR"`**（即使只有 1 个条件也必须包在 `group.children` 内，严禁把 `condition` 直接作为根节点）；同一 `group.children` 内只能全为 `condition` 或全为子 `group`（最多两层嵌套）。
- **特殊字段筛选值格式（防静默 0 行最关键项）**：
  - **成员/协作人字段**：必须传 **AccountID 数组**——查“我的/我负责的”直接传 `["user-self"]`，查“我下属的”传 `["user-sub"]`，查指定同事先调 `find_member` 拿真实 `accountId`（**严禁直接传中文姓名筛选成员字段**，否则接口返回 `success: true` + 0 行静默假阴性！）；部门字段同理调 `find_department` 传部门 ID 数组；
  - **单选 / 多选 / 下拉字段**：查询 `filter.value` 必须传真实**选项 `key` 数组**（从表结构 `options` 读取）；
  - **关联记录字段**：先查出目标记录的真实 `rowId`，再以数组传入 `value`；**日期 / 时间字段**使用 `between` / `notbetween` 数组区间。
- **0 行结果校验**：带 `filter` 查询返回 0 行时，不得盲目断言“无数据”，先核查字段 ID、选项 `key` 或成员 `accountId` 是否准确无误。

---

## 三、 分级确认门禁（免打扰直通 vs 高危必确认）

### 1. 直通执行（无需打断确认）
- **全部只读操作**：记录检索、透视统计、记录详情/关联/日志/讨论查询、审批列表与详情查询、知识库检索、封装业务流程列表与入参查询；
- **轻量无损提醒**：对在途审批发送催办提醒（`urge_approve`）；
- **单条唯一且参数明确的记录新增或修改**：
  - 单条新增（`create_record`）：目标工作表唯一，且业务必填字段与用户指定字段值均已明确（若缺关键必填值，先用宿主提问工具请用户补充，**严禁臆测编造金额、日期、负责人或状态**）；
  - 单条修改（`update_record`）：已精确定位唯一目标记录（已有明确 `rowId`，或按条件查询确认 `total == 1`），且待改字段与目标值无歧义（若命中 `> 1` 条同名/相似记录，先列出候选标题请用户点选消歧）。

### 2. 强制确认门禁（必须先列明命中目标，获用户明确确认后再执行）
1. **记录删除（`delete_record` / `batch_delete_records`）**：
   - 执行前必须先查实并向用户展示**工作表名、命中记录准确条数及记录标题清单**；
   - **默认一律采用逻辑删除进回收站（`permanent: false`）**！除非用户主动点名“永久彻底删除 / 不进回收站”且经单独高危风险提示确认，否则**绝对禁止传 `permanent: true`**。
2. **批量修改或批量创建（`batch_update_records` / 多条 `update_record` / 多条业务 `batch_create_records`）**：
   - 更新存量多条记录前，先用同一 `filter` 查准 `total` 总数并列出代表性记录标题、原值与目标新值，经用户确认后再按真实 `rowIds` 执行（`batch_update_records` 仅适用于同值广播；每行目标值不同须逐条 `update_record`，单次对话建议不超过 20 条，超量引导使用页面批量编辑或工作流）。
3. **审批决断操作（同意 / 驳回 / 退回 / 撤回 / 终止）**：
   - 执行 `batch_process_approves`（`action: "approve" | "reject"`，单条审批同样传单元素 `instances: [{instanceId, workId}]`）、`return_approve`、`revoke_approve` 或 `terminate_approve` 前：
   - 必须先调 `get_approve_list` / `get_approve_details` 核实**单据标题、发起人、当前审批节点与关键表单摘要**（若为退回 `return_approve`，须从 `get_approve_details` 确认合法可退回的 `targetNodeId`），向用户展示待办摘要与拟执行动作（含审批意见 `opinion`），获明确确认后再提交。
4. **手动触发封装业务流程（PBP，`trigger_workflow`）**：
   - 先调 `get_hooks_workflows(appId)` 与 `get_hooks_workflow_details(appId, process_id)` 核实流程名称与输入参数定义（`id`、名称、类型、必填性），向用户列出拟触发的流程名称与实参键值对，获确认后再调 `trigger_workflow`（入参以参数 `id` 作为顶层键名平铺传入）。

---

## 四、 记录写入格式与防覆盖铁律

首次在 Lazy MCP 环境下调用写接口或审批接口前，按 [宿主适配](../HOST_ADAPTER.md) 先读取对应工具的 `.json` Schema 核对参数结构：

1. **`fields[].type` 严禁传字段类型名**：
   - `create_record` / `update_record` / `batch_update_records` 的 `fields` 元素结构为 `{"id": "<24位字段ID>", "value": ...}`；
   - 其中的可选键 `type` **不是 `"Text"` / `"Number"` 等字段类型**！普通字段一律省略 `type`；仅在单选/多选需控制是否允许新增选项（`"1"` 默认不新增，`"2"` 允许新增选项）或附件控制写入模式（`"0"` 默认覆盖，`"1"` 追加新附件）时才传对应数字字符串。
2. **查询 `key` vs 写入 `value` 格式区分（极易混淆！）**：
   - **单选 / 多选 / 下拉**：查询 `filter` 传选项 `key` 数组，但**写入 `fields[].value` 传选项显示值字符串数组**（如 `["已签约"]`）；
   - **成员 / 部门 / 组织角色 / 关联记录 / 子表**：写入 `value` 传真实对象 ID 字符串数组（如 `["accountId1"]`、`["rowId1"]`）；
   - **检查框（Checkbox）**：传 `1`（勾选）或 `0`（未勾选）；**等级（Rating）**：传数字字符串如 `"5"`；**省市区（Region）**：传地区码字符串（可调 `get_regions` 查询）；**定位（Location）**：传含 `x, y, address, title` 的 JSON 字符串；**附件（Attachment）**：传 `[{"name": "合同.pdf", "url": "..."}]`。
3. **多值字段“追加/移除”必先回读合并**：
   - `update_record` 对多选、成员、部门、关联记录及 `type: "0"` 附件均为**整组覆盖替换**；当用户要求“加上某人 / 追加一个标签 / 移除某条关联”时，**必须先调 `get_record_details` 读取现有 ID/值数组，在本地完成增删合并后再写回**，严禁直接只写增量导致历史值被清空！
4. **`triggerWorkflow` 与异常回查防重**：
   - 日常增删改默认不传 `triggerWorkflow` 或传 `true`；仅当目标应用管理员明确要求“静默修改不触发工作流”时才传 `triggerWorkflow: false`（若普通成员要求不触发流程，如实说明平台限制仅应用管理员可关闭工作流触发，切勿强传 `false` 引发权限报错）。
   - 任何写入、审批或流程触发若遇网络超时或返回异常，**必须先调只读详情/列表接口核实是否已生效**，严禁盲目重放造成重复录单或重复触发。

---

## 五、 结果展示与记录直达链接规范

1. **隐藏内部技术标识**：面向用户的回复、确认清单与统计解读中，只展示应用、工作表、字段、选项、角色和人员的**业务名称**（提及工作表名与字段名使用反引号包裹，如 `客户` 表的 `跟进阶段`），**严禁裸露 24 位 `rowId`、`controlId`、`worksheetId`、`instanceId`、`workId`、字段 `alias` 或选项 `key`**。
2. **表格呈现与记录直达链接**：
   - 多条记录明细默认使用精炼 Markdown 表格（常规明细表默认控制在 4～6 列关键字段以内，首列为序号，第二列为记录标题）；修改或新建成功后主动告知记录标题名称。
   - 若上下文已知当前环境前端域名（如用户提供过明道云页面 URL）且持有真实 `appId`、`worksheetId`、`rowId`，将记录标题渲染为可点击直达链接：`[记录标题](https://{前端域名}/app/{appId}/{worksheetId}/row/{rowId})`（上下文现成持有 `viewId` 时可用 `/app/{appId}/{worksheetId}/{viewId}/row/{rowId}`，无需为拼链接额外查视图；未知前端域名时仅展示纯文本标题，严禁臆造域名或 ID）。
