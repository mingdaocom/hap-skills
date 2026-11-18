# HAP 视图领域规范

本规范完整保留既有视图构造规则，供创建与修改场景共用。视图属于工作表；任何创建或修订都必须基于工作表的真实字段结构和真实视图 ID。

以下视角、快捷筛选、着色与顺序建议用于新建或已授权的整体设计；局部修订只应用涉及属性的规则，保留其他现有配置，不按完整设计清单补写无关属性。

## 一、对象定位与字段引用

- `worksheet_id` 必须使用真实工作表 ID，不使用工作表名称或别名。
- 修改、删除或排序使用已确认的真实 viewId；缺少身份、覆盖所需当前配置或删除影响证据时才定向读取，不根据名称猜测 ID，也不为已有可信 ID 重复定位。
- `config`、`sort`、`quickFilters`、`filterList`、`group`、`tableFields`、`card`、`color` 中的字段通常可使用真实字段 ID 或 alias，优先使用稳定且非空的 alias。
- `filter` / `enableWhen` 条件中的 `field` 必须使用真实字段 ID，不使用字段显示名或虚构 alias。
- 从 Markdown 结构提取 ID 时必须移除 `(isTitle)` 等说明后缀。
- 自定义动作只能引用已经存在的真实 actionId，不能使用动作名称代替。

创建或修改时可使用的视图主体字段包括：

```json
{
  "name": "我的待办",
  "type": "table",
  "config": {},
  "filter": {},
  "sort": [],
  "color": { "fieldId": "biz_status" },
  "quickFilters": [
    { "fieldId": "biz_owner" },
    { "fieldId": "biz_priority", "selectionType": "multiple", "displayType": "dropdown" }
  ],
  "hiddenFields": [],
  "tableFields": ["biz_name", "biz_status", "biz_owner"],
  "filterList": { "filterField": "biz_category" },
  "card": {},
  "actions": {},
  "group": { "groupField": "biz_department" }
}
```

只配置当前视图需要的字段，不用空对象覆盖已有有效配置。

## 二、九类视图

| type | 适用场景 | 关键配置 |
|---|---|---|
| `table` | 明细浏览、快速判断、批量处理 | 重点设置 `tableFields`；按需设置 `filterList`、`quickFilters`、`group` |
| `kanban` | 流程推进、状态流转 | `config.groupField` 使用业务阶段或状态字段；应设置 `card` |
| `gallery` | 图片化、卡片化浏览 | 应设置 `card`，有展示性附件时设置封面 |
| `calendar` | 预约、排期、日程 | `config.dates=[{startField,endField}]`；优先业务排期字段，不优先创建/更新时间 |
| `gantt` | 项目计划、任务排期 | `config.startField`、`config.endField` |
| `hierarchy` | 上下级、父子结构 | `config.relationField` 必须是真正表示层级关系的 Relation 字段；应设置 `card` |
| `resource` | 排班、人员或资源占用 | `config.startField`、`config.endField`、`config.resourceField` |
| `map` | 网点、客户或资产位置 | `config.locationField` 必须是定位字段 |
| `detail` | 参数配置、单记录或主从详情 | `config.mode` 必填，取 `all` 或 `first`；应设置 `card` |

补充规则：

- `detail.config.mode="first"` 只用于参数配置页或确定只有一条记录的场景，普通业务数据使用 `all`。
- `calendar` 可以设置 card，供 hover 展示摘要。
- 修改视图 type 时必须同时提供新类型所需的完整 config；缺少关键字段时不强行换型。

## 三、视图顺序

默认按以下业务优先级组织视图：

1. 主工作入口视图；
2. 待处理 / 高频操作视图，如“我的待办”“待审批”；
3. 核心业务推进视图，如状态看板、项目甘特图；
4. 重要浏览辅助视图，如画廊、日历、地图；
5. 管理分析视图，如按部门分组、按月统计；
6. “全部”类兜底管理视图；
7. 归档 / 取消 / 日志等低频视图。

当 Gallery、Kanban、Calendar、Gantt、Map 本身承担主工作入口时应直接排第一，例如“可借图书”“任务看板”“本周排班”“项目排期”“网点地图”。

应用修订中新建视图时，位置安排属于创建目标：用户明确位置优先，未指定时按上述业务优先级结合现有视图用途确定插入位置，不默认追加末尾。只插入本次新增视图，保留其他已有视图的相对顺序；整套重排需属于已授权范围。优先使用 `create_view` 顶层的 `beforeId`，以本表已有的真实 viewId 为锚点，将本次新建视图组插到该视图之前；此参数作用于整批 views，不是每个视图的独立位置。省略会追加末尾，仅在末尾就是目标位置时省略。只有单次插入无法表达目标顺序，或本次还涉及已授权的既有视图排序时，才在创建成功后使用真实 viewId 数组合并排序，保留全部其他视图。创建结果已足以确认位置满足时不再调用排序接口；结果不明确时定向核实，不重复创建。局部修改不涉及位置时保持原顺序。

## 四、filter 默认筛选

视图名称或用途暗示数据子集时必须设置 filter，例如：

- 状态类：可借、待处理、进行中、已完成、逾期；
- 归属类：我的、本部门；
- 时间类：今日、本周、本月。

如果名称暗示子集却没有 filter，视图会显示全部数据，语义与结果不一致。

### 4.1 条件树结构

- 根节点必须是 `group`，即使只有一个条件也不能直接传 `condition`。
- group 必须有 `logic: "AND" | "OR"` 与 `children`。
- 最多两层 group，即 `group -> group -> condition`。
- 同一个 group 的 children 必须全是 group 或全是 condition，不能混合。
- 条件 `field` 必须使用真实字段 ID。

```json
{
  "type": "group",
  "logic": "AND",
  "children": [
    { "type": "condition", "field": "6a22a6c0912a77961c8e09ab", "operator": "eq", "value": ["进行中"] }
  ]
}
```

同一字段匹配多个互斥值时，使用一个 `in` condition 加数组，不得拆成多个 condition 后用 AND 连接：

```json
{
  "type": "group",
  "logic": "AND",
  "children": [
    { "type": "condition", "field": "6a22a6c0912a77961c8e09ab", "operator": "in", "value": ["在借中", "已超期"] }
  ]
}
```

### 4.2 运算符和值

- 比较：`eq`、`ne`、`gt`、`ge`、`lt`、`le`。
- 集合：`in`、`notin`。
- 包含：`contains`、`notcontains`、`concurrent`。
- 归属：`belongsto`、`notbelongsto`。
- 前后缀：`startswith`、`notstartswith`、`endswith`、`notendswith`。
- 区间：`between`、`notbetween`。
- 空值：`isempty`、`isnotempty`，不传 value。

`between`、`in`、`contains`、`concurrent`、`belongsto` 等多值运算符传数组。视图 filter 的单选、多选字段必须传 option key 数组；关联记录使用真实 record_id；Collaborator、Department、Role 使用实体 ID。

日期筛选按当前 MCP 工具定义构造，保留用户要求的时间语义：

- 视图动态值可直接传给 `eq/lt/gt/le/ge`。
- 支持今天等固定关键字、自然周/月/季/年及 `last<N><单位>` / `next<N><单位>`；N 为正整数，不限于预置的 7/14/30。相对单位支持 `Day/Month/Quarter/Year/Hour/Minute`，例如 `next10Day`、`last2Quarter`、`last10Minute`；小时、分钟有前端配置，回显问题不作为禁用依据。
- 区分动态范围与比较端点：`eq + next10Day` 表示未来 10 天范围，`lt + last7Day` 表示早于 7 天前。持续滚动的筛选保持动态表达，不换算为执行当天的固定日期，也不把“过去”改作“未来”。
- 不使用 `last<N>Week/next<N>Week`；相对 N 周换算为 `N × 7` 天，自然周使用 `thisWeek/lastWeek/nextWeek`。
- 日期 `between/notbetween` 使用两个具体日期，不传动态值数组或猜测 `today+7`；需要组合动态上下界时，在同一 AND 组内并列比较条件，保持已定义的包含/排除边界。

Collaborator 当前用户筛选使用 `eq` 加 `user-self`。成员条件还可按工具契约使用 `user-sub`、`user-workflow`、`user-api`。

## 五、quickFilters、filterList 与 group

三者之间默认避免重复使用同一个字段，以保持页面整洁。**但当用户指令或修订任务明确指定特定筛选字段（例如要求“按单据状态分组，并配置状态与经办人快捷筛选”）时，用户明确要求具有最高优先级**，应严格按任务要求配置，不视为冲突。

### 5.1 quickFilters 快捷筛选栏

- 每个视图都应提供快捷筛选；字段条件不足时不凑数。
- 通常选择 2～4 个高频筛选字段，优先考虑状态、负责人、优先级、分类、部门、日期。
- 字段必须真实存在，避免低频备注、长文本和系统字段。
- 每项结构为 `{ "fieldId": "<alias 或 ID>" }`。选项字段（fieldType 9、10、11）还可设置 `selectionType: "single" | "multiple"` 与 `displayType: "dropdown" | "tile"`。

### 5.2 filterList 左侧分类导航

filterList 使用 `{ "filterField": "<alias 或 ID>" }`，用于在左侧列出字段的枚举值，用户一次查看一个分类。

“全部”类 table 视图没有预设 filter 时必须设置 filterList，按以下顺序选择最具业务区分度的字段：

1. 业务分类 / 类型字段；
2. 选项值不少于 5 个的状态 / 阶段字段；
3. 关联分类表、部门表等字典 Relation 字段。

### 5.3 group 页面分组

group 使用 `{ "groupField": "<alias 或 ID>" }`，适用于 table、gallery、kanban，用于同时展示所有分组。当 table 视图的核心用途是按人或按类对比工作量、进度时必须设置，例如按负责人查看任务量、按部门查看待办。

- 分组字段的枚举值不超过 10，避免页面过长。
- 不使用文本类字段分组。
- filterList 一次只看一个分类，group 同时看所有分组；两者可以共存，但不能使用同一字段。

## 六、字段显示、排序与隐藏

### 6.1 tableFields

围绕“快速扫读、判断、跟进、批量处理”组织 table 列顺序：

1. 主标题字段；
2. 状态 / 阶段；
3. 负责人；
4. 关键日期；
5. 关键业务字段；
6. 辅助信息。

不优先展示长文本、低频备注、系统字段或冗余字段。

### 6.2 sort

sort 是有先后优先级的数组，每项使用真实字段引用与排序方向：

```json
[
  { "fieldId": "biz_priority", "sortType": 1 },
  { "fieldId": "biz_due_date", "sortType": 2 }
]
```

`sortType=1` 表示升序，`sortType=2` 表示降序；不要用自然语言代替数值。修改排序时数组整体替换，应先读取并保留仍需要的排序项。

### 6.3 hiddenFields

hiddenFields 只隐藏当前视图不需要展示的真实字段，不等同于删除字段。修改时传入的数组会整体替换旧数组，不能只发送“新增隐藏”的那一项。

## 七、card 记录卡片

card 在不同视图中的用途：

- `gallery` / `kanban` / `hierarchy`：主区域记录卡片；
- `detail`：左侧记录列表摘要；
- `calendar` / `map` / `resource` / `gantt`：hover 摘要。

可配置：

- `titleField`：最能识别记录的主标题字段，使用 card 时必传；
- `summaryField`：描述性文本，可选；
- `displayFields`：1～4 个便于快速判断的关键字段，detail / hierarchy 建议 1～2 个；
- `coverField`：展示图片或文档的附件字段；
- `coverDirection`：`top` / `left` / `right`；
- `coverDisplayMode`：`full` / `square` / `circle`。

封面规则：

- 专门用于文档或图片展示的视图必须设置封面；其他视图只在封面能增强识别时设置。
- gallery 优先 `top + full`；人员类优先 `top + circle`；文档类优先 `top + full`。
- 其他视图优先 `right + square`；人员类优先 `left + circle`；文档类优先 `left + square`。

## 八、actions 操作按钮

视图提供三个动作入口：

- `detailActions`：打开记录详情后右上角的自定义动作，值为真实 actionId 数组；
- `quickActions`：表格行或卡片上直接显示的快捷动作；
- `batchActions`：多选记录后的批量操作，值为本工作表真实 actionId 数组，按数组顺序展示。非空绑定仅支持 `table`，以及 `config.layout: treeTable` 的 `hierarchy` 视图。

quickActions 条目：

```json
[
  { "type": "copy" },
  { "type": "print" },
  { "type": "delete" },
  { "type": "share" },
  { "type": "action", "id": "<真实 actionId>" }
]
```

使用规则：

- 自定义动作创建成功并取得 actionId 后才能被视图引用。
- 单/多数据源动作均可挂载详情、行内或适用视图的批量入口；数据源决定逐条触发还是集合处理，遵循 `hap-domain-custom-action-spec`，不由入口位置推断。不为挂载批量按钮擅自改变现有视图类型。
- 自定义动作不会自动出现在详情页，必须加入 detailActions 才能从该入口使用。
- quickActions 建议不超过 3 个，只放最高频动作。
- `copy`、`print`、`delete`、`share` 是系统动作，不需要先创建。
- 不是所有视图都需要 quickActions；detail、hierarchy 视图不设置 quickActions。
- 修改或删除动作仅处理已知且需要调整的视图入口，不固定扫描所有调用方。`actions.detailActions`、`actions.quickActions`、`actions.batchActions` 传入时各自整体替换，基于完整数组保留其他按钮；省略的子属性保持原值。`batchActions: []` 仅清除视图专属绑定，工作表设置中的全视图可见动作仍可能显示，不将清空数组视为全局停用。

## 九、color 记录着色

color 使用 `{ "fieldId": "<alias 或 ID>" }` 指定 SingleSelect 字段，以字段选项颜色为记录着色，帮助用户快速区分状态或类型。

- 工作表存在表示状态、阶段或优先级的 SingleSelect 字段时，table 和 kanban 视图通常应设置 color。
- **Kanban 视图着色规则**：当 Kanban 视图本身已使用状态字段进行分列分组（`config.groupField`）时，卡片着色既可使用该状态字段，亦可灵活选用其他分类/类型字段（如“报损类型”）增强区分度，或直接继承已有配置；**一旦选定即单次提交，严禁在不同选项字段间来回修改纠结**。
- 只支持 SingleSelect 字段（fieldType 9 或 11），且该字段已开启选项标签颜色。
- 每个视图只能指定一个着色字段。

## 十、创建、修改、排序与删除边界

- `create_view` 是纯创建操作；同名视图不会自动覆盖，重复调用会产生重复视图。同批次创建多个视图时合并在单次调用中提交。
- `update_view` 使用 `worksheet_id + view_id` 定位单个视图。**平台接口已支持完整落库，修改时必须一次性组装该视图的完整目标配置单次提交，严禁按单个属性拆分多次调用**。未传字段保持原值；数组字段整体替换。
- 修改视图时优先按单次完整提交，返回 `success: true` 即视为成功，严禁无依据“改一个属性查一次”形成微震荡。
- `sort_views` 的 viewIds 数组表示最终顺序，必须使用当前工作表的真实 viewId，并保留所有仍存在的视图。
- delete_view 使用支持回收站的标准入口，删除后至少保留一个可用视图；修订授权遵循 hap-revision-safety。
- 只需调整名称、筛选或展示字段时使用 update，不通过“删除再新建”代替修改。

## 十一、提交前自检

1. worksheet_id、view_id、字段 ID / alias 与 actionId 是否真实？
2. view type 与必需 config 是否匹配？
3. 名称暗示的数据子集是否有正确 filter？
4. quickFilters、filterList、group 是否字段互斥且符合用途？
5. tableFields、card、actions、color 是否保留旧规范中的可用性要求？
6. PATCH 是否只改变需求影响字段，数组是否完整保留未变项？
7. 排序是否包含所有仍存在的视图，删除是否完成影响检查？
