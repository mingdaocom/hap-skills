# Step 6: 自定义页面组件组装与布局校正 SOP (`6_create_pages`)

<!-- SOURCE: build-app/custom-page-config-sub-agent.yaml -->

## 一、 本地宿主输入与参考映射

- **执行方式**：独立 Subagent 按单个自定义页面并发执行（页面空壳已由 Step 1 创建就绪）。
- **输入切片**：读取 `.build/task-context/{taskId}.json`：
  - `planSlice`：`page`（含 `name`、`type`: `"dashboard" | "workspace"`、`description`、`charts` 或 `components`、可选 `viewBindings`、`requirements`）、`appColor`、`appLanguage`；
  - `contextSlice`：`appId`、`pageId`（24 位真实 hex）、`worksheetIdByName`、`viewIdByName`；
  - `worksheetContextSlice`：全量已建工作表及真实字段列表（含 `id`、`alias`、`type`、`options`）。
- **必读领域规范**：`references/hap-domain-custom-page-spec.md`、`references/hap-chart-design-guide.md`（若需挑选数值卡片图标，按需查阅 `references/hap-icon-palette.md`）
- **主要业务工具**：`["update_custom_page", "get_custom_page_structure", "patch_custom_page_components"]`；必要时用只读 `get_view_structure` 核验视图筛选（**严禁调用 `create_chart`**！自定义页面内图表统一作为页面内联组件保存）。

---

## 二、 核心构建规则与执行步骤

- **输出语言与补充要求**：页面内所有组件标题、按钮文案与筛选名称使用 `appLanguage` 指定语言；优先落实 `page.requirements` 中的视觉、图标显隐与对齐要求。

### 1. 指标核实、组件映射与整页组装
1. `pageId` 缺失时，从建壳结果、完整上下文或线上页面定位真实 ID；前置工作未完成则向主调度器报告具体依赖，按宿主适配继续恢复。
2. **先核实指标可实现性**：从 `worksheetContextSlice` 确定每个指标的真实数据源 `worksheetId`、字段 `id`/`alias` 与聚合口径（已有匹配的汇总/公式字段直接聚合，不重复套计算；差额保留减项、比率保留分母，无法由现有字段真实表达的指标跳过并记入 `notes`，严禁用恒零或无关总额冒充）。
3. **视图语义与 ID 核对**：按组件用途先确定目标表、状态/归属/时间口径；若 `page.viewBindings[组件名]` 存在，使用其 `{worksheet, view}` 查找对应真实对象并验证语义；旧方案缺省时从已确认方案解析。再从 `viewsByWorksheet` / `viewIdByName` 定位语义匹配的真实 `viewId`；视图筛选条件未获可靠证据时调用 `get_view_structure` 验证。待办、待审批、在途等子集不能引用未筛选的“全部”视图冒充；不存在匹配视图时由视图执行阶段补建，或在页面明确标注实际范围并在 `issues` 记录缺口，不能虚报完成。仅真正需要全部记录时使用“全部/All”，严禁填视图中文名、表名或空串作为 ID。
4. **共用组件映射与 `filtersGroup` 置后输出**：
   - 为每个内联图表/视图分配稳定的本地 UUIDv4 `objectId`，`filtersGroup` 同一业务条件只建一个筛选项（内层 `filterId` 传 UUIDv4，外层 `filtersGroupId` 留空不传），在 `objectControls` 中绑定所有语义兼容的图表/视图 `objectId`（目标 `controlId` 必须属于对应工作表，同一筛选项内每张表最多绑定 1 个字段，跨表绑定选项字段须确认同源兼容，不兼容对象记入 `notes`）；
   - `components` 数组中先排列被引用的 `chart` / `view` 组件，最后输出 `filtersGroup`（其坐标 `position` 仍置顶于 `y: 0`）；
   - 按 `page.type` 应用页面规范对应的 Dashboard 或 Workspace 新建规则，依据真实数据源完成本页组件与布局。
   - 每张图分别核实事实表、筛选、维度、聚合、单位和时间范围，分配独立的组件/图表配置，不能复制第一个图的指标冒充其他图。数据为空时保留真实查询及空状态，禁止制造零值或示例结果作为真实统计；无法可靠表达的指标记入 `notes` 与 `issues`。
   - **主题色呼应与数值卡图标**：富文本使用指南（多阶段/多角色工作台优先采用多场景分栏卡片，自带外层圆角底色时将 `text` 组件顶层 `appearance` 设为 `"transparent"`）与快捷按钮（主动作优先使用 `appColor`）须结合当前应用主题色 `appColor` 设计；数值卡需显示图标时从 `references/hap-icon-palette.md` 选带 `sys_` 前缀的合法 `fileName` 写入 `components[].config.config.numberCard` 并显式开启图标显示开关，量级/小数位/单位写入 `values[]`。

### 2. 一次全量保存 + 摘要布局检查 + 局部补丁校正
1. **一次全量保存**：先按 [宿主适配](../../HOST_ADAPTER.md) 核实 `update_custom_page` 实时 Schema，再调用 1 次 `update_custom_page(appId, page_id: pageId, components)` 保存整页组件树（若写入前参数校验报错未落库，一次集中修正全部错误路径后重提，最多 3 次；若确认线上页面已有组件树落库或本次保存已成功，**严禁再次调用 `update_custom_page`**）。
2. **写后核验**：保存成功后，调用 `get_custom_page_structure(appId, page_id: pageId, detail: "summary")` 检查栅格及重叠；摘要不能证明图表口径、筛选器绑定或视图条件。对每张新增图表及筛选组读取 `full` 或对应组件详情，核对实际名称、数据源、字段、聚合及绑定；视图条件以 `get_view_structure` 为准。需要实际渲染或交互验证时单独验证；未验证的部分在 `issues` 如实说明。
3. **在原页面补齐**。读取当前版本，按实时 `patch_custom_page_components` 契约用 `add` 补齐缺少的图表、筛选器或视图，用 `update` 修正已有组件。布局微调可省略 `config`；涉及数据源、指标或绑定时，读取组件详情并按写入契约构造配置。版本冲突或返回不明先回读差异，只重试未落库部分。布局用 `summary` 复核，业务配置用组件详情或 `full` 复核。
4. **按页面用途验收（严格以 `planSlice.page` 规划组件为唯一完成标准）**。用回读结果核对 `planSlice.page` 中规划的 `charts` 或 `components` 清单，在 `verification.evidence` 列出实际组件、绑定及指标。**只要 `planSlice.page` 规划的组件与业务口径已落库（例如 `workspace` 工作台页面若在 `components` 中仅规划了视图 `View` 与按钮 `Button` 而未规划统计图，则配齐规划的视图与按钮即为 100% 完成），必须填 `outputs.completed: true` 且顶层 `status: "succeeded"`！严禁因为未额外添加规划外的 KPI 卡片或配套统计图、未做前端渲染实测或跨表站点动态约束未配而将 `outputs.completed` 设为 `false`！** 受限的可选派生指标或布局微调写进 `outputs.notes`。仅当 `planSlice.page` 明确规划的核心组件确实缺失或待办视图错误绑定了无筛选“全部”视图时，才填 `outputs.completed: false` 并记 `failed` 供续作。

---

## 三、 本地回执落盘契约

执行完成后，将标准回执写入 `receiptPath`（`.build/receipts/step6-page-{name}.json`）：

```json
{
  "taskId": "<来自 taskContext.taskId>",
  "runId": "<runId>",
  "executor": { "kind": "subagent", "agentId": "<agentId>" },
  "step": "6",
  "target": { "type": "page", "id": "<pageId>", "name": "<pageName>" },
  "status": "succeeded",
  "outputs": {
    "pageName": "<pageName>",
    "pageId": "<pageId>",
    "completed": true,
    "notes": []
  },
  "verification": {
    "passed": true,
    "evidence": ["填写回读所得的实际数据源、指标聚合或视图筛选，以及布局结果"]
  },
  "issues": []
}
```
