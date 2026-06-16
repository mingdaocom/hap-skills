# Workflows — 自动化工作流（顶层 `workflows[]`）

> ## ⛔ 完整性铁律（违反即为失败交付）
>
> **必须按方案设计实现工作流的完整业务逻辑，一个节点都不许省。**
> - 方案里规划了审批，就**必须**用审批块（`approval_block` + `approve` + 审批结果分支），**不许**退化成"只更新一个状态字段"。
> - 方案里有冲突校验/库存扣减/多级流转/异常分支，就**必须**用 `get_single`/`get_relation_records`/`query_update`/`branch`/`sub_process` 把它建出来。
> - **严禁**以「避免发布风险」「降低复杂度」「先覆盖简单场景」「审批太复杂容易出错」等任何借口，把一条多节点流程**简化成单节点**（如只发个通知、只改个状态）。这是**不可接受**的偷工减料。
> - 这套框架的审批块/子流程/分支/查询并更新**都已 live 验证可发布**（见 [examples/warehouse/04-workflows.design.json](../examples/warehouse/04-workflows.design.json)：`入库审批`/`出库审批`=record_update 触发(筛选「状态=审批中」)+审批块+优先级分支+4 路结果分支，配 `入库单送审`/`出库单送审` 按钮流只改状态——「状态驱动审批」解耦模式；执行出库=取关联+子流程+查询并更新）。复杂工作流**能建出来**，不存在"风险"理由。
> - 节点哪里容易写错，照 [workflow-gotchas.md](workflow-gotchas.md) 一条条对；写错就按真实报错改，**而不是把流程砍简单**。
> - 自检：每条工作流的节点数与复杂度，应与方案里该流程的业务描述**相称**。一条"提交→冲突校验→审批→下达/驳回"的流程若只生成 1~2 个节点，就是错的，必须重做。

## 工作流结构

```jsonc
{ "name":"安全水位预警", "trigger":{ "type":"record_update","worksheet":"库存","fields":["当前数量"] },
  "nodes":[ ... ] }
```

> 本文是节点/触发器的**结构参考**。工作流的隐藏规则（不写就建错/发布失败）单独在
> 按钮触发的工作流也写在这里（`trigger.type:"button"`），只是再由一个 `trigger_workflow` 自定义动作按逻辑名指向它（见 [custom-actions.md](custom-actions.md)）。所有工作流的节点写法都一样。

> 下面先讲**怎么设计一条好的工作流**（设计清单 + 节点用途 + 设计规则），再往下是各触发器/节点的**参数结构规范**。

## 设计清单（每条工作流必须逐项思考）

拿到每条工作流后，依次回答以下问题，将答案体现在最终节点方案中：

1. **触发时机**：触发时这条记录处于什么业务状态？有哪些字段已有值？
2. **主表更新**：触发后，主表的哪些字段需要更新？（状态、时间戳、操作人等）
3. **关联表联动**：逐表扫描 `worksheets`——这次变化会影响哪些关联表？需要查询和更新什么？
4. **是否需要审批**：这个业务动作是否涉及人工审核？审批通过/否决后分别如何处理？
5. **分支细化**：是否存在多种业务情况需要区分处理？
6. **通知策略**：谁需要知道这件事？用什么方式通知？
7. **异常处理**：查不到数据怎么办？状态不符合预期怎么办？

## 节点类型速查（名称与用途）

> 下表只列**本执行器支持**的节点，名称即 `nodeType` 键。每个节点认的 `config` 键见本文后面《节点 `nodes[]`》的表格；坑点见 [workflow-gotchas.md](workflow-gotchas.md)。

| nodeType               | 名称       | 用途                                          |
|------------------------|----------|---------------------------------------------|
| `get_single`           | 查询单条记录   | 按条件从指定工作表查询一条记录                             |
| `get_multiple`         | 查询多条记录   | 按条件查询多条记录                                   |
| `get_relation_records` | 取关联/子表多条 | 从当前记录的关联/子表字段取多条记录                          |
| `update_record`        | 更新记录     | 更新指定记录的字段值                                  |
| `create_record`        | 新增记录     | 在指定工作表中新增一条记录                               |
| `query_update`         | 查询并更新    | 定位记录后就地更新（扣减/累加，addType 0/1/2）              |
| `delete_record`        | 删除记录     | 删除指定记录                                      |
| `branch`               | 条件分支     | 根据字段值条件进入不同处理分支                             |
| `sub_process`          | 子流程      | 对多条记录逐条执行一组节点                               |
| `approval_block`       | 审批流程     | 审批容器，内部可包含 approve、fill_in 和任意节点            |
| `approve`              | 审批节点     | 发起人工审批（**只能在 approval_block 内使用**）          |
| `fill_in`              | 填写节点     | 发起人工填写                                      |
| `rollup`               | 汇总统计     | 对多条记录做聚合运算（count/sum/avg/max/min）           |
| `compute`              | 运算       | 数值公式、日期差值或日期偏移                              |
| `cc`                   | 抄送       | 将记录详情通知给指定人员查看（**仅单条记录**）                   |
| `notice`               | 站内通知     | 发送站内消息通知（不需要数据源）                            |
| `send_email`           | 发送邮件     | 发送邮件通知                                      |

## 设计规则

### 1. 关联表联动（必须检查）

每条工作流触发时，**逐表扫描** `worksheets`，判断是否有其他表需要同步更新：

- 子表记录变化 → 主表的统计字段（数量/金额）或状态字段是否需要更新？
- 主表字段修改 → 关联的子表记录是否需要同步？
- 记录状态变更 → 其他业务表的可用数量、占用状态是否受影响？

> 示例：借阅记录新增时，不仅要更新本表字段，还应查询并更新「图书」表的馆藏状态；归还时恢复。

### 2. 前置数据查询（先查后用）

如果某个节点需要更新**其他工作表**的记录，必须先安排一个查询节点：

- 触发记录本身可直接操作
- 其他表的记录必须先通过查询（`get_single`/`get_multiple`/`get_relation_records`）获取，然后再更新
- 定时触发的工作流没有触发记录，**必须**通过查询获取待处理数据

在方案中明确标注每个更新节点的数据来源。

### 3. 状态流转完整性

当涉及状态变更时，检查是否覆盖完整的状态链：

- 主记录状态更新 → 是否需要同步写入时间戳（完成时间、审批时间）？
- 是否需要记录操作人（审批人、处理人）？
- 关联表的状态是否需要联动更新？

### 4. 分支处理

存在多种条件走不同路径时，安排分支节点：

- 状态字段多种取值 → 不同处理（如审批通过/否决/撤回）
- 数值区间判断（如金额 > 阈值走审批）
- 查询结果为空/非空的不同后续

#### 查询结果分支（重要）

- **`get_single` 结果分支**：可直接在分支条件中判断该查询节点的系统列 `rowid` 是否为空（`rowid` 不为空 = 找到记录，为空 = 未找到），无需额外节点。写法：`left:{kind:"field", node:{nodeAlias:"查询节点别名"}, fieldId:"rowid"}`。
- **`get_multiple` 结果分支**：不能直接判断结果是否为空。**必须先安排一个 `rollup` 汇总节点**（对查询结果做 COUNT），然后在分支中判断汇总值（如 count > 0 / count == 0）。

### 5. 审批环节补全

涉及资金支出、库存变更、权限变更、合同签署等关键业务操作，即使需求与计划方案未提及审批，也应主动考虑是否需要补全审批流程块。审批节点设计时需明确：

- 审批人：使用应用角色或人员字段（动态审批人）
- 审批模式：会签（全部通过）/ 或签（任一通过）/ 依次审批

审批结果有**两种处理位置**，按需要选用（也可并用）：

> ⚠️ **① 主流程结果分支**（块外，最常用）：在 `approval_block` 之后接一个 `branch`，读审批块的虚拟字段 `result`，按 `PASS`/`OVERRULE`/`REVOKE`/`SUSPEND`（通过/否决/撤回/中止）分流，在各路径下用 `update_record` 写状态/时间戳。
>
> 写法：分支条件 `left:{kind:"field", node:{nodeAlias:"审批块别名"}, fieldId:"result"}`，`op:"eq"`，`right:{kind:"literal", value:"PASS"}`。完整正例见 [examples/warehouse/04-workflows.design.json](../examples/warehouse/04-workflows.design.json) 的「审批结果分流」。

> ⚠️ **② 内部审批结果分支**（块内，紧跟 `approve` 节点）：在 `approval_block` 的 `process.nodes` 里、`approve` 节点之后放一个**结果分支** `branch`，按审批节点本身的通过/否决就地处理。写法：
>
> ```jsonc
> { "nodeType":"branch", "name":"审批结果",
>   "config":{ "result_branch": true, "paths":[
>     { "result_type":"pass",     "nodes":[ /* update_record... */ ] },
>     { "result_type":"overrule", "nodes":[ /* update_record... */ ] }
>   ] } }
> ```
>
> - `result_branch:true` + 每个 path 的 `result_type`（`pass`/`overrule`）取代 `condition`——**不要再写 condition**。
> - **块内节点引用被审批的记录，别名用 `approval_trigger`，不是 `trigger`**（块内是独立子流程；用 `trigger` 会跨流程绑定失败、发布报 warningType 200）。例：`"target":{"kind":"record","node":{"nodeAlias":"approval_trigger"}}`。
> - 同一套结果分支也适用于**查询节点**：紧跟 `get_single`/`get_multiple` 后用 `result_branch` + `result_type:"has_data"`/`"no_data"` 按有无数据分流。

> 多级审批用 `approval_block` 内**串联多个 `approve` 节点**实现（见 [workflow-gotchas.md](workflow-gotchas.md)），不是单节点的 multipleLevel。

### 6. 通知与提醒补全

即使需求与计划方案没有提到通知，也应根据业务场景主动补充：

- 记录状态变更 → 通知负责人/相关人员
- 审批完成 → 通知发起人
- 异常/逾期 → 通知责任人及上级

通知方式选择：
- **站内通知**：能随通知发送记录详情时优先用 `cc`（收件人可查看记录，**仅支持单条记录**）；不关联具体记录时用 `notice`。若上游是 `get_multiple` 多条记录，必须先用 `sub_process` 逐条处理，再在子流程内使用 `cc`。
- **邮件通知**：`send_email` 用于向**记录中的邮箱字段**发送邮件（如客户邮箱、供应商邮箱）——收件人用 `accounts` 里 `kind:"field"` 指向邮箱字段，或 `kind:"email"` 直填地址。

**通知/邮件内容要求**：`content`/`body` 必须写出完整文案，让收件人无需登录系统即可了解完整上下文。正文里引用记录字段用模板 **`$别名-工作表名/字段名$`**（从触发/查询节点取列值，见后文《字段写入项》；富文本会自动转成正确的提及格式）。

> 正例：`"content": "您的借阅申请已提交。借阅人：$trigger-借阅记录/借阅人$，图书：$trigger-借阅记录/图书名称$，预计归还：$trigger-借阅记录/预计归还日期$。请登录系统审批。"` ✅
> 反例：`"content": "借阅申请异常，请核查"` ❌（信息量不足）

⚠️ 如果文案要引用**其他工作表**的字段（如通知里要显示关联图书名，而图书名不在触发表上），必须在通知节点之前安排 `get_single` 查询节点取数，模板里用该查询节点的别名引用。

接收人选择（`accounts[]`，见后文 `wfAccount`）：流程触发人 / 记录中的人员字段 / 应用角色。

### 7. 异常与边界场景

主动补充需求与计划方案未提及的边界处理：

- 查询节点未找到记录时：是继续还是停止？（配合规则 4 的 `rowid` 空判断分支）
- 批量操作的筛选条件是否足够精确？
- 定时任务无待处理数据时直接结束

### 8. 字段选项值映射

需求与计划方案中可能提到某些字段选项值（如「全部借出」「审核通过」等），但这些只是业务描述，**不一定对应 `worksheets` 中的实际选项**。

设计时必须：
- 查看 `worksheets` 中对应字段的 `options` 数组
- 在方案中使用实际存在的选项名称（`options[].value`）
- 如果没有精确匹配，选择语义最接近的选项

## 触发器 `trigger.type`

> ⛔ **自动触发为主、`button` 为辅。** `button` 是兜底选项不是默认选项——只有当流程必须由人**主动发起**、系统无法自判时机时（提交审批、确认收货、发起退款/作废）才用它。状态流转、库存增减、时效预警、数据联动、新建即通知，都该用 `record_*` / `date` / `scheduled` 自动触发。**一个应用里若 `button` 触发的工作流占多数，几乎一定是把本该自动跑的流程错挂成了按钮——回去改。** 选型优先级见 [design_guide.md](design_guide.md) 四「触发方式选型」。

- `record_create` / `record_update` / `record_create_or_update`：记录触发，配 `worksheet`；
  `fields`(仅更新触发：仅这些字段变更才触发)、`filter`(触发筛选条件，通用工作流条件 wfCondition，按触发记录字段写)。
- `scheduled`：定时。配 `schedule`：`repeat`(day/week/month/year/workday/hour/minute/custom)、`interval`、`week_days`、`start_time`、`end_time`。
- `date`：按日期字段。配 `date_field` + `date_config`(`offset_type` on/before/after、`offset_number`、`offset_unit` minute/hour/day、`time`、`repeat` once/year/month/week)。
- `button`：由自定义动作按钮触发。这条工作流写在 `workflows[]`，`trigger` 只需 `{"type":"button"}`（无需 worksheet）；
  另在 `custom_actions[]` 配一个 `type:"trigger_workflow"` 的按钮、其 `workflow` 字段指向本工作流名（一对一配对，见 [custom-actions.md](custom-actions.md)）。
  节点里用 `{nodeAlias:"trigger"}` 引用按下按钮的那条记录。
  > ⛔ **`trigger` 就是按钮所在表（宿主表）的记录**：自定义动作 `worksheet="A"` ⇒ `trigger` 永远是一条 A 表记录。所有 `{nodeAlias:"trigger"}` 引用与 `$trigger-表/字段$` 模板的 `表名` 前缀**必须是 A**。要写/审另一张表 B 的记录，**先 `create_record` 建 B 记录、再绑定到那个节点的别名**（别把 `trigger` 当 B 记录用），否则发布报 `warningType 200`、validate 会直接拦下。详见 [workflow-gotchas.md](workflow-gotchas.md) 按钮触发条目。
- `webhook`：外部系统通过 HTTP 推送触发。`trigger` 写 `{"type":"webhook","sample":{...}}`——`sample` 是一份**代表性入站 JSON 请求体样例**，构建时会把它发到 webhook 接收地址，由服务端按结构推导入站参数（每个顶层键成为一个参数，**参数名即键名**）。下游节点用 `$trigger-键名$` 取对应入站值写入工作表（如 create_record 的字段 `{"fieldId":"订单/订单号","value":"$trigger-order_id$"}`）。
  - sample 的值类型决定参数类型（字符串/数字），尽量给真实示例值。键名建议用字母/数字/下划线，避免连字符（`$trigger-...$` 以首个 `-` 分隔别名与参数名）。
  - 全链路已 live 验证：建表→建 webhook 流→发布→真实 POST 入站值正确落库。

## 节点 `nodes[]`

每个节点：`nodeAlias`(流程内唯一别名)、`nodeType`、`name`、`prevNode`(前驱别名，省略=接上一个)、`config`(键由 nodeType 决定)。
触发节点固定别名 **`trigger`**（执行器注册，条件/模板用 `{nodeAlias:"trigger"}` 引用）。

> ⛔ **保留别名禁止用作 `nodeAlias`**：`trigger` / `sub_trigger` / `approval_trigger` / `approval_start`。
> 它们由执行器绑定到触发记录/内层流程记录；节点占用会把绑定顶掉，导致 `$trigger-...$` 模板和收件人全部解析到错误节点（发布报 105/200）。校验和构建都会直接拒绝。
> 触发记录本来就能用 `trigger` 引用——节点不需要、也不许叫这个名字。

**nodeType → 它认的 config 键**（schema 的 allOf 强制必填项，**别给错类型的键**）：

| nodeType | 作用 | 关键 config 键 |
| :-- | :-- | :-- |
| `update_record` | 更新记录 | `target`(写入目标记录) + `fields`(写入项 wfFieldPatch[]) |
| `create_record` | 新建记录 | `fields`（目标表由 `fields` 的 `表名/字段` 前缀自动推出；字段跨多张表时须显式写 `worksheet` 指明建在哪张表） |
| `delete_record` | 删除记录 | `target` |
| `get_single` | 查询单条 | `worksheet` + `filter` |
| `get_multiple` | 获取多条(按工作表) | `worksheet`(+ `filter`) |
| `get_relation_records` | 取关联/子表多条 | `relation_field`("父表/子表字段") |
| `query_update` | 查询并更新(扣减/累加) | `worksheet` + `fields`(+ `match`/`filter`，`addType` 0覆盖/1累加/2累减) |
| `branch` | 分支 | `paths`(wfBranchPath[])，`mode` exclusive(默认唯一分支)/parallel |
| `approval_block` | 审批块(含内部流程) | `process`(内部流程 wfInnerProcess) |
| `approve` | 审批(只能在审批块内用) | `accounts`(+ `countersign` single/all/sequential) |
| `sub_process` | 子流程 | `process`(内部流程，可带 `parameters`/`wait_complete`/`data_source`) |
| `cc` / `notice` / `send_email` | 抄送/站内通知/邮件 | `accounts` + `content`(cc/notice) 或 `subject`+`body`(email) |
| `fill_in` | 填写 | `worksheet` |
| `compute` / `rollup` | 公式/汇总 | `config`(按 `mode` 取键，见 `workflow-gotchas.md`) |

节点的可选配置：
- `get_multiple`：`random:true` + `count:N` 随机抽 N 条；`sorts` 指定排序。
- `delete_record`：`permanent:true` 彻底删除(不可恢复)，省略=删到回收站。
- `sub_process`：`config.process.execute_type` —— 1 并行(默认) / 2 逐条串行(中止则不再触发后续) / 3 逐条串行(中止仍继续下一条)。
- `sub_process` 的 `data_source`(逐条处理的记录来源，**必填**，指向上游多条节点)规范位置在 `config.process.data_source`；写在 `config.data_source`(rollup 同款位置)也接受。漏写则数据源为空，发布报 103。
- `cc`(抄送)：`card_fields:["字段名",...]` 指定在抄送卡片上**高亮展示**的字段(其余字段仍在卡片但不高亮)；省略=不高亮。需配 `worksheet` 指明记录来源。
- `fill_in`(填写)：用字段角色控制表单——`editable_fields`(可修改)、`readonly_fields`(只读可见)、`hidden_fields`(不展示)；`submit_btn_name` 改提交按钮文案。省略全部=可写字段默认可编辑。需配 `worksheet`。
- `approve`(审批)的进阶能力(全部可选，省略=基础审批)：
  - **可改字段**：`editable_fields`/`readonly_fields`/`hidden_fields` —— 审批人可在审批时修改/只读/隐藏哪些字段。需配 `worksheet`(被审批记录的工作表)才会生成可改字段表。
  - `allow_transfer:true` 允许**转审**、`allow_add_sign:true` 允许**加签**。
  - `reject_opinion_required:true` 否决时**必须填意见**；`pass_opinion_required:true` 通过时必须填意见。
  - `batch_approve:true` 允许批量审批、`fast_approve:true` 允许快捷审批、`allow_attachment:true` 允许上传附件。
  - `countersign` 会签方式仍是 single(任一)/all(全部)/sequential(依次)。

> 字段角色(`card_fields`/`editable_fields`/…)填**逻辑字段名**(工作表里的字段名)，不填 id；构建时按名匹配该工作表的控件。

- `send_email`(邮件)：
  - `subject` 主题(纯文本)、`body` 正文。正文**含 HTML 标签**时自动按富文本发送，模板令牌会转成富文本提及；纯文本则普通发送。可用 `rich:true/false` 强制。
  - `accounts` 收件人、`ccAccounts` 抄送人——除常规 `{kind:role/user/...}` 外，支持**外部邮箱** `{kind:"email","email":"a@b.com"}`。
  - `sender_name` 发件人显示名、`reply_email` 回复邮箱。
  - 正文里引用记录字段照常写 `$别名-工作表名/字段名$`，富文本会自动转成正确的提及格式。

### 字段写入项 `wfFieldPatch`（create/update/query_update 的 `fields[]`）

```jsonc
{ "fieldId":"出库单/状态", "value":"审批中" }                               // 静态值(选项写显示名,自动转key)
{ "fieldId":"库存/当前数量", "addType":2,                                   // 累减
  "valueRef":{ "kind":"field", "node":{"nodeAlias":"取明细"}, "fieldId":"出库明细/数量" } }   // 动态取自其他节点
{ "fieldId":"出库单/完成时间", "valueRef":{ "kind":"system", "field":"now" } }   // 系统值：当前时间
{ "fieldId":"冲突预警/主计划编号", "value":"$trigger-检修计划/计划编号$" }    // 模板：从某节点记录取列值拼字符串
```

> 文本字段写入也可用 `$别名-工作表名/字段名$` 模板（从触发/查询节点的记录取列值）。要从另一节点取**单值**写入，
> 用 `valueRef`（动态引用）或上面的 `$...$` 模板皆可。
>
> **写系统值（当前时间等）用 `valueRef:{kind:"system", field:..}`**，不要写成字面量字符串"当前时间"。可用 `field`：
> `now`/`当前时间`、`trigger_time`/`触发时间`、`trigger_user`/`触发者`、`timestamp`(毫秒)、`timestamp_seconds`(秒)。

### 条件 `wfCondition`（查询/分支/触发筛选）—— 支持「或/且」组合

凡是写筛选/分支条件的地方（`get_single`/`get_multiple`/`query_update` 的 `filter`、`branch` 路径的 `condition`、触发器 `trigger.filter`）都用 `wfCondition`，两种写法：

```jsonc
// ① 简单：一组条件统一 and 或 or
{ "logic":"and", "items":[ {left,op,right}, {left,op,right} ] }

// ② 或且组合：每个 group 内是 AND，group 之间是 OR —— (A且B) 或 (C且D)
{ "groups":[
    { "items":[ {状态=待审}, {金额>1000} ] },     // 第 1 组：两条 AND
    { "items":[ {状态=加急} ] }                    // 第 2 组
] }                                                // => (状态=待审 且 金额>1000) 或 (状态=加急)
```

- 纯 AND 用 `items`+`logic:"and"`；纯 OR 用 `items`+`logic:"or"`；**(…且…) 或 (…且…) 这种混合**用 `groups`。

### 值引用 `wfValueRef`（条件 right、字段写入 valueRef、传参 value 等）

- 字段引用 `{kind:"field", node:{nodeAlias}, fieldId:"工作表名/字段名"}`（从某节点记录取列值）
- 系统值 `{kind:"system", field:"now"}`（当前时间/今天/触发时间/触发者/时间戳，见上方 wfFieldPatch 的 field 取值表）。**既可用于写值，也可用于条件 right**——如定时/无触发记录的流程按「某日期字段早于当前时间」筛记录：`{"left":{...,"fieldId":"预约/预约时间"},"op":"lt","right":{"kind":"system","field":"now"}}`。
- 记录引用 `{kind:"record", node:{nodeAlias}}`
- 字面量 `{kind:"literal", value:..}` 或多值 `{kind:"literal", values:[..]}`（选项字段写显示名；「是其中之一」用 `values`）
- 流程参数 `{kind:"param", name:".."}`（子流程内引用主流程传入的参数）

> ⚠️ 字段引用一律用 **`"工作表名/字段名"`** 逻辑名（执行器译成 controlId）；别直接写裸字段名或猜 id。

### 收件人/审批人 `wfAccount`（accounts[]）

`{kind:"role", role:"角色名"}` / `{kind:"user", userId}` / `{kind:"triggerUser"}` /
`{kind:"owner"}`(记录拥有者) / `{kind:"supervisor"}`(触发者直属上司) / `{kind:"field", fieldId:"表/成员字段"}`(发给记录里某成员/部门字段，可选 `node:{nodeAlias}` 指定取自哪个节点的记录，默认 trigger)。

> ⚠️ 审批人优先用 `{kind:"role"}`（环境无关最稳）；`supervisor` 需组织真有上下级层级，否则发布报 warningType 200。详见 `workflow-gotchas.md`。

> 完整正例见
> [examples/warehouse/04-workflows.design.json](../examples/warehouse/04-workflows.design.json) 的 `workflows`。
> **生成前务必对照 [workflow-gotchas.md](workflow-gotchas.md)。**
