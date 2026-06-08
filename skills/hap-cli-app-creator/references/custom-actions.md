# Custom Actions — 自定义动作（顶层 `custom_actions[]`）

按钮挂在某工作表上，点击执行一个动作。每个按钮在服务端派生一个影子工作流。

```jsonc
{ "worksheet":"出库单", "name":"提交审批", "type":"trigger_workflow",
  "confirm": true, "confirm_msg":"确认提交审批？",
  "enable_when":[ {"field":"状态","op":"eq","value":"未提交"} ],   // 仅满足条件时按钮可点
  "workflow": "出库审批" }                                         // 指向 workflows[] 里一条 button 工作流
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
- **审批不要拆成「通过」「驳回」两个按钮**——用一个 `trigger_workflow` 按钮，里面放审批块 + 审批结果分支。
- `create_related` 必须有真实的 Relation 字段作桥：源表 `fields` 里要显式声明该 Relation 字段并在 `relation_field` 引用它；
  两表间没有 Relation 就别用 `create_related`，改用 `trigger_workflow` 让后台工作流建关联记录。

## `trigger_workflow` ↔ 顶层 button 工作流（成对出现）

一个 `trigger_workflow` 按钮，必须在 `workflows[]` 里**配一条** `trigger.type:"button"` 的工作流，二者按逻辑名配对：

```jsonc
// custom_actions[]
{ "worksheet":"出库单","name":"提交审批","type":"trigger_workflow","workflow":"出库审批",
  "enable_when":[ {"field":"状态","op":"eq","value":"未提交"} ] }

// workflows[]  —— 节点拓扑在这里
{ "name":"出库审批", "trigger":{ "type":"button" }, "nodes":[ ... ] }
```

- 配对是**一对一**：一个 button 工作流只能被一个 `trigger_workflow` 按钮指向（校验会拦多对一/找不到/类型不是 button）。
- 节点写法（节点类型、按 nodeType 取 config 键、wfFieldPatch / wfValueRef / wfAccount）全部见 **[workflows.md](workflows.md)**；
  工作流隐藏规则见 **[workflow-gotchas.md](workflow-gotchas.md)（生成前必读）**。
- 构建顺序：按钮先建（派生空的影子流程），工作流阶段再在该影子流程上加节点并发布——你无需关心，执行器自动处理。

> 完整正例见 [examples/warehouse/04-workflows.design.json](../examples/warehouse/04-workflows.design.json)（`custom_actions` + `workflows`）（提交审批 / 执行出库）。
