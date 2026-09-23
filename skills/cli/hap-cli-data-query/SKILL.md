---
name: hap-cli-data-query
description: 用 hap 命令行查询/筛选/统计 HAP 工作表里的业务数据时用本 skill——尤其当筛选条件复杂、需要多条件 AND/OR、嵌套分组，或要做透视表聚合统计（求和/计数/平均/分组维度）。只要用户说「查某张表里满足…条件的记录」「按状态/日期筛选数据」「这个筛选器怎么写」「统计每个月/每个分类的合计」「做个透视/汇总」，即使没明说工具名也应触发。不用于：写入数据（增删改记录用 record 命令）。
---

# HAP 数据查询助手（筛选 · 透视 · 统计）

帮用户用 `hap` 命令行从 HAP 工作表里**把想要的数据查出来**。难点不在命令本身，而在**参数 JSON 怎么写对**——筛选条件的写法、各处支持哪些比较方式、透视的维度与聚合。本 skill 把这些易错点讲清楚，并给可直接套用的模板。

> 本 skill 只管"查/筛/统计"（只读）。定位到目标行后要**写回数据**（改备注、改状态等）用
> `hap worksheet record update`——**写记录不依赖默认应用**，有 `WORKSHEET_ID` 就能定位，
> `-a/--app-id` 可传可不传（传了只是限定字段查找范围），写入失败时别往「是不是没 select
> 对应用」上想。各字段类型该传什么值见 `hap guide record`，写完读回确认。
> 增删改记录也直接用 `hap worksheet record` 相关命令。

## 覆盖的命令

| 命令 | 用途 | 筛选器格式 |
| --- | --- | --- |
| `worksheet record list` | 按条件查记录（筛选/排序/分页） | **filter-json（统一筛选写法）** |
| `worksheet record pivot` | 透视聚合（分组维度 + 求和/计数等） | **filter-json（同上）** |
| `worksheet record bottom-stats` | 视图底部那条汇总（单行统计） | filter-controls（主站 wire，**不同**） |
| `worksheet record relations` | 顺着某条记录的关联字段列出被关联的记录 | 无（直接给 记录+字段） |
| `worksheet record logs` | 某条记录的变更日志（谁在什么时候改了什么） | 无 |
| `worksheet chart` | 图表命令组（create/get/update/delete/list） | spec-json（在 `chart create` 上） |

> **关键认知**：`record list` 和 `record pivot` 共用同一套 **filter-json**；`bottom-stats` 用的是另一套老格式，别混。绝大多数"查数据"诉求用前两个就够。

## 第 0 步永远是：拿到字段 ID

筛选条件里的 `field` 可以写字段 ID（controlId）、别名，或界面上显示的列标题原文（工作表上没有的名字会被点名拒绝）；
但透视的维度 `--rows-json` / `--columns-json` 和值 `--values-json` **只认字段 ID 或别名**，写列标题会被拒。先查出来：

```bash
hap worksheet fields WORKSHEET_ID        # 列出每个字段的 controlId / 名称 / 类型
```

记下要筛选/分组/聚合的那几个字段的 controlId，后面 JSON 里直接用。

---

## filter-json：筛选器怎么写（record list / pivot 通用）

### 写法

筛选条件就是一组条件，用 `logic` 组合，**可嵌套**以表达复杂的与/或：

```jsonc
{ "logic": "and",                     // and | or
  "items": [
    { "field": "<字段 ID、别名或列标题>",
      "op": "<比较方式>",
      "value": <标量 或 数组> },       // empty / not_empty 不需要 value
    { "logic": "or", "items": [ ... ] }  // 某一项本身也可以是一个组
  ] }
```

要表达「(A 且 B) 或 (C 且 D)」就在 `items` 里再嵌组。这一种写法 `hap` 各处都收——记录查询、视图、
业务规则、按钮、图表、工作流条件——权威说明见 **`hap guide record filter`**（3.1 写法、3.2 各处支持哪些
比较方式、3.3 透视的限制），它随 CLI 版本走，别照本 skill 的记忆写。

> 旧写法（`{"type":"group","children":[{"type":"condition",...}]}` 那棵树）和旧拼法（`notin`、`isempty`、
> `ge`、`startswith`…）仍然可用，以前写的筛选照样能跑；新写的一律用上面这种。

### 比较方式：记录查询能用哪些

**`record list` / `record pivot` 能用这 21 个**：

```
eq ne  in not_in  contains not_contains  all_contains
starts_with not_starts_with  ends_with not_ends_with
gt gte lt lte  between not_between  belongs not_belongs
empty not_empty
```

视图、业务规则、按钮、图表那几处还多一些专用的比较方式（`date_is`、`self`、`rc_eq`、`array_eq`…），
**它们在 `record list` / `record pivot` 上不存在**——写了 `hap` 会当场拒绝并列出这里能用的。
各处的完整对照见 `hap guide record filter` 的 3.2。

要点：

- **日期也用 `between`**（配 `["2026-02-01","2026-03-31"]`）和 `gt` / `gte` / `lt` / `lte`。
  在视图/规则/按钮/图表上，`hap` 会按列类型自动换成日期专用的比较方式，你照常写即可；
  但 `date_between` 这类显式日期名只在那几处合法，**记录查询会拒绝它**。
- `empty` / `not_empty` **不带 `value`**。
- 写错名字、写了这里没有的比较方式、写了不存在的列，`hap` 都会在发出去之前点名拒绝并告诉你可用取值。
- `node` 键和对象形态的 `value` 只属于工作流条件，写在记录查询里会被拒绝。

> 🚨 **服务端对不认识的比较方式不报错——它把整个条件丢掉，返回全表，并且报成功。**
> 用一个它不认的名字去查十二条逾期订单，拿回来的是全部订单，没有任何迹象说明筛选没生效。
> 你能看到报错，靠的是 `hap` 在发出去之前的本地拦截。所以**只要不是用 `hap` 发的筛选请求
> （自己拼 HTTP、别的客户端），看结果要看条数，别只看 `success`。**

### value 怎么填（按字段类型）

- **选项 / 单选 / 多选字段**：value 用选项的 **key** 最稳（从 `worksheet fields` 的字段 options 里查）；写选项的显示文本 `hap` 也会替你换成 key。
- **关联表字段（Relation）**：value 用关联记录的 **rowid 数组**，配 `in` 或 `eq`。⚠️ 必须用 rowid，**不能用关联显示的标题文本**（如版本名）去匹配。怎么拿这个 rowid 见下方「关联字段筛选」。子表的反向关联字段同理：value 填**父记录的 rowid**，即可筛出该父记录的全部子行。
- **成员字段（Collaborator）**：value 用成员的 **accountId 数组**，配 `in`/`eq`。
- **部门字段**：value 用部门 **ID 数组**，配 `belongs` / `not_belongs`（在 `record pivot` 上这两个只对**地区**字段可用，见下方 pivot 一节）。
- **文本字段**：`contains` / `starts_with` / `eq` 等，value 直接给文本。
- **日期字段**：`between` 给 `["2025-01-01","2025-01-31"]`，或 `gt` / `gte` / `lt` / `lte` 给单个日期/时间戳（**不是** `date_between`，记录查询不收它）。

### 关联字段筛选：先拿到关联记录的 rowid

关联字段（如「任务」表里的「版本」「项目」「客户」）在**返回数据里长这样**——一个数组，每项带 `sid`（关联记录的 rowid）和 `name`（显示标题）：

```json
"版本字段": [ { "sid": "ITERATION_ROW_ID", "name": "迭代A" } ]
```

筛选时 value 要用那个 `sid`。**最直接的办法是让命令替你列**：

```bash
hap --json worksheet record relations <本表WS_ID> <本条记录rowid> <关联字段ID>
```

它顺着这条记录的关联字段把被关联的记录列出来，并附带它们的来源工作表信息——省掉下面两步手工反查。
分页用 `-p`/`-n`（默认每页 20），要连系统字段一起拿加 `--is-return-system-fields`。

手工反查的两种办法（还没有具体某条记录、或要按名字找时用）：

1. **从关联表查**：去被关联的那张表 `record list --search "迭代A"`，拿到目标记录的 `rowid`。注意关联显示的 `name` 来自该表的标题字段，可能和你以为的不一样（比如标题其实是 "2.3" 而非 "迭代A 2.3"），所以以实际查到的为准。
2. **从已有数据反查**：先 `record list` 拉几条本表记录，看那个关联字段里已出现的 `{sid, name}`，挑出 `name` 匹配的 `sid`。

拿到 sid 后这样筛（任务表里「版本」关联到「迭代A」）：

```bash
hap worksheet record list TASK_WS_ID --filter-json '{
  "logic":"and",
  "items":[{"field":"<版本字段ID>","op":"in","value":["ITERATION_ROW_ID"]}]
}' -p 1 -n 100
```

#### 子表（SubTable）：查"某条父记录下的所有子行"

子表数据不在父记录里，存在一张独立工作表（父 SubTable 字段的 `dataSource`），
子行通过**反向 Relation 字段**（父 SubTable 字段的 `sourceField`）挂回父行。
所以查某父记录的子行 = 在子表工作表上，按这个反向关联字段筛 = 父记录 rowid：

```bash
hap worksheet record list <子表WS_ID> --use-field-id-as-key -p 1 -n 100 \
  --filter-json '{"logic":"and","items":[
    {"field":"<反向关联字段ID>","op":"in","value":["<父记录rowid>"]}]}' \
  --sorts-json '[{"field":"<明细编号等排序字段ID>","isAsc":true}]'
```

- `<反向关联字段ID>`：在父表 `worksheet fields` 里，找 SubTable 字段的 `sourceField`。
- value 是**父记录的 rowid**（不是父记录标题文本），用 `in`。
- 子表行的"第几行"由排序决定，通常按 AutoNumber 明细编号升序，与表单里看到的顺序一致；
  务必带 `--sorts-json`，否则默认顺序不保证稳定，"数第 N 行"会数错。


### 完整示例

「姓张、且 1 月入职」**或**「在销售/市场部、或属于华北区」：

```bash
hap worksheet record list WORKSHEET_ID --filter-json '{
  "logic": "or",
  "items": [
    { "logic": "and", "items": [
      { "field": "name",         "op": "starts_with", "value": "张" },
      { "field": "onboard_date", "op": "between",     "value": ["2025-01-01","2025-01-31"] }
    ]},
    { "logic": "or", "items": [
      { "field": "dept_option",  "op": "in",      "value": ["k_sales","k_mkt"] },
      { "field": "dept_id",      "op": "belongs", "value": ["DEPT_HUABEI_ID"] }
    ]}
  ]
}'
```

简单单条件（状态为空的记录）——注意 `empty` 不带 value：

```bash
hap worksheet record list WORKSHEET_ID --filter-json '{
  "logic":"and",
  "items":[{"field":"status","op":"empty"}]
}'
```

---

## record list：查记录

```bash
hap worksheet record list WORKSHEET_ID \
  --filter-json '<见上>' \
  --sorts-json '[{"field":"onboard_date","isAsc":false}]' \
  --fields '["name","status","amount"]' \   # 只返回这几个字段，省 token
  --page-size 50 --page-index 1 \
  --include-total-count                       # 想要总行数时加
```

- `--page-size` / `--page-index` **都是必填**。
- `--search` 关键字模糊搜索（跨字段），可与 filter 叠加。
- `--view-id` 套用某视图的内置筛选/排序。
- 不传 `--filter-json` 就是查全部（按分页）。
- **返回数据默认用字段别名作 key**（如 `mingcheng`、`fuzeren`、`ssdd`），不是 controlId。所以解析结果时按别名取值，或加 `--use-field-id-as-key` 让 key 变成 controlId。别名可在 `worksheet fields` 里看到。
- `--fields` 传字段 ID 或别名都行；只想要某几列时用它省 token。
- 成员字段返回的是对象数组 `[{accountId, fullname, avatar, status}]`，取 `fullname` 显示人名。

---

## record pivot：透视聚合（统计的首选）

任何「按 X 分组，算 Y 的合计/计数/平均」都用它。**只有 `--values-json` 是必填**；`--view-id` 可选
（给了就套用该视图的筛选/排序，视图 id 用 `hap worksheet view list WORKSHEET_ID` 查），
`-p`/`-n` 不传走默认值。`-a` 也可以不传——命令会按工作表反查它属于哪个应用；传错了会明确告诉你
「这张表不属于该应用，请用它真正所属的应用」。

```bash
hap worksheet record pivot WORKSHEET_ID \
  --view-id VIEW_ID \                                          # 必填
  --rows-json '[{"field":"status"}]' \                         # 行维度（分组）
  --columns-json '[{"field":"create_date","granularity":3}]' \ # 列维度，可选
  --values-json '[{"field":"amount","aggregation":"SUM"}]' \   # 值（聚合），必填
  --filter-json '<同 list 的筛选条件>' \                        # 可选
  --include-summary                                            # 要总计行加
```

返回结构是 `data.pivot`（一个数组），每项形如：

```json
{ "rows":    { "<行维度字段ID>": "进行中" },
  "columns": { },
  "values":  { "<值字段ID>": 190000.0 } }
```

解析时按字段 ID 从 `rows`/`values` 里取值；要排名就把 `pivot` 数组按某个 value 排序后取前 N（透视本身不保证按值排序）。

### 🚨 pivot 能用的筛选比 list 少

同一份 filter-json，`record list` 收、`pivot` 未必收——**pivot 认哪些比较，取决于字段装的是什么**：

| 比较方式 | 在 pivot 上 |
| --- | --- |
| `eq` / `ne`、`empty` / `not_empty` | 都行 |
| `contains` / `not_contains` | **一律不行**，任何字段类型都拒。`hap` 本地就拦下并提示改用 `starts_with` / `ends_with`，或干脆换 `record list` |
| `in` / `not_in` | 只在**单选、地区**上行；文本 / 数值 / 日期会被拒 |
| `gt` / `gte` / `lt` / `lte`、`between` / `not_between` | 只在**数值、日期**上行 |
| `belongs` / `not_belongs` | 只在**地区**上行 |
| `all_contains` | 只在**文本**上行 |
| `starts_with` / `ends_with` 及其否定式 | 只在**文本**上行 |

除 `contains` 外，其余按类型的限制 `hap` 拦不住（它不知道字段类型），由服务端拒绝并把你这次发的
条件补回错误信息里，形如「A pivot accepts fewer comparisons than `record list` does…」。

**pivot 还挑 `value` 的形态**（`record list` 不挑，两种写法都收）：

| 比较方式 | pivot 要什么 |
| --- | --- |
| `gt` / `gte` / `lt` / `lte` | **裸值**。写成数组会被拒——`"value": 0` 行，`[0]` 和 `["0"]` 都不行 |
| `between` / `not_between` | **两个元素的数组**。写成裸值、或只给一个元素，都会被拒 |
| `eq` / `ne` / `in` / `not_in` | 两种都收，不用管 |

同一条件在 `record list` 上无论哪种写法都能跑，**所以这类报错只会在换成 pivot 时冒出来**。
这两张表以 `hap guide record filter` 的 3.3 为准。

> 筛不动就退回 `record list` 拿明细，再在本地聚合——比跟 pivot 的类型和形态限制较劲快。

### 维度（rows / columns）

每项 `{"field":"<controlId 或别名>", "displayName":"可选", "granularity":<整数>, "includeEmpty":false}`：

- `granularity` 仅对**日期/地区**字段有意义：
  - 日期：`1`=日，`2`=周，`3`=月
  - 地区：`1`=省，`2`=省/市，`3`=省/市/县
- `includeEmpty`：是否把空值也作为一组，默认 false。

### 值（values）

每项 `{"field":"<controlId 或别名>", "aggregation":"<聚合>", "displayName":"可选"}`：

- `aggregation`（不区分大小写）：`COUNT` 计数、`DISTINCTCOUNT` 去重计数、`SUM` 求和、`MIN` 最小、`MAX` 最大、`AVG` 平均。
- **只想数行数**（不针对某字段）：`field` 填特殊值 `record_count`，配 `COUNT`。

示例——按月统计每个状态的订单数和金额合计：

```bash
hap worksheet record pivot WORKSHEET_ID \
  --rows-json '[{"field":"create_date","granularity":3}]' \
  --columns-json '[{"field":"status"}]' \
  --values-json '[
    {"field":"record_count","aggregation":"COUNT"},
    {"field":"amount","aggregation":"SUM"}
  ]' --include-summary
```

---

## bottom-stats 与 chart（次要）

- **`record bottom-stats`**：只返回视图底部那一行汇总（不是多维透视）。它走的是**另一套老格式**：`--column-rpts '[{"controlId":"amount","rptType":1}]'`（rptType 是整数，按 `--help` 确认对应关系），`--filter-controls` 用主站 wire 结构而非 filter-json。另有 `-k/--keywords` 按关键字筛，以及 `--report-id`——给了它就读**某个图表视图**的汇总而不是普通表格的汇总（图表 id 来自 `hap worksheet chart list`）。需要真正的分组统计时优先用 `record pivot`。
- **`record logs`**：某条记录的变更日志，回答"这个值是谁什么时候改的"。定位到可疑记录后用它，比翻应用级 `hap app logs` 精准。
- **`worksheet chart`**：**是一个命令组**（`create` / `get` / `update` / `delete` / `list`），
  在工作表上建/改图表配置，不是即时取数。建图用 `hap worksheet chart create`，
  `--report-type`（整数图表类型）+ `-j/--spec-json`（含 xaxes/yaxisList/filter 等）都在**子命令**上，
  `hap worksheet chart --help` 只会列出子命令。图表规格怎么写见 `hap guide chart`。
  建图表多数时候属于"改应用"，可交给 hap-cli-app-editor；纯取数分析用 `record pivot` 更直接。

先看 `hap worksheet record bottom-stats --help` / `hap worksheet chart create --help` 再用。

---

## 写对查询的要点

照这些规则写，绝大多数查询一次就成：

- **字段标识**：筛选条件里的 `field` 可用 controlId、别名或列标题；透视的维度 / 值里只认 controlId 或别名（用 `worksheet fields` 查）。
- **筛选条件**：统一写法 `{"logic","items":[{"field","op","value"}]}`，比较方式用 `gte` / `lte` / `empty` / `not_in` 这类统一名；视图/图表专用的（`date_is`、`self`…）记录查询不收。拿不准就看 `hap guide record filter`。
- **value 形态**：选项字段用选项 key；关联字段用关联记录 rowid；成员字段用 accountId；`empty` / `not_empty` 不带 value。
- **必填项**：只有 `record pivot` 的 `--values-json` 是必填。分页 `-p`/`-n` 都有默认值
  （`record list` 每页 20、`pivot` 每页 100，页码都从 1 起），`--view-id` 两个命令都是可选的。
  要一次取更多就显式给 `-n`。
- **结果解析**：返回默认用字段别名作 key，要用 controlId 作 key 就加 `--use-field-id-as-key`；成员/关联字段是对象数组，取其中的 `fullname` / `name`。
- **Shell 转义**：用单引号包整个 JSON、内部用双引号；筛选复杂时写进文件再 `--filter-json "$(cat f.json)"`。
- **核对实际请求**：`hap config log on` 后再跑命令，可在日志里看到真正发出的请求体。
