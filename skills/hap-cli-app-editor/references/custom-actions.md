# 自定义动作按钮（记录按钮）

## 调用范式

```bash
# 列出工作表上的按钮
hap worksheet custom-actions <worksheetId>

# 模式一：--action-spec 高层声明（推荐）
hap worksheet create-custom-action <worksheetId> -a <appId> --action-spec '{
  "name": "标记完成",
  "type": "updateCurrentRecord",
  "updateFields": ["<controlId>"],
  "confirm": true,
  "confirmMsg": "确认标记为完成吗？"
}'

# 模式二：--config 原始 wire 配置，原样下发
hap worksheet create-custom-action <worksheetId> -a <appId> --config '{...}'

# 原地更新：带 --btn-id，在原按钮上改
hap worksheet create-custom-action <worksheetId> -a <appId> \
  --btn-id <btnId> --action-spec '{...}'

# 删除（永久，不进回收站）
hap worksheet delete-custom-action <worksheetId> <btnId> -a <appId> -y
```

坑位提示：

- **两种模式二选一**：`--action-spec` 是干净的高层结构，由命令降级为 wire 配置；`--config` 是原始 wire 形态，原样发送。不要混填。
- 每个按钮创建时会**自动生成一条关联的自动化流程**，命令会把它的 processId 一并返回，方便接着搭流程。**后续修改必须带 `--btn-id` 原地更新**——不带就会新建一个按钮和一条新流程，老流程上的配置全丢。
- `updateFields` 里列出的每个字段，在按钮弹出的填写表单中都是**必填**的；没有"可选填写"档位。
- 筛选门槛二选一：`enableWhen` 给高层筛选组结构（推荐），或 `filters` 直接给 wire 形态数组。
- 任何 type 都可以叠加 `confirm` / `confirmMsg`，触发流程类按钮会因此从"立即执行"升级为"二次确认"。

## 数据字典

字典生成于 2026-06-10；未覆盖的键以读命令返回的实际结构为准。

### action_spec 键表（--action-spec 输入）

未列出的键会被忽略。worksheetId / appId / btnId 由命令行参数提供，不要写进 JSON。

| 键 | 含义 | 值形态 |
|---|---|---|
| name | 按钮显示名 | string |
| desc | 按钮描述 | string（默认 ""） |
| type | 动作类型，默认 triggerWorkflow | enum `updateCurrentRecord` \| `createRelatedRecord` \| `triggerWorkflow` |
| updateFields | （updateCurrentRecord）弹窗中要填写的字段 | `["<controlId>", ...]` |
| relationField | （createRelatedRecord）新记录写入的关联字段 | controlId string |
| relationControl | （createRelatedRecord）配套透传值 | string（默认 ""） |
| enableWhen | 按钮可用条件（满足筛选才显示） | → [FilterCondition[]](../scripts/types/filter-condition.schema.json) |
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
| updateCurrentRecord | 3（填写） | 1（填写字段） | 1（本记录） | `writeControls: [{controlId, type:3}]` |
| createRelatedRecord | 3（填写） | 2（新建关联记录） | 2（关联记录） | `addRelationControlId`、`relationControl` |
| triggerWorkflow（默认） | 1（立即执行）；带 confirm 时 2（二次确认） | ""  | "" | — |

固定下发：`workflowType: 1`（按钮驱动其关联流程）、`isAllView`。

### wire config 键表（--config 输入 / custom-actions 返回）

| 键 | 含义 | 值形态 |
|---|---|---|
| name | 按钮名 | string |
| desc | 描述 | string |
| clickType | 点击行为 | int enum：1=立即执行，2=二次确认，3=填写 |
| writeType | 填写类型 | int enum：1=填写字段，2=新建关联记录 |
| writeObject | 填写对象 | int enum：1=本记录，2=关联记录 |
| writeControls | 填写字段清单 | `[{controlId, type}]`；type：1=只读，2=填写，3=必填（高层模式固定下发 3） |
| addRelationControlId | 新建关联记录的目标关联字段 | controlId string |
| relationControl | 关联配套值 | string |
| showType | 显示条件 | int enum：1=一直显示，2=满足筛选条件 |
| filters | 显示/可用筛选 | → [FilterCondition[]](../scripts/types/filter-condition.schema.json) |
| isAllView | 所有视图显示 | int 0/1 |
| workflowType | 流程驱动标记 | int（固定 1） |
| confirmMsg / sureName / cancelName | 二次确认文案三件套 | string |
| icon / color | 图标与颜色 | string |
| isBatch | 允许批量执行 | bool |
| advancedSetting | 高级设置 | object（以读命令返回为准） |
