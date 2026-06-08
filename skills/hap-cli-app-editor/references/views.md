# view ops

- `view.create` — `{worksheet, name, [view_type], [config]}`
  view_type：sheet|board|gallery|calendar|gantt|structure|detail|map（或整数字符串）。
  config：额外视图配置（viewControl/coverCid/advancedSetting/filters…）。
- `view.update` — `{worksheet, view:"<名|id>", [name], [set:{…}], edit_attrs:[…], [edit_ad_keys:[…]]}`
  **局部更新**：只改 `edit_attrs` 列出的顶层属性，其余不动。`name` 是改名捷径（自动并入
  edit_attrs）。`set` 是要写入的属性值；`edit_ad_keys` 缩小 advancedSetting 的改动范围。
- `view.delete` — `{worksheet, view:"<名|id>", confirm:true}`
