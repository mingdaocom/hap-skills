# custom-page & component ops

## 页面级
- `custom-page.create` — `{name, [section], [icon], [remark]}`
- `custom-page.update` — `{page:"<名|id>", [name], [icon]}`
- `custom-page.delete` — `{page:"<名|id>", [permanent], confirm:true}`

## 组件级（读改写整页 components）
- `component.add` — `{page, component:{name, type, [value], [layout:{x,y,w,h}], [raw:{…}]}}`
  type：richText|embedUrl|image|chart|view|filter|button|carousel|tabs|card（或整数）。
  value 型（richText 给 html、embedUrl/image 给 url）直接 lower；数据型（chart 需 reportId、
  view 需 worksheetId/viewId、filter 需 filtersGroup）用 `raw:{<wire 键>}` 逃生口。
  组件名写入 `web.title`（HAP 不回传顶层 name，按 web.title 解析）。
- `component.update` — `{page, component:"<名>", set:{<wire 键>}}`（读全量→改目标→savePage）
- `component.delete` — `{page, component:"<名>", confirm:true}`

> 机制：getPage(pageId) 取 version+components → 改 → savePage(pageId, version, components,
> owner-app-id=appId)。其余组件原样保留。
