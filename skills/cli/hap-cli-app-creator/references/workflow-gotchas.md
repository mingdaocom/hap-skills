# Workflow Gotchas — 工作流隐藏规则（不写就建错/发布失败）

这些规则来自对真实手建流程的 wire ground truth 抓取与覆盖度审计（已 live 验证）。
**生成任何工作流（`workflows[]` 或 `custom_actions[].workflow`）前必读。** design 写错虽能通过 schema 校验，但会语义错或发布失败。

---

## 1. 分支默认「唯一分支」

`branch` 节点 `config.mode`：
- **`exclusive`（默认，唯一分支）**：从上到下只走**第一个**条件匹配的路径。绝大多数业务分支用这个——不写 mode 就是它。
- `parallel`（并行分支）：每个匹配的路径都跑。仅当你确实要并发多路时才用。

分支路径 `paths[]`：每条 `{ name, condition/filter, nodes:[...] }`。**省略 condition 的那条 = 默认/否则路径**，放最后。
⚠️ **默认路径可以省 `condition`，但 `nodes` 仍必填**——否则分支不做任何事时也要写空数组 `"nodes":[]`（漏写 `nodes` 会校验失败：`paths[N]: missing required property 'nodes'`）。
```jsonc
{ "nodeAlias":"判断库存","nodeType":"branch","config":{ "mode":"exclusive","paths":[
    { "name":"充足","condition":{"logic":"and","items":[
        {"left":{"kind":"field","node":{"nodeAlias":"取库存"},"fieldId":"库存/当前数量"},
         "op":"gte","right":{"kind":"field","node":{"nodeAlias":"trigger"},"fieldId":"出库单/数量"}} ]},
      "nodes":[ ... ] },
    { "name":"不足","nodes":[ ... ] } ] } }    // 无 condition = 否则
```
条件 `op`∈eq/ne/gt/gte/lt/lte/in/not_in/empty/not_empty/contains/not_contains/starts_with/ends_with/all_contains/belongs/not_belongs/checked/unchecked。

## 2. 选项字段「是其中之一」用复数 `values`

条件右值是选项字段时：
- **单值**（等于某一个选项）：`right:{ kind:"literal", value:"加急" }`。
- **多值/是其中之一**（in）：`op:"in"` + `right:{ kind:"literal", values:["加急","特急"] }`——**用复数 `values`，填选项显示名**。
执行器会把显示名转成带 key 的完整选项对象（这是历史上分支 500 的根因）。

## 3. 触发器各类配置

- **记录触发**：`record_create` / `record_update` / `record_create_or_update` + `worksheet`。
  - 仅某字段变更才触发：`trigger.fields:["当前数量"]`。
  - 仅满足条件的记录进流程：`trigger.filter`（wfCondition，按触发记录字段写，`left.node = {nodeAlias:"trigger"}`）。
- **定时 `scheduled`**：`trigger.schedule = { repeat, interval, week_days, start_time, end_time }`。
  `repeat`∈day/week/month/year/workday/hour/minute/custom；`start_time` 是首跑锚点（**必给**，否则触发器永久未配置、流程不可发布）。
- **按日期 `date`**：⚠️ **`trigger.worksheet` 必填**（和 `date_field` 一样不可少——只给 `date_field` 漏 `worksheet` 是高频错误，会校验失败）。再配 `trigger.date_field`(驱动的日期字段) + `trigger.date_config = { offset_type(on/before/after), offset_number, offset_unit(minute/hour/day), time, repeat(once/year/month/week) }`。
  完整示例：`"trigger":{ "type":"date", "worksheet":"设备", "date_field":"下次保养日", "date_config":{ "offset_type":"before","offset_number":3,"offset_unit":"day","time":"09:00","repeat":"once" } }`。
  > 记录触发(`record_*`)同理：`worksheet` 也是必填。button / scheduled / webhook 才不写 worksheet。
- **按钮 `button`**：工作流写在 `workflows[]`（`trigger:{type:"button"}`），再由一个 `trigger_workflow` 自定义动作的 `workflow` 字段按名指向它；触发记录用 `{nodeAlias:"trigger"}`。
  > ⛔ **`trigger` 记录 = 自定义动作所在的那张表（宿主表）的记录，不是别的表。**
  > 自定义动作挂在 A 表（`custom_actions[].worksheet="A"`），用户就是在 A 表的某条记录上点按钮，所以 `trigger` 永远是一条 **A 表记录**。
  > 因此**所有** `{nodeAlias:"trigger"}` 的引用——update/query 的 `target`+`fields`、`valueRef`、filter 的 left/right、`$trigger-表/字段$` 模板——其 `表名/字段` 前缀**必须是宿主表 A**。
  > 写成 `$trigger-B/...$`，或 `target=trigger` 却填 B 表字段（把按钮记录当成 B 表记录），构建会把节点绑到 A 表却塞入 B 表列 id，发布必报 `warningType 200`（"N 个节点未设置有效的操作或操作内容异常"）、整条流程发布失败。**validate 现在会直接拦下这类引用。**
  > **要操作另一张表 B 的记录**（典型："从 督查事项 点『发起延期』，要落一条 延期申请"）：
  > 1. 先加 `create_record` 节点在 B 表建记录（关联字段用 `valueRef:{node:{nodeAlias:"trigger"},fieldId:"A/rowid"}` 指回 A；其余值来自 `$trigger-A/字段$`）；
  > 2. 之后对这条 B 记录的所有 update/引用，**绑定到该 create_record 节点的别名**（如 `target:{kind:"record",node:{nodeAlias:"建延期申请"}}`），**不要用 `trigger`**；
  > 3. 审批块要审 B 记录时，让它跟在 create_record 之后，块内用 `approval_trigger` 引用被审记录。
  > 一句话：`trigger` 只代表宿主表那条记录；别的表的记录都得先用节点建出来/取出来再引用。

> ⚠️ **「到期前 N 天 / 未来 N 天内到期」怎么写**——工作流日期条件**只能跟某个时间点比较（早于/晚于/在范围内），没有「当前时间 ± N 天」的相对偏移**。所以：
> - **逐条「到期前 N 天」提醒** → 直接用 **date 日期触发器**：`date_config.offset_type:"before"` + `offset_number:N`（每条记录在其日期字段前 N 天自动触发，无需扫描）。这是首选。
> - **批量「未来 N 天内到期」扫描汇总**（定时流里筛"还有 N 天到期"的一批）→ 先在工作表加一个 **DateFormula 字段「距到期天数」=（日期字段 − 今天）**，定时流再用**普通数值条件** `距到期天数 >= 0 且 <= N` 来筛——不要试图用「日期字段 早于 当前时间+N天」（平台无此表达）。
> - 同理「已逾期」用日期字段 **早于** 当前时间（`right:{kind:"system",field:"now"}`）即可。

## 4. 审批块 approval_block（T26）

审批块自带一段**独立的内部流程**，写在 `config.process`（wfInnerProcess）：
```jsonc
{ "nodeAlias":"出库审批","nodeType":"approval_block","name":"出库审批","config":{ "process":{
    "name":"出库审批流程",                          // 内部流程名（避免显示「未命名审批流程」）
    "nodes":[
      { "nodeAlias":"优先级分支","nodeType":"branch","config":{"mode":"exclusive","paths":[
          { "name":"加急","condition":{"items":[ {"left":{"kind":"field","node":{"nodeAlias":"approval_trigger"},"fieldId":"出库单/优先级"},"op":"in","right":{"kind":"literal","values":["加急","特急"]}} ]},
            "nodes":[ {"nodeAlias":"主管审批","nodeType":"approve","config":{"accounts":[{"kind":"role","role":"仓库主管"}]}} ] },
          { "name":"普通","nodes":[
              {"nodeAlias":"上司审批","nodeType":"approve","config":{"accounts":[{"kind":"supervisor"}]}},
              {"nodeAlias":"主管复审","nodeType":"approve","config":{"accounts":[{"kind":"role","role":"仓库主管"}]}} ] } ] } } ] } } }
```
要点：
- **内部触发别名固定 `approval_trigger`**（在内部流程里引用「发起审批的那条记录」用它）。
- **审批结果分支**：在审批块**之后**接一个 `branch`，读审批块的虚拟字段 `result`，值为 `PASS`/`OVERRULE`/`REVOKE`/`SUSPEND`（通过/否决/撤回/中止）：
  ```jsonc
  {"left":{"kind":"field","node":{"nodeAlias":"出库审批"},"fieldId":"result"},"op":"eq","right":{"kind":"literal","value":"PASS"}}
  ```
  四路常见：通过→下一步 / 否决→标记未通过 / 撤回→回未提交 / 中止(默认)→已取消。
- `approve` 节点的 `accounts`：应用角色 `{kind:"role"}`、直属上司 `{kind:"supervisor"}`、触发者 `{kind:"triggerUser"}`、成员字段 `{kind:"field"}`；`countersign`∈single/all/sequential。
  - ⚠️ **审批人优先用显式应用角色 `{kind:"role"}`**（环境无关，最稳）。`{kind:"supervisor"}`（直属上司）只有当**组织里确实定义了上下级层级**时才能发布——否则审批人无法确定，发布报 `warningType 200`、`isPublish:false`。没把握就用 role。
- 内部流程可命名（`process.name`/`explain`/`icon_color`）。

## 5. 子流程 sub_process（T16）

```jsonc
{ "nodeAlias":"检查库存","nodeType":"sub_process","config":{ "process":{
    "name":"检查库存",
    "wait_complete": true,                                  // 同步：子流程跑完再继续（改的数据主流程才拿得到）
    "parameters":[ { "name":"主单rowid",
        "value":{"kind":"field","node":{"nodeAlias":"trigger"},"fieldId":"出库单/rowid"} } ],   // 传主单 ID
    "nodes":[
      { "nodeAlias":"查主单","nodeType":"get_single","config":{ "worksheet":"出库单",
          "filter":{"items":[ {"left":{"kind":"field","node":{"nodeAlias":"查主单"},"fieldId":"出库单/rowid"},
                               "op":"eq","right":{"kind":"param","name":"主单rowid"}} ]} } },
      ... ] } } }
```
要点：
- **内部触发别名固定 `sub_trigger`**（当前迭代记录）。保留别名（`trigger`/`sub_trigger`/`approval_trigger`/`approval_start`）**不许**用作任何节点的 `nodeAlias`——占用会顶掉绑定、引用全错（发布 105/200），校验和构建都会拒绝。
- 子表无反向关联→子流程拿不到主单，所以把主单 `rowid` 当 `parameters` 传进去，子流程内 `get_single.filter` 用 `{kind:"param", name:..}` 过滤。
- `wait_complete:true` = 同步（串行）；**`data_source` 必填**（指定遍历的记录集，如某 get_multiple / get_relation_records 节点），规范位置 `config.process.data_source`（写在 `config.data_source` 也接受）。漏写则发布报 103。
- 内部流程的显示名：优先 `process.name`，缺省回退**节点的 `name`**——两个都不写才会留服务器默认的"未命名子流程"，所以子流程节点务必起业务化的 `name`。

## 6. 查询节点的 left.node 指向

- **查询节点自身的 filter**（get_single/query_update）：条件 `left.node` 必须指向**该查询节点自己**（按它查到的记录字段过滤）。
- **分支/触发器的 filter**：`left.node` 指向**上游数据源节点**（trigger 或某 get 节点）。

## 7. get_relation_records 必带 relation_field

取触发记录的关联子表多条记录：`config.relation_field = "父表/子表字段"`（父表上那个 SubTable/Relation 控件的逻辑名）。
缺它会被服务端打回父表、isException、发布失败。

## 8. query_update 扣减/累加

`addType`：0=覆盖、1=累加、2=累减。扣库存 = 当前数量 累减 出库数量：
```jsonc
{ "fieldId":"库存/当前数量","addType":2,
  "valueRef":{"kind":"field","node":{"nodeAlias":"sub_trigger"},"fieldId":"出库明细/数量"} }
```
匹配哪条记录用 `match` 或 `filter`；排序默认按创建时间倒序取最新。

> ⚠️ **`match` / `valueRef` 引用的字段必须真实存在于它所属的表上。** 高频错误:想从触发记录取一个「外键编号」去 match 目标表(如 `$trigger-消耗记录/耗材库存编号$`),但触发表上**根本没有**这个字段 → 发布失败(`control X not found`)。要按关联匹配,触发表必须**先有一个指向目标表的 Relation 字段**,再 match 该 Relation 带出的字段;不要凭空引用一个 `<目标表>编号` 外键。`$trigger-<表>/<字段>$` 里的 `<字段>` 必须是 `<表>` 上已声明的字段或系统字段(rowid/ctime/...)。validate 现在会拦下这类悬空引用。

## 9. compute / rollup 是模式化的（actionId 由 mode 决定，别写死旧码）

- `compute`：`config.mode`∈`number`(数值公式) / `date`(日期公式) / `date_diff`(日期差) / `function`(函数)。
  数值/日期/函数用 `formula`(可含 `$alias-字段$` 模板)；date_diff 用 `start`/`end`/`out_unit`(minute/hour/day/month/year/week)。
  > ⚠️ **`function` 模式返回文本或日期时，必须声明 `config.output_type`**（`text`/`number`/`date`/`datetime`，省略默认 `number`）。它决定下游引用该节点「结果」时用的字段 id（见下条）：写错或漏写会让消费节点引用到不存在的结果列，发布报 `warningType 200`。如 `CONCAT(...)` 拼字符串 → `"output_type":"text"`。`number`/`date`/`date_diff` 模式无需设置（数值/日期由 mode 决定）。
- `rollup`：`config.mode`∈`worksheet`(按工作表汇总) / `object`(对象计数)。聚合项写在 **`aggregations[]`**，每项：
  - `alias`(必填，结果别名，下游用 `$别名-alias$` 引用)；
  - `aggregate`(**推荐小写**：sum/count/avg/max/min，与字段级 Rollup 一致；也接受大写 `func`，二者等价、执行期都归一化为大写)；
  - `fieldId`("工作表名/字段名"，count 行数时可省略)。
  - 遍历某个查询节点的结果集时用 **`data_source`**(指向 get_multiple/get_relation_records 节点)；按工作表整体汇总则配 `worksheet`(+可选 `filter`)。

  **完整最小示例**（统计某 get_multiple 结果的行数到别名 cnt）：
  ```jsonc
  { "nodeAlias":"统计", "nodeType":"rollup", "name":"统计数量", "config":{
      "mode":"worksheet",
      "data_source":{ "kind":"record", "node":{ "nodeAlias":"查多条" } },
      "aggregations":[ { "alias":"cnt", "aggregate":"count" } ] } }
  ```
  > ⚠️ 易错点：① `aggregate` 用小写(或 `func` 大写)，**不要**写成裸 `aggregate:"COUNT"` 之外的拼写；② `data_source` 只属于 rollup/sub_process，**不要**把它放进别的节点；③ 别给 `aggregations[]` 项漏 `alias`。
- **引用 rollup / compute 节点的「结果」**（分支条件、通知/文本模板、写入字段值里都可用）：统一写 **`$节点别名-结果$`**，执行器按该节点的结果数据类型自动解析为对应结果列（数值→`number_fx_id`、文本→`string_fx_id`、日期→`date_fx_id`、日期时间→`datetime_fx_id`）。`结果`这个名字只是显示名，真正的字段 id 由类型决定——所以 `function` 模式务必声明 `output_type`（见上条），否则按默认数值解析、文本结果就会引用错列。
  - 分支条件比较结果：`{"left":{"kind":"field","node":{"nodeAlias":"统计"},"fieldId":"结果"},"op":"gt","right":{"kind":"literal","value":"0"}}`（fieldId 写 `结果`/`result`/聚合别名均可，执行器按类型转成对应 `*_fx_id`）。
  - 通知/抄送/邮件内容引用结果：`"content":"本周共 $统计-结果$ 条，请复核。"`。
  - 写入字段值引用结果（如把一个文本公式结果写进新建记录的文本字段）：字段项写 `{"fieldId":"表/字段","value":"$别名-结果$"}`（**用 `value` 模板，不要用 `valueRef{fieldId:"结果"}`**——valueRef 只用于引用 trigger/查询节点的真实列）。
  - ⚠️ **不要**在文本里用 `$别名-某聚合别名$`（如 `$统计-加油条数$`）去指代结果——统一用 `$别名-结果$` 最稳。
- 聚合结果存到下游可引用的别名（`aggregations[]` 的 alias，引用用 `$alias-别名$`）。

> 旧实现把 compute→104、rollup→105 是语义错误（104 其实是日期差、105 是对象计数）。现按 mode 正确取 actionId，**你只要写对 `mode`**。

## 10. cc / notice / send_email 的差异

- `notice`(站内通知,27)：只要 `content` + `accounts`，不带表单字段列表。收件人可用 `triggerUser`/`owner`/`role`，
  也可用**当前/触发记录上的成员字段** `{kind:"field", fieldId:"表名/成员字段"}`（已 live 验证可发布）。
  ⚠️ 但若要取**关联表**里的成员（如「该设备所属科室的负责人」），不能直接引用关联/Lookup 字段——
  先用「获取关联记录(单条/多条)」节点把那条记录取进来，再用 `{kind:"field", node:{nodeAlias:"取记录节点"}, fieldId:"关联表/成员字段"}`
  指向该节点的成员字段（直接引用关联表成员/被 Lookup 的字段会发布失败）。
- `cc`(抄送,5)：`content` + `accounts`，会带通知卡片字段列表（执行器从工作表表单自动生成）。
- `send_email`(11)：`subject` + `body` + `accounts`。
内容可用 `$别名-工作表名/字段名$` 模板插值。

> ⚠️ **工作流里不能直接引用 Lookup（他表镜像）字段**——无论是模板插值 `$…/某Lookup字段$`、条件 left/right，还是写值 valueRef。Lookup 只是另一张表字段的镜像，工作流节点无法解析它。
> 正确做法：先加一个**「获取关联记录」节点**（单条 get_single / 多条 get_relation_records）把那条关联记录取进流程，再引用**该节点上被 Lookup 的源字段**（`{kind:"field", node:{nodeAlias:"取记录节点"}, fieldId:"关联表/源字段"}`，模板同理用该节点别名）。即「绕到源头取真字段」，不要图省事直接用本表的 Lookup 镜像。Rollup/公式等派生结果同理——用对应节点的结果引用，别直接引镜像字段。

## 11. 能力边界

**先纠正一个常见误解——下面这些复杂能力都已 live 验证可发布，不要因为"怕复杂/怕发布失败"而回避：**
- **多级审批**：在审批块里**串接多个 `approve` 节点**（如 调度审核 → 营销评估 → 部门主管）即可实现逐级审批——这是已验证的标准做法，**不需要**单节点的 multipleLevelType。
- **审批块 + 审批结果分支**（4 路 通过/否决/撤回/中止）、**分支**（唯一/并行）、**子流程**（同步 `wait_complete`、传参）、
  **查询并更新**（扣减/累加）、**取关联多条**、**cc/notice/send_email**（收件人 role/owner/triggerUser）、
  **定时/按日期触发**——全部可用。

所以**正常的企业级工作流（含多级审批、冲突校验、库存扣减、异常分支）都能完整建出来**，没有"风险"理由去简化。
