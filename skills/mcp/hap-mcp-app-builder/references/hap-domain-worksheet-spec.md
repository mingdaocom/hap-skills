# HAP 工作表与字段领域对象规范

本规范定义 HAP（明道云）平台工作表、字段、布局、关联及表单设置的核心数据结构、属性契约与平台约束。适用于创建和修改工作表配置时的对象构造与校验。

---

## 一、 工作表元数据与配置规范

工作表（Worksheet）是 HAP 应用中承载业务数据的核心实体。

### 1.1 基础属性
- **`name`**（String，必填）：工作表业务名称（如 `"客户"`、`"采购订单"`）。命名应使用简洁纯粹的业务实体或事项名词，**自动剔除用户口语或需求描述中用于指代对象类型的“表 / 工作表”后缀**（例如用户描述“新建《客户信息表》《中奖名单表》”，实际工作表 `name` 应命名为 `"客户信息"`、`"中奖名单"`），并与同应用/同分组已有工作表的命名风格保持一致；仅当“表”字属于不可拆分的专有名词本身（如“资产负债表”“利润表”“课程表”“时刻表”）或用户显式强调必须保留“表”字时除外。
- **`alias`**（String，必填）：工作表英文别名，应用内全局唯一。采用 snake_case 英文短词（新建工作表建议带 `biz_` 前缀，如 `biz_customer`、`biz_purchase_order`；已有别名必须严格保留不可随意改动）。
- **`sectionId`**（String，可选）：所属应用分组（Section）ID。
- **`icon`**（String，可选）：工作表图标文件名（如 `sys_1_worksheet`、`12_2_book`）。
- **`displayType`**（Integer，可选）：工作表导航栏显示模式：
  - `1`：Show All（默认展示，PC 端与移动端均在导航栏正常显示）。
  - `2`：Hide All（完全隐藏工作表。适用于从属于主表的内嵌明细子表 SubTable，不在应用导航栏独立显示）。
  - `3`：Hide PC（仅移动端显示，PC 端隐藏）。
  - `4`：Hide Mobile（仅 PC 端显示，移动端隐藏）。
- **`addRecordButtonName`**（String，可选）：新建记录按钮的自定义名词名称。界面已自带「+」号，仅填写名词对象名称，不带“新建/新增/添加”等动词（默认是“记录”）。
  - 正例：`"任务"`（界面呈现为「+ 任务」）、`"客户"`（「+ 客户」）、`"订单"`（「+ 订单」）。
  - 反例：`"新建任务"`（会导致「+ 新建任务」出现动词重复）。

### 1.2 描述与提示文本
- **`remark`**（String，可选）：面向开发者/AI 的内部注释，说明该表的业务定位、核心用途与关联流转。
- **`desc`**（String，可选）：面向用户的工作表使用说明指南，显示在标题旁的帮助图标中（hover 查看；当同时设置了 importantNote 时作为“详情”链接展开查看）。
  - **格式约束**：必须使用**原生 HTML**，**禁止使用 Markdown**。
  - **标签约束**：仅允许使用 `<p>`、`<strong>`、`<br>` 标签，禁止使用 `<div>`、`<ul>`、`<li>` 等复杂嵌套结构。
  - **转义约束**：严禁输出 `&lt;p&gt;` 等 HTML 转义实体。
  - **内容维度**：涵盖该表的核心用途与适用场景（管什么、谁来用）、数据生命周期流转路径（如 `"新建 → 审核 → 归档"`），以及针对 `importantNote` 一句话警告的展开详细说明（哪些字段由工作流自动维护、触发条件是什么等）。
- **`importantNote`**（String，可选）：显示在工作表标题下方的重要提示文本（始终常驻可见）。
  - **典型适用场景**：
    1. 表中包含由工作流/系统自动更新的状态字段（如 `"状态字段由系统自动维护，请勿手动修改"`）；
    2. 数据依赖其他表的前置数据（如 `"请先在项目表中创建对应项目"`）；
    3. 表涉及审批流程（如 `"提交后将进入审批流程，请确认信息无误后再提交"`）。
  - **`importantNoteColor`**（String，可选）：提示文本颜色，HEX 格式。常规信息固定使用深灰色 `"#515151"`，高危告警可使用 `"#fd5546"`。

---

## 二、 字段设计业务思考与选型决策

### 2.1 字段设计 8 大维度完整性（必须覆盖）
设计一张工作表字段时，建议对照以下 8 个维度依次补齐，确保业务表达完整：

| 维度 | 说明 | 典型字段与类型 |
|---|---|---|
| ① **主标识** | 名称、编号、标题——让用户一眼识别该条记录 | 标题 (`Text`)、单号 (`AutoNumber`)、复合标题 (`Concatenate`) |
| ② **核心业务属性** | 体现行业特征与业务深度的属性信息（最易被遗漏） | ISBN/规格型号 (`Text`)、联系人 (`Text`)、所属行业 (`SingleSelect`/`Relation`) |
| ③ **状态与分类** | 驱动视图看板与自动化工作流流转的枚举 | 审批状态 (`SingleSelect`)、业务分类 (`Dropdown`)、紧急程度 (`SingleSelect`)、是否有效 (`Checkbox`) |
| ④ **时间维度** | 业务相关的时间节点（无需重复创建 ctime/utime） | 计划开始/结束 (`Date`/`DateTime`)、预约时段 (`Time`)、完成时间 (`DateTime`) |
| ⑤ **责任与协作** | 确定数据权限范围与通知推送对象 | 负责人 (`Collaborator`)、所属部门 (`Department`)、承办角色 (`Role`) |
| ⑥ **数量与金额** | 数量、金额、统计值——支撑工作流加减与汇总运算 | 单价/总额 (`Currency`)、库存数量/工时 (`Number`)、服务评分 (`Rating`) |
| ⑦ **说明与凭证** | 详情描述、凭据文件与签名确权 | 图文说明 (`RichText`)、合同扫描件 (`Attachment`)、验收确认 (`Signature`) |
| ⑧ **计算与衍生** | 系统自动计算/引用/汇总，用户无需手动填写 | 金额计算 (`Formula`)、逾期天数 (`DateFormula`)、带出单价 (`Lookup`)、明细总额 (`Rollup`)、条码 (`Barcode`) |

### 2.2 标题字段规范（isTitle）
每张工作表**有且仅有一个**标题字段（作为记录的唯一视觉识别主键）：
- **合法类型**：`Text`, `AutoNumber`, `Date`, `DateTime`, `PhoneNumber`, `Email`, `Concatenate`。
- **业务单据推荐**：对于没有天然单一短名称的业务单据/流转记录（如借阅记录、维修工单、预约单、审批申请），标题强烈推荐使用 `Concatenate` 自动拼接核心维度（如 `"$biz_code$ - $biz_customer_name$"`）。
- **禁止类型**：人员（`Collaborator`）、部门（`Department`）、角色（`Role`）、定位（`Location`）、附件（`Attachment`）、关联（`Relation`）、富文本（`RichText`）、单选/多选/下拉（`SingleSelect`/`MultipleSelect`/`Dropdown`）等**绝对禁止**设为标题字段。
- 若表内没有天然标题字段，必须新建一个 `Text`、`AutoNumber` 或 `Concatenate` 字段作为标题。

### 2.3 字段类型选型决策清单
对照业务数据特征与使用场景，遵循以下选型决策，严禁滥用 `Text` 或编造 `Textarea`：
* **单行短文本 / 多行备注说明 / Markdown** → `Text`（`config.textMode: "singleLine" | "multiLine" | "markdown"`）
* **带格式长文本 / 制度条款 / 图文介绍** → `RichText`
* **普通数值 / 数量 / 工时 / 计量** → `Number`
* **金额 / 单价 / 预算 / 费用** → `Currency`
* **固定单值枚举（≤ 5 项，状态/优先级）** → `SingleSelect`
* **固定多值枚举（≤ 10 项，多标签）** → `MultipleSelect`
* **选项较多需搜索 / 下拉选择（> 5 项）** → `Dropdown`
* **单个确认 / 是与否开关** → `Checkbox`（严禁用 SingleSelect 选"是/否"）
* **1～10 级评分 / 满意度** → `Rating`
* **只要日期、年、年月** → `Date`
* **具体时刻点（含时分秒）** → `DateTime`
* **纯时间段（不含年月日）** → `Time`
* **手机号码** → `PhoneNumber`
* **固定电话 / 座机** → `LandlinePhone`
* **电子邮箱** → `Email`
* **地理位置 / GPS 坐标打卡** → `Location`
* **省市区行政区划（三级级联）** → `Region`
* **负责人 / 经办人 / 审批人** → `Collaborator`（严禁用 Text 录入人员）
* **组织部门 / 业务科室** → `Department`
* **业务角色 / 权限组** → `Role`
* **跨表引用 / 关联独立实体** → `Relation`
* **本表父子层级（上级部门/父任务）** → `Relation`（`dataSource: "selfRelation"`）
* **从属明细数据（随单据创建/销毁）** → `SubTable`
* **树形层级分类（多级品类/组织树）** → `CascadingSelect`
* **引用他表字段（只读/带入）** → `Lookup`
* **汇总关联数据（求和/计数/均值等）** → `Rollup`
* **简单数值四则运算** → `Formula`
* **需要函数表达式的计算与衍生** → `FunctionFormula`，按目标确定输出类型，不替换已满足需求的专用类型
* **日期差值 / 偏移 / 实时倒计时** → `DateFormula`
* **文本拼接组合（格式化全称/标题）** → `Concatenate`
* **单据流水号** → `AutoNumber`
* **材料 / 图片 / 文件附件** → `Attachment`
* **电子手写签名** → `Signature`
* **条形码 / 二维码生成** → `Barcode`
* **业务分段 / 卡片标题** → `Divider`
* **自定义代码组件 / 交互卡片** → `CustomField`

### 2.4 关联衍生控件设计建议
1. **跨表与主子表汇总（`Rollup`）建议**：当子表或关联业务单据包含可度量指标或状态流转计数（如明细金额、累计收款、累计发货/退货数量、待办工单数）时，优先在主表配置原生 `Rollup` 字段（支持按关联表状态/类型做条件过滤汇总，不得退化为普通数值字段靠工作流手工累加）；纯文字过程记录无需强求配置汇总字段。
2. **`Lookup` 按用途选择存储模式**：表单独立展示关联值使用仅显示 Lookup（`storeData: false`）；关联卡片已满足展示需求时可复用卡片。存储模式按 §9.2 的用途规则选择。
3. **`SubTable` vs `Relation` 选型决策**：明细从属于主记录、不独立管理使用 `SubTable`；全局共享独立管理的实体使用 `Relation`。

### 2.5 计算、默认值与表单行为选型

| 目标 | 优先实现 |
|---|---|
| 值随来源变化持续计算，用户不手工维护 | 公式字段；简单数值、日期或拼接仍可使用专用类型，需要函数表达式时使用 `FunctionFormula` |
| 为可编辑字段提供初始值 | 字段默认值；需要表达式且字段类型支持时使用 `dynamicDefault.function`，不当作持续计算或保存后处理 |
| 按条件显隐、必填、只读、赋值或校验提交，未指定前端事件时机 | 业务规则；无条件的属性使用字段自身配置 |
| 用户明确要求字段在失焦、点击等前端时机执行动作 | `customEvents`，事件种类须与字段类型匹配 |
| 保存后、定时或无需打开表单的自动处理 | 工作流 |

同一行为优先复用既有实现，不重复配置事件、业务规则和工作流。**仅当用户明确要求新增、修改或移除前端事件，或明确提出特定前端触发时机与动作时，才配置 `customEvents`**；例如“离开输入框时提示”已足够，不要求用户说出事件名或参数名。“优化表单”“增加计算字段”等泛化需求不自动增加事件，也不为询问是否需要事件另起确认。已有事件在无关修改中原样保留。

---

## 三、 字段通用控制属性与约束 (Field Controls)

### 3.1 字段控制属性对照表

| 属性 | 适用类型 | 说明 |
|---|---|---|
| `isTitle` | Text / AutoNumber / Date / DateTime / PhoneNumber / Email / Concatenate | 每张表**有且仅有一个**字段可设为 true（标题字段），其他控件不支持作标题，否则平台报错 |
| `required` | 大多数输入型业务字段 | 必填约束。**注意**：AutoNumber / Formula / Collaborator / Divider **不可设为 true**，否则创建/修改失败 |
| `isReadOnly` | 大多数业务字段 | 只读约束，用户不可在表单中手动修改 |
| `isUnique` | Text / Number / Email / PhoneNumber 等 | 唯一性约束，防止录入重复数据 |
| `isHidden` | 任意字段 | 表单中是否完全隐藏 |
| `isHiddenOnCreate` | 任意字段 | 新建记录时是否在表单中隐藏（如系统自动计算/回填的字段） |
| `precision` | Number / Currency / Formula / DateFormula / Rollup | 小数位精度（0-14） |
| `max` | Rating | 最大评分值（1-10） |

### 3.2 必填（required）平台约束
- `AutoNumber`（自动编号）、`Formula`（公式）、`Collaborator`（成员）、`Divider`（分段）**不得设置** `required: true`，否则平台接口会直接报错拒绝。

### 3.3 alias 命名规范与保护
每个字段必须拥有唯一 `alias`：
- **唯一性约束**：同工作表内各字段的 `alias` 必须全局唯一。
- **命名规范**：采用全局唯一 `biz_` 前缀 + snake_case 英文短词（如 `biz_visitor_name`、`biz_visit_time`、`biz_status`）。
- **跨表关联字段命名建议**：建议带上本工作表的名称/别名缩写前缀（格式为 `biz_<本表名缩写>_<目标表名/字段名>`，如 `biz_advice_supplier`、`biz_inbound_supplier`），避免多张表关联同类主数据时发生别名命名冲突。
- **已有别名不可静默变更**：已有字段的 `alias` 一经创建，禁止随意重命名或静默丢弃，避免破坏下游公式、Lookup、Rollup、视图筛选及自动化工作流的既有引用。

---

## 四、 特殊字段配置说明

### 4.1 组织与复合控件配置
- **`Collaborator` / `Department` / `Role` 组织字段**：`config.isMultiple` 控制单/多选（单数语义 `false`，团队/参与人 `true`）。`Collaborator` 另由 `config.userPermission` 控制被选成员对该记录的数据权限（与角色 `recordDataScope: 20` 联动）：`2`=拥有者权限（执行人/巡检人/维修员/负责人等需编辑处理记录者必设）、`1`=只读权限（默认，抄送/知会）、`0`=无权限（仅展示）；
- **`Concatenate`（文本拼接）**：`config.expression` 必填拼接公式，引用其他字段用 `$alias$` 包裹，可加固定分隔符。示例：`"$biz_code$ - $biz_name$"` → 显示 "ORD-001 - 张三"。可作为标题字段（isTitle）；
- **`Signature`（电子签名）**：直接传 `type: "Signature"`，布局推荐 `span: 12`；
- **`Barcode`（条码）**：`config.displayMode` 可选 `"code128"`（一维码，默认）或 `"qrCode"`（二维码）；`config.expression` 必填生成公式，引用字段用 `$alias$`（如 `"$biz_auto_number$"`）。

### 4.2 公式与函数表达式

- 引用本表真实字段，按工具契约使用 `$字段ID或alias$`，不把显示名称当引用。先利用已有字段信息确定输入类型及结果用途，再构造表达式；简单数值例：`$biz_total_amount$ * (1 - $biz_discount_rate$)`。
- `FunctionFormula`（Type 53）用于函数计算；按工具 Schema 选定输出类型，创建后不可通过编辑改变输出类型或字段类型。普通计算需求不因此改成事件赋值，也不把 Type 53 当成其他计算类型的无条件替代品。
- 所有公式类型均不支持直接引用关联记录或子表字段，不构造关系路径表达式。确需关联值或集合汇总时，先按业务需要使用 Lookup / Rollup 取得可被公式引用的本表标量值，并核对实际类型与存储要求；不是取到任意 Lookup 或数组就能直接计算。
- 函数名、参数签名与语法须有当前工具说明、已验证的平台配置或平台参考依据；已有可靠表达式直接复用，不固定重复查证。不将 Excel 或 JavaScript 的同名函数视为 HAP 等价能力；没有依据时说明具体能力缺口，不猜函数或以反复保存试探支持范围。
- `FunctionFormula` 的表达式、`dynamicDefault.function` 和事件中的函数赋值/条件属于不同配置位置；按当前 Schema 构造，不把表达式字符串、Function 对象或整段 JavaScript 相互套用。公式与 JavaScript 的语言选择遵循各自配置契约。

### 4.2.1 前端事件（`config.customEvents`）配置与局部修改

- 前端事件属于字段的 `config.customEvents` 配置，不是独立业务规则。事件类型、条件、动作及函数赋值结构以实时 MCP Schema 为准，不套用业务规则的条件树或写成 `advancedSettings.custom_event` 字符串；提示、跳转或赋值使用原生动作，不为此生成 CustomField 组件。
- 每个新建事件在 `customEvents[].id` 传入独立生成的 UUID。修改 `config.customEvents` 按整数组替换处理：复用完整当前配置，缺失时定向读取目标字段，保留未修改事件、分支顺序和稳定 ID；省略整个属性表示不修改。不要把只传一个事件当作按 ID 局部更新。
- 动作引用 API、工作流或查询时使用真实资源标识与参数。事件查询是当前字段已有查询的引用，不能套用动态默认值的完整查询定义或编造 ID；现有工具无法补齐资源时报告具体缺口，已有有效资源不重复查询。
- 前端事件依赖表单交互，不代替服务端保存校验、权限或后台自动化。配置事件不等于授权立即触发实际业务动作；沿用既有执行范围及结果核验规则，区分配置已保存与实际计算、触发的证据，不将配置成功当作运行验证，也不为验收自动试写或连续轮询。

### 4.3 AutoNumber 常用编号模板
- 纯流水号：`[{ type: "sequence", length: 6, repeat: "never" }]`
- 日期 + 流水：`[{ type: "createdTime", format: "yyyyMMdd" }, { type: "sequence", length: 4, repeat: "day" }]`
- 前缀 + 流水：`[{ type: "text", value: "ORD-" }, { type: "sequence", length: 6, repeat: "never" }]`

### 4.4 DateFormula（日期公式）
DateFormula 用于计算日期差值、日期时间偏移或实时倒计时：
- `type: "DateFormula"`
- **`config.formulaType`**：
  - `"dateDiff"`：计算两个指定日期字段之间的差值（后端计算）；
  - `"dateOffset"`：在指定时间基础上增加/减少时间偏移量（后端计算）；
  - `"dateNowDiff"`：目标时间与当前实时时刻的动态差值（前端实时计算，不落库）。
- **`config.outputUnit`**：输出时间单位，可选 `"Y"`（年）、`"M"`（月）、`"d"`（天）、`"h"`（小时）、`"m"`（分钟）、`"s"`（秒）。
- **`config.precision`**：计算结果小数位精度。
- **`config.direction`**（`dateNowDiff` 专属）：`"targetMinusNow"`（目标减当前，倒计时/距到期）或 `"nowMinusTarget"`（当前减目标，已逾期/已历时）。

### 4.5 CascadingSelect（级联选择）
CascadingSelect 用于在具有层级树形自关联的数据源表中进行多级联动选择（如行政区划、多级商品类目、多层级组织架构）：
- `type: "CascadingSelect"`, `dataSource: "<目标层级表ID>"`, `viewId: "<目标表树形视图ID>"`, `layout: { rowIndex, span }`；
- **`config.displayMode`**：`"cascader"`（级联下拉菜单）或 `"tree"`（树形展开弹窗）。

### 4.6 Date / DateTime / Time 显示格式 (Moment.js)
Date / DateTime / Time 字段必须显式配置 `config.format`，采用 **Moment.js 格式符号**（注意：与 AutoNumber 的 .NET 格式不同，勿混用）：
- **大小写区分**：大写 `D` = 日，小写 `d`/`dd`/`ddd` = 星期。
- **常用模板**：
  - 中文：`"YYYY年M月D日"`，带时间：`"YYYY年M月D日 HH:mm"`，带星期：`"YYYY年M月D日 ddd"`
  - 英文：`"MMM D, YYYY"`，带时间：`"MMM D, YYYY HH:mm"`，带星期：`"ddd, MMM D, YYYY"`
  - ISO 兜底：`"YYYY-MM-DD"`，带时间：`"YYYY-MM-DD HH:mm"`
  - 仅年：`"YYYY"`，年月：`"YYYY-MM"` / `"YYYY年M月"`
  - 纯时间：`"HH:mm"`（默认），仅小时：`"HH"`，含秒：`"HH:mm:ss"`

---

## 五、 Divider 业务分段规范

Divider 用于在长表单中将字段划分至不同的视觉区块：
- **结构定义**：`type: "Divider"`, `required: false`, `layout: { rowIndex: N, span: 12 }`。
- **设计建议**：
  - 每张表建议设置 2～5 个 Divider，每个分组内建议包含 3～8 个字段。
  - 附件、备注、说明、治理归档类内容通常放置在最后一个 Divider。
- **命名规范**：结合业务语义提炼自然名称（通常 2～6 个字，优先使用业务名词）：
  - 客户表：`客户资料`、`联系信息`、`跟进情况`
  - 合同表：`合同主体`、`签约安排`、`履约信息`
- **禁忌**：禁止使用空泛无意义的模板名（如 `基本信息`、`归属与协作`、`计划与进度`、`审批与治理`、`备注与附件`）。

---

## 六、 Layout 12 栅格排版系统 (Layout)

HAP 表单采用 **12 等分列栅格系统**。每个字段的 `layout` 必须同时包含 `rowIndex`（行号，从 0 开始递增）和 `span`（列宽占比）。

### 6.1 网格布局平台约束
- **同行判定**：只有 `rowIndex` 相同的字段才会显示在同一行。`rowIndex` 不同则强制分行。
- **列宽总和**：同一行内（相同 `rowIndex`）各字段的 `span` 之和必须 **≤ 12**（排满整行时为 12）。
- **合法 span 取值**：平台支持的合法 span 取值为 `3, 4, 6, 8, 9, 12`：
  - `span: 12`：整行宽（独占整行）
  - `span: 6`：半行宽（同行可放 2 个）
  - `span: 4`：三分之一宽（同行可放 3 个）
  - `span: 3`：四分之一宽（同行可放 4 个）
  - `span: 8`：三分之二宽（可与 span:4 同行）
  - `span: 9`：四分之三宽（可与 span:3 同行）

### 6.2 栅格排版推荐实践
平台允许上述任意合法 span 自由组合（存量表单中所有合法 span 组合均属有效配置）。为保证新建表单在视觉上整齐对齐，**推荐**在表单内优先保持一致的栅格节奏：
- **四等分体系（推荐默认）**：基于 `3 / 6 / 9 / 12` 栅格（如紧凑 4 列 `3+3+3+3`、双列 `6+6`、主从 `9+3`、独占 `12`）；
- **三等分体系**：基于 `4 / 8 / 12` 栅格（如 3 列并排 `4+4+4`、主从 `8+4`、独占 `12`）；
- **消灭半截留白（核心准则）**：
  - 同一行若只有 2 个字段，应使用 `span: 6 + 6 = 12` 撑满整行；
  - **严禁使用 `span: 4 + 4` 留下右侧 1/3 的难看留白**。若紧凑短字段凑不够 3 个（无法形成 4+4+4=12），不要使用 4+4，应使用 `6 + 6` 双列排满整行。
- **设计建议**：在全新创建表单时，推荐优先选用同一套栅格体系，避免无序混排产生列宽错位感。

### 6.3 布局适用模式
- **强制独占一行（span: 12）**：`Divider`、`RichText`、`Attachment`、`SubTable`、`Signature`、以及 `displayMode` 为 `inlineTable` / `tabTable` 的 `Relation` 字段。
- **紧凑字段并排（span: 3 或 4）**：`Number`、`Currency`、`Date`、`PhoneNumber`、`Email`、`AutoNumber`、`Dropdown` 等。
  - 四等分体系（span: 3 示例）：数量 + 单价 + 金额 + 折扣率；联系电话 + 邮箱 + 入库日期 + 编号。
  - 三等分体系（span: 4 示例）：规格型号 + 单位 + 单价；联系人 + 手机号 + 职位。
- **语义成对并排（span: 6）**：
  - 示例：开始时间 + 结束时间；状态 + 优先级；负责人 + 所属部门。同行两两成对，使用 `span: 6 + 6` 填满整行，杜绝半截留白。

---

## 七、 选项字段规范与色彩体系 (SingleSelect / MultipleSelect / Dropdown / Checkbox)

### 7.1 控件选型决策
- **单选场景**：
  - 选项数 ≤ 5 个 → 优先使用 `SingleSelect`（平铺单选，选项平铺直观）；
  - 选项数 > 5 个 → 优先使用 `Dropdown`（下拉单选，收纳节省表单空间）。
- **多选场景**：
  - 选项数 ≤ 10 个 → 优先使用 `MultipleSelect`（标签多选）；
  - 选项数 > 10 个 → 优先使用 `Dropdown`（`config.isMultiple: true` 下拉多选）。
- **二元状态场景**：
  - 单个是/否、确认/未确认、启用/停用 → 必须使用 `Checkbox` 控件（严禁使用 SingleSelect + 是/否 选项）。

### 7.2 数据结构
以下内置选项与颜色规则适用于字段自身选项；绑定共享选项集的字段沿用选项集配置，不重复提交 options。
`options` 数组，每项包含 `index`（从 1 递增的整数）和 `value`（选项文本，必须有实际业务含义，严禁“选项1/选项2”占位符）。

### 7.3 isColorOptions 显式配置（硬约束）
每个选项字段必须在 `config` 中显式配置 `isColorOptions` 布尔值：
- **彩色选项**：必须设置 `config: { isColorOptions: true }`，同时 `options` 数组中的每个选项**必须带有 `color` 属性**（十六进制 HEX 颜色）。
- **非彩色选项**：必须设置 `config: { isColorOptions: false }`，`options` 数组中的选项**不得携带 `color` 属性**。

### 7.4 颜色映射与分类适用规则
- **必须使用彩色（`isColorOptions: true`）的场景**：状态、处理阶段、优先级、紧急程度、风险等级、审批结果等具有明显进度、情感倾向或告警意义的字段。
  - 负面 / 失败 / 拒绝 / 紧急 / 严重 → `#F52222`（红）
  - 正面 / 完成 / 通过 / 正常 → `#00C345`（绿）
  - 警告 / 待处理 / 待审核 / 中等 → `#FAD714`（黄）
  - 进行中 / 处理中 / 执行中 → `#2D46C4`（蓝）
  - 取消 / 归档 / 已作废 / 停用 → `#484848`（灰）
  - 调色盘备用集：`#C0E6FC` `#C3F2F2` `#00C345` `#EAB308` `#FF9300` `#F52222` `#EB2F96` `#7500EA` `#2D46C4` `#484848`
- **必须使用无色（`isColorOptions: false`）的场景**：纯业务分类、数据字典、行业类别、渠道来源、部门类别等中性无倾向的分类/标签字段。

---

## 八、 Relation 跨表关联字段规范

### 8.1 核心参数结构
每个 Relation 字段必须包含 `dataSource`、`config.isMultiple`、`config.bidirectional`、`config.displayMode` 四个属性：

1. **`dataSource`**（字段根属性，非 config 内部）：
   - **自关联（关联本表自身）**：赋值为 `"selfRelation"`。
   - **跨表关联**：赋值为目标表的真实 `worksheetId`（24 位 hex 字符串，严禁随意伪造或借用未创建表的 ID）。
2. **`config.isMultiple`**（Boolean，必填）：
   - `false`：多对一关联（一条记录只关联一条目标记录）。自关联时必须为 `false`。
   - `true`：一对多 / 多对多关联（一条记录可关联多条目标记录）。
3. **`config.bidirectional`**（Boolean，必填）：
   - `true`：双向关联（平台会自动在目标表生成对应的反向关联控件）。自关联时必须为 `true`。
   - `false`：单向引用（仅本表持有引用，目标表不产生反向控件）。
4. **`config.displayMode`**（String，必填）：
   | displayMode | 适用场景 | 对应表类型 | 备注与布局 |
   |---|---|---|---|
   | `dropdown` | 关联目标是**字典/分类/标签表**（数据源表），仅选择引用、无需展示详情 | 如 `图书类型`、`客户级别`、`任务状态` | 条目少、结构简单，`span: 3/6` |
   | `card` | 关联目标是**核心业务表**（实体表），需展示关键字段（**默认推荐**） | 如 `图书清单`、`订单`、`客户`、`项目` | 可设 coverField，`span: 6/12` |
   | `inlineTable` / `tabTable` | 一对多且需集中展示 | 业务明细、子项清单 | **必须设置 `span: 12`** |
5. **`config.showFields`**（条件必填）：
   - `displayMode` 为 `card` → **必须 ≥ 2 个**，推荐 2~4 个（**必须包含目标表的标题字段**，挑选最具业务识别度的字段如编号、名称、金额、状态，排除富文本、附件等复杂控件）。
   - `displayMode` 为 `inlineTable` / `tabTable` → **必须 5~10 个**。
   - `displayMode` 为 `dropdown` → 不需要。
   - 取值：目标表中最具业务识别度的字段真实 `alias` 或 ID 列表。
6. **`config.coverField`**（条件必填）：
   - 仅 `displayMode === "card"` 时有效。
   - 当目标表有附件字段，且该附件是记录的核心视觉标识（如产品主图、用户头像、房源照片、设备外观、Logo 等）时设置。
   - **反例（绝对不设 coverField）**：操作截图（如 bug 截图、巡检拍照）、纯文档类附件（合同 PDF、报告、表格）、辅助性附件（签名、回执）。

### 8.2 平台双向关联机制与关系模型
- **明细子表 (SubTable) 关系模型**：明细子表控件由主表（父表）承载并配置。主表添加子表控件后，从属子表会自动获得指向主表的父级关联，**子表不可且无需单独定义指向主表的关系控件**。
- **双向关联 (Relation) 仲裁模型**：若两张表之间存在双向业务联系，以从属端/单条引用端（`isMultiple: false`）作为关系主定义表；主表/多条端作为反向宿主表（自动承接反向卡片/Tab 列表），避免关系双向冗余定义。

---

## 九、 关联衍生控件规范 (SubTable / Lookup / Rollup)

### 9.1 SubTable（明细子表控件）
明细子表用于主从内嵌明细结构（如采购明细、报销明细、工单配件明细）：
- **目标子工作表层级**：子工作表本身必须设置工作表元数据属性 `displayType: 2`（完全隐藏），不在应用侧边栏独立展示。
- **主表 SubTable 字段层级**：主表表单内的 SubTable 字段对象包含以下属性（**字段对象本身不含 `displayType`**）：
  - `type`: `"SubTable"`
  - `name`: 字段名称（如 `"采购明细"`）
  - `alias`: 字段别名（如 `"biz_po_items"`）
  - `dataSource`: 目标子表的 `worksheetId`（24 位 hex 字符串）
  - `layout`: `{ rowIndex, span: 12 }`（**子表控件在主表表单中固定独占整行**）
  - `config`: 高级配置对象：
    - `bidirectional`: 固定为 `true`
    - `showFields`: 必填，指定在主表表单中内嵌展示的子表字段列表（通常配置该子表的所有业务字段，确保明细完整可查看与录入；子表新增字段时，必须同步在此补齐该新字段）
- **单向定义约束**：主表添加 SubTable 控件后，子表会自动获得指向主表的父级关联，**子表端不需要且严禁再次创建指向主表的关系字段**。

### 9.2 Lookup（他表字段引用）
Lookup 用于通过关联关系，自动从关联记录中带出指定字段的值并在本表中引用：
- **单条关联约束**：必须挂载在单条关联（`isMultiple: false`）字段上，不支持多条关联；
- **配置结构**：`relationField` 为本表关联字段的 alias 或 ID，`sourceField` 为目标表源字段的 alias 或 ID；
- **同批创建**：目标表及来源字段已明确时，本表 Relation 与依赖它的 Lookup 可在同一次 `create_worksheet.fields` 或 `update_worksheet.addFields` 中创建，通过本批明确声明的关联字段 alias 引用；直接创建正确类型，不先建普通 PhoneNumber/Text 占位再改类型，也不为取得本批关联字段 ID 固定拆批回读。依赖尚未创建的目标表或服务端生成的反向关联时，仍须先取得真实来源，不能编造未来字段引用；Build 既有两遍建表在关联补全阶段合并处理，不改变跨表依赖顺序。
- **存储型 vs 动态引用决策**：
  - `config.storeData: false`（仅显示）：需要在本表独立展示关联值时使用，手机号、奖品等带出展示无需改成存储型。
  - `config.storeData: true`（存储副本）：本表公式计算、视图分组/筛选等确需存储值时采用，并确认同步与业务取值要求；不能把存储副本必然等同于当前来源值。
  - 不因工作流取值需求开启 Lookup 存储或改变字段类型；来源取值由工作流领域处理。不擅自改变已有字段的存储模式。

### 9.3 Rollup（跨表汇总计算）
用于通过本表关联（`Relation`）或子表（`SubTable`）对多条关联记录进行跨表统计聚合（求和、计数、均值、最大/最小值）：
- **原生支持条件过滤（仅限平铺条件，不支持条件组）**：支持按关联目标表的状态、类型等字段过滤统计范围（如“累计已确认收款”“累计发货数量”“累计退货数量”）。注意平台能力边界：**汇总过滤仅支持单个条件或单层平铺多条件（统一“且”或统一“或”），不支持嵌套条件组**；若业务逻辑需要复杂 `(A 且 B) 或 C` 组合，应在关联表用枚举或衍生标识收敛为单层条件后再汇总。
- **真实字段引用与实时 Schema 对齐**：本表关联字段与目标表度量字段均须使用真实字段标识（纯记录计数可不指定度量字段）；聚合方式与汇总过滤的具体参数结构一律以当前 MCP 工具实时 Schema 为准（切勿与关联可选范围过滤混淆）。

---

## 十、 默认值 (defaultValue) 4 种 source 规范

### 10.1 使用原则与边界
- **原则**：优先用于高频、重复、规则明确、存在稳定预期的场景；以减少输入成本为目标，不应增加误填风险。
- **边界**：不确定、易变化、依赖人工主观判断的字段，不建议设置默认值。
- **格式**：始终传数组，即使单值字段也使用包含一个对象的数组：
  ```json
  "defaultValue": [
    { "source": "system", "value": "currentUser" }
  ]
  ```

### 10.2 4 种 source 数据源类型
1. **`system`**：系统内置动态变量。
   - `value: "currentUser"`：当前登录用户（适用于 Collaborator、Department、PhoneNumber、Email）。
   - `value: "now"`：当前时间（适用于 Date、DateTime）。
   - `value: "currentLocation"`：当前定位（适用于 Location）。
   - 示例：`[{ "source": "system", "value": "currentUser" }]`
2. **`static`**：静态固定初始值。
   - 状态/选项：`value: "待处理"`（填选项文本）。
   - 日期：`value: "2026-01-01 09:00:00"`。
   - 数值：`value: "100"`。
   - 示例：`[{ "source": "static", "value": "待处理" }]`
3. **`field`**：动态引用当前表单内其他字段的值。
   - `field: "startTime"`（引用本表其他字段 alias）。
   - 示例：结束时间默认为开始时间 `[{ "source": "field", "field": "biz_start_time" }]`。
4. **`relation`**：引用已选关联记录中的字段值（级联带出）。
   - `relationField: "biz_customer", field: "biz_customer_phone"`。
   - 示例：选择客户后自动带出客户电话 `[{ "source": "relation", "relationField": "biz_customer", "field": "biz_phone" }]`。

### 10.3 控件类型支持矩阵

| 字段类型 | 多值支持 | static | system | field / relation |
|---|---|---|---|---|
| `Text` | ✅ | ✅ | — | ✅ |
| `Number` / `Currency` | — | ✅ | — | ✅ |
| `SingleSelect` | — | ✅ (选项名) | — | ✅ |
| `MultipleSelect` / `Dropdown` | ✅ | ✅ | — | ✅ |
| `Date` / `DateTime` | — | ✅ (YYYY-MM-DD HH:mm:ss) | `now` | ✅ |
| `Collaborator` / `Department` | `isMultiple` | — | `currentUser` | ✅ |
| `Role` | `isMultiple` | — | — | ✅ |
| `PhoneNumber` / `Email` | — | ✅ | `currentUser` | ✅ |
| `LandlinePhone` | — | ✅ | — | ✅ |
| `Region` | — | — | — | ✅ |
| `Rating` | — | ✅ (数值) | — | ✅ |
| `Location` | — | — | `currentLocation` | ✅ |

> **不支持 defaultValue 的字段类型**：`AutoNumber`、`Formula`、`DateFormula`、`Attachment`、`Relation`、`Divider`。

---

## 十一、 字段辅助文本规范 (placeholder, desc, remark)

### 11.1 placeholder（输入占位提示）
所有输入型字段支持 placeholder，用于引导用户了解应输入什么内容：
- 支持类型：`Text`、`Number`、`Email`、`PhoneNumber`、`LandlinePhone`、`Dropdown`、`Date`、`DateTime`、`Time`、`Currency`。
- 示例对照：
  | 字段类型 | 场景 | placeholder 示例 |
  |---|---|---|
  | Text | 名称/实体类 | `"请输入客户全称"`、`"请输入项目名称"` |
  | Text | 描述/说明类 | `"请简要描述问题现象和影响范围"` |
  | Number | 数量类 | `"请输入数量"` |
  | PhoneNumber | 手机号码 | `"请输入手机号"` |
  | Email | 电子邮箱 | `"请输入邮箱地址"` |
  | Date / DateTime | 日期选择 | `"请选择日期"`、`"请选择开始时间"` |
  | Dropdown | 下拉选择 | `"请选择"` |

### 11.2 desc（字段说明文本）
面向用户的字段说明，显示在字段下方。仅当字段有**特殊填写要求**或**业务逻辑需要解释**时设置：
- **适用场景**：
  - 格式/精度/业务规则补充（如金额字段 → `"含税金额，精确到分"`）；
  - 选项含义解释（当 SingleSelect/MultipleSelect 的选项含义不直观时，解释适用场景）；
  - 不支持 placeholder 的控件引导（如 Relation 字段 → `"选择本次服务对应的签约客户"`；Rating 字段引导）；
  - Checkbox 勾选含义说明（如 `"勾选表示已完成现场验收并确认收货"`）；
  - Formula / AutoNumber 计算与编号规则解释（如 `"由系统根据 单价×数量 自动计算"`、`"按 年月+4位流水号 自动生成"`）。
- **禁忌**：禁止生成单纯重复字段名称的无意义 desc（如字段"性别" → desc"请选择客户性别"）。

### 11.3 remark（开发者注释）
面向开发者/AI 的字段级注释，用一句话说明字段的业务用途，若字段被工作流读写或被视图筛选依赖，应一并注明。

---

## 十二、 工作表设置与表单体验增强规范 (update_worksheet_settings)

### 12.1 适用场景与边界准则
- **新建工作表场景（完整应用 Build 或存量应用单独追加表）**：当当前任务新建工作表并取得 `worksheetId` 后，都应根据工作表的业务定位和字段构成判断是否需要配置表单设置。只有存在实际生效配置时才调用 `update_worksheet_settings`；从属明细子表或纯数据字典表通常无需增强。
- **修改已有工作表场景（存量修订）**：仅当用户明确需求或修订计划明确影响表单设置时才进行修改，**严禁主动覆盖或顺带修改未受影响的既有设置**。
- **调用安全约束**：禁止发送仅含 `appId` 和 `worksheet_id` 的空参数请求，每次调用必须至少包含实际生效的 `form`、`submission` 或 `basic` 配置。

### 12.2 封面大图 (form.cover)
当本表包含 `Attachment` 附件且字段语义适合作为详情页主视觉封面时（如商品主图、物料照片、房源实拍、头像、设备铭牌、设计效果图等），配置其为封面，**推荐指定 `height: 200 ~ 400`** ；

### 12.3 新建表单标题 (form.title)
针对业务单据或流程发起表单，动态定制动作化标题（如 `"发起采购申请"`、`"提交故障报修"`、`"录入新客户"`、`"起草业务合同"` 等），替代默认机械的“新建 xxx”；

### 12.4 关联 Tab 标签页呈现 (form.tabs)
固定开启 `hideWhenSingle: true`（单个标签页时自动隐藏 Tab 栏消除视觉噪音）；Tab 位置默认设为 `"top"`（顶部 Tab），当关联 Tab 较多时（>3 个，如客户 360 视图、项目总览）设为 `"left"`（左侧 Tab 导航）；

### 12.5 场景化提交行为与专业文案 (submission)
- **审批/流转单据**（如请假、报销、采购申请、立项等）：
  - 配置提交按钮文案：`submission: { submitButtonLabel: "提交审批" }`（或 `"提交立项"`、`"提交报修"`）；
  - 配置提交后动作：`submission: { afterSubmit: { action: "openCreatedRecord" } }`（自动打开刚创建的记录详情）。
- **高频录入/基础建档/流水登记表**（如商品档案、物料主数据、联系人名片、访客登记、设备巡检、电销跟进等）：
  - 开启连续提交：`submission: { continueCreation: { enabled: true, buttonLabel: "保存并继续添加" } }`，方便批量连续录入。
- **登记/填报单据**：
  - 定制提交按钮文案：`submission: { submitButtonLabel: "确认登记" }` 或 `submission: { submitButtonLabel: "保存记录" }`。
- **高风险/重大单据**（如资产报废、合同作废、调账出库等）：
  - 按需开启提交二次确认弹窗：`submission: { submitConfirmation: { enabled: true, title: "确认提交", content: "提交后将锁定并进入流转，是否确认？", confirmButtonLabel: "确认提交", cancelButtonLabel: "返回检查" } }`，提升系统严肃性与防错体验。

### 12.6 平台通用约束
- **`editFields` 增量更新与 `type` 只读约束**：使用 `update_worksheet.editFields` 修改已有字段时，只需传入 `id`（字段 ID 或 alias）及需要更新的属性，省略的属性保持原值不变；所有字段的 `type` 只读，严禁修改字段类型。

## 修订中的字段与工作表删除

授权、类型范围、空表证据和最小检查由 hap-revision-safety 维护。标题切换或引用调整明确成功后才调用标准删除入口，前置失败或结果未知停止依赖删除。
