# Roles — 应用角色（顶层 `roles[]`）

`hide_app_for_members`：对成员隐藏应用。

## 细粒度配置（`permission_scope` = "0"）

`worksheet_permissions[]` + `page_permissions[]`，工作表/字段/视图/页面按逻辑名引用：

```jsonc
{ "name":"访客","permission_scope":"0",
  "worksheet_permissions":[
    { "worksheet":"出库单",
      "data_scope":{ "read":100, "edit":0, "delete":0 },        // 0未授权/20仅自己/30自己及下属/100全部
      "record_actions":{ "add":false, "share":false },
      "fields":[ { "field":"成本价", "read":false } ],           // 只列要细控的字段，其余默认 true
      "views":[ { "view":"出库看板", "read":true, "edit":false, "delete":false } ] } ],
  "page_permissions":[ { "page":"仓储看板", "enable":true } ],
  "chatbot_permissions":[ { "chatbot":"仓储助手", "enable":true } ] }
```

## AI 助手访问（`chatbot_permissions`）

控制该角色能访问哪些 AI 助手（顶层 `chatbots[]` 里定义的助手，按逻辑名引用）。

- **省略 `chatbot_permissions`（默认）**：该角色可访问应用内**全部** AI 助手。
  绝大多数应用的助手就是给业务用户用的，默认开放即可——不写这一项就行。
- **提供 `chatbot_permissions`**：转为白名单语义——只有列出且 `enable:true` 的助手
  可访问，未列出的助手对该角色一律关闭。仅在需要**限制**某些角色（如外部访客）
  不能用某个助手时才显式写。

> 不写 `chatbot_permissions` 是常态。只有要收紧时才列。

> 坑（执行器已自动处理）：服务端要求**发该工作表的全部字段+全部视图**权限才生效，handler 会自动补全你没列出的字段/视图为默认。
> 你只需列出**要偏离默认**的字段/视图即可。

## 成员

`members`：`{ users:[accountId...], departments, department_trees, jobs, org_roles }`。冒烟/建应用默认把当前登录者加进角色，真实成员可后续在 UI 或用 `hap` 命令补。

---

## 权限推理规则

### permission_scope（强制使用 "0"）

> [!CAUTION]
> **所有角色必须使用 `permission_scope: "0"`（精细权限分配）。** 禁止使用 "80"/"60"/"30"/"20" 等全局快捷值。精细权限能产出更专业、更安全的角色配置，必须为每个角色配置完整的 `worksheet_permissions` 和 `page_permissions`。

### worksheet_permissions

为应用中该角色涉及到的每张表，在 `worksheet_permissions[]` 里配置一项（`worksheet` 为表逻辑名）：

#### data_scope（记录数据范围）
- `read`：0=无权查看, 20=只看自己, 30=自己及下属, 100=查看全部
- `edit`：0=无权编辑, 20=只编辑自己, 30=自己及下属, 100=编辑全部
- `delete`：0=无权删除, 20=只删除自己, 30=自己及下属, 100=删除全部
- 省略各项默认 100。

#### actions（工作表操作，省略各项默认 false）
- `shareView`：是否可分享视图（通常只有管理角色开启）
- `import`：是否可导入数据
- `export`：是否可导出数据（财务、管理类角色开启）
- `discuss`：是否可发起讨论（默认 true 的业务习惯，可显式开启）
- `batchOperation`：是否可批量操作（管理类角色开启）

#### record_actions（行记录操作，省略各项默认 false）
- `add`：是否可新增记录
- `share`：是否可分享记录
- `discuss`：是否可讨论记录
- `systemPrint`：是否可打印（单据类业务开启）
- `attachmentDownload`：是否可下载附件
- `log`：是否可查看操作日志（管理类角色开启）

#### pay（支付权限）
- `pay`：是否有支付权限（默认 false）

#### 其他级联权限（仅在特定场景使用）
- `views`：视图下的行记录权限。**只列出要偏离默认的视图**（按视图逻辑名），每项 `{ "view":逻辑名, "read":bool, "edit":bool, "delete":bool }`，省略默认 true。未列出的视图由执行器自动补为默认全开——不需要也不要手写 viewId。
- `fields`：字段级权限。**仅在需要隐藏或保护某几个字段时列出**（按字段逻辑名），例如只读 `{ "field":逻辑名, "edit":false }`、隐藏 `{ "field":逻辑名, "read":false }`。未列出的字段由执行器自动补为默认全开。
- `page_permissions`：自定义页面权限，每项 `{ "page":页面逻辑名, "enable":true }`。页面名必须是已定义的自定义页面（`validate` 合并后会做存在性检查）。
  > **拆分生成时**：角色分片（03）与自定义页面分片（05）由不同子代理并行产出，所以 `page` 引用的页面名**必须严格用地基锁定的「自定义页面清单」里的名字**，否则合并校验会报「page … not found in custom_pages」。

---

## 推理原则

1. **基于描述深度推演**：角色涉及的表/页面仅告诉你该角色需要访问哪些表和仪表盘，**你必须深刻理解角色的 `description` 语义**来分配详细权限。例如，如果描述表明只是"查阅/汇总"，则绝不能给 `edit` 或 `delete` 权限。

2. **默认职能惯例参考**：
   - 未体现为可见范围的工作表：`data_scope` `read:0, edit:0, delete:0`，且 `record_actions.add:false`（或干脆不在该角色的 `worksheet_permissions` 中列出该表）。
   - 普通业务角色（销售、内勤）：通常只对自己负责的数据有写权限（`read:100, edit:20, delete:20`）。
   - 管理类角色（主管、总监）：通常具有所有数据的写权限（`read:100, edit:100, delete:20/100`）。
   - 只读巡查角色（老板、审计）：全局或指定表的只读（`read:100, edit:0, delete:0`）。
