# hap-context.json 结构定义

本文件定义 `{PROJECT_ROOT}/.hap-copilot/apps/{appName}/hap-context.json` 的权威结构。所有构建步骤与运行时脚本读写上下文时必须遵守此契约。

## 一、 标准 JSON 结构

```json
{
  "appId": "string",
  "appUrl": "string (create_app 返回的应用直达访问链接)",
  "appName": "string",
  "orgId": "string",
  "language": "zh-CN",
  "progress": "string (见 build/PROGRESS.md)",

  "sectionIdByName": { "分组名称": "sectionId" },
  "worksheetIdByName": { "工作表名称": "worksheetId" },
  "relationLayoutByWorksheet": {
    "工作表名称": [
      { "name": "关联客户", "alias": "biz_cust", "fieldType": "Relation", "targetWorksheet": "客户", "rowIndex": 2, "span": 6, "isMultiple": false, "bidirectional": true, "displayMode": "card" }
    ]
  },
  "worksheetFieldsPreview": {
    "工作表名称": [{ "name": "客户名称", "id": "fieldId", "alias": "biz_name", "type": "Text" }]
  },
  "fieldOptionsContext": [
    { "name": "工作表名称", "fields": [{ "name": "状态", "alias": "biz_status", "options": [{ "key": "opt_1", "value": "待处理", "index": 1 }] }] }
  ],
  "viewIdByName": { "工作表名称/视图名称": "viewId" },
  "viewsByWorksheet": { "工作表名称": [{ "name": "全部记录", "id": "viewId", "type": "table" }] },
  "actionIdByName": { "工作表名称/动作名称": "actionId" },
  "actionProcessIdByKey": { "工作表名称::动作名称": "processId" },
  "customPageIdByName": { "页面名称": "pageId" },
  "chatbotIdByName": { "助手名称": "chatbotId" },
  "roleIdByName": { "角色名称": "roleId" },
  "roleContext": [{ "name": "角色名称", "id": "roleId", "roleScope": "general" }],

  "workflowResults": [],
  "customActionWorkflowResults": [],
  "appDescUpdated": true,
  "itemsSorted": true,
  "sampleDataCreated": true,
  "buildRun": {
    "runId": "string",
    "executionMode": "subagent_required",
    "lastPhaseReport": ".build/phase-report.json",
    "blocked": false
  }
}
```

## 二、 单写入者与字段通道规则

1. **单写入者原则**：除 Step 1 初始化外，所有 ID 映射与 `progress` 均由 `scripts/build_runtime.py advance` 在阶段报告放行后独占原子写入，主调度器与 Subagent 严禁直接修改 `hap-context.json`。
2. **两遍建表与选项保真通道**：
   - `relationLayoutByWorksheet` 与 `worksheetFieldsPreview` 在阶段 1.5（Step 2a 完成后）保存，供 Step 2b 精准回填预留 `rowIndex/span` 与 `showFields`；
   - `fieldOptionsContext` 保留 Step 2a 建表时的单多选/下拉选项列表，供 Step 5 示例数据生成真实选项值，防止字段结构刷新时丢失选项细节；
   - `actionProcessIdByKey` 按 `"{工作表名}::{动作名}"` 复合键存储 Step 3 创建按钮返回的预建 `processId`，确保不同工作表上的同名按钮（如多张表均有「提交审批」）互不覆盖。
3. **`worksheetContext.json` 只读共享契约**：由阶段 2 末尾调用 `scripts/merge_worksheet_context.py` 校验合并生成；后续任务优先复用已有结构。合并产物尚未生成、摘要缺项或线上结构变化时，按任务的 `sourceFiles` 查阅同批回执与单表分片，或定向读取线上结构，不将缓存缺失视为对象不存在。
4. **配置、成员与试跑分开记录**：`roleContext` / `roleIdByName` 仅代表已定位角色，不代表已有成员或审批已完成；`sampleDataCreated` 仅代表示例数据状态，不能证明真实业务已执行。未规划的可选对象无需捏造 ID，尚未试跑或成员为空的限制留在对应回执与交付说明，不覆盖真实配置状态。
