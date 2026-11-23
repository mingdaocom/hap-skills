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
4. **页面需要筛选器组时的共用映射与 `filtersGroup` 置后输出**：
   - 为每个内联图表/视图分配稳定的本地 UUIDv4 `objectId`，需要筛选器组时 `filtersGroup` 同一业务条件只建一个筛选项（内层 `filterId` 传 UUIDv4，外层 `filtersGroupId` 留空不传），在 `objectControls` 中绑定所有语义兼容的图表/视图 `objectId`（目标 `controlId` 必须属于对应工作表，同一筛选项内每张表最多绑定 1 个字段，跨表绑定选项字段须确认同源兼容，不兼容对象记入 `notes`）；
   - `components` 数组中先排列被引用的 `chart` / `view` 组件，最后输出 `filtersGroup`（页面显示位置按布局坐标确定：仪表盘置顶 `y: 0`，工作台默认不加全局筛选器，仅在明确需要跨组件联动时放在受控组件之前）；
   - 按 `page.type` 应用页面规范对应的 Dashboard 或 Workspace 新建规则，依据真实数据源完成本页组件与布局：**其中 `Dashboard` 转换 `charts` 并配齐 `filtersGroup`、核心 KPI 与分析图；`Workspace` 除转换 `Text / Button / View / Carousel` 外，必须按 `hap-domain-custom-page-spec.md` §3.2 基于 `worksheetContextSlice` 默认补充 KPI 卡片（2～6 个）、业务 `section` 分段与每个 `View` 右侧上下排列的 2 张辅助图（View `w=32`，右图各 `w=16`、同一父级对齐），仅当方案/`requirements` 显式排除统计或缺少真实统计依据时不添加**。
   - 每张图分别核实事实表、筛选、维度、聚合、单位和时间范围，分配独立的组件/图表配置，不能复制第一个图的指标冒充其他图。数据为空时保留真实查询及空状态，禁止制造零值或示例结果作为真实统计；无法可靠表达的指标记入 `notes` 与 `issues`。
   - **主题色呼应与数值卡/按钮高频防错键名（核对实时 Schema 优先，防静默丢键）**：富文本使用指南（多阶段/多角色工作台优先采用多场景分栏卡片，自带外层圆角底色时将 `text` 组件顶层 `appearance` 设为 `"transparent"`）与快捷按钮（主动作优先使用 `appColor`）须结合当前应用主题色 `appColor` 设计；数值卡需显示图标时从 `references/hap-icon-palette.md` 选带 `sys_` 前缀的合法 `fileName` 写入 `components[].config.config.numberCard`（注意精准键名防静默忽略：`icon.visible: true` 而非 `show`、`icon.color` 为图标底色且图形固定白色、`icon.shape` 为 `square`/`circle`、`value.valueColor` 而非 `color`），量级/小数位/单位写入 `values[]`；快捷按钮组件（`componentType: "button"`）通过 `config.count` / `mobileCount` 控制每行列数，新建记录按钮项使用 `action: 1` + `value: "<worksheetId>"`（无 `data` 嵌套，无需手造 `buttonId`，其余动作枚举与属性以实时 Schema 为准）。**工作流按钮边界**：`action=6`（及扫码 `action=5`、`scan.textAction="workflow"`）只支持绑定当前应用已发布且启用的封装业务流程（PBP），严禁绑定普通事件流或自定义动作流；新建应用阶段无已有 PBP，对应审批/收款/核销等快捷入口直接配置为新建记录（`action=1`）或打开对应待处理视图（`action=2`）。

### 2. 一次全量保存 + 摘要布局检查 + 局部补丁校正
1. **一次全量保存（全新构建免写前探查）**：全新构建（无 `previousReceipt`）已知 `pageId` 为 Step 1 新建空壳，**直接组装组件树调用 1 次 `update_custom_page(appId, page_id: pageId, components)` 保存整页，无需写前调用 `get_custom_page_structure` 探查空壳**（若写入前参数校验报错未落库，一次集中修正全部错误路径后重提，最多 3 次；若确认线上页面已有组件树落库或本次保存已成功，**严禁再次调用 `update_custom_page`**）。
2. **轻量摘要核验（`summary` 通过即收口，免 `full` 逐图回读）**：保存成功后，调用 1 次 `get_custom_page_structure(appId, page_id: pageId, detail: "summary")` 检查组件数量、位置尺寸及相邻占位是否重叠；**摘要参数符合目标即完成检查，直接写入成功回执，不追加 `full` 或逐组件配置读取**。
3. **异常时在原页面局部补齐**：仅当 `summary` 发现组件缺失/栅格重叠或属于断点续作时，按 `patch_custom_page_components` 契约用 `add` 补齐缺失组件、用 `update` 修正已有组件（布局微调可省略 `config`；涉及数据源、指标或绑定修正时才按需读取对应组件详情或 `full`）。
4. **按页面用途验收**：用回读结果核对 `planSlice.page` 中规划的 `charts` 或 `components` 清单（含 `Workspace` 按规范补齐的 KPI 与右侧辅助图），在 `verification.evidence` 列出实际组件、绑定及指标。可实现且符合规范的组件均已落库（受限于平台能力或 `requirements` 显式排除的统计项记录在 `outputs.notes`），即填 `outputs.completed: true` 且顶层 `status: "succeeded"`，严禁仅因未做前端渲染实测或运行态未验证将 `outputs.completed` 设为 `false`！仅当 `planSlice.page` 明确规划的核心组件确实缺失、未完成布局错位或待办视图错误绑定了无筛选“全部”视图时，才填 `outputs.completed: false` 并记 `failed` 供续作。

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
