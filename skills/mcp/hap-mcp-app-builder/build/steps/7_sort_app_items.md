# Step 7: 应用项导航分组内智能排序 SOP (`7_sort_app_items`)

<!-- SOURCE: build-app/sort-app-items-sub-agent.yaml -->

## 一、 本地宿主输入与参考映射

- **执行方式**：**主调度器内联执行**（在阶段 2 结束拿到全量页面、工作表与 AI 助手真实 ID 后，由主调度器内联按分组调用 `sort_app_items`，无需单独拉起 Subagent 或写回执文件）。
- **输入来源**：优先直接使用阶段 3 `prepare`（或阶段 2 `nextStagePrepare`）返回的 **`sortAppItemsHints`**（已按 `navGroups` 汇总真实 `sectionId` 与全部 ≥2 项分组的真实 `id` 及初始结构顺序 `suggestedItemIds`，无需再调 `get_app_info`）；必要时回退读取 `hap-plan.json` 与 `hap-context.json`。
- **必读领域规范**：`../../references/hap-domain-app-spec.md`
- **主要业务工具**：`["sort_app_items"]`

---

## 二、 核心构建规则与执行步骤

1. **汇总名称到真实物理 ID 的映射字典 (`nameToId`)**：合并 `customPageIdByName`、`worksheetIdByName`、`chatbotIdByName`。缺少某个规划项的真实 ID 时先查已有回执或线上对象；仍找不到则跳过该项、记录缺口并继续独立分组，严禁编造 ID，也不得把部分排序描述为全部完成。
2. **按业务角色操作动线排定每个分组内的最佳展示次序**：
   遍历 `navGroups` 中的每个分组，将该分组下的全部页面、工作表与 AI 助手按以下 6 级优先级排列：
   1. **门户/工作台/全局总览置顶**：`dashboard` 与 `workspace` 自定义页面排在分组最前，作为进入模块的第一视觉入口；
   2. **核心业务主单据与主实体**：高频核心业务表排在页面之后（如「客户」「合同」「采购申请」）；
   3. **关联从属表与业务明细**：明细子表紧跟在其所属主单据表正后方（如「采购明细」紧随「采购申请」）；
   4. **台账与追溯流水日志**：库存台账、出入库流水、状态变更记录排在业务单据之后；
   5. **基础字典与分类配置沉底**：维护频次低的分类、仓库、参数配置表排在工作表末尾；
   6. **AI 智能助手**：排在该分组最末尾作为常驻辅助入口（特定要求除外）。
3. **逐分组调用 `sort_app_items`**：
   - 从 `sectionIdByName` 取当前分组的真实 `sectionId`；
   - 将排好序的对象转换为真实 `itemIds` 数组；
   - **仅当 `itemIds` 包含 2 个及以上有效 ID 时**，调用 `sort_app_items(appId, sectionId, itemIds)`（单分组仅 0 或 1 项时跳过；完成后在 `hap-context.json` 记录 `"itemsSorted": true`）。
