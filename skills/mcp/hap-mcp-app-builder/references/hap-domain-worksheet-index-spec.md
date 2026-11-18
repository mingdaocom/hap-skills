# HAP 工作表索引规范

## 一、核心契约

按需调用 `get_worksheet_index_list` 定位真实索引并核对本次操作所需状态，已有有效结果直接复用。创建时检查配额；创建或修改索引字段时从 `availableFields` 中选择字段，不使用显示名称或猜测字段 ID。仅改名依据 `canRename=true` 使用 `rename_worksheet_index`，不检查创建配额、不重新选择字段，不用完整更新或删除重建绕过不可改名限制。

```json
{
  "worksheet_id": "<worksheetId>",
  "type": "normal",
  "name": "idx_customer_sign_date",
  "fields": [
    { "field": "biz_customer", "mode": "ascending" },
    { "field": "biz_sign_date", "mode": "descending" }
  ]
}
```

- `type`：`normal` 或 `unique`，不支持 `fullText`。
- `fields`：1～32 个有序字段；`mode` 为 `ascending` 或 `descending`。
- 每张工作表最多 5 个自定义索引，系统 `index_rowid` 不占配额且不可修改或删除。
- 一个复合索引最多包含一个多选类型字段。

## 二、设计规则

- 复合索引遵循最左前缀原则，字段顺序必须与高频筛选条件一致。
- 高区分度字段优先放在前面；排序方向尽量与高频视图默认排序一致。
- 数万行以下的小表通常无需索引；优先用于大表和稳定高频查询。

## 三、唯一索引

- `unique` 会强制字段组合全表唯一，不只是查询优化。
- 仅新建唯一索引、改为唯一或改变唯一字段组合时检查相关数据；复用有效检查结果，缺少时用 `isempty` 精确计数、`get_record_pivot_data` 按目标字段组合统计重复。覆盖不完整或数据不满足当前唯一性契约时停止该索引写入，报告具体缺口，不自行清理记录或改变字段约束。
- 普通索引、仅改名称或删除索引不为唯一性查询记录；已确认空表无需再做重复值统计。
- 唯一索引字段应设置为必填；允许为空时，全表通常只能存在一条空值记录。
- 创建失败但正常记录无重复时，还需检查回收站中的历史重复记录。

## 四、验证与安全

- 创建或结构更新后，若接口返回明确索引状态和真实 `indexId`，可直接记账；返回 `building`、字段状态不明、下游马上依赖唯一性或用户要求复核时才回读索引列表。改名明确成功即可收口，不等待构建；改名、删除结果不明时定向核查，不盲目重放。
- 删除以索引列表的 canDelete=true 为依据；唯一索引删除后不再强制该字段组合唯一。修订授权与最小检查遵循 hap-revision-safety。
- 索引创建、结构修改和删除分别使用 `create_worksheet_index`、`update_worksheet_index`、`delete_worksheet_index`，参数与限制以当前 MCP Schema 为准。
