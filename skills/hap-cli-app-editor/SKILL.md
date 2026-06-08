---
name: hap-cli-app-editor
description: 修改一个已存在的明道云 HAP 应用里的某个具体元素时用本 skill。覆盖：字段（加/改/删、设下拉选项、改字段名）、视图（加/删/重命名表格/看板等）、工作表与分组（建表/删表、新建分组、把页面或仪表盘归类到分组下）、角色与权限（给角色加查看/编辑权限、修「登录后看不到内容」、增删成员）、工作流（启用/停用/暂停/改名，含定时任务与自动化，及增删工作流节点）、自定义动作按钮（新增或调整「点击后改记录」类按钮）、自定义页面与页面组件、仪表盘、应用本身（改名/导航色）。只要用户说「在某表加个字段」「把这个视图改名」「停用那条工作流」「给某角色加权限」「加个动作按钮」「新建分组并归类页面」「删掉这张表/视图」「修一下建到一半出错的应用」之类、针对已有应用做单点局部修改，就触发——即使用户没明说要用 hap-cli 或工具。不触发：增删改业务记录、导入/导出/查询数据、写调 hap 的代码、调研明道云产品；从零搭整个新应用请改用 hap-cli-app-creator。
---

# HAP 应用编辑器（细粒度元素 CRUD）

你对一个**已存在**的明道云 HAP 应用做精确的局部修改：增、删、改单个元素（工作表 / 字段 / 视图 / 角色权限 / 自定义动作 / 工作流 / 自定义页面与组件），而不重建整个应用。典型场景：修复 hap-cli-app-creator 建到一半出错的半成品、按用户要求调整某张表的字段或视图、删除多余元素。

执行逻辑在 hap-cli 内置的 **`hap app-editor`** 命令里（引擎随 hap-cli 一起安装，直接调用 HAP API，无需 subprocess）。你把修改表达成一个结构化的 **edit-spec**（JSON），命令负责校验、读取应用实时结构解析逻辑名、预演、执行。本 skill 提供 schema（`scripts/editspec/`）、写法文档（`references/`）与示例（`examples/`）。

## 核心模型

- **真相来源 = 实时 HAP**：每次操作前从后端读取应用当前结构（工作表/字段/视图…）解析「逻辑名 → 真实 id」。所以能编辑任意已存在的应用，不依赖任何本地缓存。
- **edit-spec**：`{ "app": "<appId 或应用名>", "ops": [ {op}, ... ] }`，按声明顺序执行。每个 op 形如 `{"type": "<元素>.<动作>", ...}`，如 `field.add`、`view.update`、`worksheet.delete`。
- **破坏性操作必须显式确认**：删除/覆盖类 op 必须带 `"confirm": true`，否则拒绝执行。
- **同一个 spec 内可链式依赖**：后面的 op 可以引用前面 op 刚创建的元素（apply 每步都会重新读取实时结构）。

## 前置条件

1. **登录**：执行 `hap auth whoami` 确认 CLI 已登录且有当前组织。
   - 返回用户信息 ➔ 继续。
   - 未登录 ➔ 让用户先 `hap auth login`（并选好组织）。

2. **管理员权限（硬性前提）**：编辑应用元素**要求当前用户对该应用有管理权限**，否则增删改会被后端拒绝。动手前用 `hap app list-managed` 列出当前用户有管理权限的应用
   （返回 `[{appId, name, worksheetCount}]`），确认目标 app 在其中：
   - 目标 app（按 appId 或名称）**在列表里** ➔ 有权限，继续。
   - **不在列表里** ➔ 当前账号无管理权限，**不要硬试**；告知用户需要应用管理员权限（让管理员授权，或换用有权限的账号 `hap auth login`），再重试。

3. 如果上下文中没有明确的 appId 信息，则用户必须提供应用名或 appId。

命令都是 `hap app-editor ...`（随 hap-cli 安装；`--json` 可加在 `hap` 后输出 JSON）。

## 工作流（4 步）

1. **Inspect**：`hap app-editor inspect <appId 或应用名>` 打印应用的「逻辑名 → id」结构（工作表、视图、角色、工作流、页面、分组…）。先看清要改的元素叫什么、在哪。

2. **Author**：写 edit-spec JSON。按需查阅 `references/`（**不要一次性全读**，只读你这次要操作的元素那一份）：
   - `references/edit-spec.md` — 信封与通用语义、op 总表。
   - `references/worksheets-and-fields.md`、`references/views.md`、`references/roles.md`、`references/custom-actions.md`、`references/workflows.md`、`references/custom-pages.md`、`references/application.md`。
   schema 按模块拆分在 `scripts/editspec/`（envelope + 每类元素一份），可对照；`examples/` 有各 op 家族的样例。

3. **Validate + Plan**：
   - `hap app-editor validate <edit-spec.json>` — 纯本地校验，零网络；报错带 JSON 路径，先改对结构。
   - `hap app-editor plan <edit-spec.json>` — 读取实时结构、预演将执行的改动（dry-run，不改任何东西）。链式依赖的 op 会显示「resolved at apply time」。

4. **Apply**：`hap app-editor apply <edit-spec.json>` — 逐 op 执行，每步前重新读取实时结构以支持链式依赖；出错默认停下（加 `--continue` 可继续），每步结果有记录。

> 可用 `--app <appId>` 覆盖 spec 里的 `app`，`--org-id <org>` 指定组织：`hap app-editor apply <edit-spec.json> --app <appId>`。

## 字段操作的硬规则（重要）

- **新增字段**走增量路径（不会丢掉系统自动生成的反向控件）。
- **修改 / 删除 / 重排已有字段**走「读取该表完整控件集 → 只改目标 → 整表写回」，与 HAP UI 一致、保留反向/系统控件。
- 绝不用「只发部分字段的整表替换」来改单个字段——那会丢控件。命令已封装好，按 `field.*` op 写即可。

## 边界

- 只改用户明确要求的元素；破坏性操作没有 `confirm: true` 一律不执行。
- 不猜 HAP 行为；元素语义与约束以 `references/` 与实时读取为准。
- 整应用从零生成不属于本 skill —— 用 hap-cli-app-creator。
