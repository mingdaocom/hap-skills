# 视图（view）— 命令参考与数据字典

视图命令都挂在 `hap worksheet view <动词>` 下。机器可读输出在 `hap` 后加全局 `--json`。

> **全局规则：改复杂值前先用读命令导出现状，在真实结构上改，再写回。**

## 调用范式

### 读：list / info

```bash
# 列出工作表下的所有视图（拿 viewId / viewType / 名称）
hap --json worksheet view list 6845f0a1b2c3d4e5f6a7b8c9

# 单个视图完整配置：filters、排序、显示字段、advancedSetting 全在这里
hap --json worksheet view info 6845f0a1b2c3d4e5f6a7b8c9 64a1b2c3d4e5f60123456789
```

任何「改复杂值」的操作（filters / fastFilters / navGroup / advancedSetting 里的 JSON 串…）
都必须先 `view info` 导出现状，在真实结构上改，再写回 —— 不要凭记忆手搓整个结构。

### 创建：create

```bash
# 默认表格视图
hap worksheet view create 6845f0a1b2c3d4e5f6a7b8c9 "全部订单"

# 看板：按某个选项/关联字段分组
hap worksheet view create 6845f0a1b2c3d4e5f6a7b8c9 "按状态" \
  --view-type board --group-control ctrl_status_24hex

# 画廊：附件字段做卡片封面
hap worksheet view create 6845f0a1b2c3d4e5f6a7b8c9 "产品图册" \
  --view-type gallery --cover-control ctrl_photo_24hex --cover-type 0

# 日历 / 甘特
hap worksheet view create 6845f0a1b2c3d4e5f6a7b8c9 "排期" \
  --view-type gantt --begin-date ctrl_start_24hex --end-date ctrl_end_24hex

# 层级：单表自关联树
hap worksheet view create 6845f0a1b2c3d4e5f6a7b8c9 "任务树" \
  --view-type structure --child-type 1 --group-control ctrl_parent_24hex

# 过滤表格（每个状态一张表）
hap worksheet view create 6845f0a1b2c3d4e5f6a7b8c9 "进行中" \
  --view-type sheet --filter-json '[{"controlId":"ctrl_status_24hex","dataType":11,"spliceType":1,"filterType":2,"values":["opt_key_1"]}]'

# 一次成型整视图（分组/封面/过滤/快筛/筛选列表/行色/按钮）用 --view-spec
hap worksheet view create 6845f0a1b2c3d4e5f6a7b8c9 "总览" --view-spec '{...}'

# 其它创建期参数（advancedSetting 等）走逃生口
hap worksheet view create 6845f0a1b2c3d4e5f6a7b8c9 "紧凑表" \
  --config-json '{"advancedSetting":{"alternatecolor":"1"}}'
```

### 更新：update（局部更新，三件套）

`view update` 是**局部**更新：只有 `--edit-attrs` 列出的顶层属性会被写入，其余保持原样。

```bash
# 仅改名（最简形态，--edit-attrs 自动按 name 处理）
hap worksheet view update 6845f0a1b2c3d4e5f6a7b8c9 64a1b2c3d4e5f60123456789 \
  --name "看板（新）"

# 改 advancedSetting 子键 —— 必须三者配对：
#   --view-json 给值 + --edit-attrs 含 advancedSetting + --edit-ad-keys 列出改动子键
hap worksheet view update 6845f0a1b2c3d4e5f6a7b8c9 64a1b2c3d4e5f60123456789 \
  --view-json '{"advancedSetting":{"alternatecolor":"1","titlewrap":"1"}}' \
  --edit-attrs advancedSetting \
  --edit-ad-keys alternatecolor,titlewrap

# 改分组字段（看板分组 / 层级父字段 / 日历主时间字段都叫 viewControl）
hap worksheet view update 6845f0a1b2c3d4e5f6a7b8c9 64a1b2c3d4e5f60123456789 \
  --view-json '{"viewControl":"ctrl_owner_24hex"}' \
  --edit-attrs viewControl

# 改卡片显示字段及顺序（先 info 读出现有数组再整体替换）
hap worksheet view update 6845f0a1b2c3d4e5f6a7b8c9 64a1b2c3d4e5f60123456789 \
  --view-json '{"displayControls":["ctrl_a","ctrl_b"],"controlsSorts":["ctrl_a","ctrl_b"]}' \
  --edit-attrs displayControls,controlsSorts
```

坑位提示：

- **advancedSetting 必须配对 `--edit-ad-keys`。** 只给 `--edit-attrs advancedSetting`
  不给 `--edit-ad-keys`，等于让服务端把整个 advancedSetting 当作改动范围——
  没出现在 `--view-json` 里的其它子键可能被清掉。永远把改了哪几个子键显式列出来。
- **advancedSetting 的值全部是字符串**（布尔写 `"1"`/`"0"`，数字也写成字符串，
  JSON 结构先序列化成字符串再放进去）。写成裸数字/布尔可能不生效。
- `--edit-attrs` 之外的键即使出现在 `--view-json` 里也不会被写入；反过来，
  列进 `--edit-attrs` 却没给值的属性会被写空。两边要一致。
- `filters` / `fastFilters` / `navGroup` / `viewControls` 这类数组属性是**整体替换**，
  务必先 `view info` 读全量，在其上增删，再整体写回。

### 删除 / 复制 / 排序

```bash
hap worksheet view delete 6845f0a1b2c3d4e5f6a7b8c9 64a1b2c3d4e5f60123456789 -y

# 复制（可选给新名字）—— 复杂视图调参前先 copy 一份当沙盒
hap worksheet view copy 6845f0a1b2c3d4e5f6a7b8c9 64a1b2c3d4e5f60123456789 "看板-副本"

# 视图在导航栏的顺序 = 传入 viewId 的顺序（要列全）
hap worksheet view sort 6845f0a1b2c3d4e5f6a7b8c9 \
  64a1b2c3d4e5f60123456789 64a1b2c3d4e5f6012345678a 64a1b2c3d4e5f6012345678b
```

> 视图编辑**只走上面这些命令**——edit-spec 没有 view 类 op，写了会被 `validate` 拒绝并提示改用对应命令。视图名 → viewId 用 `hap worksheet view list` 解析。

## 数据字典

字典生成于 2026-06-10；未覆盖的键以读命令（`hap --json worksheet view info`）返回的实际结构为准。

### 1. viewType 枚举

| viewType | 名称 | 含义 |
|---|---|---|
| 0 | sheet | 表格视图 |
| 1 | board | 看板视图 |
| 2 | structure | 层级视图 |
| 3 | gallery | 画廊视图 |
| 4 | calendar | 日历视图 |
| 5 | gunter | 甘特视图 |
| 6 | detail | 详情视图 |
| 7 | resource | 资源视图 |
| 8 | map | 地图视图 |
| 21 | customize | 插件视图 |

`childType` 修饰符：详情视图 `1`=单条详情、`2`=多条列表+详情；层级视图 `1`=单表层级（自关联）、`2`=多表层级。

### 2. editAttrs — 顶层视图属性

`view update --edit-attrs` 可写的顶层属性。复杂值先读后改。

| attr | 含义 | 值形态 |
|---|---|---|
| `name` | 视图名（改名） | string |
| `advancedSetting` | 设置项字符串字典；**必须配 `--edit-ad-keys`**（见 §3） | 值全为字符串的对象 |
| `AdvancedSetting` | 服务端接受的首字母大写别名 | 同上 |
| `filters` | 视图过滤条件 | → [FilterCondition[]](../scripts/types/filter-condition.schema.json) |
| `fastFilters` | 快速筛选字段配置 | 数组 `[{controlId, dataType, spliceType, filterType, advancedSetting{…}}]`，每项的 advancedSetting 为模块专属结构，先读后改 |
| `moreSort` | 多字段排序 | → [SortItem[]](../scripts/types/sort-item.schema.json) |
| `sortCid` | 主排序字段 | controlId 字符串 |
| `sortType` | 主排序方向 | int：`1`=升序 `2`=降序 |
| `controls` | 字段配置中的隐藏字段列表（个人保存场景下＝个人隐藏列） | controlId 的数组 |
| `displayControls` | 卡片 / 移动端列表显示的字段 | controlId 的数组 |
| `showControls` | 表格显示列（`customdisplay='1'` 时生效） | controlId 的数组 |
| `ShowControls` | 大写别名（列隐藏保存路径） | 同上 |
| `controlsSorts` | 卡片字段显示顺序 | controlId 的数组 |
| `customDisplay` | 移动端使用独立显示字段列表 | boolean |
| `coverCid` | 封面图片字段 | controlId 字符串 |
| `coverType` | 封面填充方式 | int：`0`=填满 `1`=完整显示 |
| `showControlName` | 卡片上显示字段名 | boolean |
| `rowHeight` | 行高 | int：表格 `0`紧凑/`1`中等/`2`高/`3`超高；资源 `0`紧凑/`1`宽松 |
| `viewControl` | 分组/维度字段（看板分组、层级父字段、日历/地图/资源主字段） | controlId 字符串 |
| `viewControls` | 多表层级的层定义 | 数组 `[{worksheetId, controlId, …}]`，先读后改 |
| `layersName` | 多表层级各层显示名 | string 的数组 |
| `childType` | 见 §1 | int `1`\|`2` |
| `navGroup` | 筛选列表分组字段 | 最多 1 项的数组 `[{controlId, viewId?, filterType?, isAsc?}]` |
| `personal_setting` | 标志属性：与 `controls` 同传时把改动存入**个人层**而非共享视图；数据落在 `advancedSetting.personal_setting` | JSON 字符串 `{"controls":[…],"controlsSorts":[…]}` |
| `pluginId` | 插件视图绑定的插件 id | string |

> 读返回里还会出现 `pluginName` / `pluginIcon` / `pluginIconColor` / `pluginSource`
> 等插件元数据键，按读到的实际结构处理。

### 3. editAdKeys — advancedSetting 子键

`--edit-ad-keys` 可指定的子键。**所有值都是字符串**；JSON 结构需序列化为字符串。

#### 3.1 表格（sheet）

| 键 | 含义 | 值形态 | 适用 |
|---|---|---|---|
| `sheettype` | 表格交互风格 | `"0"`=经典 `"1"`=电子表格 | 表格 |
| `fastedit` | 行内直接编辑 | `"1"`=开（默认） `"0"`=关 | 表格 |
| `enablerules` | 视图内启用业务规则 | `"1"`=开（默认） `"0"`=关 | 表格 |
| `rctitlestyle` | 记录标题样式 | 枚举字符串，`"0"`=默认 | 表格 |
| `showno` | 显示行号 | `"1"`=开（默认） `"0"`=关 | 表格 |
| `showquick` | 显示记录快捷菜单（…） | `"1"`=开（默认） `"0"`=关 | 表格 |
| `showsummary` | 显示汇总行 | `"1"`=开（默认） `"0"`=关 | 表格 |
| `showvertical` | 显示纵向网格线 | `"1"`=开（默认） `"0"`=关 | 表格 |
| `alternatecolor` | 隔行换色 | `"1"`=开 `"0"`=关（默认关） | 表格 |
| `titlewrap` | 表头换行 | `"1"`=开 `"0"`=关（默认关） | 表格 |
| `liststyle` | 各列宽度/样式 | JSON 字符串 `{"time":<毫秒>,"styles":[{cid, width?, …}]}` | 表格 |
| `fixedcolumncount` | 冻结列数 | 数字字符串 | 表格 |
| `layoutupdatetime` | 布局最后保存时间戳 | epoch 毫秒字符串 | 表格 |
| `customdisplay` | `"1"`=视图用自己的列表（`showControls`）`"0"`=跟随表单布局 | `"0"`\|`"1"` | 表格 |
| `customShowControls` | `customdisplay='0'` 时暂存的自定义列清单 | controlId 的 JSON 数组（字符串） | 表格 |
| `sysids` | 跟随表单布局时可见的系统字段 | controlId 的 JSON 数组（字符串） | 表格 |
| `syssort` | 系统字段顺序 | controlId 的 JSON 数组（字符串） | 表格 |
| `personal_setting` | 用户个人的列隐藏/排序 | JSON 字符串 `{"controls":[ids],"controlsSorts":[ids]}` | 表格 |

#### 3.2 排序 / 过滤 / 刷新 / 链接参数（各类视图通用）

| 键 | 含义 | 值形态 | 适用 |
|---|---|---|---|
| `closedefsort` | 清空自定义排序后禁用默认排序 | `"0"`\|`"1"` | 全部 |
| `refreshtime` | 自动刷新间隔（秒），`"0"`=关 | 枚举字符串：`"0"`,`"30"`,`"60"`,… | 全部 |
| `urlparams` | 视图过滤可引用的 URL 参数 | 参数名字符串的 JSON 数组（每个 ≤20 字符） | 全部 |
| `clicksearch` | 快筛：`"1"`=执行查询后才显示数据 | `"0"`\|`"1"` | 配了快筛的视图 |
| `enablebtn` | 快筛：显示「查询」按钮（>3 个筛选时强制开） | `"0"`\|`"1"` | 配了快筛的视图 |
| `fastrequired` | 快筛：查询前必填开关 | `"0"`\|`"1"`\|`""` | 配了快筛的视图 |
| `requiredcids` | 快筛：必填的筛选字段 id | controlId 的 JSON 数组（字符串） | 配了快筛的视图 |
| `showhide` | 视图在导航中的可见性 | `"show"`=显示 `"hide"`=隐藏 `"hpc&sapp"`=仅 PC 隐藏 `"spc&happ"`=仅移动端隐藏 | 全部 |

#### 3.3 记录点击与自定义按钮（表格 + 卡片类）

| 键 | 含义 | 值形态 | 适用 |
|---|---|---|---|
| `clicktype` | 点记录的动作 | `"0"`=打开记录 `"1"`=打开链接 `"2"`=无 | 表格/卡片类 |
| `clickcid` | `clicktype='1'` 时使用的链接字段 | controlId 字符串 | 同上 |
| `listbtns` | 列表/行区显示的自定义按钮 | 按钮 id 的 JSON 数组（字符串） | 表格/卡片类 |
| `detailbtns` | 记录详情中按钮的顺序 | 按钮 id 的 JSON 数组（字符串） | 全部 |
| `hidebtn` | 隐藏不可用按钮 | `""`\|`"1"` | 全部 |
| `acstyle` | 按钮样式配置 | JSON 对象字符串，先读后改 | 全部 |
| `actioncolumn` | 行「操作列」配置（按钮、宽度等） | JSON 对象字符串，先读后改 | 表格、层级（表格模式） |

#### 3.4 卡片外观（看板/画廊/层级/日历/甘特/详情/地图/资源 的卡片）

| 键 | 含义 | 值形态 | 适用 |
|---|---|---|---|
| `viewtitle` | 卡片/记录标题字段 | controlId 字符串 | 卡片类、甘特标签 |
| `abstract` | 卡片摘要字段 | controlId 字符串，`""`=无 | 卡片类 |
| `maxlinenum` | 摘要最多显示行数（1–5） | 数字字符串 | 卡片类 |
| `cardwidth` | 卡片宽度 | `"1"`=小 `"2"`=中 `"3"`=大 `"4"`=超大 `"5"`=自定义 | 看板/画廊/层级 |
| `coverposition` | 封面位置 | `"2"`=上 `"1"`=左 `"0"`=右 | 卡片类 |
| `coverstyle` | 封面显示模式 | `"0"`=覆盖 `"2"`=圆形 `"3"`=矩形 | 卡片类 |
| `opencover` | 点击封面可预览 | `"1"`=允许（默认） `"2"`=不允许 | 卡片类 |
| `showcount` | 卡片默认显示字段数；不设=关 | 数字字符串 | 卡片类 |
| `emptyname` | 「未指定」看板的自定义名称 | string | 看板 |
| `navempty` | 启用「未指定」看板 | `"1"`=开 `"0"`=关 | 看板 |
| `freezenav` | 滚动时冻结第一个看板 | `"0"`\|`"1"` | 看板 |

#### 3.5 分组与筛选列表导航

`navshow`/`navfilters` 由看板分组、画廊分组、筛选列表、资源视图共用。

| 键 | 含义 | 值形态 | 适用 |
|---|---|---|---|
| `navshow` | 显示哪些分组项 | `"0"`=全部 `"1"`=有数据的项 `"2"`=指定项 `"3"`=满足筛选条件的项 | 看板/画廊分组、筛选列表、资源 |
| `navfilters` | `navshow='2'`：指定项 id/值的 JSON 数组；`navshow='3'`：→ [FilterCondition[]](../scripts/types/filter-condition.schema.json)（序列化为字符串） | JSON 字符串，形态随 navshow 变化，先读后改 | 同上 |
| `navsorts` | 分组项自定义顺序 | JSON 数组（字符串） | 看板/筛选列表 |
| `customitems` | 自定义/合并的分组项 | JSON 数组字符串，先读后改 | 看板/画廊分组 |
| `customnavs` | 筛选列表自定义导航项 | JSON 数组字符串，先读后改 | 筛选列表 |
| `navlayer` | 层级型分组字段显示的层数，`"999"`=全部 | 数字字符串 | 筛选列表 |
| `navwidth` | 筛选列表面板默认宽度 px（100–500） | 数字字符串 | 筛选列表 |
| `usenav` | 新建记录时把选中项作为默认值 | `"0"`\|`"1"` | 筛选列表 |
| `navsearchtype` | 导航搜索模式 | `"0"`=模糊 `"1"`=精确 | 筛选列表 |
| `navsearchcontrol` | 导航内搜索的字段（关联记录分组） | controlId 字符串 | 筛选列表 |
| `showallitem` | 「全部」项 | `""`=显示 `"1"`=隐藏 | 筛选列表/看板分组 |
| `allitemname` | 「全部」项的自定义名称 | string | 筛选列表/看板分组 |
| `shownullitem` | 显示「为空」项 | `"1"`=显示 | 筛选列表/看板分组 |
| `nullitemname` | 「为空」项的自定义名称 | string | 筛选列表/看板分组 |
| `appnavtype` | 移动端导航展示类型（关联/级联字段固定 `"2"`） | `"1"`\|`"2"`\|`"3"` | 筛选列表（移动端） |
| `showNextGroup` | 自动展开下一层分组（与 navshow `"2"` 搭配，`"999"`） | 数字字符串 | 筛选列表 |
| `groupsetting` | 表内分组字段配置 | JSON 数组字符串 `[{controlId,…}]`，先读后改 | 表格（分组）、看板 |
| `groupshow` | 表内分组版 `navshow` | 同 navshow 取值 | 表格分组 |
| `groupfilters` | 表内分组版 `navfilters` | 同 navfilters，先读后改 | 表格分组 |
| `groupsorts` | 表内分组版 `navsorts` | JSON 数组（字符串） | 表格分组 |
| `groupcustom` | 表内分组版 `customitems` | JSON 数组字符串，先读后改 | 表格分组 |
| `groupempty` | 显示「未分组」组 | `""`\|`"1"` | 表格分组 |
| `groupemptyname` | 「未分组」自定义名称 | string | 表格分组 |
| `groupopen` | 分组默认状态 | `"1"`=展开第一个 `"2"`=展开全部 `"3"`=收起全部 | 表格分组 |

#### 3.6 层级（structure）

| 键 | 含义 | 值形态 | 适用 |
|---|---|---|---|
| `hierarchyViewType` | 展示模式 | `"0"`=横向 `"1"`=竖向 `"2"`=混合 `"3"`=树形表格 | 层级 |
| `hierarchyViewConnectLine` | 连接线样式 | 枚举字符串 | 层级 |
| `minHierarchyLevel` | 混合模式竖向层数 | 数字字符串 | 层级 |
| `topshow` | 顶层范围 | `"0"`=全部顶层 `"3"`=满足条件的项 `"2"`=指定项 | 层级 |
| `topfilters` | `topshow='3'`：→ [FilterCondition[]](../scripts/types/filter-condition.schema.json)（序列化为字符串）；`topshow='2'`：id 的 JSON 数组 | JSON 字符串，先读后改 | 层级 |
| `defaultlayer` | 默认展开层数 | `"1"`–`"5"` | 层级 |
| `defaultlayertime` | defaultlayer 修改时间戳 | epoch 毫秒字符串 | 层级 |
| `treestyle` | 树形表格样式 | 枚举字符串，默认 `"1"` | 层级（表格模式） |

#### 3.7 日历 / 甘特 / 资源（时间类）

| 键 | 含义 | 值形态 | 适用 |
|---|---|---|---|
| `begindate` | 开始日期/时间字段 | controlId 字符串 | 日历/甘特/资源 |
| `enddate` | 结束日期/时间字段 | controlId 字符串 | 日历/甘特/资源 |
| `calendarcids` | 多组起止时间对（多事件） | JSON 字符串 `[{"begin":"<cid>","end":"<cid>"}]` | 日历 |
| `calendarType` | 默认刻度 | `"0"`=月 `"1"`=周 `"2"`=日（资源视图取值更多） | 日历、资源 |
| `calendartype` | 甘特默认刻度（注意全小写 t） | 枚举字符串 | 甘特 |
| `weekbegin` | 每周起始日 | `"1"`–`"7"` | 日历/资源 |
| `unweekday` | 隐藏的星期位，如 `"67"`=隐藏周六日；`""`=全显示 | 数字位字符串 | 日历/甘特/资源 |
| `unlunar` | 农历显示 | `"0"`=显示 `"1"`=隐藏 | 日历 |
| `hour24` | 24 小时制 | `"0"`\|`"1"` | 日历/资源 |
| `showall` | 显示全部事件/宽松行 | `"0"`\|`"1"` | 日历 |
| `showtime` | 工作时段，如 `"08:00-18:00"`；不设=全天 | `HH:mm-HH:mm` 字符串 | 日历/资源 |
| `rowHeight` | 日历行密度（advancedSetting 内变体；资源视图用顶层属性） | `"0"`=紧凑 `"1"`=宽松 | 日历 |
| `milepost` | 里程碑字段（检查项类型） | controlId 字符串 | 甘特 |
| `navtitle` | 左侧导航记录标签字段 | controlId 字符串 | 甘特 |
| `showgroupcolor` | 显示分组颜色 | `"0"`\|`"1"` | 甘特 |

#### 3.8 详情视图

| 键 | 含义 | 值形态 | 适用 |
|---|---|---|---|
| `showtitle` | 显示记录标题（地图视图复用为地点标签） | `""`=显示（默认） `"0"`=隐藏 | 详情、地图 |
| `showtoolbar` | 显示操作工具栏 | `""`=显示 `"0"`=隐藏 | 详情 |

#### 3.9 地图视图

| 键 | 含义 | 值形态 | 适用 |
|---|---|---|---|
| `maplocation` | 默认地图中心/缩放配置 | JSON 对象字符串（center、zoom…），先读后改 | 地图 |
| `tagType` | 地点标记展示类型 | 枚举字符串 | 地图 |
| `tagcolorid` | 给标记上色的选项字段 | controlId 字符串 | 地图 |

#### 3.10 记录颜色

| 键 | 含义 | 值形态 | 适用 |
|---|---|---|---|
| `colorid` | 提供记录颜色的单选/多选字段 | controlId 字符串 | 表格/看板/画廊/层级/日历/甘特 |
| `colortype` | 颜色展示方式，`"0"`=默认 | 枚举字符串 | 同上 |
| `coloritems` | 显示哪些颜色项：`""`=全部，否则指定项 | `""` 或 JSON 数组（字符串） | 同上 |

#### 3.11 移动端显示

| 键 | 含义 | 值形态 | 适用 |
|---|---|---|---|
| `appshowtype` | 移动端卡片布局类型（默认 `"0"`＝一行三列、限 3 字段） | 枚举字符串 | 表格/卡片类（移动端） |
| `checkradioid` | 移动端卡片上显示的检查项字段 | controlId 字符串 | 移动端 |
| `rowcolumns` | 移动端每行字段数 | `"1"`\|`"2"` | 移动端 |

#### 3.12 插件视图（customize）

| 键 | 含义 | 值形态 | 适用 |
|---|---|---|---|
| `environmentparams` | 传给插件的环境参数 | JSON 对象字符串（自由键值） | 插件 |
| `plugin_map` | 按字段 id 存放的插件参数值 | JSON 对象字符串 `{"<fieldId>": value}` | 插件 |
| `plugin_attachement_info` | 锁定的插件版本信息 | JSON 对象字符串，先读后改 | 插件 |

> 注意两类同名不同层的键：快筛**每个筛选项内部**的 advancedSetting（`allowscan`、
> `daterange`、`allowitem`、`direction`、`searchtype`、`searchcontrol`、`limit`、
> `defsource`、`showtype` 等）住在 `fastFilters[].advancedSetting` 里，不是视图级
> editAdKeys；`shownullitem`/`nullitemname` 在视图级（§3.5）和单个快筛项里**都**存在，
> 改之前用 `view info` 确认你要动的是哪一层。
