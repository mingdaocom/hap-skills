# Layout — 表单 12 栅格 + 页面 48 栅格（排版是硬要求）

design 不只是字段清单，更是**表单与页面的版面**。每次生成或修改 design，都把整张表单、整个页面当一个版面来排，
可以也应该按业务需要整体重排。**绝不允许**把新字段/新组件随手丢到最前或最后、不给位置属性就完事。

## 工作表表单布局（12 栅格）

design 不只是字段清单，更是表单版面。每次生成/修改都把整张表单当一个版面来排，**每个字段都给 `size` 和 `row`**。

### `size` 只能是 3 / 6 / 12（禁用 4、8）

- 1 个字段独占一行 → `size: 12`
- 2 个字段同行 → 各 `size: 6`
- 4 个字段同行 → 各 `size: 3`
- ❌ **不允许一行 3 个字段**（那需要 size:4，schema 的 size 枚举只有 3/6/12，校验会拦）

### HAP 是流式布局——光给 `size` 不够，要并排的字段必须在数组里【连续相邻】

> [!CAUTION]
> 字段按 `fields` 数组顺序从左到右排：**相邻**字段的 `size` 之和 ≤ 12 就并排在同一行，超过 12 自动换行。
> **所以要并排的字段必须在数组中【连续相邻】，并给它们相同的 `row`、且 `size` 之和 ≤ 12。**
> 两个 `size:6` 之间若插入了别的字段，它们就不会在同一行。

`row` 从 0 起，按业务分组成行：标题/编号在最上，关键业务字段靠前，明细子表/汇总/附件靠后。
同一 `row` 内各字段 `size` 之和必须 ≤ 12。普通字段**要么整表都给 `row`+`size`，要么都只给 `size` 走自动拼行**——不要只给一部分。

### 强制整行（`size: 12`）的类型

`Divider`（分段）、`RichText`（富文本）、长文本、`Attachment`（附件）、`SubTable`（子表）、`Location`（定位），
以及 **`Relation` 用 `table` / `tab_table` 显示时**。

> `Relation` 用 `dropdown` / `card` 显示时可与别的字段并排：`dropdown` 建议 `size: 3/6`，`card` 建议 `size: 6/12`。

### 语义成组（同行怎么分）

- **紧凑字段**（`Dropdown`、`Number`、`Currency`、`Date`、`PhoneNumber`、`Email`、`AutoNumber` 等）**优先 4 个一行**（各 `size:3`）；
  仅当语义上天然成对时才 2 个一行（各 `size:6`）。
- `size:3`（优先，四个一行）示例：
  - 数量 + 单价 + 金额 + 折扣率
  - 联系电话 + 邮箱 + 入库日期 + 编号
  - 关联分类(dropdown) + 页数 + 价格 + 入库日期
- `size:6`（语义成对或非紧凑字段）示例：
  - 开始时间 + 结束时间
  - 状态 + 优先级
  - 负责人 + 所属部门
  - 计划日期 + 实际日期

正例（节选；row 0 四个紧凑字段并排，关联用 dropdown 与成员并排，子表/附件整行）：

```jsonc
"fields": [
  { "type":"AutoNumber","name":"出库单号","is_title":true,"row":0,"size":3,"auto_number":{"prefix":"CK-","date_format":"YYYYMMDD","digits":4} },
  { "type":"Date","name":"单据日期","row":0,"size":3 },
  { "type":"SingleSelect","name":"状态","options":["未提交","审批中","已完成"],"row":0,"size":3 },
  { "type":"SingleSelect","name":"优先级","options":["普通","加急","特急"],"row":0,"size":3 },
  { "type":"Relation","name":"客户","relation":{"worksheet":"客户","display":"dropdown"},"row":1,"size":6 },
  { "type":"Collaborator","name":"经办人","row":1,"size":6 },
  { "type":"Divider","name":"出库明细","row":2,"size":12 },
  { "type":"SubTable","name":"明细","child_fields":[ ... ],"row":3,"size":12 },
  { "type":"Rollup","name":"总金额","rollup":{ ... },"row":4,"size":6 },
  { "type":"Rollup","name":"总数量","rollup":{ ... },"row":4,"size":6 },
  { "type":"Attachment","name":"附件","row":5,"size":12 }
]
```

反例：一行放 3 个字段（需 size:4，禁用）；两个要并排的 `size:6` 之间插了别的字段（不会同行）；
附件/子表给 `size:6`（必须 12）；只给一部分字段 `row`。

> 修改即整体重排：插入字段要顺带调周围字段的 `row`/`size`，让整张表单仍紧凑、不留空洞、不重叠。

## 自定义页面布局（48 栅格）

所有组件基于 48 列栅格，`x + w ≤ 48`。

| 组件类型 | 推荐宽度 | 推荐高度 |
|---|---|---|
| `number` 图表 | 4 张一行 w=12；6 张一行 w=8（紧凑） | 标准 h=8，紧凑 h=6 |
| 分析图表（趋势/分布/对比） | 半宽 w=24 或通栏 w=48 | 推荐高度 h=12 |
| 透视表 | 固定通栏 w=48 | 推荐高度 h=12 |
| `button` | w=48（通栏铺满即可） | 固定高度 h=6 |r
| `view` | 通栏 w=48 或半宽 w=24 | 推荐高度 h=20~24 |
| `rich_text` | 半宽 w=24 或通栏 w=48 | 推荐高度 h=8~12 |

布局原则：

- 优先追求可读性和视觉平衡，不机械套坐标
- **每个组件都给 `layout {x, y, w, h}`**，不要依赖自动堆叠。`x∈[0,47]`、`w∈[2,48]`、`x+w≤48`、`y≥0`、`h≥2`。
- 版面规划：
  KPI 数值卡一行（同宽、同高，如 4 个各 `w:12` 铺满 48）；
  图表两两一行（如 2 个各 `w:24`），趋势图优先放分析区左侧或上方，信息量大的图表/视图可用通栏，不强制半宽；
  按钮区/视图按需。**同一行各组件不重叠；下一行 `y` = 上一行 `y + h`**。
- **修改即重排整页**：加一个图表，重排所有 x/y/w/h 让整页仍对齐、无重叠、无大块空白。

正例（一个看板的 components 节选）：

```jsonc
"components": [
  { "type": "chart", "name":"今日入库","chart": {"report_type":"number", ...}, "layout": {"x":0,  "y":0, "w":12, "h":8} },
  { "type": "chart", "name":"今日出库","chart": {"report_type":"number", ...}, "layout": {"x":12, "y":0, "w":12, "h":8} },
  { "type": "chart", "name":"库存预警","chart": {"report_type":"number", ...}, "layout": {"x":24, "y":0, "w":12, "h":8} },
  { "type": "chart", "name":"待出库存","chart": {"report_type":"number", ...}, "layout": {"x":36, "y":0, "w":12, "h":8} },
  { "type": "chart", "name":"出入库趋势","chart": {"report_type":"line", ...}, "layout": {"x":0,  "y":8,"w":24, "h":12} },
  { "type": "chart", "name":"物料占比",  "chart": {"report_type":"pie",  ...}, "layout": {"x":24, "y":8,"w":24, "h":12} }
]
```

> 看板里有「全局筛选条」(`type:filter`) 时，把它放在被它联动的图表**之前**（顶部），但执行器会自动延后构建——
> 见 [custom-pages.md](custom-pages.md) 的 filter 小节。
