# edit-spec 总览

一个 edit-spec 是一个 JSON 文件，描述对**一个已存在应用**的一组「读改写」式局部修改。它只覆盖三类编辑——**字段、页面组件、动作按钮**——因为这三类的安全写法是「读出整体 → 改一处 → 整体写回」，由 `hap app-editor` 替你完成。其它元素（工作表、视图、角色、工作流、节点、应用与分组）直接用对应的 `hap` 命令，见各模块文档。

## 信封

```json
{
  "app": "<appId 或 应用名>",
  "org": "<组织 id，可选；默认当前会话组织>",
  "ops": [ { "type": "...", "...": "..." } ]
}
```

- `app`：优先用真实 appId；也可用应用名（命令会在当前组织里解析）。
- `ops`：按声明顺序执行。同一 spec 内后面的 op 可引用前面 op 刚创建的元素。

## op 通用字段

| 字段 | 说明 |
|---|---|
| `type` | 必填，`<元素>.<动作>`，决定用哪份模块 schema 校验。 |
| `confirm` | 破坏性 op（`field.delete` / `component.delete`）必填且必须为 `true`，否则拒绝执行。 |
| `label` | 可选，plan/apply 输出里显示的人类标签。 |

## 引用元素的方式

元素一律用**逻辑名**（工作表名、字段名、组件名…）或**真实 id** 引用——两者都行。命令每步执行前从
HAP 实时读取结构来解析。

**二级分组里的工作表现在也解析得到。** 应用的分组树会被整棵拍平（子分组一并纳入），所以
`"worksheet": "<放在子分组里的表名>"` 不会再答「worksheet not found」，`inspect` 也会把它列出来。

- 工作表：`"worksheet"` 可以写表名，也可以写 **worksheetId**——名字在两个分组里重名时用 id 最稳。
- 分组：除了名字和 id，还可以写**路径** `"组/子组"` 来区分同名分组。

## op 总表

| type | 作用 | 详见 |
|---|---|---|
| `field.add` | 新增字段（增量，保留反向控件） | [worksheets-and-fields.md](worksheets-and-fields.md) |
| `field.update` | 改字段（读全量 → 改目标 → 整表写回） | 同上 |
| `field.delete` | 删字段（整表写回，需 confirm） | 同上 |
| `field.reorder` | 重排字段（整表写回） | 同上 |
| `component.add` | 页面加组件（页面布局读改写） | [custom-pages.md](custom-pages.md) |
| `component.update` | 改页面组件 | 同上 |
| `component.delete` | 删页面组件（需 confirm） | 同上 |
| `custom-action.create` | 新建动作按钮（高层 action_spec 翻译） | [custom-actions.md](custom-actions.md) |
| `custom-action.update` | 原地改动作按钮 | 同上 |

写了不在表里的 `type`（比如 `view.update`、`node.add`），`validate` 会直接报错并给出应该改用的 `hap` 命令。

> op 的字段级 schema 在 `scripts/editspec/`（envelope + field + component + custom-action 各一份）。

## 命令

```bash
hap app-editor validate <edit-spec.json>                 # 本地校验，零网络
hap app-editor plan     <edit-spec.json> [--app <id>]    # dry-run 预演
hap app-editor apply    <edit-spec.json> [--app <id>] [--continue]  # 执行
hap app-editor inspect  <appId|名称> [--org-id <org>]    # 打印实时 名→id 结构
```

`inspect` 返回 `app_id` / `org_id` / `name` / `sections` / `worksheets` / `pages_and_chatbots` /
`roles` / `workflows`；每张工作表带着它所属的 `section`，**含二级分组里的表**。

`--app` 覆盖 spec 里写的目标应用；`--continue` 让某个 op 失败后继续跑剩下的（默认停）。

## field 的跨表块（`field.add` 的字段词汇）

`field` 接受这些键：`name`、`type`、`required`、`unique`、`options`，加下面四个跨表块，
再加 `control` 逃生口。**跨表类型必须带自己那个块**——少了会校验报错，不会建出一列指向为空的坏列。

| 块 | 用在哪种类型 | 形状 |
|---|---|---|
| `relation` | 关联记录（RELATE_SHEET / 29） | `{worksheet, multiple?, showFields?}` |
| `lookup` | 他表字段（SHEET_FIELD / 30） | `{via, field}` |
| `rollup` | 汇总（SUBTOTAL / 37） | `{via, field}` |
| `formula` | 数值公式（FORMULA_NUMBER / 31）、日期公式（FORMULA_DATE / 38） | 字符串表达式，**不是对象** |
| `subtable` | 子表（SUB_LIST / 34） | `{fields: [...]}` 新建，或 `{worksheet, showFields?}` 挂载——二选一 |

```json
{ "type": "field.add", "worksheet": "订单",
  "field": { "name": "客户", "type": "RELATE_SHEET",
             "relation": { "worksheet": "客户", "multiple": true,
                           "showFields": ["客户名称", "等级"] } } }

{ "type": "field.add", "worksheet": "订单",
  "field": { "name": "客户等级", "type": "SHEET_FIELD",
             "lookup": { "via": "客户", "field": "等级" } } }

{ "type": "field.add", "worksheet": "客户",
  "field": { "name": "订单总额", "type": "SUBTOTAL",
             "rollup": { "via": "订单", "field": "金额" } } }

{ "type": "field.add", "worksheet": "订单",
  "field": { "name": "含税金额", "type": "FORMULA_NUMBER",
             "formula": "$<金额字段id>$ * 1.06" } }
```

### 名字都能写，由引擎解析成 id

- `relation.worksheet` 写目标表的**名字或 id**；`relation.showFields` 写目标表上那些列的
  **名字或 id**。
- `relation.multiple`：`true` 多条、`false` 单条（默认单条）。
- `lookup` / `rollup` 的 `via` 是**本表**上那根桥——关联列或子表列，名字或 id 都行；
  `field` 是**远端表**上要镜像 / 要聚合的那一列。`via` 会被自动包成 `$<id>$` 的形态，
  不用自己写美元号。
- **一个例外**：远端表不在本应用里（或不在导航里、读不到）时，`field` **只能写 id**——
  引擎读不到那张表就没法把名字翻成 id，这时写名字会报错。
- `formula` 的表达式里引用列一律用 `$<列id>$`（列 id 用 `hap worksheet fields` 取）。

### 校验会挡住什么

- **块放错类型**：`Field 'x' is a Number, so it cannot carry a 'relation' block.`
- **块内未知键**：`ops[0].field.relation.bidirectional: unexpected property` ——
  `relation` 块只有 `worksheet` / `multiple` / `showFields` 三个键，**没有 `bidirectional`**。
  要双向，先用 `relation` 块建出来再 `hap worksheet pair-relation` 补反向端。
- **跨表类型缺块**：`Field 'x' needs a 'relation' block saying what it points at.`
- **公式类型缺表达式** / **表达式放在非公式类型上**：都会明确报错。
- `lookup` / `rollup` 的 `via` 指向的列**不通向另一张表**时，会告诉你「没有东西可读」。
- **子表 `fields` 与 `worksheet` 都给**：`ops[0].field.subtable: 'fields' and 'worksheet' cannot
  both be given; give exactly one` —— **在 `validate` 阶段就被拒**。
- **子表两者都不给**：`ops[0].field.subtable: give exactly one of: 'fields', 'worksheet'` —— 同样
  在 `validate` 阶段。
- **内联模式带了 `showFields`**：`The sub-table on field 'x' lists 'showFields' alongside new
  columns. The inline list shows the columns you are creating; 'showFields' is for picking among
  the columns an existing worksheet already has.`
- **`SUB_LIST` 完全没有 `subtable` 块**：`Field 'x' is a sub-table, so it needs a 'subtable' block
  saying what it holds.`

#### 哪些在 `validate` 就拒，哪些要等 `plan`

`validate` 只跑 schema（零网络），能挡住形状问题；类型与块的搭配要等 `plan`/`apply` 时的降级才发现。
所以**看到 `edit-spec OK` 不等于这份 spec 能跑**，动手前多跑一次 `plan`。

| 问题 | 谁拦下的 |
|---|---|
| 块内未知键（如 `relation.bidirectional`、`subtable.allowadd`） | `validate` |
| 子表两种模式都给 / 都不给 | `validate` |
| 块放错类型（Number 带 `relation` / `subtable`） | `plan`（validate 报 OK） |
| 跨表类型缺块、公式类型缺表达式 | `plan`（validate 报 OK） |
| 内联子表带 `showFields` | `plan`（validate 报 OK） |
| `via` 不通向另一张表、远端列名解析不了 | `plan`（要读线上结构） |

带了 `control` 逃生口的字段不受「缺块」这条拦阻（假定你自己在原始键里写全了），
且 `control` **最后合并、优先生效**。

### 子表有两种模式，必须二选一

```json
// 模式一：新建一张子表，直接写它的列
{ "type": "field.add", "worksheet": "订单",
  "field": { "name": "订单明细", "type": "SUB_LIST",
             "subtable": { "fields": [
               { "name": "商品", "type": "Text", "required": true },
               { "name": "数量", "type": "Number" },
               { "name": "所属客户", "type": "RELATE_SHEET",
                 "relation": { "worksheet": "客户" } }
             ] } } }

// 模式二：把一张已存在的表挂成子表
{ "type": "field.add", "worksheet": "订单",
  "field": { "name": "维修记录", "type": "SUB_LIST",
             "subtable": { "worksheet": "维修单",
                           "showFields": ["故障描述", "处理人"] } } }
```

- **子字段用与顶层 field 完全相同的 clean 形**——`name` / `type` / `required` / `unique` /
  `options`，而且**子字段里还能再写 `relation` / `lookup` / `rollup` / `formula` 块**，名字解析
  照样生效（上例里子字段的 `relation.worksheet: "客户"` 会被解析成客户表的 id）。不必学第二套词汇。
- **`showFields` 只能用在挂载模式**：内联模式下那些列还不存在，内联列表显示的就是你正在建的这些列。
  写在内联模式里会被明确拒绝。挂载模式下 `showFields` 写子表上那些列的名字或 id，不给就是全部可见列。
- `subtable.worksheet` 同样接名字或 id。

两种模式走的是不同的写入路径，值得知道：

| 模式 | 怎么落地 |
|---|---|
| 内联 `fields` | **整表写回**（和 `field.update` / `field.delete` 同一条路）：读出父表全部控件，把新的子表列接在后面，整份存回。同时建出一张承载子行的子表工作表。 |
| 挂载 `worksheet` | 与 `hap worksheet mount-subtable` **同一个两步握手**：先建 SUB_LIST 列，再在子表侧配好回指父表的反向关联列。少了第二步，子表行就不会按父记录过滤显示。 |

挂载完两侧都能读到：父表的 SUB_LIST 列 `dataSource` 指向子表、`sourceControlId` 是子表侧那根反向列；
子表上多出一列指回父表的关联。子表工作表**不能单独读**，要 `hap worksheet fields <子表ID> --parent <父表ID>`。

**「恰好一个」是 schema 硬约束**：`fields` 和 `worksheet` 同时给、或两个都不给，
`hap app-editor validate` 阶段（零网络）就会拒绝：

```
两者都给 → ops[0].field.subtable: 'fields' and 'worksheet' cannot both be given; give exactly one
都不给   → ops[0].field.subtable: give exactly one of: 'fields', 'worksheet'
```

## 这个引擎继承哪些修复

`app-editor` 直接调用 CLI 的核心层，**不经过命令层**。所以命令层的行为（选项翻译、参数推导、
确认提示）与它无关：命令行上加的新选项，不会自动出现在 edit-spec 里。反过来，核心层的写入规则
（整表写回保反向控件、选项值校验、按钮填写模式推导）它都拿得到。

一处例外要记住：`custom-action.create` / `custom-action.update` 里**给 `config` 是原始逃生口，
不经适配器**——填写模式推导、门控、二次确认一概不生效。详见
[custom-actions.md](custom-actions.md) 末节。

## 示例

```json
{
  "app": "myAppId",
  "ops": [
    { "type": "field.add", "worksheet": "订单",
      "field": { "name": "优先级", "type": "SingleSelect", "options": ["高", "中", "低"] } },
    { "type": "field.update", "worksheet": "订单", "field": "金额",
      "set": { "required": true } },
    { "type": "field.delete", "worksheet": "订单", "field": "废弃备注", "confirm": true },
    { "type": "component.add", "page": "首页",
      "component": { "name": "公告", "type": "richText", "value": "<p>本周盘点</p>" } }
  ]
}
```
