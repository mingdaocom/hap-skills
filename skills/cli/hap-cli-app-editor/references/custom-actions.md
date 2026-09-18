# 自定义动作按钮（记录按钮）

## 调用范式

```bash
# 列出工作表上的按钮
hap worksheet custom-actions <worksheetId>
hap worksheet custom-actions <worksheetId> --view-id <viewId>   # 只看该视图显示的
hap worksheet custom-actions <worksheetId> --kind ai            # 只看 AI 动作（另一档是 action）
hap worksheet custom-actions <worksheetId> --deleted            # 已删除的按钮
hap worksheet custom-actions <worksheetId> --record-id <rowid>  # 这条记录上哪些按钮能点

# 模式一：--action-spec 高层声明（推荐）
hap worksheet create-custom-action <worksheetId> -a <appId> --action-spec '{
  "name": "标记完成",
  "type": "updateCurrentRecord",
  "updateFields": ["<controlId>"],
  "confirm": true,
  "confirmMsg": "确认标记为完成吗？",
  "enableWhen": {"logic":"and","items":[
    {"field":"<状态列>","op":"ne","value":"<已完成选项key>"}]}
}'

# 模式二：--config 原始 wire 配置，原样下发
hap worksheet create-custom-action <worksheetId> -a <appId> --config '{...}'

# 原地更新：带 --btn-id，在原按钮上改
hap worksheet create-custom-action <worksheetId> -a <appId> \
  --btn-id <btnId> --action-spec '{...}'

# 删除（永久，不进回收站）
hap worksheet delete-custom-action <worksheetId> <btnId> -a <appId> -y

# 「从某个视图里撤下」是另一回事，不是删除
hap worksheet delete-custom-action <worksheetId> <btnId> --view-id <viewId>
hap worksheet delete-custom-action <worksheetId> <btnId> --view-id <viewId> --placement list
```

坑位提示：

- **两种模式二选一**：`--action-spec` 是干净的高层结构，由命令降级为 wire 配置；`--config` 是原始 wire 形态，原样发送。不要混填。
- 每个按钮创建时会**自动生成一条关联的自动化流程**，命令会把它的 processId 一并返回，方便接着搭流程。**后续修改必须带 `--btn-id` 原地更新**——不带就会新建一个按钮和一条新流程，老流程上的配置全丢。
- **`updateFields` 里每个字段的填写模式，跟着字段自己在工作表上的设置走**：工作表上必填的字段
  在按钮表单上也必填，其余是选填，本来就不能填写的类型（附件、公式、备注…）只读展示。不需要、
  也不应该自己去指定档位。
- **`enableWhen` 一给，按钮就自动变成「满足条件才可用」**，不用再手工设别的开关。筛选门槛二选一：
  `enableWhen` 用统一筛选写法（推荐，如 `{"logic":"and","items":[{"field":"<状态列>","op":"ne","value":"<已完成选项key>"}]}`），
  或 `filters` 直接给 wire 形态数组。写法与按钮上可用的比较方式见 `hap guide record filter`（3.2 那张表的
  「视图/规则/按钮/图表」一列）。
- **`confirm` 一给，按钮就真的弹二次确认框**；`confirmMsg` 是框里的文案，不给用默认文案（按当前
  CLI 语言写入按钮）。任何 type 都能叠加。
- **`--view-id` 撤下按钮只对「限定了显示视图」的按钮有效**。按钮设成「所有视图都显示」时没有
  「某个视图的成员资格」可撤，命令会直接报错让你先限定显示视图，而不是假装撤下了。
  `--placement` 配合 `--view-id`：`list` 只从记录行撤，`detail` 只从记录页撤，不给就两处都撤。

## 数据字典

字典核对于 hap-cli 0.9.0；未覆盖的键以读命令返回的实际结构为准。

### action_spec 键表（--action-spec 输入）

未列出的键会被忽略。worksheetId / appId / btnId 由命令行参数提供，不要写进 JSON。

| 键 | 含义 | 值形态 |
|---|---|---|
| name | 按钮显示名 | string |
| desc | 按钮描述 | string（默认 ""） |
| type | 动作类型，默认 triggerWorkflow | enum `updateCurrentRecord` \| `createRelatedRecord` \| `triggerWorkflow` |
| updateFields | （updateCurrentRecord）弹窗中要填写的字段；每项的填写模式由该字段自身的必填/可写性推导 | `["<controlId>", ...]` |
| relationField | （createRelatedRecord）新记录写入的关联字段 | controlId string |
| relationControl | （createRelatedRecord）配套透传值 | string（默认 ""） |
| enableWhen | 按钮可用条件（满足筛选才显示） | 统一写法 `{logic, items:[{field, op, value}]}`；旧的 wire 数组 → [FilterCondition[]](../scripts/types/filter-condition.schema.json) 也收 |
| filters | enableWhen 的 wire 形态替代写法 | wire 筛选数组（与 enableWhen 二选一） |
| confirm | 强制二次确认弹窗 | bool |
| confirmMsg | 确认弹窗文案 | string（默认 "你确认执行此操作吗？"） |
| sureName | 确认按钮文案 | string（默认 "确认"） |
| cancelName | 取消按钮文案 | string（默认 "取消"） |
| isAllView | 在所有视图显示 | int 0/1（默认 1） |
| icon / color / showType / isBatch / advancedSetting | wire 键直通，原样复制 | 按 wire 键表 |

### type → wire 降级映射

| spec type | clickType | writeType | writeObject | 额外 wire 键 |
|---|---|---|---|---|
| updateCurrentRecord | 3（填写） | 1（填写字段） | 1（本记录） | `writeControls: [{controlId, type}]`，type 按字段推导（见下） |
| createRelatedRecord | 3（填写） | 2（新建关联记录） | 2（关联记录） | `addRelationControlId`、`relationControl` |
| triggerWorkflow（默认） | 1（立即执行）；带 confirm 时 2（二次确认） | ""  | "" | — |

固定下发：`workflowType: 1`（按钮驱动其关联流程）、`isAllView`。

**`writeControls[].type` 由字段自身推导，不是固定值**：不可写的类型（附件、公式、备注…）给 `1`
只读，工作表上必填的字段给 `3` 必填，其余给 `2` 填写。走 `--action-spec` / edit-spec 的
`action_spec` 都会这样推；**只有裸 `config` 不会**（见下）。

### wire config 键表（--config 输入 / custom-actions 返回）

| 键 | 含义 | 值形态 |
|---|---|---|
| name | 按钮名 | string |
| desc | 描述 | string |
| clickType | 点击行为 | int enum：1=立即执行，2=二次确认，3=填写 |
| writeType | 填写类型 | int enum：1=填写字段，2=新建关联记录 |
| writeObject | 填写对象 | int enum：1=本记录，2=关联记录 |
| writeControls | 填写字段清单 | `[{controlId, type}]`；type：1=只读，2=填写，3=必填 |
| addRelationControlId | 新建关联记录的目标关联字段 | controlId string |
| relationControl | 关联配套值 | string |
| showType | 显示条件 | int enum：1=一直显示，2=满足筛选条件；**没设门控的按钮读回来可能是 `0`**，以读回值为准 |
| filters | 显示/可用筛选 | → [FilterCondition[]](../scripts/types/filter-condition.schema.json) |
| isAllView | 所有视图显示 | int 0/1 |
| workflowType | 流程驱动标记 | int（固定 1） |
| confirmMsg / sureName / cancelName | 二次确认文案三件套 | string |
| icon / color | 图标与颜色 | string |
| isBatch | 允许批量执行 | bool |
| advancedSetting | 高级设置 | object（以读命令返回为准） |

## 🚨 edit-spec 里的 `config` 是原始逃生口，不经适配

`custom-action.create` / `custom-action.update` 两个 op 都能二选一地给 `action_spec` 或 `config`。
给 `config` 时它按原样发出，**适配器做的事一件都不发生**：

- `clickType` / `writeType` / `writeObject` 的配对不会补
- `showType` 不会因为你写了筛选而切到「满足条件才显示」
- 填写类按钮的二次确认（`enableConfirm`）不会设
- `writeControls[].type` 不会按字段推导，全部落到默认档

它是「适配器造不出来的形状」的正当出口，但走它就等于放弃上面所有保护。**能用 `action_spec`
就别用 `config`**；确实要用，就自己把整份 wire 配置写全。
