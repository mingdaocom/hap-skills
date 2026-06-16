# 应用角色与权限

## 调用范式

```bash
# 列出角色 / 查看某角色完整权限明细
hap app role list -a <appId>
hap app role permissions <roleId> -a <appId>

# 粗粒度创建（permission-scope > 0，按整体范围授权）
hap app role create -a <appId> --name "运营" --description "运营人员" \
  --type 0 --permission-scope 20

# 细粒度创建（permission-scope 0 的推荐入口：逐表声明意图，未写到的部分自动补全为允许）
hap app role create-fine <appId> -n "区域经理" -d "只能看和改自己的记录" \
  --worksheet-permissions '[{"worksheetId":"<wsId>",
    "recordDataScope":{"read":20,"edit":20,"delete":0}}]' \
  --page-permissions '[{"pageId":"<pageId>","enable":true}]'

# 改名与改权限是两条独立命令，互不影响
hap app role rename <appId> <roleId> -n "新名字"
hap app role set-permissions <appId> <roleId> --permission-way 10

# 成员增删（平铺 id 选项，可重复传入，一次一个 id）
hap app role add-member <roleId> -a <appId> \
  --user-ids <accountId> --user-ids <accountId2> --department-ids <deptId>
hap app role remove-member <roleId> -a <appId> --user-ids <accountId>

# 删除角色
hap app role delete <roleId> -a <appId> -y
```

坑位提示：

- **`rename` 与 `set-permissions` 是两条命令**。改名不会动权限，改权限不会动名字；不要试图用一条命令同时做两件事。
- `create` 用 `--permission-scope 0` 时**必须带非空 `--worksheet-permissions-json`**，且每条目必须是完整结构（所有子对象齐全、工作表键名为 `id`）——缺子对象的条目会被拒绝。日常细粒度需求直接用 `create-fine`：它接受简化意图（键名 `worksheetId`），自动拉取该表的字段与视图把结构补全。
- `set-permissions` 适合粗粒度的 `--permission-way` 调整；`-P` 传细粒度 JSON 的写入路径未充分验证，细粒度需求优先用 `create-fine` 新建角色替换。
- 成员选项是**平铺的 id 列表**（`--user-ids <id>` 重复传即可），**与工作流收件人那套嵌套结构（type/entityId/accounts）完全无关**，不要往这里塞对象。
- **排障范式：成员登录后"看不到内容 / 某表打不开"**：
  1. `hap app role permissions <roleId> -a <appId>` 看该角色完整权限；
  2. 若 `permissionScope` 为 0，逐项检查 `worksheetPermissions` 里对应表的 `recordDataScope.read` 是否为 0、`fieldPermissions` 是否把字段 read 关了；
  3. 检查 `pagePermissions` 里目标自定义页面的 `enable` 是否为 false；
  4. 检查 `hideAppForMembers` 是否为 true（成员入口直接隐藏）；
  5. 确认成员确实在该角色里（`hap app role list -a <appId>` 带成员信息）。

## 数据字典

字典生成于 2026-06-10；未覆盖的键以读命令返回的实际结构为准。

### 角色主体（create 的请求体 / permissions 的返回主体）

| 键 | 含义 | 值形态 |
|---|---|---|
| name | 角色名 | string（必填） |
| description | 角色描述 | string（必填） |
| hideAppForMembers | 对该角色成员隐藏整个应用 | bool |
| type | 角色类型，自定义角色固定 0 | int enum {0} |
| permissionScope | 粗粒度范围：80=全部可查看/编辑/删除；60=查看全部、仅编辑/删除自己的；30=仅加入的项、仅编辑/删除自己的；20=仅查看；0=逐项细粒度 | int enum {0,20,30,60,80} |
| globalPermissions | 应用级动作开关，仅 permissionScope > 0 时生效 | object，见下表 |
| worksheetPermissions | 逐表权限明细，仅 permissionScope == 0 时生效 | array，见下表 |
| pagePermissions | 逐自定义页面可见性，仅 permissionScope == 0 时生效 | `[{id:"<pageId>", enable:bool}]` |

### globalPermissions（8 个布尔开关，全部必填）

| 键 | 含义 | 值形态 |
|---|---|---|
| addRecord | 新增记录 | bool |
| share | 公开分享视图与记录 | bool |
| import | 导入 | bool |
| export | 导出 | bool |
| discuss | 讨论 | bool |
| systemPrint | 系统打印 | bool |
| attachmentDownload | 附件下载 | bool |
| log | 查看记录日志 | bool |

### worksheetPermissions[] 条目（scope 0 时每条必须完整）

| 键 | 含义 | 值形态 |
|---|---|---|
| id | 工作表 id（注意键名是 `id`，不是 `worksheetId`） | string |
| recordDataScope | 行级读/改/删范围 | `{read, edit, delete}`，各为 int enum：0=无权限，20=仅自己的，30=自己及下属的，100=全部 |
| worksheetActions | 表级动作 | `{shareView, import, export, discuss, batchOperation}` 全 bool |
| paymentActions | 支付 | `{pay: bool}` |
| recordActions | 记录级动作 | `{add, share, discuss, systemPrint, attachmentDownload, log}` 全 bool |
| recordPermissionInViews | 按视图的行权限 | `[{viewId, read, edit, delete}]`（bool） |
| fieldPermissions | 按字段的权限 | `[{id:"<controlId>", add, read, edit, decrypt?}]`（bool；decrypt 可选） |

`create-fine` 意图补全默认值：recordDataScope → read/edit/delete 全 100；worksheetActions → 仅 discuss 为 true；recordActions → add/discuss/attachmentDownload 为 true，其余 false；fieldPermissions → 每字段 read/edit/add true、decrypt false；视图 → 全部可读（除非给了允许清单）。`create-fine` 的意图 JSON 用 `worksheetId` 作键，落库时转换为 `id`。

### set-permissions（粗粒度）

| 键 | 含义 | 值形态 |
|---|---|---|
| permission-way | 角色粗类型 | int enum：0=自定义，10=只读，50=成员，100=管理员 |
| permissions (-P) | 细粒度权限 JSON | object（写入路径未充分验证，慎用） |

### add-member / remove-member 平铺 id 选项

均为可重复的字符串选项（一次一个 id），与工作流收件人结构无关。

| 选项 | 含义 | 适用 |
|---|---|---|
| --user-ids | 用户（账号）id | add / remove |
| --department-ids | 部门 id | add / remove |
| --department-tree-ids | 部门树 id（含子部门） | add / remove |
| --job-ids | 职位 id | add / remove |
| --project-organize-ids | 组织角色 id | 仅 add |
| --org-role-ids | 组织角色 id | 仅 remove |
