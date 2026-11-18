# HAP 已有应用修改实战手册（12 领域增量操作卡）

本手册按 12 个标准修订领域沉淀线上执行器在底层参数规格（`references/hap-domain-*-spec.md`）之外的**读写顺序、增量/全量保护与防坑规则**。执行任务时由 `scripts/resolve_context.py --mode modify --assets ... --render` 按命中领域动态提取对应章节，无需通读全文。

---

## 1. 通用内联执行方法

1. **最少往返原则**：已有可靠目标 ID 时按 ID 直达所需配置，不再查列表证明存在；同表多字段点读合并调 `get_worksheet_field`，互不依赖的只读查询同轮并发发出；同一父对象的兼容变更合并为一次物理写入。
2. **只改批准差异**：不将用户未提及的属性自动重置为默认值，也不顺带优化无关字段、布局、图标或权限。需自动挑选图标且用户未要求平台默认时，加载 `references/hap-icon-palette.md` 选取带 `sys_` 前缀的合法 `fileName`。
3. **跨步骤真实 ID 衔接**：多领域连带任务（如新建表 → 翻新默认视图 → 导航收尾 → 角色授权）严格串行使用前一步真实返回的 ID，严禁传入占位符或凭同名猜测。

---

## 2. 应用与导航 (`app_navigation`)
<!-- SOURCE: modify-app/app-navigation-revision-sub-agent.yaml -->

- **推荐精确工具集**：`get_app_info`、`get_worksheet_structure`、`get_custom_page_structure`、`get_chatbot_details`、`update_app`、`update_app_maintenance`、`update_app_items`、`create_app_sections`、`update_app_section`、`delete_app_section`、`sort_app_sections`、`sort_app_items`、`move_app_items`
- **参考规格**：`references/hap-domain-app-spec.md`、`references/hap-icon-palette.md`
- **读写与保护规则**：
  - **应用项属性与 `remark/desc` 统一入口**：仅修改工作表、自定义页面或 AI 助手的导航名称、图标、`displayType`、简要备注（`remark`）或用户说明（`desc`）时，跨类型混合去重合并为一次 `update_app_items` 提交（不传 `sectionId`）；`name/icon` 传空串保持原值，`remark/desc` 传空串表示清空（仅在明确要求清空时传）。注意区分：工作表改导航名会同步实体名，页面与助手只改导航名；局部追加说明时先按类型点读原说明保留未改部分。
  - **跨组移动与组内排序分离**：跨分组移动已有项必须用 `move_app_items(appId, sectionId, itemIds)` 原生原子移动，**严禁删分组重建**；`sort_app_items` 仅用于同分组内全量已有项重排（新建收尾默认页面在前、工作表在后，主表在前、明细子表紧随其后；当前顺序已满足则跳过不调）。
  - **分组排序与删除**：`sort_app_sections` 必须传入实时读取的全量同级分组 ID 数组；删除分组严格按 `references/hap-domain-app-spec.md` 的层级承接参数执行，保留全部应用项。
  - **维护模式与应用属性**：`update_app_maintenance` 明确启停直接执行，仅改提示文案且状态未知时先查一次，不为改文案擅自开启维护；`update_app` 只传批准差异，未经要求严禁触碰既有 `navLayout`/`navColor`/`icon`/`color`。
- **验证要点**：检查 `update_app_items` 的 `successCount / updatedIds / skipped`；若修改了 `displayType`，回读对应导航项 `status` 确认生效。

---

## 3. 工作表、字段、规则、索引与筛选器 (`worksheet`)
<!-- SOURCE: modify-app/worksheet-revision-agent.yaml -->

- **推荐精确工具集**：`get_app_worksheets_list`、`get_worksheet_structure`、`get_worksheet_field`、`get_worksheet_settings`、`create_worksheet`、`update_worksheet`、`update_worksheet_settings`、`delete_worksheet`、`get_worksheet_filter_list`、`get_worksheet_filter`、`save_worksheet_filter`、`delete_worksheet_filter`、`get_business_rule_list`、`get_business_rule_detail`、`create_business_rule`、`update_business_rule`、`delete_business_rule`、`get_worksheet_index_list`、`create_worksheet_index`、`update_worksheet_index`、`rename_worksheet_index`、`delete_worksheet_index`
- **参考规格**：`references/hap-domain-worksheet-spec.md`、`references/hap-domain-custom-field-spec.md`、`references/hap-domain-business-rule-spec.md`、`references/hap-domain-worksheet-index-spec.md`
- **读写与保护规则**：
  - **概览与布局读取选型**：仅需字段与视图概览时用 `get_worksheet_structure(responseFormat: "md")`；涉及表单排版布局设计或核验时直接用 `responseFormat: "dsl"`（已有完整 DSL 时直接复用，不再补读 MD）；点读单字段原配置用 `get_worksheet_field`。
  - **新建工作表闭环**：调用 `create_worksheet` 时使用真实 `sectionId`，**禁止传入 `createDefaultView: false`**（必须保留默认视图，拿回真实 `worksheetId` 与 `defaultViewId` 供后续原地翻新）；图标必带 `sys_` 前缀；同表配套的表单业务规则（`create_business_rule`）与物理索引（`create_worksheet_index`）紧接完成。
  - **单任务新增/编辑账本铁律**：`update_worksheet.addFields` 成功创建字段后，若后续仍需微调该字段属性，**必须改用 `editFields` 并传真实字段 `id`/`fieldId`**，严禁对已建字段再次发 `addFields` 撞别名唯一约束；新字段 `alias` 带 `biz_` 前缀。
  - **新增字段语义就近排版**：未指定位置时，按业务分段、相关字段与录入动线就近插入并协调同行 `span`（不把“未指定位置”机械等同于“塞到表单最末尾”），保留其他未受影响字段的相对顺序。
  - **主从子表与跨表衍生顺序**：建子表（`displayType: 2`）先于主表 `SubTable` + `showFields` + `Rollup`；多表双向关联先建主动关联使服务端生成真实反向字段后，再写引用反向关联的 `Lookup/Rollup`。已有子表新增字段时，同步将新字段补入主表对应 `SubTable` 的 `showFields`。
  - **专项能力要点**：① `CustomField`（`type: 48`）必读 `references/hap-domain-custom-field-spec.md`，`customWidget.script` 为无 import 纯函数源码（禁带 Markdown 代码围栏），引用的真实 `controlId` 全量声明在 `reference` 数组；② 业务规则停用须先读完整详情保留条件和动作，仅改 `enabled: false`；③ 索引仅改名使用 `rename_worksheet_index`；④ 工具栏漏斗已保存筛选器使用 `save_worksheet_filter` / `delete_worksheet_filter`（勿与视图筛选混淆）。
- **验证要点**：布局调整与全量数组替换在最后一次写入后用 `dsl` 或对应详情接口集中核对一次；索引构建异步受理如实报告“已提交构建”。

---

## 4. 视图与自定义动作 (`view_action`)
<!-- SOURCE: modify-app/view-action-revision-sub-agent.yaml -->

- **推荐精确工具集**：`get_worksheet_structure`、`get_view_structure`、`create_view`、`update_view`、`delete_view`、`sort_views`、`get_custom_action_list`、`create_custom_actions`、`update_custom_action`、`delete_custom_action`
- **参考规格**：`references/hap-domain-view-spec.md`、`references/hap-domain-custom-action-spec.md`
- **读写与保护规则**：
  - **默认「全部」视图原地翻新铁律**：新表配套视图或整套视图设计必须保留初始 `defaultViewId` 的身份，通过 `update_view` 原地完善展示列、排序、快捷筛选、分类导航或着色（保持全量浏览用途，不加缩小范围的预设 `filter`），**严禁另建同用途视图或删成 0 视图**。局部修改其他视图时不连带重做默认视图。
  - **视图创建与位置排序**：多个新视图合并放入一次 `create_view.views` 数组；优先用创建接口位置参数一次到位，确需重排时调用 `sort_views` 传入本表**全量现有真实 `viewId` 数组**；局部隐藏视图中的某个动作按钮使用 `update_view` 保留其余按钮。
  - **自定义动作与数据源切换**：`updateCurrentRecord` 的 `updateFields` 是让用户手填弹窗，若需求是一键自动赋值/流转必须选 `triggerWorkflow` 并接续配置关联流程；`recordScope`（单条/多条）创建后不可修改，确需切换时先只读备份原流程配置 → `delete_custom_action` 删旧动作 → 重建新动作并挂载视图 → 接续恢复权限与新关联工作流。
- **验证要点**：回读比对着色/筛选字段时注意接口入参可用 `alias` 而回包可能返回 24 位字段 `id`，通过表结构映射等价即收口，不反复重写。

---

## 5. 角色、权限与成员 (`role_permission`)
<!-- SOURCE: modify-app/role-permission-revision-sub-agent.yaml -->

- **推荐精确工具集**：`get_role_list`、`get_role_summary`、`get_role_worksheet_permission`、`get_role_details`、`find_member`、`find_department`、`create_role`、`update_role`、`sort_roles`、`add_member_to_role`、`remove_member_from_role`、`delete_role`
- **参考规格**：`references/hap-domain-role-spec.md`
- **读写与保护规则**：
  - **新建角色一次闭环**：`create_role` 原生支持初始权限参数，必须一次提交角色信息与完整初始权限拿回 `roleId`（严禁先建空壳再调 `update_role`），紧接按需执行 `add_member_to_role` 与 `sort_roles`。
  - **局部权限增量更新铁律**：调用 `update_role` 做局部修改时，**必须显式传 `isIncremental: true` 且显式保留原 `permissionScope`**（省略 `permissionScope` 会被重置为 `0`！）。单表权限修改先用 `get_role_worksheet_permission` 获取基线，合并批准的视图/字段/动作差异并原样回写未改项及三组关联扩展权限数组，严禁用空数组覆盖未知权限；视图权限不得超过 `recordDataScope`。
  - **成员粒度与排序/删除**：添加成员前用 `find_member` / `find_department` 解析唯一真实 ID；移除成员必须匹配原加入粒度（部门/职位加入不可传个人 ID 移除），`operatorId` 传当前认证用户 ID（可通过 `get_current_user` 获取，不可猜测）；`sort_roles` 必须传全量可排序角色 ID。
- **验证要点**：原生响应已确认变更时直接记账；全量替换或存在跨表覆盖风险时定向回读对应权限摘要核实旧权限未丢失。

---

## 6. 自定义页面与页面内图表 (`custom_page`)
<!-- SOURCE: modify-app/custom-page-revision-sub-agent.yaml -->

- **推荐精确工具集**：`get_app_info`、`get_custom_page_structure`、`get_custom_page_component`、`get_custom_page_settings`、`create_app_items`、`patch_custom_page_components`、`update_custom_page`、`update_custom_page_config`、`update_custom_page_settings`、`delete_custom_page`、`update_chart`、`move_chart`
- **参考规格**：`references/hap-domain-custom-page-spec.md`、`references/hap-chart-design-guide.md`、`references/hap-icon-palette.md`
- **读写与保护规则**：
  - **定制前端代码需求前置拦截**：若需求本质是需要后端/随机算法逻辑的定制交互页（如点击随机抽奖写库）且无真实外部 URL，直接说明需由网站开发能力承接，**严禁先建空白画布页面或用普通新建按钮冒充**。
  - **外链页面分流 (`pageType: url`)**：新建外链页调 `create_app_items(type: "customPage", pageType: "url", url: ...)` 一次完成；修改外链地址、打开方式、标题栏及同页名称/图标/说明调 `update_custom_page_config` 增量提交，不走画布组件树接口，也不跨类型互转。
  - **画布局部维护优先用补丁**：已有画布页面的组件增删改与布局调整默认先读 `get_custom_page_structure(detail: "summary")` 取组件身份、坐标与 `version`（需保留某组件原配置时点读 `get_custom_page_component`），合并为 1～20 项 `operations` 调用 `patch_custom_page_components`（同一 `componentId` 每批仅出现一次；纯移位/缩放省略 `config`；删除图表前同批先更新引用它的 `filtersGroup`）。仅新建空页首次填充或用户明确批准整页重做（且 `detail: "full"` 回读无裁剪）时才用 `update_custom_page` 全量写入。
  - **页面设置、单图更新与跨页复制/移动**：页面背景/刷新/屏幕适配/分享开关用 `get_custom_page_settings` + `update_custom_page_settings`（带 `version`）；仅改页面内某张已有图表配置用 `update_chart`（必传真实 `customPageId`、`worksheet_id`、`chart_id`，严禁调 `create_chart`）；将工作表或页面已有图表复制/移动到目标页面使用 `move_chart`（仅明确从 A 页移到 B 页时用移动模式；若要求“把工作表图移入页面并删原图”，先 `move_chart` 复制到页面拿新身份，再走 `worksheet_chart` 调 `delete_chart` 删原图）。
  - **主题色视觉呼应与数值卡片图标铁律**：新建或调整富文本使用指南（多阶段/多角色工作台优先采用多场景分栏卡片，自带外层圆角底色时将 `text` 组件顶层 `appearance` 设为 `"transparent"`）与快捷按钮时，复用 `get_app_info` 已读的应用主题色（`appColor`）保持视觉统一；数值卡 `icon.icon` 必须从 `references/hap-icon-palette.md` 选取带 `sys_` 前缀的合法名称，严禁使用无前缀示例值。
- **验证要点**：新建/重建页面或增删调整组件布局后，必须调一次 `get_custom_page_structure(detail: "summary")` 检查重叠、错位与同排对齐，有问题用 `patch_custom_page_components` 做一轮局部校正。

---

## 7. 工作表统计图 (`worksheet_chart`)
<!-- SOURCE: modify-app/worksheet-chart-revision-sub-agent.yaml -->

- **推荐精确工具集**：`get_chart_list`、`get_chart_details`、`get_worksheet_structure`、`get_view_structure`、`create_chart`、`update_chart`、`update_chart_owner`、`move_chart`、`sort_charts`、`delete_chart`
- **参考规格**：`references/hap-domain-worksheet-chart-spec.md`、`references/hap-chart-design-guide.md`
- **读写与保护规则**：
  - **严格区分归属**：本领域仅处理工作表「统计」面板中的图表（调 `update_chart` 时不传 `customPageId`）；在本表统计列表内复制图表副本使用 `move_chart` 复制模式且不传 `targetPageId`；公共与个人图表切换使用 `update_chart_owner`；`sort_charts` 必须包含本表全部图表 ID。
  - **类型切换与清空语义**：切换 `chartType` 会清理旧类型专属配置，须先读 `get_chart_details` 再按新类型组装兼容配置一次提交；`get_chart_details` 返回的 `filter` 不可原样回传，修改筛选须按输入 Schema 重构，清空筛选传 `{}`，清空说明传 `""`，禁传 `null` 或只读字段 `isPublic`。

---

## 8. AI 智能助手 (`chatbot`)
<!-- SOURCE: modify-app/chatbot-revision-sub-agent.yaml -->

- **推荐精确工具集**：`get_chatbot_details`、`create_chatbot`、`update_chatbot`、`delete_chatbot`、`get_workflow_structure`、`get_workflow_node`、`update_workflow_node`、`validate_process`、`publish_process`、`get_app_ai_models`、`get_app_knowledge_list`
- **参考规格**：`references/hap-domain-chatbot-spec.md`、`references/hap-icon-palette.md`
- **读写与保护规则**：
  - **创建参数白名单**：`create_chatbot` 必传 `name`、`prompt`、`welcomeMessage`、`presetQuestions`（1～5 项具体业务问题，用户明确要求为空才传 `[]`）及 `sys_` 前缀 `icon`；**严禁向 `create_chatbot/update_chatbot` 传 `model`、`worksheets`、`knowledgeBases`、`iconColor` 等不存在的参数**。
  - **通过关联工作流修订助手核心行为**：底层 **`chatbotId == workflowId`**！修改已有助手的系统提示词（Prompt）、模型、绑定工作表/视图范围、知识库或输出结构，或为新建助手绑定数据资源时，直接以 `workflow_id: chatbotId` 调用 `get_workflow_structure(version: "draft")` 定位 `ai_agent` 节点 → 按需 `get_workflow_node` 读取保留既有 `toolId/fieldId` → 一次 `update_workflow_node`（`config` 必须为原生 JSON Object）合并提交 → 若目标已获上线发布授权则调 `publish_process`（未授权发布则保留草稿并明确说明“草稿已保存尚未发布生效”）。

---

## 9. 打印模板 (`print_template`)
<!-- SOURCE: modify-app/print-template-revision-sub-agent.yaml -->

- **推荐精确工具集**：`get_worksheet_structure`、`get_print_template_list`、`get_print_template_details`、`create_system_print_template`、`update_system_print_template`、`create_qr_code_print_template`、`update_qr_code_print_template`、`create_barcode_print_template`、`update_barcode_print_template`、`create_file_print_template`、`update_file_print_template`、`replace_print_template_file`、`delete_print_template`
- **读写与保护规则（含本地环境原生适配）**：
  - **模板类型与更新范围**：复用已确认类型及配置，缺少时读取模板详情，使用对应类型的更新工具并保留 templateId。只提交批准差异，不用创建默认值覆盖原设置；不能为排版方便切换已有模板类型。
  - **纯配置操作不碰文件**：系统打印、二维码、条码模板全程走各自 `create_*/update_*` 接口（读取 `get_print_template_details` 时省略 `importFile`；更新 `fields/relatedFields/showTexts` 数组时先读完整配置保留未改项和顺序）；Word/Excel 仅改名称、可见范围、下载权限或打印前编辑开关时直接调 `update_file_print_template`；删除指定模板（含 cloud）直接调 `delete_print_template`。
  - **标签编码与访问**：二维码按已授权用途编码记录链接或真实字段，条码使用真实字段；纸张、标签布局、尺寸及显示文本组合按实时 Schema。打印二维码不隐含公开访问授权；空间不足先调整支持的布局，不通过换文件格式绕过编码限制。
  - **文件模板制作与替换**：仅新建或替换 DOCX/XLSX 文件时，读取 [打印模板文件规程](print-template-file.md)，按其中的本地文件流程、HAP 占位符与交付检查执行。纯配置和删除不加载文件制作内容。

---

## 10. 工作表公开表单 (`public_form`)
<!-- SOURCE: modify-app/public-form-revision-sub-agent.yaml -->

- **推荐精确工具集**：`get_worksheet_structure`、`get_worksheet_field`、`get_public_form_config`、`switch_public_form`、`update_public_form`、`update_public_form_settings`、`reset_public_form_fields`、`refresh_public_form_url`、`get_share_card_setting`、`update_share_card_setting`、`get_sms_signatures`
- **读写与保护规则**：
  - **独立配置对象边界**：工作表内部表单的 `form/submission` 与公开表单配置相互独立；仅查启停状态可复用工作表设置，查公开链接或详细配置直接调 `get_public_form_config`（分享卡片调 `get_share_card_setting`，`share_type: "public-form"`）。
  - **启用即交付可用收集表**：首次启用先调 `switch_public_form` 初始化配置与链接，随即核对工作表结构，**仅公开收集目标所需且支持公开填写的字段，隐藏内部审批/流转字段**（切勿无脑全表公开；若隐藏必填字段导致无法提交，停止并汇报缺口，不擅改工作表字段约束）；设置清晰的标题、说明、提交按钮文案与匹配场景的 `coverPreset` 预设封面（`coverPreset` 与自定义 `coverImagePath` 互斥，切预设时不回传旧图片路径；Logo 默认沿用组织 Logo 不覆盖）。
  - **更新与重置保护**：`update_public_form` 和 `update_share_card_setting` 仅传批准差异；**`update_public_form_settings` 会整组替换 `settings`**，必须先通过 `get_public_form_config` 取完整当前设置合并修改后提交（读取失败或截断时禁写）；`reset_public_form_fields` 仅在明确授权重置时使用；`refresh_public_form_url` 会废除旧链接，必须按 `high` 风险先经用户确认。明确关闭公开表单直接调 `switch_public_form`（保留已有配置与历史数据）。

---

## 11. 外部用户门户 (`external_portal`)
<!-- SOURCE: modify-app/external-portal-revision-sub-agent.yaml -->

- **推荐精确工具集**：`get_org_detail`、`get_portal_status`、`get_portal_config_sections`、`switch_portal`、`patch_portal_config`
- **参考规格**：`references/hap-domain-external-portal-spec.md`
- **读写与保护规则**：
  - **按初始化状态配置**：已初始化且关闭时，可先用 `patch_portal_config` 保存已批准的配置；首次启用需初始化时，按已确认的准入范围调用 `switch_portal`。明确仅关闭门户按 `low` 直接执行（中断访问但保留用户和配置）。
  - **局部递归合并与准入映射**：按需用 `get_portal_config_sections` 读取相关分组（局部改协议正文时传 `termsContent` 按篇读取）；`patch_portal_config` 为递归合并，只传批准差异，清空文本传 `""` 禁传 `null`；准入方式映射为仅邀请 `invite`、注册需审核 `approval`（配 `enableApproval: true`）、任何人可注册 `anyone`。
  - **Logo 与背景素材优先级**：涉及美化或补齐外观时加载 `references/hap-domain-external-portal-spec.md`；未指定自定义 Logo 时先用组织 ID 调 `get_org_detail`，组织有真实 Logo URL 则直接用于 `appearance.logoSource`，否则再按行业匹配规范内置的七牛公网永久直链资产（禁传 SVG/WebP）。

---

## 12. 工作流 (`workflow`)
<!-- SOURCE: modify-app/workflow-revision-sub-agent.yaml -->

- **推荐精确工具集**：`get_workflow_list`、`get_workflow_structure`、`get_workflow_node`、`get_workflow_variables`、`create_process`、`delete_process`、`close_workflow`、`batch_create_process_nodes`、`batch_delete_process_nodes`、`update_workflow_node`、`update_workflow_info`、`update_workflow_variables`、`validate_process`、`publish_process`、`get_workflow_sms_templates`、`get_sms_signatures`、`find_member`、`find_department`、`get_current_user`
- **参考规格**：`references/hap-domain-workflow-spec.md`、`references/hap-workflow-design-guide.md`
- **读写与保护规则**：
  - **设计与身份解析**：新建、重构或复杂分支/审批调整前先读 `references/hap-workflow-design-guide.md` 自检 7 个维度；仅改流程名/说明直接调 `update_workflow_info` 无需读整图或发布。固定姓名/部门用 `find_member`/`find_department`（`orgId` 传当前组织 ID，脱敏手机/邮箱不可用于外发）；“通知我”调 `get_current_user` 取真实用户 ID（勿与运行时动态触发人 `triggerUser` 混淆）；短信签名从 `get_sms_signatures` 有效结果中选取。
  - **草稿增量修改与嵌套块分层处理**：新建普通流程用 `create_process(publish: false)` 拿 `processId/triggerAlias` 后调 `batch_create_process_nodes`（超长拓扑按几组完整依赖小组分批落盘）；自定义动作流程复用动作返回的 `workflowId` 先读真实触发 `nodeId`（不调 `create_process`，也不单独调 `delete_process` 删动作流）。修改已有节点用 `update_workflow_node` 最小 PATCH（**`config` 必须传原生 JSON Object，严禁序列化为字符串**；严禁把读取的整包 `config` 回写，严禁靠删全部下游节点修复普通参数错误；局部替换错误节点时换用新 `alias`）。`approval_block / sub_process / loop` 不展开内部节点，须以其内部 `processId` 分层调 `get_workflow_structure / update_workflow_node`，发布时**由内向外**先发布修改过的内部流程再发布父流程。
  - **校验、发布与既有草稿保护**：复杂拓扑或仅交付草稿时调 `validate_process`，按 `issues` 的 `nodeId/path/hint` 定点修复；发布必须已获授权（注意核对是否存在任务外未发布草稿，合并既有草稿须经用户确认）；发布非幂等，超时或结果不明先回查 `published` 版本状态，严禁盲目重放。

---

## 13. 结构修订连带记录数据 (`record_data`)
<!-- SOURCE: modify-app/record-data-revision-sub-agent.yaml -->

- **推荐精确工具集**：`get_record_list`、`get_record_details`、`get_record_relations`、`get_record_pivot_data`、`get_record_logs`、`batch_create_records`、`batch_update_records`、`update_record`
- **参考规格**：`references/hap-domain-record-data-spec.md`、`references/hap-sample-data-spec.md`
- **读写与保护规则**：
  - **强制前置探测与冻结**：所有写调用强制 `triggerWorkflow: false`。修改存量记录前必须先用实际筛选调 `get_record_list(includeTotalCount: true, pageSize: 1, pageIndex: 1)` 探测准确行数并核对 `modify/safety-rules.md` 阈值；首次写入前分页拉取并去重冻结全部目标 `rowId`，二次核对 `totalCount` 无漂移后再执行。
  - **五类场景执行规范**：① **初始记录与示例新增**：加载 `references/hap-sample-data-spec.md`（仅示例场景），按稳定唯一业务键查重，零匹配项调 `batch_create_records`；② **同值初始化/广播**：全部目标行写入完全相同 `fields` 时按冻结 ID 分片（≤1,000 行/批）调 `batch_update_records`，核对 `successfulRowIds / failedRowIds`；③ **逐行差异转换（≤20 行）**：基于确定字典/公式逐条 `update_record` 并立即 `get_record_details` 回读；④ **跨表结转（≤20 行）**：第一批在目标表按唯一业务键查重创建拿真实 `rowIds`，第二批逐条回写源表关联字段；⑤ **旧字段清理**：仅在新字段 100% 对账通过且引用全部切换后执行，禁传 Schema 未声明的 `null` 猜测清空。
