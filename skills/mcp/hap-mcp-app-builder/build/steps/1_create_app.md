# Step 1: 创建应用外壳、导航分组与页面空壳 SOP (`1_create_app`)

<!-- SOURCE: build-app/create-app-sub-agent.yaml -->
<!-- SOURCE: build-app/custom-page-create-sub-agent.yaml -->

## 一、 本地宿主输入与参考映射

- **执行方式**：主调度器极速内联执行（建壳、建分组、建页面空壳），随后紧接阅读 `build/steps/1b_update_app_desc.md` 内联更新应用说明与使用手册，一并将物理 ID 写入 `hap-context.json` 并置 `progress = "app_created"`。
- **输入数据来源**：`{PROJECT_ROOT}/.hap-copilot/apps/{appName}/hap-plan.json`（含 `org_id`、`appName`、`appIcon`、`appColor`、`navLayout`、`navColor`、`enableExternalPortal`、`requirements`、`navGroups`、`customPages`）。
- **必读领域规范**：`references/hap-domain-app-spec.md`、`references/hap-icon-palette.md`
- **主要业务工具**：`["create_app", "create_app_sections", "create_app_items"]`

---

## 二、 核心构建规则与执行步骤

### Part A：创建应用实体与导航分组（源自 `create-app-sub-agent.yaml`）

1. **解析应用级 `requirements` 与默认推断规则**：
   - 将顶层 `requirements` 中的导航与应用设置要求优先映射到 `create_app` 参数（应用介绍与使用手册交由异步 Step 1b 处理，本步**严禁传 `remark` 和 `desc`**）；
   - **`navLayout` 推断规则**（用户明确要求优先，如“顶部导航”→`top`、“树形导航”→`tree`、“分组导航”→`group`、“卡片导航”→`card`；未指定时默认 `group`，层级深选 `tree`，多独立业务域并列选 `top`，门户工作台型选 `card`）；
   - **`navColor` 推断规则**（仅限枚举 `appColor | white | gray | black`，不支持自定义 HEX：蓝/绿/紫等深色主题默认 `appColor`；红/橙/黄等亮色主题选 `white`；重工/监控中心选 `black`；明确要求灰色选 `gray`）。
2. **调用 `create_app`**（参数核实与异常恢复遵循 [宿主适配](../../HOST_ADAPTER.md)，成功后复用真实 `appId`）：
   - `orgId`：`hap-plan.json` 中的 `org_id`（必填，注意参数名为 `orgId` 而非 `projectId`）；
   - `name`：`appName`（必填）；
   - `icon`：`appIcon`（带 `sys_` 前缀的合法 `fileName`）；
   - `color`：`appColor`（HEX 色值，注意参数名为 `color` 而非 `iconColor`）；
   - `navLayout` / `navColor`：按上述规则取值；
   - `enableExternalPortal`：创建时传入已确认 Plan 的布尔值；为 `true` 时随应用创建一并启用，未指定时默认 `false`；
   - 提取并原样保留返回的真实 `appId`；应用 ID 的格式以服务返回为准，不按工作表的 24 位 ID 格式推断。
3. **批量创建导航分组 `create_app_sections`**：
   - 若 `navGroups` 非空，按 `navGroups` 原顺序（严禁重排）转为 `sections: [{ "name": "<分组名>" }, ...]`，调用一次 `create_app_sections(appId, sections)`；
   - 建立分组名称到真实 ID 的映射字典 `sectionIdByName`。

### Part B：批量创建自定义页面空壳（源自 `custom-page-create-sub-agent.yaml`）

1. **组装页面项列表**：遍历 `customPages`（合并全部 `dashboard` 与 `workspace` 页面），为每页构造一个 `item`：
   - `name`：页面名称原样；
   - `type`：固定 `"customPage"`；
   - `icon`：优先原样使用页面规划的 `sys_` 前缀 `icon`；缺失时回退（`dashboard` → `"sys_dashboard"`，`workspace` → `"sys_hr_workbench"`）；
   - `sectionId`：从 `sectionIdByName` 按 `groupName` 反查（查不到则省略）；
   - `remark`：根据页面 `description` 用 `appLanguage` 生成一句简洁业务定位说明。
2. **一次性调用 `create_app_items`**：
   - 当 `customPages` 非空时，将全部页面合并到同一次 `create_app_items(appId, items)` 调用中（已成功页面不重复创建，部分失败只补缺项）；
   - 从返回结果提取每个页面的真实 24 位 hex `id`，建立 `customPageIdByName`（`{ "<页面名>": "<pageId>" }`）与 `customPageContext`（`[{ "name", "pageId", "description" }]`）。

### Part C：写入应用直达链接卡片

根据当前 MCP 服务对应域名（如 `meihua.mingdao.com`、`sandbox.mingdao.com` 或 `www.mingdao.com`），在 `{PROJECT_ROOT}/.hap-copilot/apps/{appName}/overview.md` 顶部写入访问链接提示块 `https://{前端域名}/app/{appId}`。

---

## 三、 本地状态落盘契约

将初始化结果写入 `{PROJECT_ROOT}/.hap-copilot/apps/{appName}/hap-context.json`（若走运行时引擎也可同步写入 `.build/receipts/step1-app-init.json`）：

```json
{
  "appName": "<appName>",
  "appId": "<服务返回的真实appId>",
  "org_id": "<org_id>",
  "language": "<language>",
  "progress": "app_created",
  "sectionIdByName": { "业务总览": "<sectionId>" },
  "customPageIdByName": { "经营看板": "<pageId>" }
}
```
