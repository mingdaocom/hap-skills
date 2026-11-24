# Step 2b: 单表并发按波次回填跨表关联、子表与衍生字段 SOP (`2b_create_relations`)

<!-- SOURCE: build-app/worksheet-relation-build-sub-agent.yaml -->

## 一、 本地宿主输入与参考映射

- **执行方式**：独立 Subagent **单表并发执行，按依赖图自动分波**（两遍建表 Pass 2，此时全应用所有工作表均已创建）。无前置依赖的表在第 1 波全并发落地；依赖前序波次由对端 `:bi` 自动生成的反向关联、子表跨表列或他表衍生字段的表自动排入后续波次，由运行时引擎控制波次释放；纯 `:reverse` 且无衍生字段与 `requirements` 的表已自动跳过。
- **输入切片**：读取预编译任务包或 `.build/task-context/{taskId}.json`：
  - `planSlice`：`worksheetName`、`worksheet`（该表完整设计）、`fields`、`relationLayout`（Pass 1 预留的待补复杂字段数组）、`relationDefaults`（可选：Pass 1 交接的跨表动态默认值待办数组）、`waveIndex` / `totalWaves`、`dependsOnWorksheets`、`needsPreReadStructure`、`requirements`、`appLanguage`、`allWorksheetOrder` 与 `allRelationLayouts`（供双边双向关联防重仲裁；兼容恢复历史分组工程时若存在 `planSlice.items` 则按组内逐表顺序处理）；
  - `contextSlice`：`appId`、`worksheetId`、`worksheetIdByName`（全应用表名→ID）、`worksheetFieldsByName`（本表及相关目标表在 Pass 1 已建的基础字段 `{ name, id, alias, type }` 轻量索引）、`fieldOptionsContext`（相关表选项字段的真实选项 `{ key, value }` 映射）。
- **必读领域规范**：`references/hap-domain-worksheet-spec.md`（若本表含 `requirements` 时已自动附带 `references/hap-domain-worksheet-index-spec.md`）
- **主要业务工具**：
  - 默认 `["update_worksheet"]`（Wave 1 及无反向依赖表 **零回读直写**）；
  - 仅当 `planSlice.needsPreReadStructure === true`（存在依赖前序波次 `:bi` 自动生成的反向关联或目标表无预留别名的衍生字段）时，额外开放 `get_worksheet_structure`（**仅允许写前调用 1 次**获取反向关联真实 24 位 `id` 或目标字段真实 `alias`/`id`）；
  - 仅当本表 `requirements` 非空时，额外开放 `get_worksheet_index_list` 与 `create_worksheet_index`（仅在 `requirements` 明确要求全表无条件唯一字段组合时调用；缺省、按状态防重或允许重复草稿时完全跳过索引步骤含查询）。

---

## 二、 核心构建规则与单表执行步骤

1. **前置核对与按需写前 1 次结构读取**：
   - `worksheetId` 缺失时先从 `contextSlice.worksheetIdByName`、前序回执或线上工作表定位真实 ID，无法定位时报告依赖缺口，不能伪造成功；若本表 `relationLayout` 为空、无待补非 `:reverse` 跨表/衍生字段且无需建全表唯一索引，直接写成功回执（`addedCount: 0`）。
   - **环路分段边界（`planSlice.totalParts > 1` 时适用）**：当多张表存在跨表环路依赖时，运行时会自动将破环表按字段拆分为多段（如 `p1`/`p2` 或 `p1`/`p2`/`p3`）。本段**只创建 `planSlice.fields` / `planSlice.relationLayout` 中列出的字段子集**——严禁提前建 `deferredFields`，严禁重复建 `completedInPrevPartFields`（引用前段已建关联时直接用 `allRelationLayouts` 中的预留 `alias` 或写前读取的真实 ID）。
   - **仅当 `planSlice.needsPreReadStructure === true`（且白名单包含 `get_worksheet_structure`）时**：在调用 `update_worksheet` **之前**，调用 1 次 `get_worksheet_structure(responseFormat: "md")` 读取本表精简 Markdown 结构（体积仅 ~3KB 可直接内联、避免 `dsl` 落盘多耗 1 轮读文件，已完整包含前序波次由对端 `:bi` 自动生成的反向关联真实 24 位 `id` 与 `dataSource`；若本表 `Rollup`/`Lookup` 引用的目标表字段在前序波次新建且 `allRelationLayouts` 未给出明确 `alias`，最多再以 `responseFormat: "md"` 读 1 次该目标表结构）。
   - **严禁写后回读铁律**：无论属于哪一波次，**一旦 `update_worksheet` 返回成功，严禁再调用 `get_worksheet_structure` 复核验货**（全应用最终完整结构统一在 Step 3 集中采集）。
2. **双边 `:bi` 确定性防重仲裁**：
   - 若两张表在规划中均漏标 `:reverse` 而双向互指（均含 `bidirectional: true` 指向对方），仅由单条从属端（`isMultiple === false`）调用 API 创建，多条聚合端自动跳过；
   - 若基数相同，严格按 `planSlice.allWorksheetOrder` 中的全局工作表先后顺序仅由排在前面的表创建。
3. **按依赖顺序组装本表 `addFields`（先 `Relation`/`SubTable`，再 `Lookup`/`Rollup`，最后使用这些本表字段的 `Concatenate`/`Formula`，保留预留 `layout`）**：
   - **`Relation`（跨表关联）**：`dataSource` 从 `worksheetIdByName[targetWorksheet]` 取真实 24 位 ID（查不到则跳过该项，严禁编造 ID）；传入原 `name`、`alias`、`layout: { rowIndex, span }`，落实该关联的字段级约束（如 `relationLayout.required`）；`config` 含 `bidirectional`、`isMultiple`、`displayMode`、`showFields`（从 `worksheetFieldsByName[targetWorksheet]` 挑 2～4 个核心字段的真实 **alias**，必含标题字段，排除富文本/长附件）及可选 `coverField`（仅 `displayMode === "card"` 且目标表有 `Attachment` 字段时填其真实 `alias`）。注意：`config.resultFilter` 仅支持静态常量条件，严禁填入动态字段 ID；跨表归属一致统一交由字段 `defaultValue(source="relation")`、`Lookup` 或 Step 3 业务规则 `setFieldValue(rcid)` 承接，关联字段创建成功即记 `succeeded`。
   - **`SubTable`（子表挂载）**：`dataSource` 取子表真实 ID，`layout: { rowIndex, span: 12 }`（强制独占整行 12 列），`config: { bidirectional: true, showFields: [<子表真实业务字段 alias，含前序波次子表已建好的跨表关联预留 alias>] }`（不传 `displayMode` / `isMultiple`）。无法确认的列不可编造 alias，记录到 `issues` 交由 Step 3 父表任务核对补齐。
   - **`Lookup`（他表字段）**：保留 `relationLayout.alias` 供同批表达式引用；`relationField` 填本表对应单条关联字段的真实 `alias`（若是前序波次对端 `:bi` 自动生成的反向关联则填其真实 24 位 `id`）；`sourceField` 匹配目标表真实 **`alias`**（或前序波次新建字段的真实 `alias`/`id`，严禁拼音编造）；`storeData` 按 [工作表规范 §9.2](../../references/hap-domain-worksheet-spec.md#92-lookup他表字段引用) 选择——仅显示用 `false`，本表文本组合（`Concatenate`）、公式计算、分组/筛选等确需引用存储值时设 `true`（不因工作流取值开启存储）；带原 `layout`。
   - **`Rollup`（汇总字段）**：保留 `relationLayout.alias` 供同批表达式引用；`relationField` 填本表主动 `Relation`/`SubTable` 的真实 **`alias`**，或写前 1 次 `get_worksheet_structure` 查到的**反向关联字段真实 24 位 `id`**（反向关联由服务端自动生成，通常无预定 `alias`）；`sourceField` 匹配目标表/子表字段的真实 **`alias`**（或前序波次新建字段的真实 `alias`/`id`，纯计数可省略）；结合字段名称与目标表结构判断业务统计口径（如“累计收款/累计出库/累计退货”需按目标表状态或类型过滤），对照 `update_worksheet` 实时 Schema 构造聚合配置与单层平铺过滤条件（选项 `key` 从 `contextSlice.fieldOptionsContext` 读取）；带原 `layout`。
   - **依赖衍生字段的 `Concatenate` / `Formula`**：按预留的 `name`、`alias`、`isTitle`（若为计划组合标题传 `isTitle: true`）、`precision`、`layout` 及 `config: { expression }` 构造。
4. **单次合并提交 `update_worksheet(addFields + editFields)`、按需建唯一索引与异常恢复**：
   - 对本表 `addFields` 按 `(name, dataSource)` 去重（`inlineTable` / `tabTable` 强制 `layout.span = 12`）；
   - **同请求合并回绑跨表动态默认值（`planSlice.relationDefaults` 非空时）**：构造 `editFields`——每项仅传接收字段真实 `id`（取自 `contextSlice.worksheetFieldsByName[worksheetName]`）和解析后的完整 `defaultValue` 数组（未传属性服务端自动保留）：其中 `source: "relation"` 的 `relationField` 填本表关联字段真实 `alias`（支持直接引用本批 `addFields` 新建的单条关联 `alias`，不支持多条关联）、`field` 填目标表来源字段真实 `alias`（取自 `contextSlice.worksheetFieldsByName[targetWorksheet]` 或 `allRelationLayouts`），同数组内若混有 `source: "field"` 则同步解析为本表 `alias`；缺依赖或无可用 `alias` 的单条跳过并记入 `issues`。
   - **合并为 1 次 `update_worksheet(appId, worksheet_id, addFields?, editFields?)` 提交**（HAP 后端支持同请求 `editFields` 引用 `addFields` 新建关联的 `alias`，省去额外 1 轮工具往返；若 `addFields` 与 `editFields` 均为空则跳过写入；仅当合并提交因某条 `editFields` 报参错时再拆出 `addFields` 先写并对 `editFields` 单条容错），返回成功即完成字段写入（**严禁写后回读结构**）；
   - **按需配置全表唯一索引**：仅当本表 `requirements` 明确要求全表无条件唯一字段组合时，在字段就绪后按 `references/hap-domain-worksheet-index-spec.md` 调用 `get_worksheet_index_list` 与 `create_worksheet_index(type: "unique")`（复用等价唯一索引，已确认新建空表无需查重记录）；无此要求、按状态防重或允许重复草稿时完全跳过索引步骤（含查询）；
   - **别名冲突自愈**：若遇 `别名重复` 报错，剥离冲突字段的 `alias` 让系统自动生成（若同批 `Lookup/Rollup` 依赖该字段则按需分步用返回 ID 衔接），核实写入结果后修正并继续；成功或写入状态不明时不重放 `update_worksheet`。

---

## 三、 本地回执落盘契约

本表回填完成后，立即将标准单表回执写入 `receiptPath`（`.build/receipts/step2b-rel-{worksheetName}.json`；若恢复历史分组任务 `target.type === "worksheet_group"` 则沿用 `outputs.completedWorksheets` 覆盖 `target.worksheets`）：

```json
{
  "taskId": "<来自 taskContext.taskId>",
  "runId": "<来自 taskContext.runId>",
  "executor": { "kind": "subagent", "agentId": "<当前子代理标识>" },
  "step": "2b",
  "target": {
    "type": "worksheet",
    "id": "<worksheetId>",
    "name": "<表名>"
  },
  "status": "succeeded",
  "outputs": {
    "worksheetName": "<表名>",
    "worksheetId": "<worksheetId>",
    "addedCount": 2
  },
  "verification": {
    "passed": true,
    "evidence": ["调用 update_worksheet 完成本表跨表关联与衍生字段回填"]
  },
  "issues": []
}
```
