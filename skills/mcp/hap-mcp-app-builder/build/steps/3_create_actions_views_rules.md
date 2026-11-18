# Step 3: 单表结构刷新、自定义动作、视图与业务规则一体化 SOP (`3_create_actions_views_rules`)

<!-- SOURCE: build-app/view-build-sub-agent.yaml -->
<!-- SOURCE: build-app/business-rule-build-sub-agent.yaml -->

## 一、 本地宿主输入与参考映射

- **执行方式**：独立 Subagent 按表并发执行（正常复用一次 `get_worksheet_structure` 结果完成动作、视图、业务规则与字段分片落盘；截断、状态变化或排查需要时按需补读）。
- **输入切片**：读取 `.build/task-context/{taskId}.json`：
  - `planSlice`：`worksheetName`、`views`（紧凑字符串数组）、`customActions`（本表动作数组）、`businessRules`（对应 `businessRulesNotes`）、`requirements`、`appLanguage`；
  - `contextSlice`：`appId`、`worksheetId`（24 位 hex）、`worksheetIdByName`、`artifactPath`（`.build/artifacts/worksheet-{worksheetId}.json`）。
- **必读领域规范**：`references/hap-domain-view-spec.md`、`references/hap-domain-custom-action-spec.md`、`references/hap-domain-business-rule-spec.md`
- **主要业务工具**：`["get_worksheet_structure", "get_custom_action_list", "create_custom_actions", "create_view", "get_view_structure", "update_view", "get_business_rule_list", "create_business_rule"]`
- **子表最小修复**：当 `contextSlice.subtableDisplayChecks` 非空时，额外允许 `update_worksheet`；只修复本任务父表中对应子表字段的显示列。旧任务包没有此属性时按原流程执行。

---

## 二、 核心构建规则与执行步骤

- **输出语言锁定**：视图名、动作文案、规则名称与校验提示消息必须严格使用 `appLanguage` 指定语言。
- **完建优先与契约保真**：遵循 [宿主适配](../../HOST_ADAPTER.md) 先核实 `create_custom_actions`、`create_view`、`create_business_rule` 实时 Schema；中断续跑时先核查线上已建动作/视图/规则防重。字段分片、规划动作和至少 1 个可用视图已落库，且仅有非核心辅助规则受限时，可记入 `issues` 并按成功回执继续；业务场景与规范要求的核心校验、安全或业务规则缺失则保留真实 ID 与缺项，不得虚报完成。流程发布或业务试跑属于后续阶段，不作为本步配置回读的前置条件。

### Step 0：拉取关联落定后的最新完整字段并落盘分片（集中采集供后续步骤复用）
1. `worksheetId` 缺失时，从同批回执、完整上下文或线上工作表定位真实 ID；前置工作未完成则向主调度器报告具体依赖，按宿主适配继续恢复。
2. 优先调用 1 次 `get_worksheet_structure(appId, worksheet_id: worksheetId, responseFormat: "dsl", ai_description: "Worksheet: <worksheetName>")`（此时所有表与双向关联均已落定，直接获取无损结构化 JSON，包含对端 `:bi` 反向关联字段、精确 `options[].key`、`dataSource` 与关联/他表/汇总元数据；超大表发生截断时按分页/分块补齐）。
3. 将结构回读的原始字段保存到本表分片，保留字段属性、选项、默认值、布局和配置；清洗 ID 上的 `(isTitle)` 时保留标题标志。旧分片未采集的属性按未知处理，用到时定向回读。
4. **子表显示列跨阶段补齐**：若 `subtableDisplayChecks` 存在，按名称/alias 和真实目标工作表 ID 在本表结构中定位子表字段；只对成功定位的子表读取其最新结构，核对实际已建的业务列和现有 `config.showFields`。缺少必要录入列时，查实时 `update_worksheet` Schema，用 `editFields` 对该父表字段最小增量合并已有显示列及缺失真实 ID/alias，保留其他属性；不移除既有列、不新建关联、不修改子表或其他父表。结果不明先回读防重；无法定位或修复的列写入 `issues`，不得虚报。各父表任务各自写本表，保持原有并发与任务划分。
5. 将清洗后的单表结构对象 `{ "worksheetId": "<worksheetId>", "worksheetName": "<worksheetName>", "alias": "<本表alias>", "fields": [...] }` 写入 `contextSlice.artifactPath`（`.build/artifacts/worksheet-{worksheetId}.json`），供 `merge_worksheet_context.py` 归并生成阶段 3/4 上下文。

### Part A：自定义动作与视图创建（源自 `view-build-sub-agent.yaml`）
1. **先建自定义动作（若有）**：
   - 若为中断续跑，先调用 `get_custom_action_list(appId, worksheet_id: worksheetId)` 核查已存在动作并直接复用其 `id` 与 `workflowId`，仅补建缺失项；
   - 若 `customActions` 非空，按 `references/hap-domain-custom-action-spec.md` 及各动作的 `requirements`、`runWorkflowAfterSubmit`、`recordScope` 组装参数，调用 1 次 `create_custom_actions(appId, worksheet_id: worksheetId, actions)`；
   - **区分按钮启用与工作流启用**：按钮新建默认 `status: 1`（启用），其预建空壳工作流默认处于未发布（关闭）状态，在 Step 11 发布前不会执行，**因此规划可用的按钮一律保持默认启用（`status: 1`），无需预先停用**；仅方案显式指定停用（`enabled: false` / `status: 0`）时设 `status: 0`，复用已有按钮时不改变其独立停用状态。
   - 记录返回的动作真实 `id` 与原样回传的关联 `workflowId`（回执中写入 `processId` 字段，无流程时为空串），供下一步视图挂载及阶段 4 使用。每个动作回执写 `createdByBuild`（本次新建为 true，复用既有为 false）（历史工程若曾记录 `disabledForWorkflowSetup` / `initialEnabled`，恢复时原样保留）。
2. **再建工作表视图（单表严禁无视图，保持规划视图类型保真）**：
   - 若 `views` 非空：将大驼峰类型转为 API 小驼峰（`Table→table`、`Kanban→kanban`、`Calendar→calendar`、`Gallery→gallery`、`Hierarchy→hierarchy`、`Gantt→gantt` 等），查阅 `create_view` 实时 Schema 匹配本表真实分组/日期/层级字段构建规划视图（误作展示字段的主表名不传；`batchActions` 仅挂载支持批量执行的本表动作；仅当本表确实不存在任何可承载该高级视图类型的真实字段时，才回退为 `table` 并在 `issues` 注明），按 `references/hap-domain-view-spec.md` 将本表缺失视图**合并为一次 `create_view(appId, worksheet_id: worksheetId, views)` 批量提交**；
   - 若 `views` 为空（常见于明细子表）：**必须创建 1 个兜底表格视图** `[{ "name": "全部记录", "type": "table" }]`（英文环境用 `"All"`），确保后续示例数据与查询 API 正常可用；
   - 对规划、复用和兜底视图均应用视图规范。复用同名同类型视图，以 `get_view_structure` 核对每个视图的实际筛选字段及条件并记入回执；缺项用 `update_view` 在原视图补齐。

### Part B：表单业务规则创建（源自 `business-rule-build-sub-agent.yaml`）
1. 结合本表用途、实际字段、`businessRules` 和 `contextSlice.businessRulesNotes`，按 `references/hap-domain-business-rule-spec.md` 与 `create_business_rule` 实时 Schema 落地交互、校验、锁定与样式规则：
   - **同表动态字段比较**：如“结束时间不早于开始时间”，直接使用 `businessRuleDynamicValue`（`{"sourceType": "field", "sourceField": {"sourceType": "currentFormField", "field": "<本表字段ID或alias>"}}`）构造 `validation` 规则；
   - **跨表归属一致与关联带值（`setFieldValue + rcid`）**：遇到“所选设备/地块必须与所属站点一致”或“选站点带出站点负责人”时，优先配置 `interaction` 规则的 `setFieldValue`，通过 `rcid` 从所选设备/地块自动读取其 `所属站点` 赋值给本表 `所属站点`（或从 `所属站点` 读取 `负责人` 赋值给本表 `负责人`），必要时配合 `readonly` 防止误改；若本表已有 `Lookup` 带出字段，也可直接用 `businessRuleDynamicValue` 与本表对应字段做一致性校验；
   - 对无需跨表动态查询即可由字段属性覆盖的条件（如 `required`），在 `outputs.ruleChecks` 记录对应字段属性依据；超出业务规则范围的停用前跨表统计提示等交由流程或说明承接，不作本步失败条件。
2. 对每个适用条件核对全部受影响的真实字段，续作时先查同名及同义规则：
   - 推导 `ruleType`（交互/校验/锁定/样式），纠正不严谨的动作表述（如子表行操作 `permissions` 仅用于 `editable` 动作，不得放入 `show/hide`），构造合法无冲突的 `conditions` 与动作配置块，逐条调用 `create_business_rule`。失败时按 [宿主适配](../../HOST_ADAPTER.md) 排查并继续其他独立规则。

---

## 三、 本地回执落盘契约

在 `outputs.ruleChecks` 逐项记录业务条件（`intent`，承接已有意图时沿用原文；若将一条复合意图拆分为多条规则，可在 `sourceIntent` 保留原句）和依据。由规则落实时记录规则详情中的 `ruleId/name/enabled/conditions`，汇总 ID 到 `ruleIds`；由字段配置承接或业务允许时记录 `fieldId/property/value`（如实际的 required、type、config，多字段逐条拆分或使用 `fieldIds` 数组）及 `reason`。零规则也须交代适用性；核心条件尚未落实时保留缺项续作。

确认 `.build/artifacts/worksheet-{worksheetId}.json` 已写入后，将视图、动作（含 `processId`）及规则计数写入 `receiptPath`（`.build/receipts/step3-view-act-{name}.json`）：

```json
{
  "taskId": "<来自 taskContext.taskId>",
  "runId": "<来自 taskContext.runId>",
  "executor": { "kind": "subagent", "agentId": "<当前子代理标识>" },
  "step": "3",
  "target": { "type": "worksheet", "id": "<worksheetId>", "name": "<worksheetName>" },
  "status": "succeeded",
  "outputs": {
    "worksheetId": "<worksheetId>",
    "worksheetName": "<worksheetName>",
    "viewIdByName": { "<worksheetName>/<视图名>": "<24位真实viewId>" },
    "views": [{ "name": "<视图名>", "id": "<viewId>", "type": "table" }],
    "actionIdByName": { "<worksheetName>/<动作名>": "<动作id>" },
    "actions": [{ "name": "<动作名>", "id": "<动作id>", "processId": "<关联workflowId或空串>", "createdByBuild": true }],
    "rulesCreated": 1,
    "ruleIds": ["<真实规则 ID>"],
    "ruleChecks": [{"intent": "<业务条件>", "ruleId": "<真实规则 ID>", "name": "<回读名称>", "enabled": true, "conditions": {"type": "group", "logic": "AND", "children": [{"type": "condition", "fieldId": "<真实字段 ID>", "operator": "eq", "value": "<实际条件值>"}]}}]
  },
  "verification": {
    "passed": true,
    "evidence": [
      "已拉取最新字段并写入 artifacts 分片文件",
      "已完成自定义动作、视图与表单业务规则创建"
    ]
  },
  "issues": []
}
```
