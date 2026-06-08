# worksheet & field ops

## worksheet
- `worksheet.create` — `{name, [section], [icon], [alias]}`
- `worksheet.update` — `{worksheet, [name], [alias], [desc], [icon]}`
- `worksheet.delete` — `{worksheet, [permanent], confirm:true}`（V3 永久删除）

## field（字段策略见下，决策 #10）
- `field.add` — `{worksheet, field:{name, type, [required], [unique], [options], [control]}}`
  走**增量** add-fields，保留系统自动反向控件。`type` 用 code（Text/Number/Currency/
  SingleSelect/Date/Relation…）、legacy 名或整数。select 类型给 `options:["a","b"]`。
  复杂类型（Relation/Lookup/Rollup/Formula…）用 `control:{<raw 控件键>}` 逃生口。
- `field.update` — `{worksheet, field:"<名|alias|id>", [rename], set:{<raw 控件键>}}`
  走「读完整 raw 控件集 → 改目标 → 整表写回」，反向/系统控件原样保留。
- `field.delete` — `{worksheet, field:"<名|id>", confirm:true}`（整表写回去掉目标）
- `field.reorder` — `{worksheet, order:["字段A","字段B",…]}`（赋递增 row；未列出的接在后面）

> 字段显示顺序由控件 `row` 决定，reorder 即重排 row。新增字段不要用整表替换（会丢反向控件）。
