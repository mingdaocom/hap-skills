---
name: hap-cli-data-query
description: 用 hap 命令行查询/筛选/统计 HAP 工作表里的业务数据时用本 skill——尤其当筛选条件复杂、需要多条件 AND/OR、嵌套分组，或要做透视表聚合统计（求和/计数/平均/分组维度）。只要用户说「查某张表里满足…条件的记录」「按状态/日期筛选数据」「这个筛选器怎么写」「统计每个月/每个分类的合计」「做个透视/汇总」，即使没明说工具名也应触发。不用于：写入数据（增删改记录用 record 命令）。
---

# HAP 数据查询助手（筛选 · 透视 · 统计）

帮用户用 `hap` 命令行从 HAP 工作表里**把想要的数据查出来**。难点不在命令本身，而在**参数 JSON 怎么写对**——筛选器结构、运算符词表、透视的维度与聚合。本 skill 把这些易错点讲清楚，并给可直接套用的模板。

> 本 skill 只管"查/筛/统计"（只读）。定位到目标行后要**写回数据**（改备注、改状态等）用
> `hap worksheet record update`——注意它不接受 `--app-id`，先 `hap app select <appID>`，
> 写操作细节见 `hap-cli` 主 skill。增删改记录也直接用 `hap worksheet record` 相关命令。

## 覆盖的命令

| 命令 | 用途 | 筛选器格式 |
| --- | --- | --- |
| `worksheet record list` | 按条件查记录（筛选/排序/分页） | **filter-json（builder DSL）** |
| `worksheet record pivot` | 透视聚合（分组维度 + 求和/计数等） | **filter-json（同上）** |
| `worksheet record bottom-stats` | 视图底部那条汇总（单行统计） | filter-controls（主站 wire，**不同**） |
| `worksheet chart` | 在工作表上建统计图表 | spec-json |

> **关键认知**：`record list` 和 `record pivot` 共用同一套 **filter-json**；`bottom-stats` 用的是另一套老格式，别混。绝大多数"查数据"诉求用前两个就够。

## 第 0 步永远是：拿到字段 ID

筛选/透视里的 `field` 用的是字段 ID（controlId）或别名，不是中文字段名。先查出来：

```bash
hap worksheet fields WORKSHEET_ID        # 列出每个字段的 controlId / 名称 / 类型
```

记下要筛选/分组/聚合的那几个字段的 controlId，后面 JSON 里直接用。

---

## filter-json：筛选器怎么写（record list / pivot 通用）

### 结构

筛选器是一棵树，由两种节点组成，**可嵌套**以表达复杂的 AND/OR：

```jsonc
// 分组节点：用 logic 把若干子条件组合起来
{ "type": "group", "logic": "AND",   // AND | OR（不区分大小写）
  "children": [ <条件或子分组>, ... ] }

// 条件节点：一个具体的过滤条件
{ "type": "condition",
  "field": "<controlId 或别名>",
  "operator": "<运算符>",
  "value": <标量 或 数组> }          // 为空类运算符不需要 value
```

最外层通常是一个 `group`。要表达「(A 且 B) 或 (C 且 D)」就嵌套 group。

### 运算符词表（权威，来自 HAP V3 筛选器指南）

**比较类**

| operator | 含义 | value |
| --- | --- | --- |
| `eq` / `ne` | 等于 / 不等于 | 标量或数组 |
| `gt` / `ge` / `lt` / `le` | `>` / `>=` / `<` / `<=` | 数值或时间戳 |
| `in` / `notin` | 是其中一个 / 不是任意一个 | 数组 |
| `contains` / `notcontains` | 包含 / 不包含 | 标量或数组 |
| `concurrent` | 同时包含（多选/关联同时含多个值） | 数组 |
| `belongsto` / `notbelongsto` | 属于 / 不属于（部门） | 部门 ID 数组 |
| `startswith` / `notstartswith` | 开头是 / 开头不是 | 标量 |
| `endswith` / `notendswith` | 结尾是 / 结尾不是 | 标量 |
| `between` / `notbetween` | 在范围内 / 不在范围内 | `[起, 止]` 数组 |

**为空类**（**不要带 `value` 字段**）

| operator | 含义 |
| --- | --- |
| `isempty` | 为空 |
| `isnotempty` | 不为空 |

> ⚠️ **易错点**：这是 V3 的运算符拼写，和工作流/视图里那套（`gte`/`lte`/`empty`/`not_contains`…）**不一样**。写 filter-json 一律以上表为准。
> - 大于等于是 `ge`、`le`（不是 `gte`/`lte`）
> - 否定式无下划线：`notin` / `notcontains` / `notbetween`（不是 `not_in`）
> - 为空是 `isempty` / `isnotempty`（不是 `empty`）

### value 怎么填（按字段类型）

- **选项 / 单选 / 多选字段**：value 用选项的 **key**，不是显示文本。key 可从 `worksheet fields` 的字段 options 里查到。
- **关联表字段（Relation）**：value 用关联记录的 **rowid 数组**，配 `in` 或 `eq`。⚠️ 必须用 rowid，**不能用关联显示的标题文本**（如版本名）去匹配。怎么拿这个 rowid 见下方「关联字段筛选」。子表的反向关联字段同理：value 填**父记录的 rowid**，即可筛出该父记录的全部子行。
- **成员字段（Collaborator）**：value 用成员的 **accountId 数组**，配 `in`/`eq`。
- **部门字段**：value 用部门 **ID 数组**，配 `belongsto` / `notbelongsto`。
- **文本字段**：`contains` / `startswith` / `eq` 等，value 直接给文本。
- **日期字段**：`between` 给 `["2025-01-01","2025-01-31"]`，或 `gt`/`lt` 给单个日期/时间戳。

### 关联字段筛选：先拿到关联记录的 rowid

关联字段（如「任务」表里的「版本」「项目」「客户」）在**返回数据里长这样**——一个数组，每项带 `sid`（关联记录的 rowid）和 `name`（显示标题）：

```json
"版本字段": [ { "sid": "ITERATION_ROW_ID", "name": "迭代A" } ]
```

筛选时 value 要用那个 `sid`。两种拿到它的办法：

1. **从关联表查**：去被关联的那张表 `record list --search "迭代A"`，拿到目标记录的 `rowid`。注意关联显示的 `name` 来自该表的标题字段，可能和你以为的不一样（比如标题其实是 "2.3" 而非 "迭代A 2.3"），所以以实际查到的为准。
2. **从已有数据反查**：先 `record list` 拉几条本表记录，看那个关联字段里已出现的 `{sid, name}`，挑出 `name` 匹配的 `sid`。

拿到 sid 后这样筛（任务表里「版本」关联到「迭代A」）：

```bash
hap worksheet record list TASK_WS_ID --filter-json '{
  "type":"group","logic":"AND",
  "children":[{"type":"condition","field":"<版本字段ID>","operator":"in","value":["ITERATION_ROW_ID"]}]
}' -p 1 -n 100
```

#### 子表（SubTable）：查"某条父记录下的所有子行"

子表数据不在父记录里，存在一张独立工作表（父 SubTable 字段的 `dataSource`），
子行通过**反向 Relation 字段**（父 SubTable 字段的 `sourceField`）挂回父行。
所以查某父记录的子行 = 在子表工作表上，按这个反向关联字段筛 = 父记录 rowid：

```bash
hap worksheet record list <子表WS_ID> --use-field-id-as-key -p 1 -n 100 \
  --filter-json '{"type":"group","logic":"AND","children":[
    {"type":"condition","field":"<反向关联字段ID>","operator":"in","value":["<父记录rowid>"]}]}' \
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
  "type": "group", "logic": "OR",
  "children": [
    { "type": "group", "logic": "AND", "children": [
      { "type": "condition", "field": "name",         "operator": "startswith", "value": "张" },
      { "type": "condition", "field": "onboard_date",  "operator": "between",    "value": ["2025-01-01","2025-01-31"] }
    ]},
    { "type": "group", "logic": "OR", "children": [
      { "type": "condition", "field": "dept_option",  "operator": "in",        "value": ["k_sales","k_mkt"] },
      { "type": "condition", "field": "dept_id",       "operator": "belongsto", "value": ["DEPT_HUABEI_ID"] }
    ]}
  ]
}'
```

简单单条件（状态为空的记录）——注意 `isempty` 不带 value：

```bash
hap worksheet record list WORKSHEET_ID --filter-json '{
  "type":"group","logic":"AND",
  "children":[{"type":"condition","field":"status","operator":"isempty"}]
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

任何「按 X 分组，算 Y 的合计/计数/平均」都用它。`--values-json` 和 **`--view-id` 都必填**（视图 id 用 `hap worksheet view list WORKSHEET_ID` 查，挑一个"全部"类视图即可）。

```bash
hap worksheet record pivot WORKSHEET_ID \
  --view-id VIEW_ID \                                          # 必填
  --rows-json '[{"field":"status"}]' \                         # 行维度（分组）
  --columns-json '[{"field":"create_date","granularity":3}]' \ # 列维度，可选
  --values-json '[{"field":"amount","aggregation":"SUM"}]' \   # 值（聚合），必填
  --filter-json '<同 list 的 filter 格式>' \                    # 可选
  --include-summary                                            # 要总计行加
```

返回结构是 `data.pivot`（一个数组），每项形如：

```json
{ "rows":    { "<行维度字段ID>": "进行中" },
  "columns": { },
  "values":  { "<值字段ID>": 190000.0 } }
```

解析时按字段 ID 从 `rows`/`values` 里取值；要排名就把 `pivot` 数组按某个 value 排序后取前 N（透视本身不保证按值排序）。

### 维度（rows / columns）

每项 `{"field":"<controlId>", "displayName":"可选", "granularity":<整数>, "includeEmpty":false}`：

- `granularity` 仅对**日期/地区**字段有意义：
  - 日期：`1`=日，`2`=周，`3`=月
  - 地区：`1`=省，`2`=省/市，`3`=省/市/县
- `includeEmpty`：是否把空值也作为一组，默认 false。

### 值（values）

每项 `{"field":"<controlId>", "aggregation":"<聚合>", "displayName":"可选"}`：

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

- **`record bottom-stats`**：只返回视图底部那一行汇总（不是多维透视）。它走的是**另一套老格式**：`--column-rpts '[{"controlId":"amount","rptType":1}]'`（rptType 是整数，按 `--help` 确认对应关系），`--filter-controls` 用主站 wire 结构而非 filter-json。需要真正的分组统计时优先用 `record pivot`。
- **`worksheet chart`**：在工作表上**建一个图表配置**（不是即时取数）。用 `--report-type`（整数图表类型）+ `--spec-json`（含 xaxes/yaxisList/filter 等）。建图表多数时候属于"改应用"，可交给 hap-cli-app-editor；纯取数分析用 `record pivot` 更直接。

先看 `hap worksheet record bottom-stats --help` / `hap worksheet chart --help` 再用。

---

## 写对查询的要点

照这些规则写，绝大多数查询一次就成：

- **字段标识**：filter / 维度 / 值里的 `field` 用 controlId 或别名，不用中文字段名（用 `worksheet fields` 查）。
- **运算符**：用 V3 词表（`ge`/`le`/`isempty`/`notin`…），不要套用工作流/视图那套拼写。
- **value 形态**：选项字段用选项 key；关联字段用关联记录 rowid；成员字段用 accountId；为空类（`isempty`/`isnotempty`）不带 value。
- **必填项**：`record list` / `record pivot` 的分页 `-p`、`-n` 都必填；`record pivot` 还必须带 `--view-id`。
- **结果解析**：返回默认用字段别名作 key，要用 controlId 作 key 就加 `--use-field-id-as-key`；成员/关联字段是对象数组，取其中的 `fullname` / `name`。
- **Shell 转义**：用单引号包整个 JSON、内部用双引号；筛选复杂时写进文件再 `--filter-json "$(cat f.json)"`。
- **核对实际请求**：`hap config log on` 后再跑命令，可在日志里看到真正发出的请求体。
