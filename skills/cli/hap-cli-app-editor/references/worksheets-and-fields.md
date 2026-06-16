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

# 基本信息
hap --json worksheet info 6845f0a1b2c3d4e5f6a7b8c9

# 改别名 / 描述；改侧边栏名称或图标需要 --app-id
hap worksheet update 6845f0a1b2c3d4e5f6a7b8c9 --alias customers --desc "客户主数据"
hap worksheet update 6845f0a1b2c3d4e5f6a7b8c9 --name "客户（CRM）" \
  --app-id 1f2e3d4c-5b6a-7081-92a3-b4c5d6e7f809

# 删除
hap worksheet delete 6845f0a1b2c3d4e5f6a7b8c9 --app-id 1f2e3d4c-5b6a-7081-92a3-b4c5d6e7f809 -y

# 字段清单。默认输出是高层归一形态；--raw 输出服务端原始控件（WireControl），
# 任何「读改写」操作都以 --raw 为准
hap --json worksheet fields 6845f0a1b2c3d4e5f6a7b8c9
hap --json worksheet fields 6845f0a1b2c3d4e5f6a7b8c9 --raw
```

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
```

`--controls` 接 WireControl 原始形态（与 `fields --raw` 输出同构，见数据字典 §2）。

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
  类型名（TEXT/RELATE_SHEET…）或整数；复杂控件可加 `control:{<WireControl 原始键>}` 逃生口。
- `field.update` 的 `set` 直接写 WireControl 原始键（见 §2/§3）。
- `field.reorder` 按 `order` 重排显示顺序（顺序由控件 `row` 决定）；未列出的字段接在后面。
- 元素可用名称或 id 引用，spec 内后面的 op 可引用前面刚建的元素。

#### 整表替换（update-fields）：知道自己在做什么再用

`update-fields` 把传入内容当作**完整布局**：没传的列一律删除，包括系统自动生成的
反向关联控件。仅两种场景使用：

```bash
# 场景 A：刚建的空表一次铺设全部字段（高层方言 --fields）
hap worksheet update-fields 6845f0a1b2c3d4e5f6a7b8c9 --title-name 客户名称 --fields '[
  {"type":"TEXT", "name":"客户名称", "required":true},
  {"type":"AUTO_ID", "name":"客户编号",
   "advanced_setting":{"increase":
     "[{\"type\":1,\"repeatType\":0,\"start\":1,\"length\":5,\"format\":\"C-\"}]"}},
  {"type":"DROP_DOWN", "name":"等级", "options":["VIP","普通","潜在"]}
]'

# 场景 B：完整读出 → 在真实结构上改 → 整表写回（--controls 原样回传）
hap --json worksheet fields 6845f0a1b2c3d4e5f6a7b8c9 --raw > controls.json
# ……编辑 controls.json：只动目标控件，其余键原样保留……
hap worksheet update-fields 6845f0a1b2c3d4e5f6a7b8c9 --controls "$(cat controls.json)"
```

坑位提示：

- **永远不要**用 update-fields 来「加一个字段」——加字段用 add-fields 或 `field.add`。
- 新建工作表自带的 名称/描述/附件 列在 update-fields 后会被丢弃，想保留就显式传回。
- 写回时未知键原样保留，不要清洗你看不懂的键。

## 数据字典

字典生成于 2026-06-10；未覆盖的键以读命令（`hap --json worksheet fields <id> --raw`）返回的实际结构为准。
速查也可用 `hap worksheet field-types`。

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
| 10010 | REMARK | — | 备注（静态文字） |

地区类的 CODE 统一是 `Region`，由 `regionLevel`（`"province"`/`"city"`/`"county"`，
默认 county）分流到 19/23/24。

### 2. WireControl 常用顶层键

服务端原始控件对象，完整定义 → [WireControl](../scripts/types/wire-control.schema.json)。
服务端接受部分字段，按类型补默认值；活控件携带的键比下表多，**写回时未知键原样保留**。

| 键 | 含义 | 值形态 |
|---|---|---|
| `controlId` | 字段 id；新建时可不传或预置 UUID，更新时必传 | string |
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
`isReadOnly`、`isHidden`、`isHiddenOnCreate`、`sourceType`、`relation`）在写入时会被
自动忽略——`fields` 默认输出可以原样喂回 `--fields`，无需手工清洗。
