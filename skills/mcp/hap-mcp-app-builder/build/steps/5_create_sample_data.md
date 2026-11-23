# Step 5: 拓扑感知示例数据批量填报 SOP (`5_create_sample_data`)

<!-- SOURCE: build-app/sample-data-sub-agent.yaml -->

## 一、 本地宿主输入与参考映射

- **执行方式**：独立后台 Subagent 执行（与阶段 3 页面、排序、角色、工作流设计并行运行）。
- **输入切片**：读取 `.build/task-context/step5-sample-data.json`：
  - `planSlice`：`worksheets`（含 `name`、`worksheetType`、`parentWorksheet`、`requirements`）、`appLanguage`；
  - `contextSlice`：`appId`、`worksheetIdByName`；
  - `worksheetContextSlice`：已自动过滤只读衍生字段（如自动编号、公式、日期公式、函数公式、汇总、他表字段、内联子表占位）的工作表可写字段切片，每个字段含 `{ id, name, alias?, type, dataSource?, options? }`（其中 `Relation` 字段的 `dataSource` 为目标表的 24 位 `worksheetId` 或 `"selfRelation"`，单多选/下拉的 `options` 为有效选项文本数组）。
- **必读领域规范**：`references/hap-sample-data-spec.md`（预设虚拟成员 ID、文档与分类图片资源）
- **主要业务工具**：`["batch_create_records", "get_worksheet_structure", "get_record_details", "update_record"]`（`update_record` 仅用于抽查发现本步刚写入记录存在字段 ID 误填或关联遗漏时的原位修正，同样固定传 `triggerWorkflow: false`）

---

## 二、 核心构建规则与执行步骤

- **输出语言与排除规则**：所有记录文本严格使用 `appLanguage` 指定语言；优先遵循各表 `requirements` 的条数与场景要求（明确要求不生成示例数据的表直接从灌数清单排除，且不为关联被排除的表替其新建记录）。
- 示例填值覆盖已有可写业务字段，包括适用的成员，以及有相应材料的代表性记录的附件。用户明确排除的字段或资源按其要求处理。
- **Build 默认数量与取值策略**：
  - 未显式指定条数时：参数/全局设置表 `1` 条，字典/分类表 `3` 条，核心业务表 `8～10` 条，明细子表每条父记录 `2～3` 条明细，自关联表 `2` 条根记录 + `5` 条子记录；
  - 日期默认分布在当前时间前后 3 个月内。
- **三批次依赖灌数顺序**：
  1. **第一批（无跨表引用的基础主数据/字典表）**：先调用 `batch_create_records` 写入，缓存返回的真实 `rowId` 数组；
  2. **第二批（含跨表 `Relation` 的业务单据表）**：从内存缓存取已建主表记录的真实 `rowId` 填入关联字段，调用 `batch_create_records` 并缓存本表 `rowId`；
  3. **第三批（`worksheetType === "subTable"` 明细子表）**：从缓存取所属主表（`parentWorksheet`）的真实 `rowId`，按主从写入规范为主记录批量生成明细行。
- **硬约束与防错红线**：
  - **`worksheet_id` 与字段 `id` 严禁编造**：必须逐字复制自 `worksheetContextSlice` 的 24 位 hex 字符串；`Relation` 字段通过其 `dataSource`（对照 `worksheetIdByName` 或 `"selfRelation"`）精确匹配上游表已生成的真实 `rowId`（含子表指向 `parentWorksheet` 的父记录关联字段）；若遇 `430022 worksheetId不存在` 或上下文缺失，按需调用 `get_worksheet_structure(responseFormat: "dsl")` 核实后继续；
  - **显式关闭工作流与完建不阻断**：所有 `batch_create_records` 调用固定传 `triggerWorkflow: false`；单表失败按 [宿主适配](../../HOST_ADAPTER.md) 排查续作，保留已创建记录，只补未完成部分。受限部分逐表记录实际数量及原因；仅部分完成时不得在证据中声称全部写入。按回执契约报告状态，后台示例任务不阻塞主链路推进。

---

## 三、 本地回执落盘契约

逐表记录实际条数，用返回的 rowId 抽查适用的成员和附件字段，在 `verification.evidence` 写明记录、字段及保存结果，缺项记入 `issues`。

全部目标表处理完毕后，将标准回执写入 `receiptPath`（`.build/receipts/step5-sample-data.json`）：

```json
{
  "taskId": "step5-sample-data",
  "runId": "<runId>",
  "executor": { "kind": "subagent", "agentId": "<agentId>" },
  "step": "5",
  "target": { "type": "sample_data", "name": "全局示例数据" },
  "status": "succeeded",
  "outputs": { "completed": true },
  "verification": {
    "passed": true,
    "evidence": ["<实际写入表及条数>", "<适用成员或附件字段的抽查记录与回读结果>"]
  },
  "issues": []
}
```
