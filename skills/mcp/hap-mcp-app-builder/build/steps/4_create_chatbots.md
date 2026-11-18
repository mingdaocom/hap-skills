# Step 4: AI 智能助手创建与 Agent 节点配置 SOP (`4_create_chatbots`)

<!-- SOURCE: build-app/chatbot-create-sub-agent.yaml -->
<!-- SOURCE: build-app/chatbot-config-sub-agent.yaml -->

本文件按构建阶段分为两节：**Step 4a（阶段 2 创建助手实体拿 `chatbotId`）** 与 **Step 4b（阶段 3 表/视图就绪后绑定关联工作流 `ai_agent` 节点并发布）**。请严格按 `taskContext.step`（`"4a"` 或 `"4b"`）执行对应章节！

---

## 一、 Step 4a：创建 AI 助手实体（`taskContext.step == "4a"`，阶段 2 执行）

### 1. 输入与主要业务工具
- **输入切片**（`.build/task-context/step4-chatbot.json`）：`planSlice.aiAssistants`、`planSlice.worksheetsSummary`（表名与简介，用于撰写初始提示词）、`planSlice.appLanguage`；`contextSlice.appId`、`contextSlice.sectionIdByName`。
- **必读领域规范**：`references/hap-domain-chatbot-spec.md`
- **主要业务工具**：`["create_chatbot"]`

### 2. 核心规则与执行步骤（源自 `chatbot-create-sub-agent.yaml`）
1. 若 `aiAssistants` 为空，不调用任何工具，直接输出空 `chatbotIdByName: {}` 成功回执。
2. 遍历 `aiAssistants`，使用 `appLanguage` 指定语言为每个助手构造参数并调用 `create_chatbot`：
   - `appId`：应用真实 ID；
   - `name`：原样保持规划名称；
   - `icon`：原样保留带 `sys_` 前缀的合法 `fileName`（严禁剥离 `sys_` 前缀）；
   - `sectionId`：从 `sectionIdByName` 按 `groupName` 反查（查不到则省略）；
   - `remark`：一句简洁的业务定位说明；
   - `welcomeMessage`：结合 `description` 生成友好的场景欢迎语；
   - `presetQuestions`：结合应用表名与业务场景生成 **3～5 个具体业务提问（绝对严禁超过 5 个！）**；
   - `prompt`：遵循 `references/hap-domain-chatbot-spec.md` 四段式结构生成初始系统提示词（列出应用工作表数据范围与回答准则）。
   - **参数红线**：严禁传入 `systemPrompt`、`shortcuts`、`worksheets`、`model`、`iconColor` 等不存在的伪参数！同一助手创建成功后严禁重复调用。

### 3. Step 4a 回执格式（写入 `.build/receipts/step4-chatbot.json`）
```json
{
  "taskId": "step4-chatbot",
  "runId": "<runId>",
  "executor": { "kind": "subagent", "agentId": "<agentId>" },
  "step": "4a",
  "target": { "type": "chatbot", "name": "AI智能助手" },
  "status": "succeeded",
  "outputs": {
    "chatbotIdByName": { "<助手名称>": "<create_chatbot返回的24位id>" },
    "chatbotContext": [{ "name": "<助手名称>", "id": "<24位id>" }]
  },
  "verification": { "passed": true, "evidence": ["调用 create_chatbot 成功创建助手实体"] },
  "issues": []
}
```

---

## 二、 Step 4b：配置已建助手的关联工作流 `ai_agent` 节点（`taskContext.step == "4b"`，阶段 3 按助手并发执行）

### 1. 输入与主要业务工具
- **输入切片**（`.build/task-context/step4b-chatbot-config-{name}.json`）：`planSlice.assistant`（含 `name`、`description`、`requirements`）、`planSlice.appLanguage`；`contextSlice.appId`、`contextSlice.chatbotId`、`contextSlice.viewIdByName`；`worksheetContextSlice`（已刷新工作表真实 ID 与别名）。
- **必读领域规范**：`references/hap-domain-chatbot-spec.md`（第四、五节）
- **主要业务工具**：`["get_workflow_structure", "get_workflow_node", "update_workflow_node", "publish_process", "get_app_ai_models", "get_app_knowledge_list", "get_worksheet_structure", "get_view_structure"]`

### 2. 核心规则与执行步骤（源自 `chatbot-config-sub-agent.yaml`）
1. **定位底层工作流节点**：`chatbotId` 同时就是该助手关联工作流的 `workflowId`。若计划未包含助手则无需此任务；若已规划但 `chatbotId` 为空，先查本工程回执和线上对象，仍无法定位则记录依赖缺口，不以跳过冒充完成，也不重复新建。调用 `get_workflow_structure(workflow_id: chatbotId, version: "draft")` 定位 `ai_agent` 节点的 `nodeId`，再调用 `get_workflow_node` 读取当前节点配置。
2. **绑定真实数据表与工具范围**：
   - 结合 `assistant.description`、`requirements` 与 `worksheetContextSlice` / `viewIdByName` 的真实 ID，选择必要的数据查询、统计、记录操作或知识检索配置（仅当明确需要知识库或特定模型时才调 `get_app_knowledge_list` / `get_app_ai_models`，本步骤不绑定 `callWorkflow`，不运行任何业务工具）；
   - 保留正常的 `input/file` 引用与既有 `toolId`，`tools` 数组完整保留未改项；若 `requirements` 要求只读或限定特定表范围，必须在节点工具配置中实际收窄/停用对应写工具，不能只写在提示词里；保持用户权限检查开启与写操作确认开启。
3. **一次更新并发布生效（完建优先）**：
   - 先查阅 `update_workflow_node` 实时 Schema 核实 `ai_agent` 节点 `config` 结构，合并本节点所需变更后调用 1 次 `update_workflow_node`（`config` 传原生 JSON Object；若原配置已完全满足目标则免写）；
   - 默认调用 `publish_process(workflow_id: chatbotId)` 发布生效（仅当 `requirements` 明确指定只存草稿时不发布；结果未知先核查发布版本，严禁盲目重放）；
   - 若助手实体与核心数据表工具已生效，仅个别非核心资源（如环境暂无指定外部模型或可选知识库为空）无法绑定，保留可用配置完成发布，在 `outputs.notes` 与 `issues` 如实记录差异，顶层回执仍标记 `status: "succeeded"`。

### 3. Step 4b 回执格式（写入 `.build/receipts/step4b-chatbot-config-{name}.json`）
```json
{
  "taskId": "<来自 taskContext.taskId>",
  "runId": "<runId>",
  "executor": { "kind": "subagent", "agentId": "<agentId>" },
  "step": "4b",
  "target": { "type": "chatbot", "id": "<chatbotId>", "name": "<助手名称>" },
  "status": "succeeded",
  "outputs": { "completed": true, "chatbotId": "<chatbotId>", "notes": [] },
  "verification": { "passed": true, "evidence": ["已更新关联工作流 ai_agent 节点资源绑定并发布生效"] },
  "issues": []
}
```
