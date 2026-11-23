# HAP 应用规划 Schema 规格指南 (1b_plan_schema)

> 同源基准：`skills/hap-app-plan-builder-spec`

本文档定义 `hap-plan.json` 的机器结构、紧凑字符串语法、`requirements` 补充要求通道与闭环硬约束。

---

## 一、 顶层 JSON 骨架与对象补充要求 (`requirements`)

```json
{
  "orgId": "来自前置检查确定的组织 ID",
  "appName": "应用名称（2~8字，严禁带系统/管理/平台/软件/后台等后缀）",
  "language": "zh-CN",
  "appIcon": "sys_ 前缀受控图标 fileName，如 sys_dashboard",
  "appColor": "官方 9 色板 HEX，如 #2196F3",
  "navLayout": "group | tree | top | card",
  "navColor": "appColor | white | gray | black",
  "enableExternalPortal": false,
  "requirements": ["可选：仅放应用级导航/设置/手册补充要求"],
  "navGroups": ["业务总览", "核心业务", "基础档案"],
  "worksheets": [],
  "customPages": [],
  "customActions": [],
  "workflows": [],
  "roles": [],
  "aiAssistants": []
}
```

### 1. 顶层属性约束
- **`orgId`**：当前组织 ID（与 MCP 工具 `orgId` 参数同名）。
- **`language`**：与当前会话锁定的语言代码一致（如 `"zh-CN"`、`"en"`、`"ja"`），下游构建子代理据此统一所有用户可见文本语言。
- **`appIcon` / `appColor`**：从 `../references/hap-icon-palette.md` 精确选取带 `sys_` 前缀的合法 `fileName` 与 9 色板 HEX 色值；`navLayout` 与 `navColor` 选型遵循 `../references/hap-domain-app-spec.md`。
- **`enableExternalPortal`**：规划了外部门户角色（`roleScope: "externalPortal"`）时必须设为 `true`。
- **`navGroups`**：完整覆盖 `worksheets`、`customPages`、`aiAssistants` 中用到的全部 `groupName`（逐字精确一致，严禁简写），决定分组创建与展示顺序。

### 2. 对象级 `requirements?: string[]` 补充要求通道
应用顶层、`worksheets[]`、`customPages[]`、`roles[]`、`aiAssistants[]`、`workflows[]` 以及 `customActions[].actions[]` 均可携带可选的 `requirements: string[]` 数组：
- 用于结构化传递紧凑字符串无法表达的用户定制细节（如顶层 `["采用顶部导航"]`，页面 `["四张指标卡均不显示图标"]`）；
- **跨对象要求按配置归属拆分**：引用方写清使用哪个对象，负责配置的一方优先用已有字段定义它（如 `views`、`fields`、`businessRulesNotes`、`intentHints`），其余细节写入该对象的 `requirements`。例如，销售工作台引用「销售订单」表的「我的草稿订单」视图，该表在 `views` 中声明 `我的草稿订单(Table)`，在 `requirements` 中写明该视图按「负责人是当前用户，且订单状态为草稿」筛选；流程要写入的字段和选项也应在目标表的 `fields` 中定义；
- 原有字段（如 `businessRulesNotes`、`intentHints`）能表达的内容直接写原字段，不在 `requirements` 重复；
- 按实际作用对象精准归属，严禁将具体表、页面或流程的要求笼统堆在顶层 `app.requirements`，无补充要求时省略该键。

---

## 二、 `worksheets`（工作表数组）

每个元素结构：`{ "name", "groupName", "description", "worksheetType"?, "parentWorksheet"?, "icon", "color", "fields", "views", "businessRulesNotes"?, "consistencyNotes", "requirements"? }`

- **`name`（去“表”后缀规范）**：使用纯粹业务实体名词（如 `客户`、`采购订单`、`中奖名单`），自动剔除口语中的“表/工作表”后缀（仅 `资产负债表`、`利润表`、`课程表` 等专有名词或用户显式强调保留时例外）。
- **`worksheetType` 与主子表双向闭环硬约束**：普通表为 `"normal"`（默认），明细子表为 `"subTable"` 且必填 `parentWorksheet`（主表名称）。**凡声明 `worksheetType: "subTable"` 的子表，其主表 `fields` 中必须 100% 包含对应的 `"子表名(SubTable:子工作表名)"` 字段，严禁出现孤立子表！**
- **全表无条件唯一索引声明**：明确要求某组字段在全表无条件唯一时，在本表 `requirements` 写明字段组合及必填要求；仅提交后按状态防重、允许多条空值草稿等条件约束按原业务条件规划（不由唯一索引承接）。
- **`icon`**：从 `../references/hap-icon-palette.md` 选取带 `sys_` 前缀的合法图标，同组内避免雷同。
- **`businessRulesNotes`**：字符串数组，用“意图 + 举例”的自然语言描述显隐、只读、动态赋值（含通过关联字段 `rcid` 自动带出所属站点/负责人）、本表字段对比校验（如“结束时间不早于开始时间”）或终态锁定规则（注意：关联候选框 `resultFilter` 不支持动态引用当前表单字段，跨表归属一致优先规划为“选子对象后自动带出归属站点/部门”或配合 `Lookup` 字段做同表校验）。
- **`consistencyNotes`（必填）**：简述本表选项字段如何支撑视图筛选、业务规则、动作条件与工作流流转。

### 1. `fields` 紧凑字符串语法
系统默认字段（创建时间/创建人/最近修改时间/修改人）严禁写入 `fields`。**单行与多行纯文本字段统一使用 `Text`（建表时通过 `config.textMode: "singleLine" | "multiLine"` 区分，绝对禁止编造不存在的 `Textarea`、`LongText` 或 `MultilineText`！），带图文排版使用 `RichText`**。专属业务语义必须使用 `PhoneNumber`、`Email`、`Currency`、`Collaborator`、`Department`、`Region`、`Location`、`AutoNumber`、`Signature`、`Barcode`，严禁降级为 `Text`/`Number`。
1. **选项字段**：`"状态(SingleSelect:待处理/进行中/已完成)"`（支持 `SingleSelect` / `MultipleSelect` / `Dropdown`，选项以 `/` 分隔）。
2. **跨表关联三态单边声明铁律**：`"字段名(Relation:目标表名:single|multiple:uni|bi|reverse)"`：
   - `:uni`（单向引用）：本表建选择框，目标表不生反向字段（用于选字典、仓库、商品主数据）；
   - `:bi`（双向主创建端）：仅由单边主动发起（`bidirectional: true`），服务端自动在对端生成反向 Tab 表格；**1:N 主从关系必须由 N 端从属表（`single` 单条端，尤其是需要 `Lookup` 的一端）主动声明 `:bi`**（如 `借阅记录` 写 `"关联图书(Relation:图书:single:bi)"`，`销售订单` 写 `"所属客户(Relation:客户:single:bi)"`）；
   - `:reverse`（双向反向承接端）：对端已声明 `:bi` 时，**1 端主表/聚合表（`multiple` 多条端）**如需透视标 `:reverse`（如 `图书` 写 `"借阅记录(Relation:借阅记录:multiple:reverse)"`），建表引擎自动跳过 API 调用，**严禁双边重复声明 `:bi`，也严禁在 `:reverse` 端挂 `Lookup`**。
3. **自关联与子表**：自关联 `"上级部门(selfRelation)"`；子表挂载 `"采购明细(SubTable:采购明细)"`。
4. **衍生计算字段**：主子表或多条关联主表必配 1～2 个汇总 `"总金额(Rollup:采购明细.金额.sum)"`（`sum/count/avg/max/min`）；按需配置他表字段 `"参考单价(Lookup:关联商品.销售单价)"`（**新建关系时由使用 `Lookup` 的单条端声明 `:bi` 或 `:uni`，使用同批关联别名创建 `Lookup`**）；数值计算使用 `"金额小计(Formula)"`、日期差值/加减使用 `"剩余天数(DateFormula)"`、业务单据标题推荐组合文本 `"单据全称(Concatenate)"`（需拼接他表名称时，在本表规划开启存储 `storeData: true` 的标量 `Lookup` 供表达式引用，严禁直接引用关联字段；`Formula` / `DateFormula` / `Concatenate` 括号内仅写类型名，具体计算表达式与单位写入该表 `requirements`，无需去翻阅构建脚本源码）。
5. **字段丰富度**：主数据表 ≥ 15 个、业务单据表 ≥ 12 个、过程流水表 ≥ 8 个、子表 ≥ 3 个，覆盖主标识、核心属性、状态分类、时间、责任人、数量金额、说明凭证、计算衍生 8 个维度。

### 2. `views` 紧凑字符串语法
格式 `"视图名(Type)"`，`Type` ∈ `Table | Kanban | Calendar | Gantt | Gallery | Detail | Hierarchy | Map | Resource`，所依赖分组/日期/自关联/定位字段必须在 `fields` 中真实存在。

---

## 三、 `customPages`、`customActions`、`workflows`、`roles`、`aiAssistants`

1. **`customPages`（自定义页面数组）**：
   - 公共属性：`name`、`groupName`、`type`（`"dashboard"` 或 `"workspace"`）、`description`、`icon`（从 `../references/hap-icon-palette.md` 选取带 `sys_` 前缀的合法图标，如 `"sys_control-panel_traffic"`、`"sys_hr_workbench"`）、`color`、`requirements`?。
   - `type: "dashboard"` 必填 `charts`（紧凑格式 `"名称(chartType)"`，建议 6～10 项：1 个 `"全局筛选(FiltersGroup:维度1,维度2)"` + 4～6 个 `numberChart` + 趋势/占比/排行图 + `pivotTable`，图表类型严格使用小驼峰标准 MCP `chartType`）。
   - `type: "workspace"` 必填 `components`（紧凑格式 `"名称(Type)"`，`Type` ∈ `Button | View | Text | Carousel | Section`）；新建应用若没有对应的已发布且启用的封装业务流程（PBP），页面按钮按实际操作规划新建记录或打开待处理视图等入口（需要执行审批等动作时，由相应业务流程或工作表自定义动作承接）；有实际展示需求和可用内容时才规划 `Carousel`（并在 `description` 写明面向整页还是特定业务区），明确需要跨组件联动筛选时在页面 `requirements` 写明筛选条件与受影响组件。
   - 可选 `viewBindings` 用于明确 View 组件到工作表与视图的绑定，例如 `{"待出库": {"worksheet": "出库单", "view": "待出库"}}`；键为 `components` 中的组件名称，两个值必须逐字匹配已规划对象。此映射兼容旧方案：缺省时根据已确认的方案和真实视图语义解析，不新增必填键。
   - 页面 `requirements` 写明待办组件引用的目标工作表与视图，以及每个图表的数据源、指标、聚合、维度与时间范围；被引用视图的具体筛选口径与定义归属对应工作表的 `views` 与 `requirements`，不能将不同语义映射为同一个无筛选视图或同一指标。旧方案缺少该信息时从已确认总览和字段、视图语义推导，无法确定的标记缺口，不新增固定确认门禁。
2. **`customActions`（按工作表分组的自定义动作数组）**：
   - 元素结构：`{ "worksheet": "工作表名", "requirements"?, "actions": [{ "name", "description", "type", "runWorkflowAfterSubmit"?, "targetWorksheet"?, "relateFieldName"?, "enableCondition"?, "intentHints"?, "requirements"? }] }`。
   - 每个动作在已有 `enableCondition`、`intentHints` 或 `requirements` 中明确执行角色、可执行状态、成功结果及失败/重复执行边界；审批发起、审批结果与库存执行分开表述，不把共同模板机械套用到所有动作。已有方案字段保持兼容，不因补全新增强制协议键。
   - 遇到库存过账等跨表写入，在上述字段中写明业务唯一键、余额来源和重复提交的处理。按实际需求决定是否需要并发扣减保护，结合当前平台能力核实实现。能力尚未查实时，继续设计与其独立的审批、记录和页面。使用角色审批时记录角色及其适用单据，供角色和工作流步骤共用。
   - **三类 `type` 人工输入边界铁律（严禁选错类型！）**：
     - `"createRelatedRecord"`：**操作需收集人工输入并在另一张表新增记录**（如在 `图书` 点「发起借阅」填读者与应还日期新建 `借阅记录`，或在 `借阅记录` 点「登记异常」新建 `异常赔偿`）。必填 `targetWorksheet` 与源表 `fields` 中**已显式声明**的 `relateFieldName`（指向 `targetWorksheet` 的 `Relation` 字段名；若源表尚未声明该关联字段，必须先在源表 `fields` 补上该 `Relation` 字段！）；提交后需自动改状态/扣库存则设 `runWorkflowAfterSubmit: true` 并配 `intentHints`。
     - `"updateCurrentRecord"`：**操作需收集人工输入以更新当前记录字段**（如在 `借阅记录` 点「申请续借」输入新应还日期与续借原因）。当前表 `fields` 中必须真实存在对应承接字段，并在动作 `requirements` 中指明待填字段名；提交后需自动流转则设 `runWorkflowAfterSubmit: true` 并配 `intentHints`。
     - `"triggerWorkflow"`：**仅限 100% 零人工输入的一键自动操作**（点击后不弹任何表单，仅依赖当前记录已有字段、`triggerUser` 与当前系统时间即可完成，如「确认归还」「提交审批」）。必填 `intentHints: [{ "label": "..." }]`，严禁将需要点击人现场输入读者、日期、金额、原因或类型的动作设为 `"triggerWorkflow"`！
3. **`workflows`（系统自动化工作流数组）**：
   - 元素结构：`{ "name", "description", "trigger": { "type": "worksheet_event | schedule | date_field", "source": "工作表名或空串", "label": "触发条件描述" }, "intentHints": [{ "label": "..." }], "requirements"? }`（注：按钮动作流写在 `customActions` 中，不放入 `workflows`）。
   - **严禁与按钮动作流重复更新同一状态**：若某项业务流转已通过 `customActions` 中的按钮（如 `createRelatedRecord` 或 `updateCurrentRecord` 开启 `runWorkflowAfterSubmit: true`）完成主单据状态更新（如点击「登记完成」新建执行记录后将计划更新为“已完成”），**严禁在 `workflows` 中再重复规划一条监听该明细表新增事件去更新同一个主单据状态的系统工作流**，保持状态更新责任单一清晰。
4. **`roles`（角色权限数组）**：
   - 元素结构：`{ "name", "description", "roleScope": "general | externalPortal", "permissions": ["名称(worksheet)", "名称(customPage)", "名称(aiAssistant)"], "requirements"? }`。
   - 在 `requirements` 记录角色对各表的实际业务操作、数据范围、允许动作、必要的关联表/子表/视图访问以及系统维护字段的保护要求。**按人/按归属鉴权设计衔接**：需要“仅查看和处理分派给本人的记录”时，在对应业务表规划责任成员字段（如执行人、巡检人、维修人员、负责人，建表设 `userPermission: 2` 拥有者权限），角色配 `recordDataScope: 20` 即可原生按成员字段鉴权；跨表按所属站点/项目负责人管理时，在单据表保留负责人成员字段并由业务规则从所属站点/项目自动带出。
5. **`aiAssistants`（AI 智能助手数组）**：
   - 元素结构：`{ "name", "groupName", "description", "icon": "sys_virtual-assistant_office", "color": "#9C27B0", "requirements"? }`（`icon` 必须带 `sys_` 前缀）。

---

## 四、 落盘前闭环自检清单

1. `navGroups` 100% 逐字覆盖所有工作表、自定义页面与 AI 助手的 `groupName`；所有 `icon` 均带合法 `sys_` 前缀；
2. 所有 `worksheetType: "subTable"` 子表均在 `parentWorksheet` 主表 `fields` 中有唯一对应的 `SubTable` 字段及至少 1 个 `Rollup` 字段；
3. 跨表关联严格遵守 `:bi` 单边发起、对端 `:reverse`、字典 `:uni`，零双边重复 `:bi`；
4. **自定义动作输入入口闭环**：逐个检查 `customActions`——凡需人工输入信息的动作严禁用 `triggerWorkflow`；`createRelatedRecord` 的 `relateFieldName` 在源表 `fields` 中真实存在且指向 `targetWorksheet`；`updateCurrentRecord` 待填字段在当前表 `fields` 中真实存在；严禁出现「审批通过/审批驳回」按钮；
5. 所有 `triggerWorkflow` 及 `runWorkflowAfterSubmit: true` 的动作均包含完整的 `intentHints`。
