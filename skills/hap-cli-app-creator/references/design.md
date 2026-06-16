# Design — design.json 顶层结构与生成流程

---

设计文档是一份 **ID-free 的 JSON**：所有跨对象引用都用**逻辑名**（工作表名、字段名、角色名、分组名、页面名、视图名…），
没有任何真实 id。`hap app-creator build` 按依赖顺序建资源，把每个逻辑名解析成服务端返回的真实 id 并落盘到 store。
权威契约是 [../design/design.schema.json](../design/design.schema.json)（draft-07），生成后用 `hap app-creator validate <file>` 本地校验。

设计之前必须先阅读设计指南 [design_guide.md](design_guide.md)，了解总体设计原则以及各个模块如何选型与设计。

## 顶层键

```jsonc
{
  "app":        { ... },        // 必填：应用名 + 图标 + 分组(sections)
  "optionsets": [ ... ],        // 共享选项集（在 worksheets 之前建）
  "worksheets": [ ... ],        // 必填：工作表 + 字段（含关联/他表/汇总/子表，内联在字段上）
  "views":      [ ... ],        // 视图（按 worksheet 逻辑名归属）
  "custom_pages": [ ... ],      // 自定义页面 / 统计看板（图表/视图/按钮组/筛选条…）
  "chatbots":   [ ... ],        // AI 助手
  "roles":      [ ... ],        // 必填：应用角色（一律 permission_scope:"0" 细粒度）
  "workflows":  [ ... ],        // 记录触发 / 定时 / 日期触发的自动化工作流
  "custom_actions": [ ... ]     // 工作表自定义动作按钮（含按钮触发的工作流）
}
```

## 建立顺序（执行器内部，理解依赖即可）

App/Sections → Optionsets → Worksheets/Fields → Relations → Derived fields（Lookup/Rollup）→
Custom actions → Views → Custom pages → Chatbots → Roles → Workflows。

**含义**：被引用的东西要先存在。关联目标表、汇总桥字段、视图所属表、按钮里 `open_page` 的页面、角色细粒度里的工作表/视图/页面，
以及**工作流/审批块里作审批人的角色**（角色必须先于工作流建好），
都要在引用前定义（同一份 design 内即可，顺序无所谓——执行器排序；但**逻辑名必须拼对**，否则解析失败）。

## app 段

```jsonc
"app": {
  "name": "智慧仓储", 
  "icon": "sys_18_5_warehouse",             // 用 `hap icon search 仓库 仓储 库存 货架` 这类多关键词搜索获取可用图标标识
  "icon_color": "#8E481B",
  "nav_color": "#8E481B",
  "nav_layout": "group",                    // PC 端导航方式，见下表（可省略，默认 group）
  "sections": ["库存管理", "出入库", "分析"]   // 分组逻辑名，被 worksheet.section / custom_page.section 引用
}
```

**`nav_layout`（PC 端导航方式）** —— 根据应用的业务场景和复杂度选择：

| 场景 | 值 |
|------|-----|
| 默认（大多数业务应用） | `group` |
| 结构复杂、层级深（多层分组） | `tree` |
| 多业务域并列（多个独立模块） | `top` |
| 门户/工作台型（首页入口明显） | `card` |

## 逻辑名引用速查

| 在哪里 | 引用什么 | 怎么写 |
| :-- | :-- | :-- |
| `worksheet.section` | 分组 | 分组名（须在 `app.sections`） |
| `field.relation.worksheet` | 目标工作表 | 工作表名 |
| `field.lookup.via` / `rollup.via` | 本表的桥字段 | 字段名（Relation 或 SubTable） |
| `field.optionset` | 共享选项集 | optionset 名 |
| `view.worksheet` / `view.group_by` 等 | 表 / 字段 | 逻辑名 |
| 工作流 `fieldId` | 某表某字段 | `"工作表名/字段名"` |
| 工作流 `accounts[].role` | 应用角色 | 角色名 |
| 按钮 `open_page` / 角色 `page_permissions` | 自定义页面 | 页面名 |

## 生成→建出的完整循环

1. 写 design.json（对照各 references）。
2. `hap app-creator validate <file>` → 必须零错误。校验除结构外，还做**逻辑名引用完整性**检查：`worksheet/custom_page/chatbot` 的 `section` 必须在 `app.sections` 内；`Relation.worksheet`、`view.worksheet`、`custom_action.worksheet`、角色 `worksheet_permissions[].worksheet`、图表/内嵌视图组件的 `worksheet` 必须是已定义的工作表；`field.optionset` 必须是已定义的选项集；角色 `page_permissions[].page` 必须是已定义的自定义页面；`view.actions` 外露的动作必须是该视图所属工作表上已定义的 `custom_action`。拆分生成时务必让各片引用的名字与 `01-foundation` 锁定的命名契约（表名/字段名 + 自定义动作名 + 自定义页面名）完全一致（合并后整体校验兜底）。
3. `hap app-creator build <file>` → 一次性整跑、拿 appId。build 永远从干净 design 整跑到底，**没有分阶段重跑/续跑**；中途某步失败会被记录、流程继续到底，失败项事后用 hap-cli-app-editor 按真实 id 在原位修复，绝不回头重跑某个 build 阶段（否则会堆出重复视图/工作流）。
