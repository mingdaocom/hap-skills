# Views — 视图（9 种）

视图写在顶层 `views[]`，按 `worksheet` 逻辑名归属。类型专属参数一律按**字段逻辑名**引用，执行期解析为 controlId。

```jsonc
{ "worksheet":"出库单", "name":"按状态看板", "view_type":"kanban", "group_by":"状态",
  "card":{ "title":"单据编号", "display_fields":["客户","总金额","状态"] } }
```

通用键：`worksheet`(必填)、`name`(同表唯一)、`view_type`(必填)、`filter`(通用筛选器，行筛选)、`filter_list`(左侧分类导航字段名列表)。

## 9 种类型与专属参数

| view_type | 说明 | 必填 / 专属参数 |
| :-- | :-- | :-- |
| `table` | 表格（用于明细浏览、快速判断、批量处理，默认自动创建1个，） | `group_by`(可选，按列分组) |
| `kanban` | 看板（适合流程推进、状态流转场景） | **`group_by` 必填**（单选/关联字段，分列，优先采用业务阶段、状态字段）；**`card` 必填且 `card.display_fields` 至少 1 个**（否则卡片是空的）；可选 `cover` |
| `gallery` | 画廊（适合图片化、卡片化浏览） | **`cover` 必填**（附件字段）；`cover_direction`(top/left/right)、`cover_display`(full/fill)、`card` |
| `calendar` | 日历 | `dates`: `[{start, end?}]`（日期字段名，end 可省，优先采用业务排期字段，不优先采用创建/更新时间） |
| `gantt` | 甘特图（适合项目计划、任务排期场景） | **`start_date` + `end_date` 必填**（日期字段名） |
| `hierarchy` | 层级 | **`hierarchy_field` 必填**；`hierarchy_type`(self 自关联 / multi 多表层级) |
| `detail` | 详情 | `detail_mode`(all 全部 / first 仅第一条，用于参数配置页、单记录场景) |
| `resource` | 资源（适合排班、资源占用场景） | `resource_field`(资源泳道字段，成员/部门)、`start_date`、`end_date` |
| `map` | 地图 | **`location` 必填**（定位字段名） |

## card（gallery / kanban 卡片摘要）

```jsonc
"card": { "title":"标题字段名", "summary":"摘要字段名",
          "display_fields":["字段A","字段B"], "show_field_names":true }
```

- **`display_fields` 必填、至少 1 个**字段逻辑名——卡片视图据此决定每张卡显示哪些字段，不配就是一张空卡。
- **看板(kanban) 必须带 `card`**（连同 `group_by`）；画廊(gallery) 若用 `card` 也同样要求 `display_fields`。`title`/`summary` 可选。
- `show_field_names`（可选，默认 `true`）：卡片上每个展示字段前是否带「字段名称」。默认打开更易读；设 `false` 只显示值。

## 例子

```jsonc
"views": [
  { "worksheet":"出库单","name":"出库看板","view_type":"kanban","group_by":"状态",
    "card":{"title":"单据编号","display_fields":["客户","总金额"]} },
  { "worksheet":"出库单","name":"出库日历","view_type":"calendar","dates":[{"start":"单据日期"}] },
  { "worksheet":"物料","name":"物料画廊","view_type":"gallery","cover":"图片","cover_display":"fill" },
  { "worksheet":"组织架构","name":"层级","view_type":"hierarchy","hierarchy_field":"上级","hierarchy_type":"self" },
  { "worksheet":"门店","name":"门店地图","view_type":"map","location":"位置" }
]
```

## 增强配置

### filter（视图默认筛选）

**视图名称暗示数据子集时，必须设置 `filter`**。常见关键词：

- 状态类：可借 / 待处理 / 进行中 / 已完成 / 逾期
- 归属类：我的 / 本部门
- 时间类：本月 / 本周

> ⚠️ 如果视图名称含上述关键词却不设 filter，视图将显示全部数据，**与名称语义不符**。
> 视图的行筛选 `filter` 用通用筛选器（见 worksheets-and-fields.md「通用筛选器」）：选项字段填显示名、关联/成员填 id、日期用 date_range。

### 无 filter 的 table 视图 = 工作表自带的"全部"视图（自动收养）

每个工作表创建时平台自带一个名为"全部"的表格视图。design 里**无 `filter` 的 table 视图**不会新建视图，而是把这个自带视图**就地改造**（重命名为你的 `name` + 应用 `filter_list`/`group_by` 等属性），不会产生重复的"全部"视图。因此：

- 每个工作表**最多设计一个**无 filter 的 table 视图（校验会拦截第二个）；
- 想配置"全部"视图（比如加 `filter_list`），就照常声明一个无 filter 的 table 视图即可，名字随意（如"全部需求"）。

### filter_list（左侧分类导航）

在视图左侧栏列出指定字段的所有枚举值，用户点击某一值后，视图只展示该值对应的数据子集。是用户切换数据子集最直观的入口。

> ⚠️ **必须设置 `filter_list` 的场景**：当 table 视图为"全部"类视图（无 filter 预设筛选），且工作表存在选项值 ≥ 5 的 SingleSelect 字段或指向分类/字典表的 Relation 字段时，**必须**选取最具业务区分度的字段设为 `filter_list`。

字段选取优先级：

1. 业务分类/类型字段（如客户类型、图书分类、商品品类）
2. 状态/阶段字段（选项值 ≥ 5 时）
3. 关联字典表的 Relation 字段（如关联分类表、关联部门表）

### group_by（分组）

按指定字段值在同一页面内分段展示，用户无需切换即可对比不同分组的数据。

> ⚠️ **必须设置 `group_by` 的场景**：当 table 视图的核心用途是"按人/按类对比工作量或进度"时（如按负责人查看各自任务量、按部门查看待办），**必须**设置 `group_by`。

约束条件：

- 分组字段的枚举值数量不超过 10，否则页面过长反而难用
- 不能使用文本类字段作为分组字段
- 不能与 `filter_list` 使用同一字段

> `filter_list` 与 `group_by` 的区别：`filter_list` 同一时刻只看一个分类；`group_by` 同一时刻可以看到所有分组。两者可同时存在。

### actions（把自定义动作按钮外露在视图里）

把本表的自定义动作按钮放到视图的**行操作列**，用户在列表里就能点（无需进详情）。值为本表 `custom_actions` 的动作**逻辑名**列表：

```jsonc
{ "worksheet":"借阅记录", "name":"待归还", "view_type":"table",
  "filter":[ {"field":"状态","op":"eq","value":"借出中"} ],
  "actions":["归还","续借"] }     // 「归还」「续借」按钮直接出现在每行
```

- 动作必须**挂在本视图所属工作表上**、且已在 `custom_actions` 中定义（执行期解析为 btnId）。`validate` 会在合并后检查：`actions` 里的名字必须是该工作表已定义的 `custom_action`。
- 适合把高频的行级操作（归还/审批/标记完成）直接放在列表里，减少点击。
> **拆分生成时**：视图分片（02）与自定义动作分片（04）由不同子代理并行产出，所以 `actions` 引用的动作名**必须严格用地基锁定的「自定义动作清单」里的名字**，否则合并校验会报「custom action … not defined」。
> 自定义动作的定义见 [custom-actions.md](custom-actions.md)。

