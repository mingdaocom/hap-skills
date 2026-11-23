# Step 10: 单条系统工作流设计、创建、校验与发布 SOP (`10_create_workflows`)

<!-- SOURCE: build-app/workflow-design-sub-agent.yaml -->
<!-- SOURCE: build-app/workflow-build-sub-agent.yaml -->

## 一、 本地宿主输入与参考映射

- **执行方式**：独立 Subagent 按**单条系统工作流**并发执行，在同一子代理上下文内一气呵成完成 **「7 维闭环节点设计 ➔ 真实 ID 与身份映射 ➔ 物理建流与节点注入 ➔ 校验修复与发布」**，消除双阶段 JSON 传话失真与重复读表开销。
- **输入切片**：读取 `.build/task-context/{taskId}.json`：
  - `planSlice`：`workflow`（来自 `hap-plan.json` 的单条系统流定义，含 `name`、`description`、`trigger`、`intentHints`、`requirements`）、`workflowIndex`（全应用系统流职责索引）、`customActionIndex`（全应用动作流职责索引）、`relationLayouts`、`appLanguage`；
  - `contextSlice`：`appId`、`orgId`（用于人员/部门查询）、`worksheetIdByName`、`roleContext`（`[{ name, id, roleScope }]`）、`viewIdByName`；
  - `worksheetContextSlice`：已建工作表真实 `worksheetId` 及字段 `{ name, id, alias, type, options }`（含选项 `{ key, value, index }`）。
- **必读领域规范**：`references/hap-workflow-design-guide.md`、`references/hap-domain-workflow-spec.md`
- **主要业务工具**：`["find_member", "find_department", "get_current_user", "get_worksheet_field", "get_worksheet_structure", "create_process", "get_workflow_structure", "get_workflow_node", "get_workflow_variables", "update_workflow_node", "update_workflow_variables", "batch_create_process_nodes", "batch_delete_process_nodes", "validate_process", "publish_process", "get_sms_signatures"]`

---

## 二、 核心构建规则与执行步骤

### 1. 基于真实表结构的节点拓扑设计（源自 `workflow-design-sub-agent.yaml`）
1. **只用真实上下文与主动等价纠正**：严格基于 `worksheetContextSlice` 中真实存在的表名、24 位字段 `id` 与选项 `key` 设计条件、查询、计算和更新，严禁捏造不存在的字段或选项；上游描述中的实现细节若与真实字段类型、表关系或节点能力不符，保留业务目标并按真实结构纠正为最简合法节点设计（如单条记录的多选人员/部门字段直接由单个通知节点群发，不拆成 `sub_process`；`compute` 仅用于数值或日期计算，文本拼接直接在模板中完成）。对照 `workflowIndex` 与 `customActionIndex` 明确本流程边界，避免与按钮动作流重复写数或互相循环触发。
2. **完整因果闭环**：将 `workflow` 的 `description`、`intentHints` 与 `requirements` 全部落实为“触发（更新时间触发必设具体监听字段防死循环）→ 必要关联/单条取数 → 业务计算/审批/分支 → 状态与关联写回/通知”的完整节点链，不得停留在仅取数的半截步骤。
3. **审批块（`approval_block`）双分支闭环硬门禁**：
   - 凡包含 `approval_block` 的审批流程，**严禁只建一个孤立的 `approval_block` 就结束或发布**！
   - 审批前确保单据状态处于“待审批/审核中”（若触发条件本身未限定或前置未置状态，先用 `update_record` 写入对应选项 `key`）；
   - **必须完整处理通过与驳回两种审批结果**：按当前 Schema 选择合法位置。父流程若支持读取审批块最终结果，可在块后使用支持该输出的普通条件分支；若 `approval_result` 仅接受 `approve` 前驱，须在审批块内部 `approve` 之后建立该分支，不能接在父流程 `approval_block` 后。路径首节点的 `prevNode` 指向分支、`parentNode` 指向对应路径，更新引用该作用域内真实记录节点：
     - **通过路径**：调用 `update_record` 将状态更新为业务约定的通过后状态（真实选项 `key`）+ 完成必要的下游关联写回/台账生成 + 使用当前 Schema 支持的通知节点通知发起人；
     - **驳回路径**：调用 `update_record` 将状态回退为“已驳回/待修改”（真实选项 `key`）+ 使用当前 Schema 支持的通知节点通知发起人驳回信息以便修改重提。
4. **人员与通知语义保真**。确认应用角色真实存在，并从 `roleContext` 或 `roleIdByName` 绑定该角色真实 ID（`PersonRef { kind: "role", id }`）。角色成员为空或数量未知仅记入 `issues` 说明审批、通知可能无人接收；不追问成员、不自动加人、不因此阻止发布。角色身份无法确认则继续无依赖配置并如实报告身份缺口。固定人员或部门用 `find_member` / `find_department`，组织参数取 `contextSlice.orgId`。“通知我”用 `get_current_user`，运行时发起人用 `triggerUser`，短信签名用 `get_sms_signatures`。

### 2. 物理创建、参数核实与发布流水线（源自 `workflow-build-sub-agent.yaml`）
1. **高效参数核对与 `appId` 必传铁律**：
   - 按 [宿主适配](../../HOST_ADAPTER.md) 与任务包内联的 `references/hap-domain-workflow-spec.md` 构造 `create_process`、`batch_create_process_nodes`、`update_workflow_node`、`validate_process`、`publish_process` 参数；**预编译任务包已内联全部规则与字段，严禁使用 `Glob`/`find`/`ls`/`Grep` 翻找外部 skill 目录（含 `*.yaml`、`references/*.md`、其他步骤文档）或历史回执搜寻节点 Schema**，遇宿主折叠深层 Schema 时直接按 [宿主适配](../../HOST_ADAPTER.md) 受控试调 1 次并按服务端报错路径修参；所有应用内流程接口调用时均须显式传入 `"appId": contextSlice.appId`。
2. **字段与选项铁律**：
   - 节点中引用业务 `fieldId` **必须使用 24 位真实 `id`，严禁传 `alias`**；
   - 给单选/多选/下拉字段赋值时，**必须且只能传选项的真实 `key`**，严禁传中文名 `value`！关联取数节点的目标表由来源关联字段自动推导，不传 `worksheetId`；严禁直接更新公式/汇总/他表只读衍生字段。
3. **创建流程外壳**：若 `worksheet_event` / `date_field` 的触发工作表 ID 缺失，先核对工程上下文与线上表列表；仍无法定位时报告依赖缺口，不伪造 ID 或跳过必需流程。恢复时用已有流程 ID 回读；缺 ID 时用 `get_workflow_list` 按名称、触发表和触发类型定位，再核对节点。复用本工程的流程，只补缺项，已发布且符合方案的直接回执。确认尚未创建时调用 `create_process(appId, name, description, publish: false, trigger)`，读取返回的 `processId` 与 **`triggerAlias`**（缺失 `triggerAlias` 时按需调用 `get_workflow_structure` 兜底取 `trigger.nodeAlias`）。
4. **批量注入节点与内部块由内向外发布**：
   - 调用 `batch_create_process_nodes(workflow_id: processId, nodes)` 一次性或分组写入节点（触发记录引用使用 `triggerAlias`）；
   - 若含 `approval_block / sub_process / loop`，单独对其内部 `processId` 完成校验与 `publish_process`，**先内后外**。
5. **校验定点修复、等价自愈与主流程发布**：
   - 调用 `validate_process(workflow_id: processId)`；若有 `issues` 或设计与真实接口/字段不一致，按 `references/hap-domain-workflow-spec.md` 第四节（`nodeId / path / hint`）用 `update_workflow_node`（`config` 传原生 Object）或局部补建/重建**主动完成等价自愈并补齐合理默认参数**，严禁静默删减审批或通知节点凑发布；
   - 遵循 [宿主适配](../../HOST_ADAPTER.md)「零代码建模与配置态交付原则」：流程内通过前置状态查询/分支过滤保障幂等；只要核心节点齐全且 `validate_process` 返回 `valid: true`，**必须立即调用 `publish_process(workflow_id: processId)` 发布上线**（超时或结果未知先回读防重），不因运行态事项或底层并发锁假设保留草稿。

---

## 三、 本地回执落盘契约

> **顶层 `status` 与 `outputs.status` 严格区分铁律**：
> - 顶层 `"status"` 表示**本搭建任务是否完成落库**（枚举仅 `"succeeded" | "failed"`）；`outputs.status` 表示**线上工作流的发布状态**（`"published" | "draft"`）。
> - `validate_process` 通过并调用 `publish_process` 完成后，以 `status: "succeeded"` 和 `outputs.status: "published"` 记成功；角色成员为空或未知、尚未试跑仅记入 `issues`，不当作草稿理由。仅当接口报错或外部必需短信签名确实缺失导致服务端拒绝发布时，才保留真实 ID 与证据记录未完成。

执行完成后，写入 `receiptPath`（`.build/receipts/step10-sys-wf-{name}.json`）：

```json
{
  "taskId": "<来自 taskContext.taskId>",
  "runId": "<runId>",
  "executor": { "kind": "subagent", "agentId": "<agentId>" },
  "step": "10",
  "target": { "type": "workflow", "id": "<processId>", "name": "<workflowName>" },
  "status": "succeeded",
  "outputs": {
    "workflowName": "<workflowName>",
    "processId": "<processId>",
    "status": "published",
    "description": "<已发布简述用途；若为 draft/skipped/unknown 说明具体原因>"
  },
  "verification": {
    "passed": true,
    "evidence": ["已完成系统工作流节点设计、创建、validate_process 校验与 publish_process 发布"]
  },
  "issues": []
}
```
