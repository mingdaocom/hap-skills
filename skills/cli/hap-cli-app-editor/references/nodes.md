# 工作流节点深度配置 — 8 类高频节点逐键字典

覆盖 8 类高频节点：ACTION(6)、SEARCH(7)、APPROVAL(4)、CC(5)、WEBHOOK(8)、EMAIL(11)、DELAY(12)、BRANCH 网关(1) + 分支项(2)。
流程级与节点增删见 [workflows.md](workflows.md)。

**全局规则**：改节点配置前先 `hap --json workflow node get <process_id> <node_id>` 导出现状，在真实结构上改，再写回。**读出来的结构就是写回去的结构**——只改你理解的键，其余原样保留。

## 调用范式

写回配置走三条路，按节点类型选：

| 节点类型 | 命令 |
|---|---|
| ACTION(6) | `hap workflow node save-action`（专用快捷命令） |
| SEARCH(7) | `hap workflow node save-search`（专用快捷命令） |
| GET_MORE_RECORD(13) | `hap workflow node save-get-more`（专用快捷命令） |
| 其余所有类型（含 APPROVAL/CC/WEBHOOK/EMAIL/DELAY/BRANCH） | `hap workflow node save <pid> <nid> --type <typeId> -c '<整段配置JSON>'` |

通用坑位（先读完再动手）：

- **accounts 收件人编码是头号坑**：`type` 字段反直觉——`1`=固定用户（accountId 放在 `roleId` 里，不是 entityId！）、`2`=应用角色（`entityId`=应用 ID、`roleId`=角色 ID）、`6`=动态引用（触发者 `roleId:"uaid"`；成员字段引用放该字段的 controlId）、`7`=邮箱字面量（放 `entityId`）。编码错会让收件人显示为「已删除」、流程无法发布。完整结构 → [WorkflowAccounts](../scripts/types/workflow-accounts.schema.json)。
- **条件里的字段键拼写是 `filedId`**（历史拼写，不是 `fieldId`——写成 `fieldId` 会被静默忽略，条件永远不命中）。条件是二维数组：外层 OR、内层 AND。完整结构 → [OperateCondition](../scripts/types/operate-condition.schema.json)。
- 字段写入项（fields）的动态值用 `$<nodeId>-<fieldId>$` 模板引用上游节点的字段，nodeId 来自 `node list`。完整结构 → [WorkflowFieldWrite](../scripts/types/workflow-field-write.schema.json)。
- 数据类节点的目标工作表 `appId` 必须在 `node add` 时给定，save 阶段补传无效（见 workflows.md）。
- **长尾节点类型的处理**：本文未覆盖的类型（公式、代码块、子流程、站内通知……）一律先 `hap --json workflow node get <pid> <nid> --type <typeId>` 读现状，照着返回结构的形状改写要改的键，再用 `node save` 整段写回。不要凭空构造配置。
  - **站内通知(27)** 有两个易漏点：收件人写「触发者」用 `accounts:[{"type":6,"roleId":"triggeraid"}]`；且配置里**必须保留 `flowNodeMap["106"]` 推送子块**（read-modify-write 时原样带回，删了发布会报错）。无现成模板时可先 `node get` 一个同流程已有的 27 节点照形改写。

### ACTION(6) — 增 / 改 / 删记录

```bash
# 在目标表新增一条记录，两个字段：一个静态值、一个引用触发记录的字段
hap workflow node save-action <pid> <nid> -a 1 --app-id <worksheet_id> \
  -f '[{"fieldId":"<状态字段id>","type":11,"fieldValue":"<选项key>"},
       {"fieldId":"<标题字段id>","type":2,"fieldValue":"$<trigger_node_id>-<标题字段id>$"}]'

# 按条件更新上游节点指向的记录
hap workflow node save-action <pid> <nid> -a 2 --app-id <worksheet_id> \
  -s <source_node_id> \
  -f '[{"fieldId":"<金额字段id>","type":6,"fieldValue":"100"}]' \
  --condition '[[{"filedId":"<字段id>","filedTypeId":6,"conditionId":"9","conditionValues":[{"value":"0"}]}]]'
```

### SEARCH(7) — 查询单条记录

```bash
# 按条件查一条，查不到就新建（--not-found 1），新建时写入 fields
hap workflow node save-search <pid> <nid> -a 406 --app-id <worksheet_id> \
  --condition '[[{"filedId":"<编号字段id>","filedTypeId":2,"conditionId":"2","conditionValues":[{"value":"","nodeId":"<trigger_node_id>","controlId":"<编号字段id>"}]}]]' \
  --sorts '[{"controlId":"ctime","controlType":16,"isAsc":false}]' \
  --not-found 1 \
  -f '[{"fieldId":"<编号字段id>","type":2,"fieldValue":"$<trigger_node_id>-<编号字段id>$"}]'
```

`-a` 取值：`406`=按条件查工作表、`421`=查到并更新、`422`=查到并删除、`407`=从多条记录节点取一条（配 `-s <多条节点id>`）。多条 / 批量场景换 `save-get-more`（`-a 400`=查多条、`412`=批量更新、`413`=批量删除，选项同形，另有 `--limit '{"fieldValue":"100"}'` 限制条数）。

### APPROVAL(4) / CC(5) / WEBHOOK(8) / EMAIL(11) / DELAY(12) / BRANCH(2) — 通用 save

这几类没有专用快捷命令，统一走 read-modify-write + `node save`：

```bash
# 1. 导出现状
hap --json workflow node get <pid> <nid> --type 4 > /tmp/node.json
# 2. 在 /tmp/node.json 的真实结构上只改要改的键（如 accounts、countersignType）
# 3. 整段写回
hap workflow node save <pid> <nid> --type 4 -c "$(cat /tmp/node.json | jq '.<配置所在层>')"
```

一次性给一个 CC 节点换收件人（写成应用角色）的最小示例：

```bash
hap --json workflow node get <pid> <nid> --type 5   # 先读，确认其余键
hap workflow node save <pid> <nid> --type 5 -c '{
  "selectNodeId": "<trigger_node_id>",
  "accounts": [{"type": 2, "entityId": "<app_id>", "roleId": "<role_id>"}],
  "sendContent": "有新记录需要您关注",
  "showTitle": true
}'
```

> `-c` 传的是配置 JSON；`node get` 返回中与配置无关的只读键（id、连线等）不必回传，但**所有配置键都应保留原值回传**，漏键可能被视为清空。

## 数据字典

字典生成于 2026-06-10；未覆盖的键以 `hap workflow node get` 返回的实际结构为准。

值形态分三级：① 标量/枚举（直接列值）；② 简单结构（一句话描述）；③ 复杂结构（链接到 schema，或以 `node get` 实际返回为准）。

### ACTION(6)

| 键 | 含义 | 值形态 |
|---|---|---|
| `actionId` | 操作子类型 | ① `"1"`=新增记录 `"2"`=更新记录 `"3"`=删除记录 `"5"`=新建并关联 `"6"`=刷新单条 `"20"`=关联记录 `"411"`=批量动作 `"412"`=批量更新 `"413"`=批量删除 `"415"`=刷新多条 |
| `appId` | 目标工作表 ID（必须在 `node add` 时设定） | ① 字符串 ID |
| `appType` | 目标对象类别 | ① int：1=工作表 2=任务 5=循环 6=日期 7=Webhook 8=自定义动作 |
| `selectNodeId` | 该动作作用的记录来自哪个上游节点 | ① 节点 ID 字符串 |
| `fields` | 新增/更新时的字段写入 | ③ → [WorkflowFieldWrite](../scripts/types/workflow-field-write.schema.json) 数组 |
| `operateCondition` | 限定作用记录的过滤条件 | ③ → [OperateCondition](../scripts/types/operate-condition.schema.json) |
| `sorts` | 排序（取第一条语义） | ③ → [SortItem](../scripts/types/sort-item.schema.json) 数组 |
| `executeType` | 无匹配数据/失败时的行为 | ① 0=中止（或走「无数据」分支） 1=新增一条后继续 2=跳过继续 |
| `random` | 忽略排序随机取 | ① bool |
| `destroy` | 删除操作跳过回收站（硬删） | ① bool |
| `sourceAppId` / `sourceAppType` | 跨表复制/关联时的来源对象 | ① 字符串 ID / int（同 appType） |
| `filters` | 批量操作的「条件+排序」分组 | ③ 元素内的条件同 OperateCondition 形状；以 `node get` 实际返回为准 |

### SEARCH(7)

查询变体（406/420/421/422）在建节点时已固定，save 时不传 `actionId`（专用命令的 `-a` 只用于选参数组合）。

| 键 | 含义 | 值形态 |
|---|---|---|
| `appId` | 被查询的工作表 | ① 字符串 ID |
| `selectNodeId` | 提供查询输入的上游节点 | ① 节点 ID 字符串 |
| `operateCondition` | 查询条件 | ③ → [OperateCondition](../scripts/types/operate-condition.schema.json) |
| `sorts` | 排序——第一条命中 | ③ → [SortItem](../scripts/types/sort-item.schema.json) 数组 |
| `random` | 忽略排序随机取 | ① bool |
| `executeType` | 查不到时 | ① 0=中止或走「无数据」分支 1=新建一条后继续 2=跳过继续 |
| `fields` | `executeType=1` 时新建记录的字段值 | ③ → [WorkflowFieldWrite](../scripts/types/workflow-field-write.schema.json) 数组 |
| `findFields` | 链接解析/匹配模式下作为查找键的字段 | ③ 以 `node get` 实际返回为准 |
| `link` | 记录链接来源值（链接解析变体） | ② 字符串或字段引用，待解析的记录 URL |
| `destroy` | 「查到并删除」变体：硬删跳过回收站 | ① bool |
| `returnNew` | 后续节点看到的快照 | ① `false`=本节点时刻的数据副本，`null`=每次使用重新取最新 |
| `ignoreError` | `executeType=1` 时插入失败（唯一索引冲突）也继续 | ① bool |
| `execute` | 透传标志，按读到的原值回传 | ① bool |
| `filters` | 「条件+排序」分组 | ③ 同 ACTION 的 filters |
| `flowNodeMap` | 内嵌子节点配置（如查不到时的新建分支） | ③ 以 `node get` 实际返回为准 |

### APPROVAL(4)

| 键 | 含义 | 值形态 |
|---|---|---|
| `accounts` | 审批人 | ③ → [WorkflowAccounts](../scripts/types/workflow-accounts.schema.json) 数组 |
| `multipleLevelType` | 审批人模式 | ① 0=指定审批人；1/2=逐级向上（变体）；3/4=逐级向下（变体）；11=由上一审批人从候选范围圈定 |
| `multipleLevel` | 逐级模式的层数 | ① int，-1=直到最高层 |
| `countersignType` | 多人审批方式 | ① 3=或签（一人通过即可） 1=会签（全员通过） 2=会签（一人通过即通过，否决需全员） 4=会签（按通过比例） |
| `condition` | `countersignType=4` 的通过比例 | ① 字符串 `"10"`…`"100"` |
| `operationTypeList` | 启用的附加操作（转交/加签/退回/打印…） | ② int 列表，按 `node get` 读到的现值增删 |
| `ignoreRequired` | 必填字段为空也允许通过 | ① bool |
| `isCallBack` | 退回后允许重新审批（回调） | ① bool |
| `callBackType` / `callBackMultipleLevel` / `callBackNodeType` / `callBackNodeIds` | 回调方式 / 深度 / 退回到哪些节点 | ② int / int / int / 节点 ID 列表；照读到的原值改 |
| `formProperties` | 审批时每个字段的查看/编辑/必填/隐藏 | ③ 以 `node get` 实际返回为准 |
| `passBtnName` / `overruleBtnName` / `returnBtnName` | 自定义按钮文案 | ① 字符串 |
| `auth` | 通过/否决时的签名、附件要求 | ③ `{passAuth:[], overruleAuth:[]}`，以实际返回为准 |
| `batchApprove` / `fastApprove` | 允许批量审批 / 免打开记录快速审批 | ① bool |
| `allowUploadAttachment` | 审批意见允许传附件 | ① bool |
| `schedule` | 超时自动通过 / 升级提醒 | ③ 以 `node get` 实际返回为准 |
| `passSendMessage` / `passMessage` / `overruleSendMessage` / `overruleMessage` | 通过/否决时通知发起人 + 模板文案 | ① bool / 字符串 |
| `encrypt` | 审批操作需身份验证 | ① bool |
| `operationUserRange` | 各操作（转交/转审…）允许的人员范围 | ③ 操作码 → Accounts 数组的映射 |
| `opinionTemplate` | 预置审批意见模板 | ③ 以 `node get` 实际返回为准 |
| `flowNodeMap` | 内嵌通知子节点配置 | ③ 以 `node get` 实际返回为准 |
| `userTaskNullMap` | 审批人为空时的处理 | ③ 以 `node get` 实际返回为准 |
| `candidateUserMap` | `multipleLevelType=11` 的候选范围 | ③ 以 `node get` 实际返回为准 |
| `addNotAllowView` | 审批人无视图权限时隐藏记录 | ① bool |
| `signOperationType` | 加签的先/后顺序行为 | ① int，照读到的原值改 |
| `explain` | 展示给审批人的说明文字 | ① 字符串 |

### CC(5)

| 键 | 含义 | 值形态 |
|---|---|---|
| `accounts` | 抄送对象 | ③ → [WorkflowAccounts](../scripts/types/workflow-accounts.schema.json) 数组 |
| `sendContent` | 通知正文（支持字段引用） | ① 字符串 |
| `selectNodeId` | 被抄送记录来自哪个节点 | ① 节点 ID 字符串 |
| `formProperties` | 收件人可见的字段范围 | ③ 以 `node get` 实际返回为准 |
| `viewId` | 用哪个视图呈现记录给收件人 | ① 视图 ID 字符串 |
| `addNotAllowView` | 收件人无视图权限时限制查看 | ① bool |
| `showTitle` | 消息里显示记录标题（`sendContent` 为空时强制 true） | ① bool |
| `flowNodeMap` | 内嵌子节点配置 | ③ 以 `node get` 实际返回为准 |

注意：`smsContent` / `templateId` 属于短信节点（type 10），不是 CC 的键。

### WEBHOOK(8)

| 键 | 含义 | 值形态 |
|---|---|---|
| `sendContent` | **请求 URL**（支持字段引用）——不要找 `url` 键，它不存在 | ① 字符串 |
| `method` | HTTP 方法 | ① 1=GET 2=POST 3=PUT 14=DELETE 5=HEAD 6=PATCH |
| `headers` | 请求头（空名会被过滤） | ② `[{name, value}]` |
| `contentType` | 请求体编码 | ① 1=x-www-form-urlencoded 2=raw 3=raw 子变体 4=form-data 5=binary |
| `body` | 原始请求体（contentType 2/3） | ① 字符串 |
| `formControls` | form-data / urlencoded 的键值参数 | ③ 以 `node get` 实际返回为准 |
| `settings` | 超时、重试等传输设置 | ③ 以 `node get` 实际返回为准 |
| `successCode` | 视为成功的状态码 | ① 字符串/int |
| `errorMap` | 状态码 → 自定义错误消息（两侧都要填） | ② 状态码到消息的映射 |
| `errorMsg` | 默认错误消息 | ① 字符串 |
| `executeType` | 超时/失败时 | ① 0=中止 2=跳过继续（此节点没有 1） |
| `authId` | 关联的鉴权账户 ID | ① 字符串 ID |
| `ignoreValueEmpty` | 跳过取值为空的参数 | ① bool |
| `disabledCode` | 判定成功时忽略 HTTP 状态码 | ① bool |
| `selectNodeId` | 字段替换的数据来源节点 | ① 节点 ID 字符串 |
| `testMap` | 已保存的测试参数值 | ③ 以 `node get` 实际返回为准 |

正式保存前可用 `hap workflow node test-webhook <pid> <nid> -u <url> -m POST -b '<body>'` 干跑。

### EMAIL(11)

| 键 | 含义 | 值形态 |
|---|---|---|
| `actionId` | 发送模式 | ① `"202"`=标准（抄送人互相可见） `"201"`=一对一单发 |
| `accounts` | 收件人（至少一个） | ③ → [WorkflowAccounts](../scripts/types/workflow-accounts.schema.json) 数组（邮箱字面量用 type 7） |
| `ccAccounts` | 抄送人（仅标准模式） | ③ 同上 |
| `fields` | 邮件内容——**主题和正文都在这里**，没有顶层 `subject`/`content` 键 | ② `[{fieldId:"subject", fieldValue:"..."}, {fieldId:"content", fieldValue:"...", isRichText:bool}]` |
| `appType` | 透传键，按读到的原值回传 | ① int |

### DELAY(12)

| 键 | 含义 | 值形态 | 适用 |
|---|---|---|---|
| `actionId` | 延时模式 | ① `"300"`=延到某个日期时刻 `"301"`=延时一段时长 | 全部 |
| `fieldValue` / `fieldNodeId` / `fieldControlId` | 目标日期：静态值或字段引用（顶层内联） | ② 静态填 `fieldValue`；引用字段填 `fieldNodeId`+`fieldControlId` | 300 |
| `fieldControlType` / `fieldControlName` | 被引用日期控件的类型/名（类型 16=日期时间，自带时间） | ① int / 字符串 | 300 |
| `executeTimeType` | 相对目标日期的时间锚点——键名是它，**没有 `executeTime` 这个键** | ① 0=当时 1=之前 2=之后 | 300 |
| `time` | 当天的时刻 `"H:mm"`（默认 `"8:00"`；日期时间控件自带时间时置 null） | ① 字符串 | 300 |
| `number` / `unit` | 前移/后移的量与单位 | ① int / 1=分钟 2=小时 3=天 | 300 |
| `day` | 天数标记；`executeTimeType != 0` 时固定为 1 | ① int | 300 |
| `numberFieldValue` / `hourFieldValue` / `minuteFieldValue` / `secondFieldValue` | 时长的天/时/分/秒，各自可静态或引用字段 | ② 每个都是 `{fieldValue, fieldNodeId, fieldControlId}` 形状 | 301 |

### BRANCH 网关(1) + 分支项(2)

分支由两层组成：**网关**（type 1，决定有哪些分支、求值顺序、互斥还是并行）和**分支项**（type 2，每个分支自己的进入条件）。两层都用同一个 `node save` 写回，但读法和键名各有坑，先看完再动手。

**坑 A — 网关配置读不出，要从 `node list` 取。** `node get --type 1` 对网关返回的 `flowIds` / `gatewayType` 全是 `null`（网关不是「详情节点」）。网关的真实配置只在 `node list` 的 `flowNodeMap` 里：

```bash
hap --json workflow node list <pid> | jq '.flowNodeMap["<gatewayId>"] | {flowIds, gatewayType}'
```

| 网关键 | 含义 | 值形态 |
|---|---|---|
| `flowIds` | 各分支项 ID 的**求值顺序**数组 | ② 分支项 ID 字符串数组 |
| `gatewayType` | 求值方式 | ① 1=并行（所有满足条件的分支都进）；2=排他（按 `flowIds` 顺序逐个判，命中第一个就停） |

写回网关（只传要改的键，走 `--type 1`）：

```bash
hap workflow node save <pid> <gatewayId> --type 1 -c '{"flowIds":["b3","b1","b2"],"gatewayType":2}'
```

**坑 B — 分支项条件「读键 ≠ 写键」，写错会静默丢弃。** 这是分支里最大的坑：

- **读**：`node get --type 2` 把条件放在 `conditions` 字段里返回（不是 `operateCondition`！`jq .operateCondition` 会得到 `null`）。
- **写**：`node save --type 2` 的**规范写键是 `operateCondition`**。值的二维数组结构两边完全相同（外层 OR、内层 AND，→ [OperateCondition](../scripts/types/operate-condition.schema.json)）。
- 本 CLI 已对分支项（type 2）做兼容：`-c` 里用 `conditions` 也会自动映射成 `operateCondition`，所以**直接把读到的 `{conditions}` 原样写回也能生效**。但请优先用 `operateCondition` 作规范键。

读分支项条件别整段打印——`node get --type 2` 会带上整张表的字段目录（`flowNodeList`/`flowNodeAppDtos`），输出可达上百 KB。只取要看的键：

```bash
hap --json workflow node get <pid> <branchItemId> --type 2 | jq '{name, conditions}'
```

save 配置只需 `{name, desc, operateCondition}`；`flowNodeList`/`flowNodeAppDtos` 是只读的字段目录，不必回传。

| 分支项键 | 含义 | 值形态 |
|---|---|---|
| `operateCondition` | 该分支的进入条件组（写键；读时叫 `conditions`） | ③ → [OperateCondition](../scripts/types/operate-condition.schema.json) |
| `resultTypeId` | 只读：系统结果分支标记（1=通过 2=否决 3=有数据 4=无数据），非 0 的分支项不可编辑、不要回传修改 | ① int（只读） |

**给已有网关加一条并列分支（标准四步）。** `node add --type 2 --after <gatewayId>` 建的新分支项总是**追加到 `flowIds` 末尾**，排在「默认分支」（空条件那条）之后。排他网关（`gatewayType=2`）按 `flowIds` 顺序求值、**空 `operateCondition` 的分支项 = 默认兜底分支，必须排在最后**，所以新分支几乎总要手动前移：

```bash
# 1. 建分支项（自动入网关 flowIds 末尾）
hap workflow node add <pid> --type 2 -n "高优先级" --after <gatewayId>
# → 记下返回的新分支项 ID，设为 <newId>

# 2. 回写网关，调整 flowIds 顺序（更具体的条件靠前、空条件默认分支放最后）
hap workflow node save <pid> <gatewayId> --type 1 -c '{"flowIds":["<newId>","<existingId>","<defaultId>"]}'

# 3. 写新分支项的进入条件
hap workflow node save <pid> <newId> --type 2 -c '{"operateCondition":[[{"filedId":"<字段id>","filedTypeId":6,"conditionId":"9","conditionValues":[{"value":"0"}]}]]}'

# 4. 在新分支项后接动作节点
hap workflow node add <pid> --type 6 -n "处理" --after <newId> -a 1 --app-id <worksheet_id>
```
