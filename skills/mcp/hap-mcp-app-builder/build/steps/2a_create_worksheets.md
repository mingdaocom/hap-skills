# Step 2a: 单表创建、基础字段排版与表单增强 SOP (`2a_create_worksheets`)

<!-- SOURCE: build-app/worksheet-build-sub-agent.yaml -->

## 一、 本地宿主输入与参考映射

- **执行方式**：独立 Subagent 按表并发执行（两遍建表 Pass 1）。
- **输入切片**：读取 `.build/task-context/{taskId}.json`：
  - `planSlice.worksheet`：当前表规划（含 `name`、`description`、`groupName`、`worksheetType`、`parentWorksheet`、`icon`、`fields` 紧凑字符串数组、`requirements`）；
  - `planSlice.appLanguage`：应用内容语言代码；
  - `contextSlice`：`appId`、`appSectionId`（按 `groupName` 查好的真实 `sectionId`）。
- **必读领域规范**：`references/hap-domain-worksheet-spec.md`（若含自定义组件字段则按需查阅 `references/hap-domain-custom-field-spec.md`）
- **主要业务工具**：`["create_worksheet", "update_worksheet", "update_worksheet_settings"]`

---

## 二、 核心构建规则与执行步骤

- **输出语言与补充要求**：所有用户可见文本（`Divider` 分段名、`placeholder`、`desc`、`remark`、选项说明等）必须使用 `appLanguage` 指定语言；优先落实 `worksheet.requirements` 中的字段与表单细节。

### 1. 紧凑字段展开与主动业务补全
- **紧凑字符串解析与关键 `config` 落地**：
  - **`Text` 文本模式（`config.textMode`）**：基础字段 `"字段名(Text)"`（若旧方案误写 `Textarea/LongText` 直接按 `Text` 处理，不记 `issues`）须按语义设置 `config.textMode`——名称/编号/联系人等短字段设 `"singleLine"`，备注/说明/原因/故障现象/维修过程等多行描述设 `"multiLine"`；
  - **选项字段** `"字段名(SingleSelect|MultipleSelect|Dropdown:选项1/选项2)"`：**必须严格保留 Plan 给定的选项文本，不得增删改名**（下游视图筛选与工作流强依赖）；仅当 Plan 未带选项值时按业务语义补齐真实选项，严禁用“选项1/选项2”占位；
  - **`Collaborator` 成员单复数与记录权限联动（`config.userPermission` 核心配置！）**：
    - `config.isMultiple`：含“人/员/负责人”单数语义设 `false`，含“团队/参与人/协同人”复数语义设 `true`；
    - **`config.userPermission`（决定角色 `recordDataScope: 20` 能否看到/编辑记录！）**：结合 `planSlice.worksheetUsage.roles` 判断——**凡业务上需要被指派人查看并编辑/执行动作的责任成员字段（如「执行人」「巡检人」「维修人员」「经办人」「负责人」），必须显式设 `config.userPermission: 2`（拥有者权限）**；仅需知悉抄送的设 `1`（只读权限）；纯展示登记设 `0`（无权限）。
- 从本表要完成的一次业务操作反推：缺什么信息会使记录无法识别、执行或追溯？按工作表规范补齐必要字段，区分草稿可空与提交时必需。无条件约束与无条件“选单条关联带出可编辑初始值”优先落字段属性（跨表初始值走下方 `outputs.relationDefaults`，**不再重复写入 `outputs.businessRulesNotes`**）；仅需按条件交互、校验、锁定，或需条件触发/配合只读强锁定同步的 `rcid` 跨表赋值（如选设备自动同步所属站点并锁定）的意图，记入回执 `outputs.businessRulesNotes` 交 Step 3。尊重明确取舍，按适用性分段。
- **标题字段（`isTitle`）唯一性兜底**：每表有且仅有一个合法标题字段（优先选识别度最高的 `Text` 或 `Concatenate`）；若选定的组合标题依赖 `Lookup/Rollup` 需留到 Pass 2，先从本次实际创建的合法字段中选一个作为临时标题（Pass 2 补建组合标题时传 `isTitle: true` 自动替换原标题）。若全表均为人员/选项/关联等非法标题类型，**必须主动新建一个 `Text` 或 `AutoNumber` 字段设为 `isTitle: true`**。

### 2. 两遍建表（Two-Pass）排版三步法
1. **Step A — 过滤不占网格项并统一排布 12 列栅格**：
   - 先剔除 `:reverse` 反向承接端字段（由对端 `:bi` 自动在标签页带出，不占表单网格）以及子表中指向 `parentWorksheet` 主表的父级关联字段；
   - 对剩余**全部表单字段**（基础字段 + `selfRelation` 自关联 + 待补跨表 `Relation` `:bi/:uni` + `SubTable` + `Lookup/Rollup` + 公式）统一分配 `rowIndex` 与 `span`（推荐 `3 / 6 / 12` 栅格：同行 2 个字段用 `6 + 6 = 12` 消灭右侧留白；`SubTable` 与 `inlineTable` 独占整行 `span: 12`；单条关联无摘要用 `"dropdown"`，需摘要用 `"card"`）。
2. **Step B — 剥离跨表与衍生字段并保留原行号间隙**：
   - 从发送给 `create_worksheet` 的 `fields` 中剔除：① 所有跨表 `Relation:目标表` 与 `SubTable` 字段；② 所有 `Lookup` 与 `Rollup` 字段；③ 依赖上述 `Lookup` 或 `Rollup` 的 `Concatenate`、`Formula` 和 `DateFormula`（表达式仅可引用本表字段 `$alias$`，严禁构造 `$关联$.目标字段$` 跨表路径语法）。**凡记入 `relationLayout` 的字段严禁同时出现在 `create_worksheet.fields` 与回执 `outputs.fields` 中（禁止在 Pass 1 建空壳 `Lookup`/`Rollup` 或把 `Lookup` 私改为临时 `Concatenate`）**；
   - **唯一自关联红线**：仅原文写为 `(selfRelation)` 的字段随本步直接创建（`dataSource: "selfRelation"`）；任何跨表 `(Relation:xxx)` **严禁伪造为 `selfRelation` 规避**！
   - 保留下来的基础字段保持 Step A 的 `rowIndex / span` **原封不动**（允许行号跳号如 `0, 1, 3`，供 Pass 2 精准插回预留行）。
3. **Step C — 构造完整 `relationLayout` 待办数组**：
   - **跨表引用只填业务名（严禁读取兄弟回执）**：所有表本步并发创建，`relationLayout` 与 `outputs.relationDefaults` 中的跨表引用直接写目标表名与目标字段业务名即可，**严禁列出或读取 `.build/receipts/` 下其他表的兄弟回执去查 `targetWorksheetId` 或对端字段 `alias`**（全部表的真实 `worksheetId` 与字段 `alias` 由调度器在进入 Step 2b 时统一注入）。
   - 将 Step B 剥离的每个字段记入输出 `relationLayout`（**每项必须带本表真实规划 `alias`，如 `biz_xxx`**）：
     - `Relation`：`{ name, alias, targetWorksheet, rowIndex, span, displayMode, fieldType: "Relation", isMultiple, bidirectional, required? }`（`:bi`→`true`，`:uni`→`false`；缺省时字典/仓库/商品等主数据引用推导为 `false`，核心主从业务穿透推导为 `true`）；
     - `SubTable`：`{ name, alias, targetWorksheet, rowIndex, span: 12, fieldType: "SubTable", bidirectional: true }`；
     - `Lookup`：`{ name, alias, rowIndex, span, fieldType: "Lookup", relationField, sourceFieldName }`（`relationField` 填本表关联字段 `alias`，`sourceFieldName` 填目标字段中文名）；
     - `Rollup`：`{ name, alias, rowIndex, span, fieldType: "Rollup", relationField, sourceFieldName, calcType }`；
     - 跨表 `Concatenate` / `Formula`：保留 `{ name, alias, rowIndex, span, fieldType, isTitle?, precision?, expression }`。
   - **跨表动态默认值交接（可选 `outputs.relationDefaults`）**：输入型基础字段需要从跨表关联带出可编辑初始值（如明细 `单价` 带出商品 `参考单价`、订单 `电话/地址` 带出客户信息，区别于只读 `Lookup`）时，本遍照常创建该基础字段、保留布局并省略其 `defaultValue`（**严禁仅写 `desc` 文案占位**），将该字段的完整默认值数组写入回执顶层可选字段 `outputs.relationDefaults`（保留混合来源顺序，引用填业务名或别名；无此需求时省略或 `[]`）：
     `[{ "field": "单价", "defaultValue": [{ "source": "relation", "relationField": "商品", "field": "参考单价" }] }]`。

### 3. 描述生成、建表调用与表单设置按需增强
1. **描述文案必填**：生成表级 `remark`、依据工作表规范 §1.2 与本表业务用途生成使用说明 `desc`（仅用 `<p>/<strong>/<br>`，禁转义实体）、按需 `importantNote`（`"#515151"`），以及每个输入字段的 `placeholder`、字段 `remark` 和按需 `desc`。
2. **调用 `create_worksheet`**（成功后直接复用返回结果，异常按 [宿主适配](../../HOST_ADAPTER.md) 排查续作）：
   - 传入 `appId`、`name`、`alias`（`biz_xxx`）、`sectionId`（取 `appSectionId`）、`icon`（保留 `sys_` 前缀）、`displayType`（**当 `worksheetType === "subTable"` 时必须传 `2` 隐藏**，普通表传 `1` 或省略）、`createDefaultView: false`、`returnData: true`、`addRecordButtonName`、`fields`（Step B 过滤后的基础字段）。
   - **`returnData: true` 直接提取铁律（严禁建表后再调 `get_worksheet_structure`）**：`create_worksheet(..., returnData: true)` 返回体已完整包含新建的 `worksheetId` 及全部字段真实 `id`、`alias`、`options`，**建表成功后直接从返回值提取回执字段，严禁额外加载或调用 `get_worksheet_structure` 重复回读**；若建表成功后发现遗漏了非关联基础字段，仅可用 `update_worksheet.addFields` 增量补齐（修改已有字段用 `editFields`），**严禁二次调用 `create_worksheet`**。
3. **按需调用 `update_worksheet_settings`（子表与纯字典表直接跳过，严禁发空请求）**：
   - 仅命中以下体验特征时调用 1 次：① 含商品/房源/设备实拍图 `Attachment` 时配 `form.cover`（高 200～400）；② 流程单据定制动作化 `form.title`（如“发起采购申请”）；③ 开启 `form.tabs.hideWhenSingle: true`（关联 Tab >3 个设 `"left"`，否则 `"top"`）；④ 审批单据配 `afterSubmit: { action: "openCreatedRecord" }`，高频建档表配 `continueCreation: { enabled: true }`，重大作废/调账单配 `submitConfirmation`。

---

## 三、 本地回执落盘契约

提取建表返回的真实 `worksheetId`、字段列表（含单多选/下拉的 `options` 数组！）与 `relationLayout`，写入 `receiptPath`（`.build/receipts/step2a-ws-{name}.json`）：

```json
{
  "taskId": "<来自 taskContext.taskId>",
  "runId": "<来自 taskContext.runId>",
  "executor": { "kind": "subagent", "agentId": "<当前子代理标识>" },
  "step": "2a",
  "target": { "type": "worksheet", "id": "<worksheetId>", "name": "<worksheetName>" },
  "status": "succeeded",
  "outputs": {
    "worksheetId": "<24位真实worksheetId>",
    "worksheetName": "<worksheetName>",
    "alias": "<biz_xxx>",
    "fields": [
      { "name": "状态", "id": "<24位字段id>", "alias": "biz_status", "type": "SingleSelect", "options": [{ "key": "...", "value": "待处理", "index": 1 }] }
    ],
    "relationLayout": []
  },
  "verification": {
    "passed": true,
    "evidence": ["调用 create_worksheet 成功获取物理 worksheetId"]
  },
  "issues": []
}
```
