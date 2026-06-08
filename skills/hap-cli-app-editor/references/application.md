# application & chatbot ops

## chatbot（AI 助手）
- `chatbot.create` — `{name, [section], [prompt], [welcome_text], [preset_questions], [remark]}`
- `chatbot.update` — `{chatbot:"<名|id>", [name], [welcome_text], [preset_questions]}`
- `chatbot.delete` — `{chatbot, [permanent], confirm:true}`

## application（应用级元数据）
- `app.update` — `{[name], [desc], [icon_color], [nav_color], [pc_nav_style]}`（编辑当前 app）
> 整应用从零创建是 hap-cli-app-creator 的职责；此处只改已存在的应用。

## section（侧边栏分组）
- `section.add` — `{name}`
- `section.update` — `{section:"<名|id>", name}`
- `section.delete` — `{section:"<名|id>", confirm:true}`
