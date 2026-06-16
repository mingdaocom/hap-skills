# Worksheets & Fields — 工作表与字段

工作表写在顶层 `worksheets[]`，关联/他表/汇总/子表都是**字段的 `type`**，子配置内联在字段上。
生成前必须阅读表单字段的排版规范 [layout.md](layout.md)，每个字段必须按规则给排版属性 `row`+`size`。

```jsonc
"worksheets": [
  { "name": "物料", "section": "库存管理", "icon": "sys_11_1_tool_storage_box",
    "fields": [ { "type": "Text", "name": "物料名称", "is_title": true, "row": 0, "size": 6 }, ... ] }
]
```

工作表键：`name`(逻辑名唯一)、`section`(分组逻辑名，省略放默认分组)、`icon`、`alias`、`fields[]`。

> [!CAUTION]
> `icon` 必须按照 [design_guide.md](design_guide.md) 中的指南，使用 `hap icon search` 加多个相关关键词（如 `hap icon search 会员 用户 成员 权益 皇冠 勋章`）搜索可用图标，从结果中选择一个。
> **图标必须唯一**：同一应用里每张工作表的图标都要不一样，也不能和自定义页面图标重复。逐表搜索时换不同关键词，并维护一份「已用图标」清单避免撞车——`validate` 会跨工作表+页面强制查重，重复直接报错（exit 2），到 build 前才发现就得返工。

## 字段通用键

`type`(必填 CODE)、`name`(本表唯一)、`required`、`unique`、`is_title`(每表至多一个，建议 Text)、`hint`(占位提示)、
`size`/`row`/`col`(排版)、`hidden`/`readonly`/`hidden_on_create`(字段权限)、`advanced_setting`/`extra`(逃生通道，自由覆盖)。

字段权限映射 fieldPermission：`hidden`=隐藏、`readonly`=只读、`hidden_on_create`=新增时隐藏。

> ⚠️ **字段名在本表内必须唯一(Divider 除外)。** Rollup/工作流都按名字解析字段,**两个真字段同名**(尤其常见的「两个 SubTable 都叫 `费用明细`」)会让 `via`/引用绑到错的那个,build 才炸。需要两份明细就起不同名(如 `费用明细`/`收款明细`)。**例外**:`Divider` 是布局分隔符、不是可寻址字段,允许它和紧随其后的 SubTable 同名(用作区块标题),这是合法写法。validate 现在会拦下「两个非 Divider 字段同名」。

## 字段设计规范（生成字段前先读）

### 一、建表前的业务思考

不要只建规划里的字段，主动扩展上下游与治理字段：

| 字段类别 | 典型字段 |
|---|---|
| 状态/阶段 | 状态、处理阶段 |
| 优先级/重要度 | 优先级、紧急程度 |
| 归属与协作 | 负责人、协作者、所属部门 |
| 时间维度 | 计划开始/结束、截止日期、实际完成 |
| 分类/标签 | 分类、标签、类型 |
| 治理 | 是否归档、是否启用、审批结果 |
| 附件/备注 | 附件、备注、说明 |

### 二、标题字段（`is_title`）

每张工作表**有且仅有一个**标题字段。选择规则：

- 优先选**识别度最高的 Text 字段**（如「名称」「标题」）。
- **仅以下类型可设为标题**：`Text` / `AutoNumber` / `Date` / `DateTime` / `Collaborator` / `Location`。
- plan 没显式指定标题就自行判断设置；若没有可用字段，**新建一个 Text 字段当标题**。

### 三、字段类型决策

```
单选 ≤ 5 个选项   → SingleSelect
单选 > 5 个选项   → Dropdown
多选 ≤ 10 个选项  → MultipleSelect
多选 > 10 个选项  → Dropdown
单个是/否        → Checkbox（不要用 SingleSelect + 是/否）
人员            → Collaborator（不要用 Text 替代）
电话            → PhoneNumber，邮箱 → Email，金额 → Currency
流水号          → AutoNumber，计算值 → Formula
```

### 四、Divider 分段规范

每张表都应使用 `Divider` 字段把表单分组，分段名必须结合业务语义生成：

- 先按字段语义分组，再提炼分段名；名称简洁自然，通常 2～6 个字，优先业务词。
- 每张表建议 **2～5 个 Divider**，每组建议 **3～8 个字段**；附件、备注、说明、归档类放最后。
- **禁止空泛模板名**：`基本信息`、`归属与协作`、`计划与进度`、`审批与治理`、`备注与附件`。
- 应按业务内容自然命名：客户表 `客户资料`/`联系信息`/`跟进情况`；合同表 `合同主体`/`签约安排`/`履约信息`。
- Divider 固定属性：`"required": false`、`"size": 12`（整行）。

### 五、选项颜色规则

状态/阶段/优先级类字段**必须加颜色**（用 `{value, color}` 写法，或在 optionset 里给 `color`）：

| 语义 | 颜色 |
|---|---|
| 负面 / 失败 / 拒绝 | `#F52222`（红） |
| 正面 / 完成 / 通过 | `#00C345`（绿） |
| 警告 / 待处理 | `#FAD714`（黄） |
| 进行中 | `#2D46C4`（蓝） |
| 取消 / 归档 | `#484848`（灰） |

- **纯分类/标签字段不加颜色。**
- 选项色**只能**取这套**选项调色板（10 色）**之一（**schema 已强制 enum，越界会校验失败**）：
  `#C0E6FC` `#C3F2F2` `#00C345` `#FAD714` `#FF9300` `#F52222` `#EB2F96` `#7500EA` `#2D46C4` `#484848`。

> ⚠️ 这是**选项状态色**调色板，和 [design.md](design.md) 里**应用/表主题色的 9 色**是两套，不要混用：主题色管 `icon_color`/`nav_color`/按钮；选项色管单选/多选/选项集的状态标记。

### 六、Relation 显示规范

| `display` | 适用场景 | `show_fields` 数量 |
|---|---|---|
| `dropdown` | 仅显示标题，纯数据选择、无需展开查看 | 不需要 |
| `card` | 数据选择 + 同时展示关联记录的关键字段（**默认推荐**） | **最少 2 个**，推荐 2-4 |
| `table` | 多条记录、需直接查看/操作多列（子表式展示） | 5-10 |
| `tab_table` | 大量记录、需独立管理（放表单最末尾） | 5-10 |

- `card` / `table` / `tab_table` **必须设 `show_fields`**，挑最有业务识别度的字段。
- **`card` 模式 `show_fields` 少于 2 个视为不合格。**

## 字段类型与专属 config

### 基础类型（无专属 config）
`Text` / `RichText`(富文本,12 宽) / `PhoneNumber` / `LandlinePhone` / `Email` / `Certificate` / `Rating` /
`Checkbox` / `Time` / `Signature` / `Location`(定位,12 宽) / `DynamicLink` / `Embed` /
`Divider`(分段标题，把表单分组；`required:false`、`size:12`，名称按业务语义起，见上「字段设计规范·四」)。

### Number / Currency
`decimals`(0~6 小数位，省略=整数)。Currency 同样可配 decimals。

### 单选/多选/下拉（选型见下）
- `SingleSelect`：单选，平铺 radio，适合少量固定选项（状态、方式）。
- `Dropdown`：单选，下拉，适合选项较多（单位、类别、地区）。
- `MultipleSelect`：多选。
- 选项来源**二选一**（互斥）：
  - 独占：`"options": ["草稿","已提交","已完成"]`（首项默认选中；或 `{value,color,checked}`）。
  - 共享：`"optionset": "<顶层 optionsets 名>"`（多个字段共用同一组选项时）。

### Date / DateTime
直接用，无必填 config。日期粒度在视图/图表里配。

### Region（行政区划）
`region_level`(**必填**)：`province`/`city`/`county`。

### Collaborator（成员）/ Department / OrgRole / Role
成员/部门/组织角色字段，直接建列；数据填充时成员用虚拟账号（见 seed-data.md）。

### Attachment（附件）
直接建列。数据填充时填 `[{name,url}]`，执行器自动上传。

### AutoNumber（自动编号）
`auto_number`(**必填**)：按 `prefix → 日期 → 自增` 拼接。
```jsonc
{ "type":"AutoNumber","name":"单号","auto_number":{
    "prefix":"WL-", "date_format":"YYYYMMDD", "digits":4, "reset":"daily" } }
```
`date_format`∈YYYY/YYYYMM/YYYYMMDD/YYYYMMDDHH(省略=不含日期)；`digits`补零位数；`reset`∈never/daily/monthly/yearly。

### Barcode / CodeScan（条码）
`source`(**必填**)：作为条码内容的**来源字段逻辑名**（同表、须先存在）。条码不能独立显示。

### AmountInWords（金额大写）
`source`(**必填**)：要转成中文大写的**数值来源字段逻辑名**（同表的 Number/Currency/Rollup）。金额大写不能独立显示，必须指定来源数值字段——**用 `source`，不要用 `formula`**。例：`{ "type":"AmountInWords","name":"合计大写","source":"费用合计" }`（来源可以是 Rollup，执行器会自动在其建好后再建大写字段）。

### CascadingSelect（级联选择）
级联选择**只能以一张"自关联（带父子层级）的工作表"为数据源**（从该层级树里逐级选择）。**它不是多级下拉枚举**。因此：
- 想要简单的「单层分类/枚举」（如 展区 A/B/C、城市、类别）→ 用 `Dropdown` 或 `SingleSelect`（带 `options`），不要用 CascadingSelect。
- 需要真正的层级级联时，先建一张带"上级"自关联字段的分类表，再用级联引用它。（注：当前执行器对级联源表的物理装配仍在完善中，flat 枚举一律用 Dropdown。）

### Formula / DateFormula / FunctionFormula（公式）
`formula`：列引用用 `${字段逻辑名}`，执行期换成 controlId。`decimals` 可配（数值公式）。

### Relation（关联记录）
`relation`(**必填**)，按逻辑名指向目标表：
```jsonc
{ "type":"Relation","name":"客户","relation":{
    "worksheet":"客户",          // 目标表逻辑名
    "multi": false,              // false=单条/一对多 · true=多条/多对多
    "display": "dropdown",       // 见下「显示方式 vs 基数」
    "show_fields": ["客户名称","等级"],   // 关联控件展示的目标表列
    "two_way": { "name":"相关订单", "display":"tab_table", "show_fields":["单号","金额"] }
}}
```
**显示方式 vs 基数（校验会拦不匹配的）**：
- 单条(`multi:false`)：`dropdown`(默认) / `card`。**单条不需要 show_fields**，可省略。
- 多条(`multi:true`)：`tab_table`(默认) / `card` / `list` / `table`。
  多条 `table`/`tab_table` 是表格展示需要多列：省略 `show_fields` 时执行器默认取目标表前 5 列；也可显式列出。
- **双向关联 `two_way`**：在目标表自动生成一个反向关联字段（HAP 特有，正向设好后服务端开放反向，**不要在两个表各建一次**）。
  反向半边**恒为多条**（父/tab_table 侧，列出所有指向它的记录，默认 tab_table，默认「新增时隐藏」）。
  正向 `multi:false` = 一对多；正向 `multi:true` = **多对多**（两侧皆多条）。`two_way.name` 必填。

### Lookup（他表字段，镜像目标表某列）
`lookup`(**必填**)：经本表某 Relation 桥接，镜像目标表一列。
```jsonc
{ "type":"Lookup","name":"客户等级","lookup":{ "via":"客户", "field":"等级" } }
```
`via`=本表作桥的 Relation 字段逻辑名；`field`=目标表要镜像的列。

### Rollup（汇总）
`rollup`(**必填**)：经本表 SubTable 或多条 Relation 桥接，对目标表某列聚合，可带筛选。
```jsonc
{ "type":"Rollup","name":"已发数量","rollup":{
    "via":"发货明细", "field":"数量", "aggregate":"sum",
    "filter":[ {"field":"状态","op":"eq","value":"已发货"} ] } }
```
`aggregate`∈sum(默认)/count/avg/max/min/distinct_count；`filter` 用通用筛选器（见下）。

> ⚠️ **`via` 必须是「本表上」的 SubTable 或 Relation 字段。** 双向关联(two_way)的反向控件**长在目标表上、不在本表**:`销售订单.店铺` 的 `two_way:相关订单` 反向是建在「店铺」上的,所以「店铺」可以 `via:相关订单` 汇总订单;但**「商品SKU」不能** `via:相关订单`(SKU 上没有这个反向)。要在 A 表汇总,A 表上必须真有一个指向来源表的 Relation 或它的反向控件。`field` 必须是被桥接目标(关联表 / 子表)上真实存在的列。validate 现在会拦下 via 不在本表、或 field 不在目标上的情况。

### SubTable（内联子表，推荐建模「一单多明细」）
`child_fields`(**必填**)：递归同 field 形状的子字段清单；子字段可含 Relation。
```jsonc
{ "type":"SubTable","name":"明细","row":3,"size":12,"child_fields":[
    { "type":"Relation","name":"产品","relation":{"worksheet":"产品"},"size":6 },
    { "type":"Number",  "name":"数量","size":3 },
    { "type":"Currency","name":"单价","decimals":2,"size":3 } ] }
```
> 父表对子表列的 Rollup：用父表的 `Rollup` 字段，`via` 指向该 SubTable 字段名、`field` 指向子字段名。

## 共享选项集（顶层 `optionsets`）

被多个字段共用的选项，定义一次、字段用 `optionset` 引用（在 worksheets 之前建）：
```jsonc
"optionsets": [
  { "name":"单据状态","enable_color":true,"options":[
      {"value":"草稿","color":"#bdbdbd"}, {"value":"已提交","color":"#2196f3"},
      {"value":"已完成","color":"#4caf50"} ] } ]
```
`enable_color`(默认 true)、`enable_score`(默认 false，开则选项可带 `score`)、选项 `value`(不可重复)/`index`/`color`/`score`。

## 通用筛选器 `$defs/filter`（汇总/视图/图表/动作启用条件复用）

数组，每个元素是一个**条件**或一个**条件组**。条件：`{field, op, value/values, date_range, min/max, join}`：
- `field`=字段逻辑名；`op`∈eq/ne/is/in/notin/contains/notcontains/startswith/endswith/isempty/isnotempty/gt/ge/lt/le/between/notbetween/date_is/date_is_not/date_gt/date_ge/date_lt/date_le/date_between/date_not_between。
- **「是其中之一」**：用 `op:"eq"` + `values:[...]`，或直接 `op:"in"`（等价别名，自动转 eq+values）；`notin`=不在其中(=ne+values)；`is` 是 eq 的别名。
- **选项字段（单选/多选/下拉）填选项的【显示名】**，执行期自动转 key 进 values——不要填 key。
- **关联/成员/部门/角色字段填记录或成员的 id**（eq/ne 自动转 RCEq/RCNe）。
- 日期用 `date_range`（today/this_week/this_month/last_30_days…，custom 时配 min/max）。
- `join`∈and(默认)/or，与其它条件的组合方式。
- **条件组**（嵌套 (A且B) 或 (C且D)）：用 `{ "join":"or", "group_join":"and", "conditions":[ {…}, {…} ] }`，组内按 `group_join` 连接、本组与外层按 `join` 连接（映射 HAP isGroup/groupFilters）。

> ⚠️ 这是【通用筛选器】（视图/图表/动作启用条件/汇总复用），与【工作流条件 wfCondition】是**两套规则**：通用筛选器用 `eq+values`/`in`、对象是数组+可嵌条件组；工作流条件用 `{logic,items}` 且 op 含 `in/not_in/gte/lte`。**不要混用**。
