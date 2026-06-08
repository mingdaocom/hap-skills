# custom-action（记录按钮）ops

- `custom-action.create` — `{worksheet, action_spec:{…} | config:{…}}`
  action_spec（高层）：`{type:"updateCurrentRecord"|"createRelatedRecord"|"triggerWorkflow",
  updateFields:[controlId…], relationField, enableWhen, name}`；或 config 给原始 wire 配置。
  创建按钮会自动建影子工作流。
- `custom-action.update` — `{worksheet, action:"<名|btnId>", action_spec|config}`
  **在原按钮上改（--btn-id），影子工作流不重建**（决策 #11）。
- `custom-action.delete` — `{worksheet, action:"<名|btnId>", confirm:true}`
