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
4. **硬约束（极高危防覆盖铁律 + 视觉排版底线）**：
   - **绝对严禁向 `update_app` 传入 `navLayout`、`navColor`、`icon`、`color` 等任何其他参数**，防止重置 Step 1 已建好的导航布局与主题色！
   - `desc` 必须使用原生 HTML + 行内 CSS，**严禁使用 Markdown，也严禁偷懒只输出无 `style` 的纯裸 `<h2>/<p>/<ul>` 白纸黑字**；严禁硬编码绝对深浅字体色（如 `color:#333`）或纯白/纯浅不透明背景色（如 `#fff`、`#f5f5f5`），所有背景与边框一律使用 `rgba(...)` 半透明色（用 `appColor` 作主题色点缀），确保 100% 兼容明暗模式。
   - **推荐暗黑兼容行内 CSS 骨架（直接按本应用 `appColor` 换算 `rgba` 套用，覆盖概览、核心流转、按角色独立卡片、关键状态与注意事项）**：
     ```html
     <div style="line-height:1.7;">
       <div style="background:rgba(48,84,235,0.08);border-left:4px solid #3054eb;padding:12px 16px;border-radius:6px;margin-bottom:16px;">
         <h3 style="margin:0 0 6px 0;">应用概览</h3>
         <p style="margin:0;">1～2 句话说明核心用途与业务价值。</p>
       </div>
       <h3 style="border-left:3px solid #3054eb;padding-left:10px;margin:18px 0 10px 0;">核心业务流转</h3>
       <p style="margin:0 0 14px 0;"><span style="background:rgba(48,84,235,0.12);padding:2px 8px;border-radius:4px;">步骤一</span> → <span style="background:rgba(48,84,235,0.12);padding:2px 8px;border-radius:4px;">步骤二</span> → <span style="background:rgba(48,84,235,0.12);padding:2px 8px;border-radius:4px;">步骤三</span></p>
       <h3 style="border-left:3px solid #3054eb;padding-left:10px;margin:18px 0 10px 0;">各角色操作指引</h3>
       <div style="border:1px solid rgba(128,128,128,0.22);border-radius:8px;padding:12px 16px;margin:10px 0;">
         <h4 style="margin:0 0 6px 0;">角色名称 · 一句话职责</h4>
         <ul style="margin:0;padding-left:18px;"><li>高频操作与工作台入口说明</li></ul>
       </div>
       <div style="background:rgba(250,173,20,0.1);border-left:3px solid #faad14;padding:10px 14px;border-radius:6px;margin-top:16px;">
         <strong>注意事项：</strong><ul style="margin:6px 0 0 0;padding-left:18px;"><li>关键防呆与流转约束提示</li></ul>
       </div>
     </div>
     ```
5. **状态记录**：成功后在 `hap-context.json` 中置 `"appDescUpdated": true`。
