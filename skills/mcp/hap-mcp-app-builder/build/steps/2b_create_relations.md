# Step 2b: 按关联组回填跨表关联、子表与衍生字段 SOP (`2b_create_relations`)

<!-- SOURCE: build-app/worksheet-relation-build-sub-agent.yaml -->

## 一、 本地宿主输入与参考映射

- **执行方式**：独立 Subagent **按关联连通组并发执行，组内逐表顺序写入**（两遍建表 Pass 2，此时全应用所有工作表均已创建；每组最多 5 张含关联的工作表，既省去逐表冷启动开销，又消除多张从表并发向同一主表注入反向关联的锁竞争）。
- **输入切片**：读取预编译任务包或 `.build/task-context/{taskId}.json`：
  - `planSlice.items`：本组待回填工作表列表，每项含 `worksheetName`、`worksheetId`、`worksheet`（该表完整设计）、`fields`、`relationLayout`（Pass 1 预留的待补复杂字段数组）、`requirements`；
  - `planSlice.allRelationLayouts` 与 `planSlice.allWorksheetOrder`：全应用待补关联索引与工作表原始顺序，供双边双向关联确定性防重仲裁；
  - `planSlice.appLanguage`：应用内容语言代码；
  - `contextSlice`：`appId`、`worksheetIds`（本组表名→ID）、`worksheetIdByName`（全应用表名→ID）、`worksheetFieldsByName`（各表在 Pass 1 已建的基础字段 `{ name, id, alias, type }` 轻量索引）、`fieldOptionsContext`（各表选项字段的真实选项 `{ key, value }` 映射）。
- **必读领域规范**：`references/hap-domain-worksheet-spec.md`
- **主要业务工具**：`["update_worksheet"]`（正常构建复用上下文，Step 3 集中采集含反向关联的完整结构；排查缺失信息或未知写入结果时可定向回读）

---

## 二、 核心构建规则与逐表顺序执行步骤

1. **断点续作跳过与前置核对**：
   - 若存在 `previousReceipt.outputs.completedWorksheets`，先提取已完成的表名（必要时核对线上结构），跳过已成功回填的工作表，仅按顺序处理本组剩余工作表；
   - 按 `planSlice.items` 顺序逐表处理（若某项 `relationLayout` 为空且无待补关联字段，直接记入 `completedWorksheets` 进入下一张表）；`worksheetId` 缺失时先从 `contextSlice.worksheetIdByName`、前序回执或线上工作表定位真实 ID，无法定位时报告依赖缺口，不能伪造成功。
2. **双边 `:bi` 确定性防重仲裁**：
   - 若两张表在规划中均漏标 `:reverse` 而双向互指（均含 `bidirectional: true` 指向对方），仅由单条从属端（`isMultiple === false`）调用 API 创建，多条聚合端自动跳过等待对端自动生成反向字段；
   - 若基数相同，严格按 `planSlice.allWorksheetOrder` 中的全局工作表先后顺序仅由排在前面的表创建（跨组亦保持同一确定性结论）。
3. **对当前表按 `fieldType` 组装 `addFields`（保留预留 `layout`）**：
   - **`Relation`（跨表关联）**：`dataSource` 从 `worksheetIdByName[targetWorksheet]` 取真实 24 位 ID（查不到则跳过该项，严禁编造 ID）；传入原 `name`、`alias`、`layout: { rowIndex, span }`，落实并回读该关联的字段级约束（如 `relationLayout.required`）；`config` 含 `bidirectional`、`isMultiple`、`displayMode`、`showFields`（从 `worksheetFieldsByName[targetWorksheet]` 挑 2～4 个核心字段的真实 **alias**，必含标题字段，排除富文本/长附件）及可选 `coverField`（仅 `displayMode === "card"` 且目标表有 `Attachment` 字段时填其真实 `alias`）。注意：`config.resultFilter` 仅支持静态常量条件，严禁填入动态字段 ID；跨表归属一致（如所选设备与站点一致）统一交由字段 `defaultValue(source="relation")`、`Lookup` 或 Step 3 业务规则 `setFieldValue(rcid)` 承接，关联字段创建成功即记 `succeeded`（反向字段默认以源表命名属平台正常行为）。
   - **`SubTable`（子表挂载）**：`dataSource` 取子表真实 ID，`layout: { rowIndex, span: 12 }`（强制独占整行 12 列），`config: { bidirectional: true, showFields: [<子表当前已存在的业务字段真实 alias>] }`（不传 `displayMode` / `isMultiple`）。子表业务字段尚未创建时不可编造 alias；记录缺失列及子表名称到本表回执的 `issues`。阶段 2b 全组完成后，由阶段 3 的父表任务核对并补齐，不能依赖跨组执行顺序或改变组划分。
   - **`Lookup`（他表字段）**：`relationField` 填本表对应单条关联字段（`isMultiple: false`）的真实 `alias`；`sourceField` 在目标表 `fields` 中按 `sourceFieldName` 匹配取出真实 **`alias`**（严禁拼音编造）；`storeData` 结合该表 `worksheet` 完整计划中的用途按 [工作表规范 §9.2](../../references/hap-domain-worksheet-spec.md#92-lookup他表字段引用) 选择；带原 `layout`（可与同批新建的主动 `Relation` 通过明确声明的 `alias` 同批提交）。
   - **`Rollup`（汇总字段）**：`relationField` 填本表 `Relation` 或 `SubTable` 的真实 `alias`；`sourceField` 在目标表/子表 `fields` 中匹配取出真实 **`alias`**（纯计数可省略）；结合字段名称与目标表结构判断业务统计口径（例如“累计收款/累计发货/累计退货”需按目标表状态或类型过滤），对照 `update_worksheet` 实时 Schema 构造聚合配置与平铺关联过滤条件（选项 `key` 从 `contextSlice.fieldOptionsContext` 读取，注意汇总过滤仅支持单层平铺条件、不支持嵌套条件组）；带原 `layout`。
   - **跨表 `Concatenate` / `Formula`**：按预留的 `name`、`alias`、`isTitle`、`precision`、`layout` 及 `config: { expression }` 原样构造。
4. **组内逐表顺序调用 `update_worksheet` 与异常恢复**：
   - **组内严禁同轮并发调 `update_worksheet`**：本组多张表往往互相关联或共同双向指向同一主表，必须**逐表顺序**执行 `update_worksheet`，待上一张表返回成功后再提交下一张表，杜绝反向字段注入时的锁表冲突；
   - 每张表内部对 `addFields` 按 `(name, dataSource)` 去重（`inlineTable` / `tabTable` 强制 `layout.span = 12`），仅传 `addFields`（**严禁传 `editFields` / `removeFields`**）；
   - **别名冲突自愈**：若遇 `别名重复` 报错，剥离冲突字段的 `alias` 让系统自动生成（若同批 `Lookup/Rollup` 依赖该字段则按需分步用返回 ID 衔接），核实写入结果后修正并继续；若本组某张表确无法恢复，在失败回执的 `outputs.completedWorksheets` 中如实保留已成功的表，不丢弃已完成成果。

---

## 三、 本地回执落盘契约

本组全部目标表回填完成后，将标准分组回执写入 `receiptPath`（`.build/receipts/step2b-rel-group-{N}.json`；`completedWorksheets` **必须完整覆盖 `target.worksheets` 中的本组全部工作表**，否则门禁校验会拦截）：

```json
{
  "taskId": "<来自 taskContext.taskId>",
  "runId": "<来自 taskContext.runId>",
  "executor": { "kind": "subagent", "agentId": "<当前子代理标识>" },
  "step": "2b",
  "target": {
    "type": "worksheet_group",
    "name": "group-1",
    "worksheets": ["<表名1>", "<表名2>"]
  },
  "status": "succeeded",
  "outputs": {
    "completedWorksheets": [
      { "worksheetName": "<表名1>", "worksheetId": "<worksheetId1>", "addedCount": 2 },
      { "worksheetName": "<表名2>", "worksheetId": "<worksheetId2>", "addedCount": 1 }
    ]
  },
  "verification": {
    "passed": true,
    "evidence": ["按组内顺序逐表调用 update_worksheet 完成本组全部跨表关联与衍生字段回填"]
  },
  "issues": []
}
```
