---
name: hap-cli-app-editor
description: 用 hap 命令行工具（CLI）修改一个已存在的 HAP 应用里的某个具体元素时用本 skill。只要用户说「在某表加个字段」「把这个视图改名」「修改工作流」「给某角色加权限」之类、针对已有应用做单点局部修改，就触发。不触发：增删改业务记录、查询数据、写调 hap 的代码；从零搭整个新应用请改用 hap-cli-app-creator。
---

# HAP 应用编辑器（细粒度元素 CRUD）

你对一个**已存在**的 HAP 应用做精确的局部修改：增、删、改单个元素（工作表 / 字段 / 视图 / 角色权限 / 自定义动作 / 工作流与节点 / 自定义页面与组件 / 应用与分组）。 如果是要增删改业务数据，请遵从 `hap-cli` 主 Skill 直接调用 `hap` 命令.

## 核心模型：两个入口，按危险度分流

**默认入口是裸 `hap` 命令** —— 绝大多数元素编辑就是一条命令：

```bash
hap worksheet view update <ws_id> <view_id> --name "进行中的订单"
hap workflow publish <process_id>
hap app role add-member <role_id> --user-ids <account_id> -a <app_id>
```

**只有三类编辑走 edit-spec（`hap app-editor`）**，因为它们的安全写法是「读出整体 → 改一处 → 整体写回」，徒手做容易静默丢数据：

| 编辑对象 | edit-spec op | 为什么不能裸做 |
|---|---|---|
| **已有字段**的修改/删除/重排 | `field.update` / `field.delete` / `field.reorder` | 必须整表控件集写回，否则系统反向控件会被静默丢掉 |
| **页面组件**增删改 | `component.add` / `component.update` / `component.delete` | 页面布局是一个整体 components 数组，必须读改写 |
| **动作按钮**新建/修改 | `custom-action.create` / `custom-action.update` | 高层 action_spec 自动翻译成按钮配置并接好关联流程 |

（新增字段 `field.add` 也在 edit-spec 里，与其它 field op 用同一份写法。）其余一切元素——工作表、视图、角色、工作流、节点、页面本身、应用与分组——**直接用命令**，各模块的命令与参数字典见下方索引。

## 前置条件

1. **登录**：`hap auth whoami` 确认已登录且选好组织；未登录让用户先 `hap auth login`。
2. **管理员权限（硬性前提）**：编辑应用元素要求当前用户对该应用有管理权限。动手前用 `hap app list-managed` 确认目标 app 在列表里；不在则**不要硬试**，告知用户需要管理员授权或换账号登录。
3. 上下文中没有 appId 时，让用户提供应用名或 appId。

## 通用工作流（4 步）

1. **Inspect**：`hap app-editor inspect <appId或应用名>` 打印应用的「逻辑名 → id」全结构（工作表、视图、角色、工作流、页面、分组…）。后续命令要的各种 id 都从这里拿；更细的 id 用各模块的 list/info 命令。
2. **Read**（改复杂值前必做）：**先用读命令导出现状，在真实结构上改，再写回**。
   - 视图：`hap --json worksheet view info <ws_id> <view_id>`
   - 节点：`hap --json workflow node get <process_id> <node_id>`
   - 字段：`hap --json worksheet fields <ws_id> --raw`
   - 页面：`hap --json custom-page info <app_id> <page_id>`
   字典没覆盖的键，以读到的实际结构为准——照形改写永远是安全的。
3. **Edit**：按模块文档的调用范式执行命令；或对三类 edit-spec 编辑：写 spec → `hap app-editor validate <spec.json>`（纯本地）→ `plan`（dry-run 预演）→ `apply`。
4. **Verify**：用对应读命令确认改动生效。

## 值形态约定（读字典表时）

各模块字典表的「值形态」列分三档：
- **标量/枚举**：可取值直接写在格内，如 `"1"=显示 "2"=隐藏`；
- **简单结构**：一行描述，如 `controlId 的 JSON 数组`；
- **复杂结构**：链接到 [scripts/types/](scripts/types/) 下的类型定义（schema + 可直接套用的示例），全 skill 每个结构只定义一次：

| 类型 | 用在哪 |
|---|---|
| [FilterCondition](scripts/types/filter-condition.schema.json) | 视图筛选、业务规则、按钮 enableWhen、图表筛选、页面筛选组件 |
| [SortItem](scripts/types/sort-item.schema.json) | 视图多重排序、工作流节点 sorts |
| [WireControl](scripts/types/wire-control.schema.json) | 字段的原始控件对象（读写通用货币） |
| [OperateCondition](scripts/types/operate-condition.schema.json) | 工作流节点/分支条件（**不是** FilterCondition，字段名是 `filedId`） |
| [WorkflowAccounts](scripts/types/workflow-accounts.schema.json) | 工作流收件人（type 语义反直觉，必读） |
| [WorkflowFieldWrite](scripts/types/workflow-field-write.schema.json) | 数据节点字段写入（`$nodeId-fieldId$` 动态模板） |

一个典型的 HAP 工作表视图页面地址：`/app/<app_id>/<section_id>/<worksheet_id>/<view_id>`。一个典型的 HAP 工作表行记录页面地址：`/app/<app_id>/<worksheet_id>/<view_id>/row/<rowid>`。

## 模块文档索引

按要操作的元素**只读对应那一份**（每份 = 调用范式 + 数据字典）：

- [references/worksheets-and-fields.md](references/worksheets-and-fields.md) — 工作表、字段（含 field edit-spec 写法）
- [references/views.md](references/views.md) — 视图（editAttrs / advancedSetting 全字典）
- [references/roles.md](references/roles.md) — 角色、权限、成员
- [references/workflows.md](references/workflows.md) — 自动化工作流与节点基础
- [references/nodes.md](references/nodes.md) — 节点配置深度字典（8 类高频节点）
- [references/custom-actions.md](references/custom-actions.md) — 动作按钮（action_spec / wire 两种写法）
- [references/custom-pages.md](references/custom-pages.md) — 自定义页面与组件（含 component edit-spec 写法）
- [references/application.md](references/application.md) — 应用本身与导航分组
- [references/edit-spec.md](references/edit-spec.md) — edit-spec 信封与三类 op 的完整语义

**多元素联动场景**（一个目标要串多条命令）见 [references/scenarios/](references/scenarios/)，每个场景一份文档，含命令顺序与 id 传递。三类 edit-spec 的可直接套用样例在 [examples/](examples/)（field / component / custom-action 各一份）。

## 边界与纪律

- 只改用户明确要求的元素。
- 破坏性操作：edit-spec 的删除类 op 必须带 `"confirm": true`；裸命令的删除类一律带 `--yes/-y` 二次确认，不传 `-y` 时会交互式询问（非交互环境下直接中止）。`-y` 只是跳过提示，不等于授权——任何删除动手前都先取得用户明确同意。
- 不猜参数：字典 + 读命令导出的现状是唯一依据；两者冲突时以读到的为准。
- 字典生成于 2026-06-10；服务端新增的键不会自动出现在字典里，照「先读后写」规则即可安全覆盖。
- 整应用从零生成不属于本 skill —— 用 hap-cli-app-creator。
