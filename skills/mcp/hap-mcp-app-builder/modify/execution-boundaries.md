# Modify 能力范围与执行边界

> 同源基准：`skills/hap-revision-execution-boundaries` + 跨应用数据源引用规则

本文件供主 Agent 在规划已有应用修订方案前快速核对平台 MCP 的真实自动化边界。具体参数与枚举以当前运行时 MCP 工具 Schema 及对应 `references/hap-domain-*-spec.md` 为准；风险授权与停止条件遵循 `modify/safety-rules.md`。

## 一、 核心领域能力边界矩阵

| 领域能力 | 自动化支持范围与限制 | 权威领域规范 |
|---|---|---|
| **自定义页面背景** | `style.backgroundColor` 仅支持当前浅色/深色风格下的预设色值。宽泛美化在预设色内选择；用户指定非预设自定义色值时说明限制并列出合法选项，不擅自替换颜色或切换深浅风格。 | `references/hap-domain-custom-page-spec.md` |
| **自定义页面内容与外链** | 画布页面支持通过 `patch_custom_page_components` 执行组件增删改与布局局部补丁；仅新建空页面首次填充或用户明确批准整页重做时使用 `update_custom_page` 全量写入（覆盖已有非空页面须能完整回读且字段对称无损）。外链页面（`pageType: url`）通过 `create_app_items` / `update_custom_page_config` 独立维护，不支持画布与外链互转。 | `references/hap-domain-custom-page-spec.md` |
| **统计图表** | `update_chart` 同时支持自定义页面内图表（需传 `customPageId`）与工作表「统计」面板图表原地更新并保留 `chartId`。页面图表的创建、布局排序和删除走页面组件接口；`create_chart`、`sort_charts`、`delete_chart`、`update_chart_owner` 仅用于工作表统计图（支持公共/个人切换，不支持指定他人为个人图表属主）；跨页复制/移动或表图复制到页面使用 `move_chart`。 | `references/hap-domain-custom-page-spec.md`、`references/hap-domain-worksheet-chart-spec.md` |
| **自定义动作** | 单条/多条数据源（`recordScope`）均可挂载详情、行内及适用视图批量入口，挂载位置不决定数据源。`recordScope` 创建后固定不可原地修改，切换只能删除原动作后重建并重新衔接关联流程与权限；动作关联流程严禁单独调 `delete_process`，必须通过 `delete_custom_action` 连带删除。 | `references/hap-domain-custom-action-spec.md`、`references/hap-domain-view-spec.md`、`references/hap-domain-workflow-spec.md` |
| **AI 智能助手** | `update_chatbot` 仅改实体名称、欢迎语和预设提问（最多 5 项）；已有助手的系统提示词（Prompt）、模型、数据表/视图范围、知识库和输出等行为配置，底层直接以 `chatbotId` 作为 `workflow_id` 通过 `get_workflow_structure` + `update_workflow_node` 原地修改关联工作流中的 `ai_agent` 节点并按授权发布，**不得误判为不支持修改转人工，严禁删建助手**。 | `references/hap-domain-chatbot-spec.md` |
| **打印模板** | 系统打印、二维码、条码模板通过各自专用 `create_*/update_*` 纯配置接口原地维护；Word/Excel 模板配置走 `update_file_print_template`，源文件新建与替换分别走 `create_file_print_template` 与 `replace_print_template_file`（保留原 `templateId`）；支持 `delete_print_template` 删除指定模板（含 cloud），但 cloud 模板的创建与内容编辑转人工处理。 | `modify/print-template-file.md` |
| **公开表单与外部门户** | 工作表原生公开表单支持 `switch_public_form`、`update_public_form`、`update_public_form_settings`、分享卡片及链接刷新；外部门户支持 `switch_portal` 与 `patch_portal_config`（名称、准入、登录页外观、协议与通知模板），但不含外部用户记录管理、邀请审核或默认门户角色修改。 | `references/hap-domain-external-portal-spec.md`、`modify/modify_guide.md` |
| **角色合并** | 平台无原子合并接口，必须按“更新目标角色权限 → 迁移成员 → 迁移已知引用 → 验证 → 确认后删除源角色”分阶段串行；存在无法自动迁移的外部或工作流引用时保留源角色并转人工处理。 | `references/hap-domain-role-spec.md` |
| **记录数据处理** | 仅承接结构修订所需的受控初始化、确定性转换、跨表结转、旧值清理，以及用户明确要求的少量示例数据写入（示例写入可独立执行，无需先改结构）；受 `modify/safety-rules.md` 行数上限与 `triggerWorkflow: false` 严格约束。日常普通业务数据增删改不在本修订范围内。 | `references/hap-domain-record-data-spec.md`、`references/hap-sample-data-spec.md` |

---

## 二、 跨应用只读数据源引用边界

1. **允许的跨应用范围**：仅支持在**当前目标应用**中配置同组织（同一 `orgId`）下其他应用的数据源引用，包括：
   - 当前应用工作表的 `Relation` 字段单向引用外部工作表（强制 `config.bidirectional: false`）；
   - 当前应用自定义页面组件/图表引用外部工作表与视图；
   - 当前应用工作流配置外部工作表数据查询/新增/更新节点。
2. **严禁越界行为**：不得借跨应用引用修改外部应用的表结构、视图、页面、工作流或角色权限，不得在外部表建立反向关联字段，也不得试写外部应用的真实业务记录。要求独立修改其他应用时，提示用户切换目标应用。
3. **权限与限制提示处理**：定位新外部数据源可用 `get_app_list(orgId, permissionScope: "manage")` 或 `get_app_info` 核对 `organizationId` 一致性；保存回包中的 `restrictedFields` 仅表示受另一侧应用权限保护的属性保持原值，只要本次批准的本表基础属性已成功生效即正常收口，不因该提示误判失败或反复重试。

---

## 三、 缺失接口与异常处理原则

- 仅当实时 MCP 工具定义或完整读取结果证实缺少安全写接口、或全量覆盖接口无法完整回读保留未修改配置时，才将该部分标为人工事项（给出清晰的操作路径与完成标准），**不得将当前工具缺口表述为“明道云平台不支持”**。
- 除“自定义动作切换单/多条数据源”这一明确规则外，**严禁通过“删除旧对象再新建”来模拟缺失的更新能力**（以免破坏线上真实对象 ID、历史数据与下游引用）。
