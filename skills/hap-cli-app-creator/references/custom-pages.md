# Custom Pages — 自定义页面 / 统计看板（顶层 `custom_pages[]`）

## 统计数据源选择规则

**不能把维度表作为统计数据源，必须用事实表**

- **事实表**：借阅记录、订单、工单、销售流水、考勤记录…… 每行代表一次业务事件
- **维度表**：图书分类、商品类目、员工档案、客户档案、部门表…… 每行代表一个实体

正确做法：在事实表上，以分类字段（Relation 字段或单选字段）作为维度分组，对事实行计数或求和。

| 分析目标 | ✅ 正确数据源 | ❌ 错误数据源 |
|---|---|---|
| 各分类借阅占比 | 借阅记录表（按分类字段分组） | 图书分类表 |
| 各客户订单量 | 订单表（按客户字段分组） | 客户档案表 |
| 各部门工单数 | 工单表（按部门字段分组） | 部门表 |

## 页面生成规范

### 一、页面结构

根据页面功能不同，采用不同的页面组织方式。

#### Dashboard（仪表盘）

页面按「分段 + 统计」方式组织，阅读顺序：核心指标 → 分析图表。

推荐结构：
```
numberChart × 3~6    ← KPI 区
lineChart / columnChart / barChart / pieChart / rankingChart ...  ← 分析区
```

- 必须同时包含 KPI（3~6 个）和分析图表（2~4 个）
- KPI 必须在分析图表之前

#### Workspace（工作台）

页面按「快捷入口 + 业务列表」方式组织。

推荐结构：
```
rich_text        ← 辅助说明
button（一组 4~6 个快捷按钮）  ← 快捷入口区
view × 1～3                 ← 列表视图区
```

- 顶部使用 `rich_text` 进行操作说明
- 中部使用 `button` 组件组提供快捷操作入口
- 下方使用 `view` 组件嵌入需要高频处理的列表视图

### 二、组件与图表约束

#### 指标与维度

- 大多数图表建议 1~2 个指标
- 多指标分析优先用 `dual_axis` 或 `pivot` 图表
- 趋势分析必须使用时间维度（date_grain 按月或按日）

#### 图表类型搭配

| 分析目的 | 优先使用 |
|---|---|
| KPI 数值 | `number` |
| 趋势变化 | `line` |
| 双轴对比 | `dual_axes` |
| 分类对比 | `bidirectional_bar`、`bar` |
| 占比分布 | `pie` |
| TopN 排名 | `ranking`（设 limit） |
| 多维交叉 | `pivot` |
| 地理分布 | `region_map`、`world_map`（**仅当存在地区字段时**）|

- 页面应包含不同分析目的的图表，避免整页同一类型
- 不建议大量使用理解成本高的图表，如 `radar`、`wordcloud`
- 无地区字段时**禁止**生成地图组件

## 组件参数格式

```jsonc
{ "name":"仓储看板", "section":"分析", "components":[ ... ] }   // components 省略 = 空白页
```

每个组件给 `type` + `layout{x,y,w,h}`（图表的排版布局为 48 栅格，见 [layout.md](layout.md)）+ 类型专属内容。
**仅 6 种组件有 builder**：`chart` / `view` / `rich_text` / `embed_url` / `button` / `filter`（其它如轮播图/标题区不支持）。

### chart（图表，`type:"chart"` + `chart`）

```jsonc
{ "type":"chart", "name":"出入库趋势", "layout":{...}, "chart":{
    "worksheet":"出库单", "report_type":"line",
    "dimensions":[ {"field":"单据日期","date_grain":"day"} ],   // bar/line/pie 的维度(xaxes)
    "metrics":[ {"field":"总金额","aggregate":"sum"} ],         // 值(yaxisList)
    "filter":[ ... ] } }                                       // 通用筛选器
```

- `report_type`∈ `number` / `bar` / `line` / `pie` / `pivot` / `funnel` / `radar` / `bidirectional_bar` / `ranking` /
  `scatter` / `wordcloud` / `world_map` / `dual_axes` / `gauge` / `progress` / `region_map`（全 16 种）。
  - 维度+值同构（1 个 `dimensions` + 1~2 个 `metrics`）：bar/line/pie/funnel/radar/ranking/wordcloud/world_map；
    `bidirectional_bar`/`scatter` 用 2 个 `metrics`。
  - `dual_axes`（双轴）：`dimensions` + 左轴 `metrics` + 右轴 `right_metrics`（可选 `right_type` bar/line，默认 line）。
  - `gauge`（仪表盘）/`progress`（进度）：**无维度**，`metrics` 放那个值；`progress` 用 `target`(目标字段)，`gauge` 可选 `target`/`min_field`/`max_field`。
  - `region_map`（区域地图）：`dimensions` 取一个 Region 字段，`map_level`(province/city/county)；`world_map` 取一个国家文本字段。
- 维度：bar/line/pie 用 `dimensions[]`(`field`,`date_grain` day/week/month/quarter/year,`sort`)。
- **pivot 透视**：用 `rows[]`(行) + `columns[]`(列) 代替 dimensions，`metrics[]` 为值。
- 记录数量：`metrics:[{"field":"count","aggregate":"count"}]`。
- **取前 N（TopN）**：图表级 `limit`（整数）= 只展示前 N 项，常用于 `ranking` 排行榜与 `bar` 柱图。省略=全部。
- **`ranking`（排行榜）默认就按数值排序**：自动按 `metrics` 第一项的值**降序**排列（无需手写排序）。要升序写图表级 `sort:"asc"`（默认 `desc`）；通常搭配 `limit` 取前 N。例：`{"report_type":"ranking","dimensions":[{"field":"成交门店"}],"metrics":[{"field":"订单金额","aggregate":"sum"}],"limit":10}`。
- **图表筛选 `filter`**：用**通用筛选器**——是一个**数组**（每项为条件或条件组），`op` 用 `eq`(不是 `is`)、「是其中之一」用 `eq+values` 或 `in`。`filters`(复数)是等价别名。为容错也接受单个条件/条件组对象（自动包成数组），但**推荐写数组**。正例 `"filter":[{"field":"状态","op":"eq","value":"已完成"}]`；反例 `"filters":{"field":...,"op":"is",...}`（旧写法 dict+is，虽被容错但不要这么写）。
  - **日期筛选两种写法别混**：相对区间用 `op:"date_is"` + `date_range`（如 `next_33_days`）；固定起止用 `op:"date_between"` + `min`/`max`（**不要** 给 `date_between` 配 `date_range`）。
  - **`date_range` 可选值因上下文而异**：图表 `filter`（通用筛选器）支持 `today/yesterday/tomorrow/this_week|month|quarter|year/last_*/next_week|month|quarter|year/last_7_days/last_14_days/last_30_days/next_7_days/next_14_days/next_33_days/custom`——注意「未来约一个月」是 **`next_33_days`（没有 next_30_days）**；自定义区间用 `custom`+`min`/`max`。全局筛选条（filterBar）的 `date_range` 集合更小（无 `next_*`，相对天数只有 `last_7_days/last_30_days`），需要 `next_*` 区间时请放在**图表 filter** 上而非 filterBar。

> **filter 在不同上下文的形态对照（最易写错，务必区分）**：
> | 上下文 | 形态 | op 风格 |
> | :-- | :-- | :-- |
> | 视图 / 图表 / 动作启用条件 / 汇总（通用筛选器） | **数组**（条件或条件组），键名 `filter`（图表也接受 `filters`） | `eq`/`ne`/`in`/`contains`… |
> | 工作流条件（wfCondition） | **对象** `{logic,items:[…]}` 或 `{groups:[…]}` | `eq`/`ne`/`gte`/`lte`/`in`/`not_in`… |
> | 自定义页面全局筛选条（filterBar） | **对象** `{filters:[{field,op,date_range,…}]}` | 见 filterBarItem |

### view（嵌入视图，`type:"view"` + `view`）

```jsonc
{ "type":"view","layout":{...},"view":{"worksheet":"出库单","view":"出库看板","allow_add":true,"show_search":true} }
```
- `view` 必须是该工作表**已在 `views` 里定义过的视图名**。一旦你为某表建了自定义视图，默认的「全部」视图就不存在了——**不要引用「全部」**，否则建应用时会报「view 不存在」。请引用你自己定义的视图名。

### rich_text / embed_url

```jsonc
{ "type":"rich_text","rich_text":"<h3>说明</h3>...","layout":{...} } // 不要单独作为标题使用此组件，需要格式丰富的说明时才使用
{ "type":"embed_url","embed_url":"https://...","layout":{...} }   // iframe 嵌入外部网址
```

### button（按钮组，`type:"button"` + `button`）

```jsonc
{ "type":"button","layout":{...},"button":{
    "shape":"graphic","count":3,"buttons":[
      { "label":"新建出库","action":"create_record","worksheet":"出库单","icon":"sys_1_2_order","color":"#3054EB" },
      { "label":"出库看板","action":"open_view","worksheet":"出库单","view":"出库看板" },
      { "label":"帮助","action":"open_link","url":"https://..." } ] } }
```

- 按钮 `action`∈create_record(需 worksheet) / open_view(需 worksheet+view) / open_link(需 url) / scan / call_process。**不支持跳转到其它自定义页面**（无 open_page）。
- 按逻辑名引用工作表/视图。`shape`(button 文字 / graphic 磁贴)、`count`(每行个数)、`direction`、`style` 等见 schema。
- 按钮 `color` 用应用主题色的 9 色（见 [design.md](design.md)）；`icon` 用 `hap icon search` 加多个相关关键词搜到的 `fileName`。

### filter（全局筛选条，`type:"filter"` + `filter`）

```jsonc
{ "type":"filter","layout":{"x":0,"y":0,"w":48,"h":3},"filter":{
    "enable_btn":true, "filters":[
      { "field":"单据日期","name":"日期","date_range":"this_month" },
      { "field":"状态" } ] } }
```

- 每个 `filters[].field` 按字段名**自动联动**所有「数据源工作表含同名字段」的图表；可用 `targets:[图表name...]` 显式指定。
- 最常见的就是以日期字段为筛选条件，**自动联动**所有图表，那就可以筛选所有图表在选定日期内的数据。
- 无独立端点：随页面保存内部建组并回填。**把 filter 组件放在被联动图表所在的页**（执行器自动延后到图表之后构建）。

> 完整看板正例见 [examples/warehouse/05-pages.design.json](../examples/warehouse/05-pages.design.json)（`custom_pages`）。
