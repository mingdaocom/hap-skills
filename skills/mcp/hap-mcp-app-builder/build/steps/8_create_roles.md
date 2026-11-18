# Step 8: 单角色创建与精细权限推演 SOP (`8_create_roles`)

<!-- SOURCE: build-app/roles-build-sub-agent.yaml -->

## 一、 本地宿主输入与参考映射

- **执行方式**：独立 Subagent 按单个角色并发执行。
- **输入切片**：读取 `.build/task-context/{taskId}.json`：
  - `planSlice`：`role`（含 `name`、`description`、`roleScope`: `"general" | "externalPortal"`、`permissions` 紧凑数组、`requirements`）、`appLanguage`；
  - `contextSlice`：`appId`、`worksheetIdByName`、`viewsByWorksheet`（或 `viewIdByName`）、`actionIdByName`、`customPageIdByName`、`chatbotIdByName`。`actionIdByName` 仅投影角色已授权表的真实动作 ID，键为 `表名/动作名`；缺失时按目标表只读查询动作列表，不推测 ID。字段和子表关系可从 `worksheetContextSlice` 或 `sourceFiles.worksheetContext` 读取，缺失时定向查结构。
- **必读领域规范**：`references/hap-domain-role-spec.md`、`references/hap-app-design-guide.md`（「角色权限」章节）
- **主要业务工具**：`["create_role", "get_role_list"]`；恢复已存在的本工程角色时，按实际授权和实时 Schema 使用 `get_role_details`、`get_role_worksheet_permission` 读取基线，必要时使用 `update_role` 精确补齐。不能确认完整覆盖基线时不写入。

---

## 二、 核心构建规则与执行步骤

- **输出语言与补充要求**：角色描述文案使用 `appLanguage` 指定语言；优先落实 `role.requirements` 中的权限细节。

### 1. 系统预设角色前置拦截（同名即复用，禁重复新建）
- 若 `role.name` 与系统预设角色名称（如「管理员」「运营者」「开发者」）**完全一致**：**严禁调用 `create_role`**！调用 `get_role_list(appId)` 定位真实 `id`，并按本步可读取的角色及权限配置核对已确认方案；同名和 ID 本身不证明授权匹配。预设角色不可调整或能力不满足时记录具体差异，不另建同名角色或擅自扩权。

### 2. 精细权限生成策略（固定 `permissionScope: "0"`）
1. **工作表权限 (`worksheetPermissions`)**：
   - 以 `role.permissions` 和 `requirements` 中已确认的操作与依赖为边界，反查真实 `worksheetId`；核对页面、视图、关联主数据、子表和操作所需访问权；
   - **`recordDataScope` 与工作表成员字段 `userPermission` 联动机制**：
     - 明道云角色接口的 `recordDataScope` 档位为 `100`（全部）、`30`（本人及下属）、`20`（本人拥有/参与）、`0`（无权）。**“按执行人/巡检人/维修人员/负责人等成员字段鉴权”是由工作表 `Collaborator` 字段上的 `config.userPermission`（`2` = 拥有者权限、`1` = 只读权限）与角色的 `recordDataScope: 20` 共同生效的**：
       - **只读/查阅/审计/高管看板/基础主数据字典表**：`read: 100, edit: 0, delete: 0`，`add: false`；
       - **按成员字段分派处理的一线操作角色 / 站点负责人角色**：核查 `worksheetContextSlice` 中目标表对应责任成员字段的 `config.userPermission`——若已为 `2`（拥有者权限），直接配置 `read: 20, edit: 20, delete: 0`（按职责定 `add`），被指派人即可原生查看并编辑自己的单据！若上游建表时某责任成员字段仅保留了默认 `userPermission: 1`（只读）且未同步 `ownerid`，可配置 `read: 100, edit: 100`（配合待办视图筛选、`unableCustomButtons` 与 `fieldPermissions` 收敛操作边界），或在 `issues` 提示将该成员字段 `userPermission` 升为 `2`；
       - **部门/团队主管角色**：`30`（本人及下属）或 `100`，删除从严（`20` 或 `0`）；
       - **业务模块管理角色**：`read: 100, edit: 100`，`delete` 仅明确需要时设 `100` 否则 `20/0`；
   - 补齐必填子对象：`worksheetActions` / `recordActions`（普通角色默认关闭公开分享、导入、导出、批量操作、系统日志；`discuss: true`、`attachmentDownload: true`）、`paymentActions: { pay: false }`。根据实际职责和实时 Schema 用真实字段 ID 配置最小必要 `fieldPermissions`：用户输入字段可写，系统维护的库存、状态、审批结果和流水等限制直接编辑；不能简单以 `[]` 证明受保护，也不得编造 ID。
   - 按方案为每个角色配置 `unableCustomButtons`，区分不同角色的按钮职责（如维修人员禁用「验收」「分派维修」按钮，作业员禁用「取消计划」按钮）。
   - **`recordPermissionInViews`（必传非空）**：提取角色获准访问的真实视图 ID，生成 `{ viewId, read, edit, delete }`（视图读写删布尔值不得超过 `recordDataScope` 上限；找不到真实视图时跳过该表，严禁传空数组或假 `viewId`）。
2. **自定义页面与 AI 助手权限**：
   - `"页面名(customPage)"` → 反查真实 `pageId` 生成 `{ id: pageId, enable: true }` 放入 `pagePermissions`；
   - `"助手名(aiAssistant)"` → 反查真实 `chatbotId` 生成 `{ id: chatbotId, enable: true }` 放入 `chatbotPermissions`。

### 3. 调用 `create_role`、重名自愈与完建验收边界
1. 调用 1 次 `create_role`：传 `appId`、`name`、`description`、`roleScope: role.roleScope || "general"`、`permissionScope: "0"`、`hideAppForMembers: "false"` 及三类权限数组（**严禁传入已废弃的旧参数 `type: "0"`**；三类权限至少一类非空；不传暂未开放自动初始化的 `extendAttrs` / `canReadExtendAttrs`）。
2. **重名恢复核验**：若返回同名错误，按计划的 `roleScope` 调用 `get_role_list` 定位同范围的真实 ID，再按需读取角色和目标表的现有权限，核对角色范围、记录/视图/字段及动作权限是否满足已批准方案；若是本次工程已建角色，按真实基线补齐授权范围内缺项，严禁改名重复创建。
3. **按证据回执**：角色按上述 `recordDataScope`、视图权限、`fieldPermissions` 与 `unableCustomButtons` 落库即标记 `status: "succeeded"` 且 `verification.passed: true`。角色成员为空或尚未指定、流程尚未发布或未做登录试跑均属运行态事项，不作为失败条件。

---

## 三、 本地回执落盘契约

执行完成后，写入 `receiptPath`（`.build/receipts/step8-role-{name}.json`）：

```json
{
  "taskId": "<来自 taskContext.taskId>",
  "runId": "<runId>",
  "executor": { "kind": "subagent", "agentId": "<agentId>" },
  "step": "8",
  "target": { "type": "role", "id": "<roleId>", "name": "<roleName>" },
  "status": "succeeded",
  "outputs": {
    "roleName": "<roleName>",
    "roleId": "<24位真实roleId>",
    "roleScope": "<general或externalPortal>",
    "roleIdByName": { "<roleName>": "<24位真实roleId>" }
  },
  "verification": {
    "passed": true,
    "evidence": ["已完成角色精细权限矩阵构建并获取真实 roleId"]
  },
  "issues": []
}
```
