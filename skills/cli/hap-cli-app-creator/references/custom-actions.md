# Custom Actions — 自定义动作（顶层 `custom_actions[]`）

按钮挂在某工作表上，点击执行一个动作。仅 `trigger_workflow` 按钮在服务端派生一个影子工作流（`update_record`/`create_related` 不产生任何工作流）。

```jsonc
{ "worksheet":"出库单", "name":"提交审批", "type":"trigger_workflow",
  "confirm": true, "confirm_msg":"确认提交审批？",
  "enable_when":[ {"field":"状态","op":"eq","value":"未提交"} ],   // 仅满足条件时按钮可点
  "workflow": "出库单送审" }                                       // 指向 workflows[] 里一条 button 工作流（推荐只改状态，见下「审批解耦」）
```

`type` 三选一：
- `update_record`：更新当前记录。必填 `update_fields`(用户填写的字段逻辑名列表)。
- `create_related`：新建关联记录。必填 `relation_field`(本表的 Relation 字段逻辑名)。
- `trigger_workflow`：触发一条工作流。必填 `workflow`(**字符串**)=顶层 `workflows[]` 里那条工作流的逻辑名——
  **工作流的节点拓扑写在那条工作流里，不内联到按钮上**（按钮只是触发器）。

通用键：`confirm`/`confirm_msg`(二次确认)、`enable_when`(通用筛选器，按钮启用条件——选项字段填显示名)。

## `enable_when`（按钮启用/触发条件）

可选。仅当当前记录满足条件时按钮才可点。结构与视图 `filter` **完全相同**（同一套通用筛选器）。不传则始终可用。

> ⚠️ **必须根据业务逻辑判断是否设置 `enable_when`，不要默认省略。**
>
> - 若按钮有前置状态要求（如「借书」要求图书状态为「在库」、「发货」要求订单状态为「已付款」），**必须设置 `enable_when`**。
> - 只有真正无前置条件的操作（如「添加备注」、「发送通知」）才可不设。

## 挂载与设计原则

- 动作挂在**操作发起方**的表上，不挂目标表（「发起借阅」按钮在「图书」表，「归还」按钮在「借阅记录」表）。
- **审批不要拆成「通过」「驳回」两个按钮**——审批块 + 审批结果分支始终放在工作流里，绝不散成按钮。**推荐「状态驱动」解耦**（见下「审批解耦」）：按钮工作流只把状态改成「审批中」，审批块单独放进一条 `record_update`、筛选「状态=审批中」的工作流里。这样审批流程可复用、按钮侧更轻。一次性的简单审批也可把审批块直接内联进按钮工作流，两种都能发布。
- `create_related` 必须有真实的 Relation 字段作桥：源表 `fields` 里要显式声明该 Relation 字段并在 `relation_field` 引用它；
  两表间没有 Relation 就别用 `create_related`，改用 `trigger_workflow` 让后台工作流建关联记录。

## `trigger_workflow` ↔ 顶层 button 工作流（成对出现）

一个 `trigger_workflow` 按钮，必须在 `workflows[]` 里**配一条** `trigger.type:"button"` 的工作流，二者按逻辑名配对：

```jsonc
// custom_actions[]
{ "worksheet":"出库单","name":"提交审批","type":"trigger_workflow","workflow":"出库单送审",
  "enable_when":[ {"field":"状态","op":"eq","value":"未提交"} ] }

// workflows[]  —— 节点拓扑在这里
{ "name":"出库单送审", "trigger":{ "type":"button" }, "nodes":[ ... ] }
```

- 配对是**一对一**：一个 button 工作流只能被一个 `trigger_workflow` 按钮指向（校验会拦多对一/找不到/类型不是 button）。
- 节点写法（节点类型、按 nodeType 取 config 键、wfFieldPatch / wfValueRef / wfAccount）全部见 **[workflows.md](workflows.md)**；
  工作流隐藏规则见 **[workflow-gotchas.md](workflow-gotchas.md)（生成前必读）**。
- 构建顺序：按钮先建（派生空的影子流程），工作流阶段再在该影子流程上加节点并发布——你无需关心，执行器自动处理。

### 审批解耦：按钮只改状态 + `record_update` 流承载审批（推荐）

审批这类「人工发起、后台流转」的动作，**推荐拆成两条工作流**，而不是把审批块塞进按钮工作流：

```jsonc
// ① 自定义动作：按钮 → 一条只改状态的 button 工作流
{ "worksheet":"出库单","name":"提交审批","type":"trigger_workflow","workflow":"出库单送审",
  "enable_when":[ {"field":"单据状态","op":"eq","value":"未提交"} ] }

// ② button 工作流：只把状态推进到「审批中」，别的什么都不做
{ "name":"出库单送审", "trigger":{ "type":"button" },
  "nodes":[ { "nodeType":"update_record","name":"置为审批中",
    "config":{ "worksheet":"出库单","target":{"kind":"record","node":{"nodeAlias":"trigger"}},
      "fields":[ {"fieldId":"出库单/单据状态","value":"审批中"} ] } } ] }

// ③ record_update 工作流：状态变为「审批中」时触发，审批块 + 结果分支都在这里
{ "name":"出库审批",
  "trigger":{ "type":"record_update","worksheet":"出库单","fields":["单据状态"],
    "filter":{ "items":[ {"left":{"kind":"field","node":{"nodeAlias":"trigger"},"fieldId":"出库单/单据状态"},
                          "op":"eq","right":{"kind":"literal","value":"审批中"}} ] } },
  "nodes":[ /* approval_block + 审批结果分流（PASS/OVERRULE/REVOKE/SUSPEND） */ ] }
```

**为什么这样拆**：
- **可复用**：审批流程只认「状态=审批中」，任何把状态改成审批中的途径（按钮、其它工作流、批量改）都会拉起同一条审批，不必每个入口各写一遍审批块。
- **按钮更轻**：按钮工作流退化成单节点改状态，逻辑清晰。
- **不会死循环**：审批结果分支把状态改成「已审批/审批未通过/未提交/已取消」等——都不等于「审批中」，过不了触发筛选，不会回头再触发自己。⚠️ 因此**审批结果的任何分支都不要再把状态写回「审批中」**，否则自触发。
- HAP 默认不区分更新来源：button 工作流的状态更新**会**触发上面的 `record_update` 流（这正是链路成立的前提）。

> 简单的一次性审批，也可以不拆——直接在按钮工作流里 `update_record`(置审批中) → `approval_block` → 结果分支。两种写法都已 live 验证可发布；按「是否要复用 / 是否有多个入口」二选一。

> 完整正例见 [examples/warehouse/04-workflows.design.json](../examples/warehouse/04-workflows.design.json)：`出库单送审`/`入库单送审`(button 只改状态) + `出库审批`/`入库审批`(record_update 承载审批块) + `执行出库`。
