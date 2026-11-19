# Step 1b: 更新应用描述与按角色使用手册 SOP (`1b_update_app_desc`)

<!-- SOURCE: build-app/update-app-desc-sub-agent.yaml -->

## 一、 本地宿主输入与参考映射

- **执行方式**：**主调度器内联执行**（紧接 Step 1 拿到 `appId` 后顺手调用 1 次 `update_app`，无需启动独立 Subagent，也无需生成 `.build/receipts/` 回执文件）。
- **输入来源**：`{PROJECT_ROOT}/.hap-copilot/apps/{appName}/hap-plan.json`（`appName`、`appColor`、`language`、`requirements`、`roles`）与同目录下的 `overview.md`，以及 Step 1 刚获取的 `appId`。
- **必读领域规范**：`../../references/hap-domain-app-spec.md`（重点参考第六节「场景一：全新编写使用手册」）
- **主要业务工具**：`["update_app"]`

---

## 二、 核心构建规则与执行步骤

1. **输出语言锁定**：生成的 `remark` 与 `desc` 全部用户可见文本必须严格使用 `hap-plan.json` 中的 `language`，禁止中英混杂。
2. **落实补充要求**：仅消费顶层 `requirements` 中与应用介绍、使用手册文案相关的要求（明确文案优先于默认模板）；导航布局与配色已由 Step 1 完成，本步严禁触碰。
3. **生成并一次提交 `update_app`**：
   - `remark`：面向 AI 与开发者的应用简介，1～2 句话概括应用业务定位与核心能力；
   - `desc`：面向终端用户的完整按角色 HTML 使用手册，结构与排版样式遵循 `../../references/hap-domain-app-spec.md` 第六节；
   - 调用一次 `update_app`：严格只传 `appId`、`name`（取 `appName`）、`remark`、`desc` 四个参数。
4. **硬约束（极高危防覆盖铁律）**：
   - **绝对严禁向 `update_app` 传入 `navLayout`、`navColor`、`icon`、`color` 等任何其他参数**，防止重置 Step 1 已建好的导航布局与主题色！
   - `desc` 必须使用原生 HTML + 行内 CSS（可用 `appColor` 作重点点缀），严禁使用 Markdown，严禁硬编码绝对深浅字体色（如 `color:#333`）或纯白背景色，必须兼容暗黑模式。
5. **状态记录**：成功后在 `hap-context.json` 中置 `"appDescUpdated": true`。
