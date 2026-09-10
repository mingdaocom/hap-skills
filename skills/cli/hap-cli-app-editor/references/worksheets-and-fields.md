# 工作表与字段 — 命令参考与数据字典

> **全局规则：改复杂值前先用读命令导出现状，在真实结构上改，再写回。**

## 调用范式

### 工作表

```bash
# 新建（可一并铺好字段；--fields 即下文 FieldSpec 高层方言）
hap worksheet create 1f2e3d4c-5b6a-7081-92a3-b4c5d6e7f809 "客户" \
  --icon table --remark "客户主数据" \
  --fields '[{"type":"TEXT","name":"客户名称","required":true},
             {"type":"MOBILE_PHONE","name":"电话"},
             {"type":"DROP_DOWN","name":"等级","options":["VIP","普通"]}]' \
  --title-name 客户名称

# 基本信息；表单布局与视图列表可以顺带取回，不必再发两条命令
hap --json worksheet info 6845f0a1b2c3d4e5f6a7b8c9
hap --json worksheet info 6845f0a1b2c3d4e5f6a7b8c9 --with-form --with-views

# 改别名 / 描述；改侧边栏名称、图标或显示状态需要 --app-id
hap worksheet update 6845f0a1b2c3d4e5f6a7b8c9 --alias customers --desc "客户主数据"
hap worksheet update 6845f0a1b2c3d4e5f6a7b8c9 --name "客户（CRM）" \
  --app-id 1f2e3d4c-5b6a-7081-92a3-b4c5d6e7f809

# 从应用导航里隐藏（表本身照常可用、数据照常读写）
hap worksheet update 6845f0a1b2c3d4e5f6a7b8c9 --visibility hidden \
  --app-id 1f2e3d4c-5b6a-7081-92a3-b4c5d6e7f809

# 删除
hap worksheet delete 6845f0a1b2c3d4e5f6a7b8c9 --app-id 1f2e3d4c-5b6a-7081-92a3-b4c5d6e7f809 -y

# 字段清单。默认输出是高层归一形态；--raw 输出服务端原始控件（WireControl），
# 任何「读改写」操作都以 --raw 为准
hap --json worksheet fields 6845f0a1b2c3d4e5f6a7b8c9
hap --json worksheet fields 6845f0a1b2c3d4e5f6a7b8c9 --raw
```

`--visibility` 取 `visible` / `hidden` / `pc-hidden` / `mobile-hidden`。**专门用来存另一张表
子记录的那种表，通常就该设成 `hidden`**——隐藏只影响导航，不影响读写。

### 只存子表行的工作表：读它要指出父表

```bash
hap --json worksheet fields <子表工作表ID> --parent <父表工作表ID>
```

这类表**不能单独读**，不带 `--parent` 会直接报读不了。把现成的表挂成某张表的子表用
`hap worksheet mount-subtable`。

### 🚨 复制工作表：没点名的关联列会变成纯文本

```bash
hap worksheet copy <工作表ID> "客户-副本" -a <应用ID> \
  --keep-relation <关联字段ID> --keep-relation <子表字段ID>
```

`--keep-relation` 要**逐个点名**（可重复）。**没被点到的关联记录、子表、级联选择列，
在副本里会被复制成普通文本列**——数据还在，关系没了，且没有任何提示。复制前先
`worksheet fields` 把这些列的 id 列出来。

副本里的列 id 和源表一模一样是正常的：列 id 只在自己表内唯一，看到两张表出现相同
controlId 不必去「修」。

### 字段：先分清「新增」还是「改已有」

字段写入有两条路，**选错会丢字段**（尤其是双向关联自动生成的反向控件）：

| 想做什么 | 用什么 |
|---|---|
| **新增**字段 | `hap worksheet add-fields`（增量、安全），或 edit-spec `field.add` |
| **修改 / 删除 / 重排**已有字段 | **edit-spec** `field.update` / `field.delete` / `field.reorder`（`hap app-editor`，自动整表读改写） |
| 字节级控制整张表布局 | `hap worksheet update-fields --controls`（整表替换，先 `fields --raw` 读全量） |

#### 新增字段（增量，安全）

```bash
# 只追加传入的控件，已有列（含反向关联控件）一概不动
hap worksheet add-fields 6845f0a1b2c3d4e5f6a7b8c9 --controls '[
  {"type": 2,  "controlName": "备注"},
  {"type": 15, "controlName": "签约日期"}
]'

# 布局太长放不进命令行时从文件读（--controls / --fields 都支持 @文件名）
hap worksheet add-fields 6845f0a1b2c3d4e5f6a7b8c9 --controls @new-controls.json
```

`--controls` 接 WireControl 原始形态（与 `fields --raw` 输出同构，见数据字典 §2）。

> 🚨 **不要自己造 `controlId`。** 省略它，列 id 由服务端铸。自己填一个（从别处抄来的、
> 或随手生成的 UUID）会被原样存下，**那样的列在表格和关联控件里读不出来，永远是空白**。

嵌入页、自定义控件、查询记录、查询按钮、API 查询、OCR、自由连接、分段这几种以前没有
模板的类型，现在也能像别的类型一样按类型名直接建，不必再手写原始控件字典。全部类型名
见 `hap worksheet field-types`。

#### 修改 / 删除 / 重排：优先走 edit-spec

这三类操作的正确语义是「读出**全部**原始控件 → 只改目标 → 整表写回」。
`hap app-editor` 的 field op 替你做这个流程，反向/系统控件原样保留：

```json
{
  "app": "1f2e3d4c-5b6a-7081-92a3-b4c5d6e7f809",
  "ops": [
    { "type": "field.add",     "worksheet": "客户",
      "field": { "name": "来源", "type": "SingleSelect", "options": ["展会", "转介绍"] } },
    { "type": "field.update",  "worksheet": "客户",
      "field": "电话", "rename": "联系电话", "set": { "required": true } },
    { "type": "field.delete",  "worksheet": "客户", "field": "旧编号", "confirm": true },
    { "type": "field.reorder", "worksheet": "客户",
      "order": ["客户名称", "联系电话", "等级", "来源"] }
  ]
}
```

```bash
hap app-editor validate edit.json   # 本地校验，零网络
hap app-editor plan     edit.json   # dry-run：读实时结构，预演每个 op
hap app-editor apply    edit.json   # 逐 op 执行（--continue 失败不中断）
```

要点：

- `field.add` 走增量追加；`field` 里 `type` 接 CODE（Text/Number/Relation…）、
  类型名（TEXT/RELATE_SHEET…）或整数。字段词汇是
  `name` / `type` / `required` / `unique` / `options` / `relation` / `lookup` / `rollup` /
  `formula` / `control`——跨表类型必须带自己那个块，写法见
  [edit-spec.md](edit-spec.md) 的「field 的跨表块」。词表以外的键、块放错类型、块内未知键
  一律**校验报错**，不会静默建出指向为空的坏列。这份词汇没建模的形状走
  `control:{<WireControl 原始键>}` 逃生口（最后合并、优先生效）。
- `field.update` 的 `set` 直接写 WireControl 原始键（见 §2/§3）。
- `field.reorder` 按 `order` 重排显示顺序（顺序由控件 `row` 决定）；未列出的字段接在后面。
- 元素可用名称或 id 引用，spec 内后面的 op 可引用前面刚建的元素。

#### 整表替换（update-fields）：知道自己在做什么再用

`update-fields` 把传入内容当作**完整布局**：没传的列一律删除，包括系统自动生成的
反向关联控件。仅两种场景使用：

```bash
# 保存前先干跑检查（一个字都不写），保存后默认自动回读比对
hap worksheet update-fields 6845f0a1b2c3d4e5f6a7b8c9 --fields @layout.json --check
hap worksheet update-fields 6845f0a1b2c3d4e5f6a7b8c9 --fields @layout.json
hap worksheet update-fields 6845f0a1b2c3d4e5f6a7b8c9 --fields @layout.json --no-verify

# 场景 A：刚建的空表一次铺设全部字段（高层方言 --fields）
hap worksheet update-fields 6845f0a1b2c3d4e5f6a7b8c9 --title-name 客户名称 --fields '[
  {"type":"TEXT", "name":"客户名称", "required":true},
  {"type":"AUTO_ID", "name":"客户编号",
   "advanced_setting":{"increase":
     "[{\"type\":1,\"repeatType\":0,\"start\":1,\"length\":5,\"format\":\"C-\"}]"}},
  {"type":"DROP_DOWN", "name":"等级", "options":["VIP","普通","潜在"]}
]'

# 场景 B：完整读出 → 在真实结构上改 → 整表写回（--raw + --controls，这条路干净往返）
hap --json worksheet fields 6845f0a1b2c3d4e5f6a7b8c9 --raw > controls.json
# ……编辑 controls.json：只动目标控件，其余键原样保留……
hap worksheet update-fields 6845f0a1b2c3d4e5f6a7b8c9 --controls @controls.json --check
hap worksheet update-fields 6845f0a1b2c3d4e5f6a7b8c9 --controls @controls.json
```

坑位提示：

- **永远不要**用 update-fields 来「加一个字段」——加字段用 add-fields 或 `field.add`。
- 新建工作表自带的 名称/描述/附件 列在 update-fields 后会被丢弃，想保留就显式传回。
- 写回时未知键原样保留，不要清洗你看不懂的键。
- **条目带不带 `id` 决定它是改已有列还是建新列**：带 `id`（`worksheet fields` 输出里的那个）
  就是改那一列，数据留着；不带 `id` 当成新列由服务端铸 id，而原来那一列如果没出现在这次
  列表里，它和它存的数据一起消失。
- **保存成功 ≠ 保存对了**：引用了已不存在的字段、表单里留下空行、同一列出现两次，这些都能
  保存成功而不报错。`--check` 只报告问题不写入，改结构前先跑一次；真正保存后会**自动回读**
  把这次留下的问题报出来（要关掉用 `--no-verify`）。看到报告别当噪音。
- `--fields` 和 `--controls` 都接受 **`@文件名`**：真实整表布局远超一条命令行能承载的长度。

### 双向关联：一对列，不是一个开关

关联字段默认单向：A 表能点名 B 表的记录，B 表看不到 A。要双向，在字段 `config` 里开
`bidirectional` 并给对方表上那一列起名，**一次建好两侧**：

```bash
hap worksheet add-fields <订单表ID> --controls '[
  {"type": 29, "controlName": "客户", "dataSource": "<客户表工作表ID>",
   "advancedSetting": {"bidirectional": "1", "showtype": "1"}}
]'
```

或走整表布局的高层方言（`update-fields --fields` / `worksheet create --fields`）：

```json
{"type":"RELATE_SHEET", "name":"客户", "dataSource":"<客户表工作表ID>",
 "config":{"bidirectional": true, "reverseName": "订单", "displayMode": "card"}}
```

走 edit-spec 时用 `relation` 块，目标表和展示列都可以写名字：

```json
{ "type": "field.add", "worksheet": "订单",
  "field": { "name": "客户", "type": "RELATE_SHEET",
             "relation": { "worksheet": "客户", "multiple": false,
                           "showFields": ["客户名称", "等级"] } } }
```

> `relation` 块本身**不含 `bidirectional`**（块内未知键会被校验拒绝）。edit-spec 里要双向，
> 先用 `relation` 块把关联建出来，再 `hap worksheet pair-relation` 补反向端；或者把
> `advancedSetting` 塞进 `control` 逃生口。词汇与校验规则见
> [edit-spec.md](edit-spec.md) 的「field 的跨表块」。

- 这会在客户表上**真的建出一列**「订单」。`reverseName` 是对方表上那列的名字，不给就用本表名。
- `displayMode` 取 `dropdown` / `card` / `inlineTable` / `tabTable`。
- 已经有好几条反向关联的表，改结构时**用 `add-fields` 或 `field.add` 加列**，别整体替换布局——
  反向列很容易在替换里被漏掉。

#### 给已存在的关联字段补反向端

建的时候没开 `bidirectional`，事后要补，用 `pair-relation`，**不要去改布局**：

```bash
hap worksheet pair-relation <工作表ID> 客户                # FIELD 传列名或字段 ID
hap worksheet pair-relation <工作表ID> 客户 --name 订单     # 指定对方表上那列的名字
hap worksheet pair-relation <工作表ID> 客户 --repair       # 覆盖对方表上的残留列
```

> 🚨 **不要用「占位 `sourceControlId`」自己伪造反向端。** 那样建出来的关联服务端并没有登记成
> 反向端，而且**之后每做一次整表替换，这个字段就会被复制多出一份**，越改越多。已经这么配过的
> 表用 `--repair` 收拾：它覆盖对方表上的残留列（含重复的多份），**只重写那一列，两张表其余列不动**。
> 不加 `--repair` 时命令会先停下来告诉你有残留，不会擅自覆盖。

#### 怎么判断一个关联到底是不是双向

看 `hap worksheet fields` 输出里该字段的 `relation.bidirectional`：`true`/`false` 是已查证的
结论，**`null` 表示查不出来**（通常是对方表没有读取权限）。

**不能用「有没有 `sourceControlId`」判断双向**——单向关联也带着它，那只是给反向端预留的位置，
目标表里并不存在这么一列。只有去对方表里找得到那一列才算数。

## 数据字典

字典核对于 hap-cli 0.8.31；未覆盖的键以读命令（`hap --json worksheet fields <id> --raw`）返回的实际结构为准。
速查用 `hap worksheet field-types`（它是运行时生成的，与本表不一致时以它为准）。

### 1. 控件类型枚举（`type` 整数）

`--fields` / edit-spec 的 `type` 接受三种写法：整数、类型名（TEXT…）、CODE（Text…）。

| type | 类型名 | CODE | 含义 |
|---|---|---|---|
| 2 | TEXT | Text | 文本（`enumDefault` 1=多行 2=单行） |
| 3 | MOBILE_PHONE | PhoneNumber | 手机号 |
| 4 | TELEPHONE | LandlinePhone | 座机 |
| 5 | EMAIL | Email | 邮箱 |
| 6 | NUMBER | Number | 数值 |
| 7 | CRED | Certificate | 证件 |
| 8 | MONEY | Currency | 金额 |
| 9 | FLAT_MENU | SingleSelect | 单选（平铺） |
| 10 | MULTI_SELECT | MultipleSelect | 多选 |
| 11 | DROP_DOWN | Dropdown | 单选（下拉） |
| 14 | ATTACHMENT | Attachment | 附件 |
| 15 | DATE | Date | 日期 |
| 16 | DATE_TIME | DateTime | 日期+时间 |
| 19 | AREA_PROVINCE | Region(province) | 地区（省） |
| 21 | RELATION | DynamicLink | 自由连接（旧式） |
| 22 | SPLIT_LINE | Divider | 分段 |
| 23 | AREA_CITY | Region(city) | 地区（省-市） |
| 24 | AREA_COUNTY | Region(county) | 地区（省-市-县） |
| 25 | MONEY_CN | AmountInWords | 大写金额 |
| 26 | USER_PICKER | Collaborator | 成员 |
| 27 | DEPARTMENT | Department | 部门 |
| 28 | SCORE | Rating | 等级/评分 |
| 29 | RELATE_SHEET | Relation | 关联记录 |
| 30 | SHEET_FIELD | Lookup | 他表字段 |
| 31 | FORMULA_NUMBER | Formula | 数值公式 |
| 32 | CONCATENATE | Concatenate | 文本组合 |
| 33 | AUTO_ID | AutoNumber | 自动编号 |
| 34 | SUB_LIST | SubTable | 子表 |
| 35 | CASCADER | CascadingSelect | 级联选择 |
| 36 | SWITCH | Checkbox | 检查框/开关 |
| 37 | SUBTOTAL | Rollup | 汇总 |
| 38 | FORMULA_DATE | DateFormula | 日期公式 |
| 39 | — | CodeScan | 扫码 |
| 40 | LOCATION | Location | 定位 |
| 41 | RICH_TEXT | RichText | 富文本 |
| 42 | SIGNATURE | Signature | 签名 |
| 43 | OCR | OCR | 文字识别 |
| 44 | — | Role | 角色 |
| 45 | EMBED | Embed | 嵌入 |
| 46 | TIME | Time | 时间 |
| 47 | BAR_CODE | Barcode | 条码 |
| 48 | ORG_ROLE | OrgRole | 组织角色 |
| 49 | SEARCH_BTN | Button | API 查询按钮 |
| 50 | SEARCH | APIQuery | API 查询 |
| 51 | RELATION_SEARCH | QueryRecord | 查询记录 |
| 52 | SECTION | Section | 标签页（注意：不是 22 分段） |
| 53 | FORMULA_FUNC | FunctionFormula | 函数公式 |
| 54 | CUSTOM | CustomField | 自定义（插件）组件 |
| 10010 | REMARK | Remark | 备注（静态文字） |

地区类的 CODE 统一是 `Region`，由 `regionLevel`（`"province"`/`"city"`/`"county"`，
默认 county）分流到 19/23/24。

### 2. WireControl 常用顶层键

服务端原始控件对象，完整定义 → [WireControl](../scripts/types/wire-control.schema.json)。
服务端接受部分字段，按类型补默认值；活控件携带的键比下表多，**写回时未知键原样保留**。

| 键 | 含义 | 值形态 |
|---|---|---|
| `controlId` | 字段 id；**新建时必须省略**（服务端铸；自造的 id 会建出永远读不出值的空白列），更新时必传 | string |
| `controlName` | 字段显示名 | string |
| `type` | 控件类型（见 §1） | int 枚举 |
| `alias` | API 别名（记录读写时可用） | string |
| `required` | 表单必填 | bool |
| `unique` | 禁止重复值 | bool |
| `attribute` | `1`=本表标题字段（每表恰一个） | int `0`\|`1` |
| `row` / `col` | 0 起的网格位置；row 顺序＝显示顺序；col 为行内列（0/1） | int |
| `size` | 12 栅格跨度 | int：`3`\|`6`（半行）\|`12`（整行） |
| `hint` | 输入占位提示 | string |
| `options` | 选项列表（type 9/10/11） | 数组 `[{key(uuid), value, isDeleted, index, checked, color}]` |
| `advancedSetting` | 按类型的设置袋；**值全是字符串**，JSON 结构序列化后放入 | 字符串值的对象（见 §3） |
| `dataSource` | 类型专属桥接：RELATE_SHEET/SUB_LIST(挂载)=目标 worksheetId；SUB_LIST(内联)=新 UUID；SHEET_FIELD/SUBTOTAL=`$<桥接controlId>$`；公式类=表达式字符串 `$id$ * $id$` | string |
| `sourceControlId` | SHEET_FIELD：目标表被映射列 id；SUBTOTAL：被聚合列 id | controlId 字符串 |
| `enumDefault` | 按类型的判别值：TEXT `1`=多行 `2`=单行；RELATE_SHEET `1`=单条 `2`=多条；ATTACHMENT `3`；SCORE `1`；SUBTOTAL=聚合方式 | int（按类型） |
| `enumDefault2` | 次级判别值（如 MONEY=2、AREA_COUNTY=3） | int（按类型） |
| `strDefault` | 按类型的位标志串（如 RELATE_SHEET `"000"`、SHEET_FIELD `"10"`），语义不全明，先读后改 | 数字位字符串 |
| `showControls` | RELATE_SHEET / SUB_LIST：在选择器/内联列表中展示的关联字段 | controlId 的 JSON 数组 |
| `relationControls` | SUB_LIST：完整子控件对象列表（内联新建或挂载已有表） | 控件对象数组，先读后改 |
| `userPermission` | 成员/部门字段权限标志（默认 1） | int |
| `fieldPermission` | 三位串：能否看见 / 能否编辑 / 新建记录时能否看见。与角色权限**按位与**之后才是最终结果 | `"111"` 这样的三位串 |
| `controlPermissions` | 同上三位，字段自身允许的部分；`fields` 输出的 `isHidden` / `isReadOnly` / `isHiddenOnCreate` 就是这两串按位与算出来的 | 三位串 |
| `dot` | 小数位（NUMBER 默认 0、MONEY/FORMULA_NUMBER 默认 2） | int |

### 3. 各控件类型高价值 advancedSetting 键

值全为字符串（布尔写 `"1"`/`"0"`）。

| 类型 | 键 | 含义 | 值形态 |
|---|---|---|---|
| NUMBER (6) | `showtype` | 显示：`"0"`=数值 `"1"`=进度 `"2"`=滑块 | 枚举字符串 |
| NUMBER (6) | `roundtype` | 取整方式（`"2"`=四舍五入） | 枚举字符串 |
| NUMBER (6) | `thousandth` | 千分位分隔 | `"0"`\|`"1"` |
| NUMBER/SCORE | `itemnames` | 数值区间命名 | JSON 字符串 `[{key,value,color}]` |
| MONEY (8) | `currency` | 币种 | JSON 字符串 `{"currencycode":"CNY","symbol":"¥"}` |
| MONEY (8) | `showformat` | 金额显示格式 | 枚举字符串 |
| 选项 9/10/11 | `showtype` | 单选显示：`"0"`=下拉(→type 11) `"1"`=平铺(→type 9) `"2"`=进度；切换会连带改写 `type` | 枚举字符串 |
| MULTI_SELECT (10) | `direction` / `checktype` / `showselectall` | 排列方向 / 勾选样式 / 全选开关 | 枚举字符串 |
| DATE (15) | `showtype` | 日期精度（DATE 默认 `"3"`；DATE_TIME 默认 `"1"`） | 枚举字符串 |
| RELATE_SHEET (29) | `showtype` | 显示：`"1"`=卡片 `"2"`=列表 `"3"`=下拉框 `"5"`=表格 `"6"`=标签页表格 | 枚举字符串 |
| RELATE_SHEET (29) | `allowlink` / `searchrange` / `scanlink` / `scancontrol` | 打开记录链接、搜索范围、扫码关联开关 | `"0"`\|`"1"` |
| RELATE_SHEET (29) | `coverid` | 卡片封面字段 | controlId 字符串 |
| RELATE_SHEET (29) | `bidirectional` | 双向关联标志 | `"0"`\|`"1"` |
| SUB_LIST (34) | `allowadd`/`allowedit`/`allowcancel`/`allowcopy`/`allowimport`/`allowexport`/`allowbatch` | 内联行的逐操作开关 | `"0"`\|`"1"` |
| SUB_LIST (34) | `enablelimit` / `min` / `max` | 行数限制 | `"0"`\|`"1"`、数字字符串 |
| SUB_LIST (34) | `controlssorts` | 可见子列顺序 | controlId 的 JSON 数组（字符串） |
| SWITCH (36) | `showtype` | 检查框显示变体 | 枚举字符串 |
| SCORE (28) | `itemnum` / `itemtype` | 等级数 / 图标类型 | 数字字符串 |
| AUTO_ID (33) | `increase` | 编号规则 | JSON 字符串 `[{type,repeatType,start,length,format}]` |
| ATTACHMENT (14) | `showtype` / `covertype` / `allowupload` / `allowdelete` / `allowdownload` / `alldownload` / `webcompress` | 画廊或列表、封面、逐操作开关 | 枚举字符串 / `"0"`\|`"1"` |
| 任意有默认值 | `defsource` | 默认值规则；静态选项默认值还会同步置 `options[].checked` | JSON 字符串 `[{cid,rcid,staticValue,…}]`，先读后改 |
| TEXT (2) | `analysislink` / `sorttype` | URL 自动转链接 / 排序规则 | `"0"`\|`"1"`、`"en"` |
| MOBILE_PHONE (3) | `defaultarea` / `commcountries` | 默认国别 / 允许的国别集 | JSON 字符串 |

选项集层面另有 `colorful`（启用选项颜色，颜色本体在 `options[].color`）与
`enableScore`（启用选项分值）两个布尔开关。

### 4. FieldSpec — `--fields` 高层方言的键

`worksheet create --fields` / `update-fields --fields` 每项接受的键
（snake_case 与对应 camelCase 同义，二选一）：

| 键 | 含义 | 值形态 |
|---|---|---|
| `type` | 必填；整数、类型名或 CODE（见 §1） | int \| string |
| `name` | 必填；字段显示名 | string |
| `required` / `unique` | 必填 / 唯一 | bool |
| `hint` | 占位提示 | string |
| `options` | 选项（type 9/10/11）；字符串自动展开成带颜色/key 的选项对象 | `["a","b"]` 或完整选项对象数组 |
| `data_source` / `dataSource` | 类型专属桥接（语义同 WireControl `dataSource`；SHEET_FIELD/SUBTOTAL 只传裸 controlId，`$…$` 包裹自动完成） | string |
| `source_control_id` / `sourceField` | SHEET_FIELD/SUBTOTAL 的目标列 | controlId 字符串 |
| `show_controls` / `showFields` | RELATE_SHEET/SUB_LIST 展示的关联字段 | controlId 的 JSON 数组 |
| `relation_controls` / `relationControls` | SUB_LIST 挂载已有表模式：目标表完整控件列表 | 控件对象数组，先读后改 |
| `child_fields` / `childFields` | SUB_LIST 内联新建子表（推荐）：子字段的 FieldSpec 列表 | FieldSpec 的数组（递归同形） |
| `multi` | RELATE_SHEET：`true`=多条 `false`=单条 | bool |
| `is_title` / `isTitle` | 标为标题字段（通常用命令级 `--title-name` 代替） | bool |
| `row` / `col` / `size` | 显式网格位置/跨度；不传则自动流式布局（半宽两列一行） | int |
| `layout` | `{span: 3|6|12}`，等价于 `size` | 对象 |
| `config` | RELATE_SHEET 便捷块：`displayMode`(`"dropdown"`/`"card"`=单条，`"inlineTable"`/`"tabTable"`=多条)、`showFields`、`coverField`、`bidirectional` | 对象 |
| `defaultValue` | 高层默认值，自动转 `advancedSetting.defsource`：`{source:"static", value}` 或 `{source:"field", field}` 或 `{source:"relationField", relationField, field}` | 对象 |
| `advanced_setting` / `advancedSetting` | 直写 advancedSetting 子键（见 §3） | 字符串值的对象 |
| `extra` | 逃生口：合并进最终控件的任意原始键 | 对象（WireControl 键） |

只读输出键（`id`、`alias`、`subType`、`precision`、`max`、`unit`、`desc`、`remark`、
`isReadOnly`、`isHidden`、`isHiddenOnCreate`、`sourceType`、`relation`）在写入时会被自动忽略。

`worksheet fields` 的默认输出**可以原样回传 `--fields`**，不需要任何手工清洗：空的
`dataSource` / `sourceField` 会被忽略，选项键统一是 `isDeleted`，颜色和分值原样保留。

```bash
hap --json worksheet fields <工作表ID> > layout.json
# 编辑 layout.json
hap worksheet update-fields <工作表ID> --fields @layout.json --check
hap worksheet update-fields <工作表ID> --fields @layout.json
```

要字节级控制 `advancedSetting` 时改走 `--raw` + `--controls`（原样下发，不做任何翻译）。
注意**非空**的 `dataSource` 放在不接受它的类型上仍会报错——那是真的用错了，不是往返问题。

其中 `isReadOnly` / `isHidden` / `isHiddenOnCreate` 是**算出来的真实值**（由
`fieldPermission` 与 `controlPermissions` 按位与得出，见 §2），可以据此判断某个字段在表单里
到底是不是被隐藏或锁定；`relation.bidirectional` 同理，`null` 表示查不出而不是「不是双向」。

### 5. 同一个数字在不同位置意思不同

- 字段类型 `2` 是文本；关联字段的 `sourceControlType: 2` 表示这是个关联；导航显示状态 `2` 是全隐藏。
  用 `--visibility hidden` 这种名字就不用记该填哪个 `2`。
- `enumDefault` / `enumDefault2` **每种字段类型含义都不一样**，不要把在某个类型上试出来的值
  套到别的类型上（见 §2 的分类型说明）。
