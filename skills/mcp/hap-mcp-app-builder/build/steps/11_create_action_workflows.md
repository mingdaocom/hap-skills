# Step 11: 单个自定义动作工作流设计、注入与发布 SOP (`11_create_action_workflows`)

<!-- SOURCE: build-app/custom-action-design-sub-agent.yaml -->
<!-- SOURCE: build-app/custom-action-workflow-sub-agent.yaml -->

## 一、 本地宿主输入与参考映射

- **执行方式**：独立 Subagent 按**单个自定义动作**并发执行，在同一子代理上下文内一气呵成完成 **「读取预建触发节点与数据源核对 ➔ 7 维闭环节点设计 ➔ 物理节点注入 ➔ 校验修复与发布」**。动作空壳流程已由 Step 3 `create_custom_actions` 自动预建，本步**严禁调用 `create_process`**。
- **输入切片**：读取 `.build/task-context/{taskId}.json`：
  - `planSlice`：`actionWorkflow`（该按钮动作完整规划定义，含所属 `worksheet`、动作 `name`、`type`、`runWorkflowAfterSubmit`、`description`、`intentHints`、`requirements`）、`workflowIndex`、`customActionIndex`、`appLanguage`；
  - `contextSlice`：`appId`、`orgId`、`processId`（Step 3 按 `worksheet::action` 精确捕获的预建 `workflowId`）、`worksheetIdByName`、`roleContext`、`viewIdByName`；
  - `worksheetContextSlice`：已建工作表真实 `worksheetId` 及字段 `{ name, id, alias, type, options }`（含选项 `{ key, value, index }`）。
- **必读领域规范**：`references/hap-workflow-design-guide.md`、`references/hap-domain-workflow-spec.md`
- **主要业务工具**：`["get_custom_action_list", "update_custom_action", "find_member", "find_department", "get_current_user", "get_worksheet_field", "get_worksheet_structure", "get_workflow_structure", "get_workflow_node", "get_workflow_variables", "update_workflow_node", "update_workflow_variables", "batch_create_process_nodes", "batch_delete_process_nodes", "validate_process", "publish_process", "get_sms_signatures"]`

---

## 二、 核心构建规则与执行步骤

### 1. 触发节点物理 `nodeId` 读取与数据源设计规则（核心铁律！）
1. **核实预建 `processId`（支持线上动作列表自愈补齐）**：检查 `contextSlice.processId`（按 `worksheet::action` 精确绑定所属表动作，严禁跨表混用同名按钮）；若为空，立即调用 `get_custom_action_list(appId, worksheet_id: <所属表真实worksheetId>)` 查找同名按钮动作，直接读取其返回的 `workflowId` 作为 `processId` 继续执行，仅当前置按钮动作本身在线上不存在时才向主调度器报告依赖缺口。
2. **首步读取物理 `nodeId`（严禁使用别名）**：
   - 自定义动作预建流程的触发节点**没有可用触发别名**！**绝对禁止**使用 `{ "nodeAlias": "trigger" }`（否则必触发 `StartNodeControlsIsNull` 错误）；
   - **第一步必须调用 `get_workflow_structure(workflow_id: processId)`**，提取触发节点的真实**物理 `nodeId`** 及真实数据源模式（单条 `single` / 多条批量 `multiple` / 表单提交后触发 `runWorkflowAfterSubmit`），后续所有节点引用触发记录一律使用 `{ "nodeId": "<真实触发nodeId>" }`，公式/模板占位符使用 `$<真实触发nodeId>-<24位真实fieldId>$`。
3. **基于真实结构与数据源语义完成节点设计（源自 `custom-action-design-sub-agent.yaml`）**：
   - 严格基于 `worksheetContextSlice` 真实存在的表、24 位字段 `id`（禁传 `alias`）与选项真实 `key`（禁传中文 `value`）设计节点；上游描述若与真实字段类型、触发所属表或节点能力不符，保留业务目标并按真实结构纠正为最简合法节点设计（单条记录的多选人员/部门字段直接由单个通知节点群发，不拆成 `sub_process`；`compute` 仅用于数值或日期计算）；
   - 将动作的 `description`、`intentHints` 与 `requirements` 落实为完整闭环（区分按钮所在表、表单提交记录与回写目标；需要跨表取值时通过真实关联定位目标记录）；多条批量数据源（`multiple`）注意批量处理语义，表单提交后触发基于提交后的当前记录字段设计。
   - **审批动作（含 `approval_block`，如「提交审批」）双分支闭环硬门禁**：
     1. **进入审批前**：先通过 `update_record` 将当前单据状态置为“待审批 / 审核中”（真实选项 `key`）；
     2. **审批后双分支必配**：按当前 Schema 选择合法位置。父流程若支持读取审批块最终结果，可在块后使用支持该输出的普通条件分支；若 `approval_result` 仅接受 `approve` 前驱，须在审批块内部 `approve` 之后建立该分支，不能接在父流程 `approval_block` 后。路径首节点的 `prevNode` 指向分支、`parentNode` 指向对应路径，更新引用该作用域内真实记录节点，完整覆盖：
        - **通过路径**：`update_record` 将状态置为业务约定的通过后状态（真实选项 `key`）+ 必要业务联动回写 + 使用当前 Schema 支持的通知节点通知申请人；
        - **驳回路径**：`update_record` 将状态回退为“已驳回 / 草稿”（真实选项 `key`）+ 使用当前 Schema 支持的通知节点通知申请人修改重提；
     3. **严禁只建孤立的 `approval_block` 漏写通过/驳回状态回写分支就发布上线！**

### 2. 参数核实、节点注入与校验上线（源自 `custom-action-workflow-sub-agent.yaml`）
1. **高效参数核对**：按 [宿主适配](../../HOST_ADAPTER.md) 与任务包内联的 `references/hap-domain-workflow-spec.md` 构造 `get_workflow_structure`、`batch_create_process_nodes`、`update_workflow_node`、`validate_process`、`publish_process` 参数；**预编译任务包已内联全部规则与字段，严禁使用 `Glob`/`find`/`ls`/`Grep` 翻找外部 skill 目录（含 `10_create_workflows.md`、`*.yaml`、`references/*.md`）或历史回执搜寻节点 Schema**，遇宿主折叠深层 Schema 时直接按 [宿主适配](../../HOST_ADAPTER.md) 受控试调 1 次并按服务端报错路径修参。
2. **组织身份解析**。确认规划角色真实存在，按 `roleContext` 或 `roleIdByName` 绑定真实角色 ID。角色成员为空或未知属运行态常规事项，不追问、不自动加人、不阻止发布，也无需写入 `issues`（终结交付总结已统一提醒）。身份无法确认则继续无依赖配置并报告具体缺口。只有方案指定固定人员、部门或签名时才解析对应身份。
3. **批量创建节点（免注入后重复回读）**：调用 `batch_create_process_nodes(workflow_id: processId, nodes)` 注入完整节点链（流程内各 `nodeAlias` 保持唯一，不直接写只读衍生字段）；注入成功后直接进入下一步 `validate_process`，**无需在注入后或发布后重复调用 `get_workflow_structure` 回读**。
4. **内部块先内后外发布、等价自愈与主流程发布**：
   - 含 `approval_block / sub_process / loop` 时，先对内部 `processId` 完成校验与 `publish_process`；
   - 对主流程调用 `validate_process(workflow_id: processId)`，若有 `issues` 或设计与真实来源/字段不一致，按 `references/hap-domain-workflow-spec.md` 第四节（`nodeId / path / hint`）用 `update_workflow_node`（`config` 为原生 Object）或局部补建/重建**主动完成等价自愈并补齐合理默认参数**，严禁私自删减核心业务节点凑发布；
   - 遵循 [宿主适配](../../HOST_ADAPTER.md)「零代码建模与配置态交付原则」：配合按钮 `enableWhen` 与流程内前置状态过滤保障幂等；只要节点齐全且 `validate_process` 返回 `valid: true`，**必须立即调用 `publish_process(workflow_id: processId)` 发布上线**，不因运行态事项或底层并发锁假设保留草稿。
5. **核对按钮启用状态（默认已启用免回读）**：按钮启用与工作流发布相互独立（Step 3 新建规划可用按钮已默认启用 `status: 1`）。若方案未显式规划停用且 `contextSlice.actionProvenance.disabledForWorkflowSetup` 不为 `true`，直接填 `outputs.actionEnabled: true`，**无需再调用 `get_custom_action_list` 回读**；仅当 `disabledForWorkflowSetup: true` 或恢复续作状态未知时，才调用 `get_custom_action_list` 核对并用 `update_custom_action(enabled: true)` 恢复启用（方案显式规划停用或非本工程既有且独立停用的按钮保持原状）。不要求业务试跑，也无需将“未业务试跑”写入 `issues`。

---

## 三、 本地回执落盘契约

> **顶层 `status` 与 `outputs.status` 严格区分铁律**：
> - 顶层 `"status"` 表示**本搭建任务是否完成节点注入落库**（枚举仅 `"succeeded" | "failed"`）；`outputs.status` 表示**线上动作流的发布状态**（`"published" | "draft"`）。
> - 核心配置与身份齐全、校验通过须立即发布，并核实应启用按钮为 `outputs.actionEnabled: true`、`issues: []`。通用的角色未分配成员、未运行态业务试跑不写入 `issues`（终结交付总结已统一提醒），不当作草稿理由。仅当存在实际配置缺口、接口调用报错或外部必需短信签名确实缺失导致服务端拒绝发布时，才保留 ID 和具体证据并报告未完成或写入 `issues`。

执行完成后，写入 `receiptPath`（`.build/receipts/step11-act-wf-{ws}_{name}.json`）：

```json
{
  "taskId": "<来自 taskContext.taskId>",
  "runId": "<runId>",
  "executor": { "kind": "subagent", "agentId": "<agentId>" },
  "step": "11",
  "target": { "type": "workflow", "id": "<processId>", "name": "<worksheet>/<actionName>" },
  "status": "succeeded",
  "outputs": {
    "worksheetName": "<worksheet>",
    "actionName": "<actionName>",
    "processId": "<processId>",
    "status": "published",
    "actionId": "<精确匹配的动作 ID>",
    "actionEnabled": true,
    "description": "<已发布简述用途；若为 draft/skipped/unknown 说明具体原因>"
  },
  "verification": {
    "passed": true,
    "evidence": ["已获取触发节点物理 nodeId，完成动作工作流节点设计、注入与 publish_process 发布"]
  },
  "issues": []
}
```
