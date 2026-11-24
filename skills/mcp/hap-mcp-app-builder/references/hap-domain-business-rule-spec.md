# HAP 业务规则领域规范

本规范以 `hap-app-copilot/references/spec-business-rules.md` 为完整基线，保留其业务场景、条件、动作、安全和锁定选型规则，并按当前 HAP MCP 工具契约补齐四类规则及修改能力。业务规则作用于新建表单和记录详情页，创建后会直接改变所有使用该表单用户的行为。

## 一、业务规则定位与核心设计场景

业务规则在表单加载（`onLoad`）及字段值发生变化（`onChange`）时实时触发，主要覆盖以下场景。

1. **动态显隐与联动录入**
   - 当“业务类型”选择“其他”时，动态显示“补充说明”。
   - 当“是否需要发票”勾选时，动态展开“发票抬头”“纳税人识别号”所在分段。
2. **条件只读保护与动态必填**
   - 当“单据状态”为“已归档”或“审批中”时，将核心业务字段设为只读。
   - 当“审批结果”为“已拒绝”时，将“拒绝原因”设为必填。
3. **业务校验与防错拦截**
   - 当“报销金额”大于 50,000 时显示错误提示并阻止提交。
   - 当数据违反可由当前条件语法表达的约束时，提示逻辑错误并拦截保存。
4. **条件样式提示**
   - 当状态、优先级或风险等级满足条件时，高亮字段标题或字段值。
5. **终态记录封存**
   - 单据已审批、已归档、已结单或已作废后，锁定整条记录并禁止删除。

业务规则适合表单内的条件交互和校验；无条件的必填、只读、默认值优先使用字段自身配置。持续计算、填写时取值或用户明确要求的前端事件按 `hap-domain-worksheet-spec` 选型，不能用前端提示代替服务端校验。业务规则不承担跨表查询或外部调用；保存后、定时及延时处理使用工作流，不为同一行为重复配置。

## 二、四类规则

| ruleType | 专用配置块 | 适用行为 |
|---|---|---|
| `interaction` | `actions[]` | 显示、隐藏、可编辑、只读、必填、全表只读、字段赋值 |
| `validation` | `validation` | 显示错误或警告，阻止提交或允许忽略后提交 |
| `lock` | `lock` | 终态物理封存，锁定编辑和删除，每张工作表最多一条 |
| `style` | `style` | 设置字段标题和值的颜色、字号和文字样式 |

每条规则都需要：

- 真实 `worksheet_id`；
- 清晰且使用应用语言的 `name`；
- `ruleType`；
- `enabled`，默认 `true`；
- 有效且非空的 `conditions`；
- 与 ruleType 对应且仅对应的配置块。

不想立即影响现有用户时，以 `enabled: false` 创建或先停用后修改。

## 三、触发条件 Conditions

### 3.1 非锁定规则的条件组

`interaction`、`validation`、`style` 的根节点必须是 group，即使只有一个条件也要包裹：

```json
{
  "type": "group",
  "logic": "AND",
  "children": [
    {
      "type": "condition",
      "fieldId": "<真实字段 ID>",
      "operator": "eq",
      "value": ["已完成"]
    }
  ]
}
```

- group 的 `logic` 必须是 `AND` 或 `OR`，children 必须非空。
- 最多两层 group，即 `group -> group -> condition`。
- 同一个 group 的 children 应全部是 group 或全部是 condition，不混合。
- condition 的 `fieldId` 必须来自目标工作表真实字段结构；从 Markdown 提取时移除 `(isTitle)` 等说明后缀。

### 3.2 锁定规则的单条件

`ruleType=lock` 的根节点仍为 `group`，但 `children` 中仅支持包含 1 个原子 `condition`：

```json
{
  "type": "group",
  "logic": "AND",
  "children": [
    {
      "type": "condition",
      "fieldId": "<状态字段真实 ID>",
      "operator": "in",
      "value": ["已归档", "已作废"]
    }
  ]
}
```

锁定条件字段只支持 SingleSelect、MultipleSelect、Checkbox（不支持 Dropdown 下拉单选）。复杂条件或非上述三类字段不能勉强改写成 lock，应改用 `interaction + readonlyAllFields`；如果必须同时禁止删除，则需要调整业务模型或拆分终态字段，使其满足锁定条件约束。

### 3.3 操作符和值

| 操作符 | 语义 | value |
|---|---|---|
| `eq` / `ne` | 等于 / 不等于 | 字符串、数字或适用的数组 |
| `gt` / `ge` / `lt` / `le` | 大于、大于等于、小于、小于等于 | 数字或日期字符串 |
| `in` / `notin` | 属于 / 不属于给定集合 | 数组 |
| `contains` / `notcontains` / `concurrent` | 包含、不包含、同时包含 | 按字段类型传字符串或数组 |
| `belongsto` / `notbelongsto` | 属于 / 不属于组织或层级 | ID 数组 |
| `startswith` / `notstartswith` | 开头是 / 不是 | 字符串 |
| `endswith` / `notendswith` | 结尾是 / 不是 | 字符串 |
| `between` / `notbetween` | 在 / 不在区间 | 两元素数组 |
| `isempty` / `isnotempty` | 为空 / 非空 | 不传 value |

基线中的 `not_in`、`gte`、`lte`、`is_null`、`not_null` 在当前 MCP 中分别使用 `notin`、`ge`、`le`、`isempty`、`isnotempty`。

- 选项字段可以直接传选项名称；必须与工作表真实选项一致。
- Collaborator 等成员字段可使用 `user-self`、`user-sub`、`user-workflow`、`user-api`，或真实实体 ID。
- 同一选项字段匹配多个可能值时，必须使用一个 `in` 条件加 value 数组。不得拆成多个 `eq` 后用 AND 连接。
- 字段间比较优先使用当前工具 Schema 支持的动态字段值条件（`businessRuleDynamicValue`），核对两侧类型及操作符适用范围；例如“结束时间早于开始时间”直接传 `value: { "sourceType": "field", "sourceField": { "sourceType": "currentFormField", "field": "<本表另一字段ID或alias>" } }`，无需默认增加公式辅助字段或工作流。比较关联记录字段时两侧须指向同一目标工作表（若需校验所选子对象与本表归属一致，可先在本表配置 `Lookup` 带出关联对象的归属字段，再用动态字段值条件与本表归属字段比较，或直接用下方 `setFieldValue` 的 `rcid` 自动带出归属字段）。不能把另一个字段 ID 作为普通字符串常量传入。

## 四、Interaction 执行动作

条件满足时执行 `actions` 数组，一条规则可以包含多个动作。

| actionType | 字段配置 | 行为 |
|---|---|---|
| `show` | `fields[]` | 满足条件时显示字段或 Divider，不满足时自动隐藏 |
| `hide` | `fields[]` | 满足条件时隐藏字段或 Divider |
| `readonly` | `fields[]` | 将指定字段设为只读 |
| `readonlyAllFields` | 不传 fields | 将当前表单全部字段设为只读，仍可按权限删除记录或触发动作 |
| `editable` | `fields[]` | 将指定字段恢复为可编辑，并可控制子表 / 关联记录操作权限 |
| `required` | `fields[]` | 将指定字段设为必填 |
| `setFieldValue` | `assignments[]` | 设置、清空字段或复制当前表其他字段的值 |

基线中的 `optional` 当前未由 MCP actionType 暴露，不得虚构调用；需要动态选填时优先反向设计触发条件，仅在条件满足时施加 `required`。基线中的 `error_prompt` 不是 interaction actionType，应转换为 `ruleType=validation`。

显隐规则优先使用 show 表达“满足条件才出现”的正向语义。多条规则不得对同一字段施加互斥动作，例如一条 required、另一条 hide，导致字段无法填写却阻止提交。

### 4.1 普通字段与 RuleField

普通字段可直接使用真实字段 ID 字符串。关联记录或子表需要对子字段和操作权限精确控制时，使用 RuleField：

```json
{
  "fieldId": "<关联记录或子表字段 ID>",
  "includeMainField": true,
  "childFieldIds": ["<子字段 ID>"]
}
```

- `includeMainField` 表示动作是否同时作用于主字段。
- `childFieldIds` 是关联记录或子表的真实子字段 ID。
- `permissions` 仅用于 `editable`（非 `editable` 动作严禁传 `permissions`，包括空对象 `{}`）：
  - 子表：`enableCustomPermissions`、`allowAddRows`、`allowEditRows`、`allowDeleteRows`；
  - 关联记录：`enableCustomPermissions`、`allowSelectExistingRecords`、`allowUnlinkRecords`。
- 权限键只有在当前工具契约能确定布尔值含义时才配置，不猜测缺失默认值。

### 4.2 Divider 分段联动

- 对 Divider 使用 show / hide 可以联动展开或收起其视觉区块。
- 当一条规则逐项隐藏某分段内全部字段时，应把 Divider 一并作为目标，避免留下空标题或空白分段。
- 根据字段布局确认 Divider 的管辖范围，不只按名称猜测。

### 4.3 setFieldValue（支持本表字段复制与 `rcid` 跨表关联字段读取赋值）

`setFieldValue` 不使用 fields，必须使用 assignments：

```json
{
  "actionType": "setFieldValue",
  "assignments": [
    {
      "field": "<目标字段 ID 或 alias>",
      "value": { "sourceType": "static", "staticValue": "已受理" }
    },
    {
      "field": "<清空目标字段 ID 或 alias>",
      "value": { "sourceType": "empty" }
    },
    {
      "field": "<目标字段 ID 或 alias>",
      "value": {
        "sourceType": "field",
        "sourceField": {
          "sourceType": "currentFormField",
          "field": "<当前表单来源字段 ID 或 alias>"
        }
      }
    },
    {
      "field": "<本表目标字段 ID 或 alias（如所属站点/负责人）>",
      "value": {
        "sourceType": "field",
        "sourceField": {
          "sourceType": "currentFormField",
          "rcid": "<本表关联字段 ID 或 alias（如设备/灌区地块/所属站点）>",
          "field": "<关联目标表中的来源字段 ID 或 alias（如设备表中的所属站点/站点表中的负责人）>"
        }
      }
    }
  ]
}
```

- `staticValue` 统一传字符串，并符合目标字段类型；选项字段传真实选项名称。
- `empty` 不传 staticValue 或 sourceField。
- **`field` 支持两种取值范围**：
  1. **不带 `rcid`**：复制当前表单其他字段的值；
  2. **携带 `rcid`（跨表关联读取赋值）**：`rcid` 传当前表单中已配置目标表的 `Relation` / `SubTable` / `CascadingSelect` 字段 ID 或 alias，`field` 传**该关联目标表**中的真实字段 ID 或 alias（关联记录类型赋值时两侧须指向同一目标工作表）。**与字段默认值分工**：无条件“选单条关联带出可编辑初始值”优先由字段原生 `defaultValue(source="relation")` 承接，不重复建 `setFieldValue + rcid` 规则；`rcid` 赋值用于需条件触发、配合 `readonly` 强制锁定防篡改（如选择「设备」或「地块」后强制同步其「所属站点」并只读以保证跨表归属一致），或字段默认值不支持的场景。
- 目标字段和来源字段类型应兼容。

## 五、Validation 验证规则

```json
{
  "ruleType": "validation",
  "validation": {
    "message": "报销金额必须大于 0",
    "errorAction": "blockSubmit",
    "fields": ["<金额字段 ID>"],
    "promptOnFieldInput": true,
    "validateOnServerSave": true
  }
}
```

- `message` 和 `errorAction` 必填。
- `blockSubmit` 阻止提交；关键数据合法性校验应同时设置 `validateOnServerSave: true`，覆盖 API、导入等服务器保存路径。
- `ignoreAndSubmit` 只用于警告，`validateOnServerSave` 必须为 false 或不传。
- fields 可将错误提示关联到一个或多个真实字段，也可使用 RuleField。
- `promptOnFieldInput` 用于需要输入时即时反馈的场景；避免对复杂或高成本条件滥用。

## 六、Style 样式规则

```json
{
  "ruleType": "style",
  "style": {
    "fields": ["<风险等级字段 ID>"],
    "titleStyle": { "color": "#f52222ff", "bold": true },
    "valueStyle": { "color": "#f52222ff", "fontSize": "1.2", "bold": true }
  }
}
```

- titleStyle 与 valueStyle 支持 `color`、`fontSize`、`bold`、`italic`、`underline`、`strikethrough`。
- fontSize 使用 `1`、`1.2`、`1.4`、`1.6`、`1.8`。
- 关联记录和子表字段只支持 titleStyle，不配置 valueStyle。
- 样式用于提示，不替代验证、权限或锁定。

## 七、终态锁定与全表只读选型

| 维度 | `ruleType=lock` | `interaction + readonlyAllFields` |
|---|---|---|
| 核心定位 | 记录终态物理封存 | 表单输入动态只读 |
| 删除操作 | 同时禁止删除记录 | 仍可按权限删除记录 |
| 前台视觉 | 显示系统锁头和 `lock.message` | 输入框置灰，无锁头提示 |
| 条件要求 | 单一 condition，仅限 SingleSelect / MultipleSelect / Checkbox | group 条件，支持多条件与更广字段类型 |
| 典型场景 | 已审批、已归档、已结单，防止篡改与删除 | 审批中只读、查看模式、外部同步流水 |

每张工作表只能有一条 lock。若已有 lock，应合并其终态条件，不能再创建第二条。

## 八、创建与修订规则

### 8.1 创建前

1. 获取目标工作表的真实字段结构，确认条件字段、目标字段、选项和 Divider 布局。
2. 仅在目标工作表已有规则、可能存在同名/同类规则或需要确认 lock 唯一性时调用 `get_business_rule_list`；新建空表且本批次没有既有规则时不为形式完整而查询。
3. 规则影响所有表单用户；不确定时先以 `enabled: false` 创建。

### 8.2 修改

- 复用真实 ruleId 及有效完整配置；缺完整配置才定向调用 get_business_rule_detail，只有必要身份缺失时先定位规则。
- `update_business_rule` 是整条覆盖，不是 PATCH。即使只改名称或 enabled，也必须基于详情回传完整的 name、ruleType、conditions 和相应配置块。
- conditions 必须有效且非空，不能省略、传 null、空对象或空 children。
- ruleType 不能直接变更。确需换型时应作为“删除旧规则并创建新规则”的显式迁移处理，先评估短暂行为变化和删除风险。
- 修改启用中的规则会立即改变表单行为；高风险修订可先完整覆盖为 disabled，确认配置后再启用。

### 8.3 停用与删除

- 明确停用指定规则时用 update_business_rule，传 enabled: false；复用有效完整详情或定向读取后回传完整条件、动作及其他属性。
- 删除使用 delete_business_rule，无需为删除读取完整详情或留存快照，不承诺可恢复。
- 删除/停用会停止该规则的表单交互及服务器保存校验效果；修订授权统一遵循 hap-revision-safety。

## 九、安全与防冲突检查

1. worksheet_id、ruleId、fieldId、childFieldIds 是否来自真实结构？
2. conditions 是否非空，且 lock 与其他类型使用了正确的根结构？
3. ruleType 是否只携带对应配置块？
4. 多值条件是否使用单个 in 加数组？
5. required 与 hide、readonly 与 editable 等动作是否在重叠条件下冲突？
6. 显隐整个分段时是否正确处理 Divider？
7. validation 是否正确选择 blockSubmit / ignoreAndSubmit 与服务器校验？
8. lock 是否保持每表唯一，且确实需要同时禁止删除？
9. update 是否基于详情整条回传，删除是否已核实目标并获得明确授权？
