---
name: hap-mcp-app-builder
description: 用于明道云/HAP 应用的方案设计、自动搭建、继续或恢复搭建、已有应用的修改重构与数据迁移、配置查看、故障排查，以及日常业务数据查询统计、记录增删改、审批待办处理与业务流程触发。用户提到明道云/HAP、发送明道云链接，或在 HAP 上下文中处理应用、工作表、字段、视图、业务规则、自定义动作、打印模板、公开表单、外部门户、对话机器人、工作流、角色、自定义页面、统计图、业务记录或审批单据时触发。不用于非 HAP 的通用软件开发。
---

# HAP 应用助手

明道云（HAP）全生命周期智能助手，覆盖 **Plan（方案设计）、Build（自动搭建）、Modify（存量修订）与 Data（数据与审批）** 四路工作流。

工具 Schema 核实、安全红线与提问交互统一遵循 [本地宿主适配](HOST_ADAPTER.md)（首次必读）：以实时 MCP Schema 为唯一能力真值源；需要用户决策时优先使用宿主原生提问工具（Plan 输出完整方案后的最终确认在正文末尾引导）。

## 1. 前置检查（按序执行）

1. **版本只读检查**：版本见 [`version.json`](version.json)。首次触发或询问版本时运行 `python3 {SKILL_DIR}/scripts/skill_update.py check`（24h 缓存、源码软链跳过、不改本地文件）；若 `"updateAvailable": true`，附 1 句提醒请用户运行 `npx skills update`（或 `npx skills add https://github.com/mingdaocom/hap-skills --skill hap-mcp-app-builder`）或通过明道云「连接 AI」更新，勿自行覆写本地目录。
2. **识别 MCP 服务**：查找同时暴露 `get_org_list` 与 `create_app` 的服务——**0 个**按 [MCP 接入指南](MCP_SETUP.md)「场景一」引导接入；**1 个**静默选定为 `MCP_SERVER_NAME`；**≥ 2 个**按宿主规则或 URL 域名匹配，无法唯一确定时提问点选。
3. **工具门禁与连通**：
   - Data 场景免卡 170 上限；其余场景硬卡 `tools_count >= 170`（不足按 `MCP_SETUP.md`「场景三」阻断）。
   - 用户提供明道云链接或 `appId` 时，直接 `get_app_info(appId)` 校验连通并记录名称与 `orgId`（跳过多组织询问）；否则调 `get_org_list` 缓存 `organizations`（唯一组织自动记为 `orgId`）。`401` 按「场景二」更新令牌，应用/组织权限受限按「场景四」排查。
4. **应用粘性与消歧**：已锁定的 `appId` 默认延续，收到新链接或明确切换时立即更新；未锁定或 `get_app_list` 命中 0/多候选时通过提问工具确认，不猜测翻找。

## 2. 场景路由

| 场景 | 入口文档与命令 | 入口硬门禁 |
| :--- | :--- | :--- |
| **新建应用 / 方案草案（Plan）** | `workflows/plan.md` | 多组织未指定时先提问点选，**⛔ STOP：确认前不输出完整方案** |
| **物理搭建 / 断点续建（Build）** | `workflows/build.md` | 重资产任务须派发独立 Subagent 并发；不支持子代理则标 `blocked` |
| **存量修改与迁移（Modify）** | `workflows/modify.md` + `python3 {SKILL_DIR}/scripts/resolve_context.py --mode modify --assets {domains} --render` | 遵循 [安全规则](modify/safety-rules.md) |
| **日常数据与审批（Data）** | `workflows/data.md` | 免卡 170 门禁，个人跨应用审批免锁单 `appId` |
| **轻量只读配置查询与排障** | [修改指南](modify/modify_guide.md) | 仅调最小只读接口，全程零写入 |

**断点分流（进入 Plan / Build 前）**：当项目目录存在 `.hap-copilot/apps/`（或历史 `apps/`）或用户要求继续/恢复搭建时，运行 `python3 {SKILL_DIR}/scripts/scan_apps.py {PROJECT_ROOT}`，按 `mcpServer`、`orgId`、`appId` 与 `appDir` 绝对路径匹配未完成工程（`planned` / `in_progress`）——明确续建且唯一匹配时直接读 `workflows/build.md` 恢复；意图不清时提问选择 `(Recommended) 继续搭建` / `调整原方案后再搭建`（`workflows/plan.md`）/ `新建独立应用`。

## 3. 通用边界

- 宽泛“优化某表/某流程”无具体改法时，先只读探查给候选方向确认再写；所有写操作严格锁定当前 `appId`。
- 过程文件统一收纳在 `{PROJECT_ROOT}/.hap-copilot/`（自动写 `.gitignore` 为 `*`），本地文件读写一律使用绝对路径。
