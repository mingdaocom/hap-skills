# HAP 自定义动作领域规范

本规范完整保留既有自定义动作构造规则，供创建与修改场景共用。自定义动作属于工作表，视图只通过真实 actionId 引用已经存在的动作。

## 一、对象结构与真实标识

创建自定义动作时，每项使用：

```json
{
  "name": "办理签到",
  "remark": "填写实际到场时间与核验结果",
  "type": "updateCurrentRecord",
  "updateFields": ["biz_check_in_time", "biz_id_verified"],
  "runWorkflowAfterSubmit": false,
  "enableWhen": {},
  "icon": "sys_16_1_checked_svg",
  "color": "#4CAF50",
  "enableConfirm": false,
  "verifyPassword": false
}
```

- `worksheet_id` 必须使用真实工作表 ID，不使用工作表名称或别名。
- `name` 与 `type` 必填；`remark` 是 hover 时显示的补充说明，仅在按钮名不足以说明行为时添加。
- 自定义动作 ID 复用创建回执或 `get_custom_action_list` 返回的 `id`，也可使用 `get_workflow_list` 返回的 `actionId`；已有可靠 ID 时，不为定位重复查询列表或流程详情。
- 字段引用优先使用真实 alias，无 alias 时使用真实字段 ID；从 Markdown 结构取值时必须移除 `(isTitle)` 等说明后缀。

## 二、三类动作及配套字段

| type | 行为 | 配套字段 |
|---|---|---|
| `updateCurrentRecord` | 允许用户填写当前记录的指定字段 | `updateFields` 必填 |
| `createRelatedRecord` | 通过本表关联字段新建一条关联记录 | `relationField` 必填 |
| `triggerWorkflow` | 直接触发该按钮绑定的工作流 | 可选配置 `recordScope`、`enableCompleteMsg`、`completeMsg` |

- `runWorkflowAfterSubmit` 表示填写/创建记录提交后是否继续触发工作流，默认 `false`；它与 `type=triggerWorkflow` 的“直接触发”不是一回事。当 `type=triggerWorkflow` 或 `runWorkflowAfterSubmit=true` 时，均可配置 `enableCompleteMsg` 与 `completeMsg`；`recordScope`（`single`/`multiple`）仅用于 `type=triggerWorkflow`。
- 改变动作 `type` 时，必须同步提供新类型的配套字段；不能沿用旧类型字段让新动作处于缺配置状态。

### 2.1 updateFields 构造

从动作语义中识别“用户要填写什么”，只选择当前工作表真实存在、且确实需要用户在这次操作中填写的字段。

例如：

- 动作「办理签到」要求填写实际到场时间、证件核验情况、访客证编号；
- 工作表中对应字段 alias 为 `biz_check_in_time`、`biz_id_verified`、`biz_badge_no`；
- 则使用 `updateFields: ["biz_check_in_time", "biz_id_verified", "biz_badge_no"]`。

不得把系统自动维护字段、无关字段或不存在的字段加入 `updateFields`。该配置只控制用户可填写字段，不提供固定值赋值或字段复制能力；任务要求零输入的一键更新时，使用 `triggerWorkflow` 配置相应工作流，不能用手填表单替代。动作创建成功不代表关联流程已配置或发布。两类触发方式都保留回执的 `workflowId`，供后续配置关联流程。

### 2.2 relationField 构造

`createRelatedRecord` 必须找到当前工作表中真实存在的 Relation 字段，并确认其数据源指向目标工作表，再使用该字段 alias 或 ID。

例如：动作「登记异常」需要在「来访异常」表创建记录，本表存在指向该表的 `biz_exception_relation`，则使用：

```json
{ "type": "createRelatedRecord", "relationField": "biz_exception_relation" }
```

不得用目标工作表 ID、目标工作表名称或普通文本字段代替 relationField。

### 2.3 工作流数据源与操作入口

`recordScope` 在创建时确定关联流程触发节点的数据源类型，创建后不可变更，与按钮挂载位置独立：

| recordScope | 详情 / 行内操作 | 视图多选操作 |
|---|---|---|
| `single` | 当前记录触发一个流程实例 | 每条选中记录分别触发一个流程实例 |
| `multiple` | 一个流程处理仅含当前记录的集合 | 一个主流程处理选中记录集合 |

各条记录独立办理选 `single`；合单、集合统一更新/删除、汇总后集中报送选 `multiple`。不因“批量”或“多选”字样直接选择多数据源；具体节点选型遵循 `hap-workflow-design-guide`。创建默认 `single`；不能通过更新动作或修改触发节点切换单条/多条数据源。

切换数据源必须删除原自定义动作后重新创建。重建前保留需沿用的动作配置（含启停状态）、流程逻辑及已知视图入口和角色限制，再以新 actionId / workflowId 恢复目标配置；原角色限制恢复后才能启用新关联流程。缺少必要保留信息时先补齐，不先删后查。授权与确认遵循 `hap-revision-safety`。

创建动作后，`actions[].id` 用于视图挂载，`actions[].workflowId` 用于关联流程配置；两者不可互换。复用返回的关联流程，不另建普通工作流；必要 ID 缺失时才定向补读动作列表。入口参数与适用视图遵循 `hap-domain-view-spec`。

## 三、enableWhen 启用条件

`enableWhen` 是按钮已启用时的记录条件，不传表示无记录条件限制；必须根据业务逻辑判断，不能默认省略。

- 有前置状态要求的动作必须设置，例如“借书”要求状态为“在库”、“发货”要求订单为“已付款”。
- 只有真正无前置条件的操作，如添加备注、发送普通通知，才可不设置。

### 3.1 条件树结构

- 根节点必须是 `group`，即使只有一个条件也不能直接传 `condition`。
- group 必须有 `logic: "AND" | "OR"` 与 `children`。
- 最多两层 group，即 `group -> group -> condition`。
- 同一 group 的 children 必须全是 group 或全是 condition，不能混合。
- `field` 支持真实字段 ID 或 alias；不得使用显示名或虚构字段。

```json
{
  "type": "group",
  "logic": "AND",
  "children": [
    { "type": "condition", "field": "biz_status", "operator": "eq", "value": ["在库"] }
  ]
}
```

同一字段匹配多个值时，使用一个 `in` condition 加数组：

```json
{
  "type": "group",
  "logic": "AND",
  "children": [
    { "type": "condition", "field": "biz_borrow_status", "operator": "in", "value": ["在借中", "已超期"] }
  ]
}
```

严禁把同一字段的多个互斥值拆成多个 condition 后用 AND 连接。

### 3.2 运算符和值

- 比较：`eq`、`ne`、`gt`、`ge`、`lt`、`le`。
- 集合：`in`、`notin`。
- 包含：`contains`、`notcontains`、`concurrent`。
- 归属：`belongsto`、`notbelongsto`。
- 前后缀：`startswith`、`notstartswith`、`endswith`、`notendswith`。
- 区间：`between`、`notbetween`。
- 空值：`isempty`、`isnotempty`，不传 value。

`between`、`in`、`contains`、`concurrent`、`belongsto` 等多值运算符必须传数组。选项字段可以传 option name 数组或 key 数组；关联记录先取得 record_id；Collaborator、Department、Role 使用实体 ID，不直接用名称。

成员条件另支持：`user-self` 当前用户、`user-sub` 下属、`user-workflow` 工作流、`user-api` API。

## 四、图标规范

创建新动作时配置贴合语义的 `icon`。既有动作局部修改时默认保留原图标，除非用户要求调整视觉。

推荐统一使用带 `_svg` 后缀的标准名称：

| 动作语义 | 推荐图标 |
|---|---|
| 审批 / 通过 / 确认 | `sys_16_1_checked_svg` |
| 驳回 / 拒绝 / 撤销 | `sys_10_3_security_checked_svg` / `sys_10_2_lock_svg` |
| 新建 / 登记 / 补录 | `sys_1_5_create_new_svg` / `sys_1_6_document_svg` / `sys_notes_object_svg` |
| 借阅 / 领用 / 调拨 | `sys_12_2_book_svg` / `sys_11_1_tool_storage_box_svg` / `sys_3_2_money_box_svg` |
| 发货 / 配送 / 物流 | `sys_delivery1_traffic_svg` / `sys_7_1_truck_svg` / `sys_delivery-fast_traffic_svg` |
| 归还 / 入库 / 归档 | `sys_18_5_warehouse_svg` / `sys_cabinet_object_svg` / `sys_8_4_folder_svg` |
| 编辑 / 更新 / 填报 | `sys_form_symbol_svg` / `sys_bullet-list_office_svg` / `sys_progress_symbol_svg` |
| 分配 / 指派 / 派单 | `sys_6_3_user_male_svg` / `sys_1_10_people_svg` / `sys_contacts_office_svg` |
| 支付 / 结算 / 扣费 | `sys_money_finance_svg` / `sys_bill_finance_svg` / `sys_wallet_finance_svg` |
| 提醒 / 催办 / 通知 | `sys_4_3_alarm_clock_svg` / `sys_10_7_bell_svg` / `sys_notification_object_svg` |
| 扫码 / 条码 / 盘点 | `sys_15_10_barcode_svg` / `sys_15_11_qr_code_svg` |
| 报损 / 作废 / 挂失 | `sys_notes_object_svg` / `sys_certificate_object_svg` |

## 五、按钮颜色

| 动作语义 | 推荐颜色 | 示例 |
|---|---|---|
| 无色 / 辅助次级 | `transparent` 或不传 | 查看历史、添加备注 |
| 正面 / 完成 / 通过 | `#4CAF50` | 确认归还、审核通过 |
| 常规业务流转 | `#3054EB` | 发起借阅、提交申请 |
| 预警 / 催办 / 变动 | `#FC532E` | 一键催办、申请延期 |
| 高风险 / 驳回 / 报损 | `#A00416` | 报损报废、审批驳回 |
| 智能化 / 特殊功能 | `#732ED1` | 智能诊断、生成分析 |

颜色必须是标准 HEX 或 `transparent`。局部修改既有动作时不无故改变颜色。

## 六、确认与执行安全

- 高风险、不可逆、涉及审批结果或资金的按钮应考虑 `enableConfirm: true`。
- `confirmMsg` 是确认标题/提问，`confirmContent` 是详细说明；两者只在 `enableConfirm=true` 时有效。
- 涉及高敏操作时可设置 `verifyPassword: true`，普通操作不滥用密码验证。
- 按钮名称应直接表达动作；复杂风险与后果放在 remark 或确认说明中。

## 七、创建、修改与删除边界

- `get_custom_action_list` 包含已停用动作，每项 `enabled` 表示按钮当前启停状态。
- 指定视图隐藏按钮时用 `update_view` 移除目标入口，数组组织与全视图可见动作的处理遵循 `hap-domain-view-spec`；入口移除不等于全局停用。
- `create_custom_actions` 是批量创建，单个动作也放入 actions 数组。
- 创建时用 `status` 指定按钮初始状态：`0` 停用、`1` 启用，默认 `1`。**注意区分「按钮启停（`status` / `enabled`）」与「关联工作流启停（`publish_process` / `close_workflow`）」**：两者相互独立；按钮新建后保持默认启用（`status: 1`）时，其自动预建的空壳工作流默认处于未发布（关闭）状态，在完成节点配置并调用 `publish_process` 发布前不会执行，无需因流程尚未发布而将按钮预先停用。
- `update_custom_action` 以 `worksheet_id + action_id` 定位单个动作，未传字段保持原值。启停使用 `enabled: true` 启用、`enabled: false` 停用；仅启停时只提交定位参数和 `enabled`，保留动作配置、视图入口和关联工作流状态。
- 修改时复用当前会话中已确认的 actionId、type 与配置；缺少目标身份或类型配套信息时才用 `get_custom_action_list` 补齐。既有可靠 ID 的普通增量属性修改不重复读取完整列表。
- 自定义动作触发的工作流不能直接删除；必须通过 `delete_custom_action` 删除所属动作及其关联流程，仅执行已授权的实际删除范围，不调用 `delete_process` 代替。
- 视图引用自定义动作时只能引用已经存在的真实 actionId；系统动作不需要创建。

## 八、提交前自检

1. worksheet_id、action_id 与所有字段引用是否真实？
2. type 与 updateFields / relationField 是否匹配？
3. 有前置条件的按钮是否配置了合法 enableWhen？
4. icon、color、确认提示是否符合动作语义？
5. 修改是否只改变需求影响字段并保留其他配置？
6. 删除目标与实际连带范围是否已授权，已知必要引用是否处理？
