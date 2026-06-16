# 场景：改造一条工作流的节点（改配置 / 换收件人 / 插节点）

目标：给「订单审批流」的通知节点换收件人，并在审批通过后插入一个「更新订单状态」节点。

## 命令序列

```bash
# 0. 定位流程与节点
hap --json workflow list <appId>                  # 拿 process_id（注意是位置参数）
hap --json workflow node list <process_id>        # 拿各节点 node_id 与 typeId

# 1. 改收件人：先读现状，照形改写
hap --json workflow node get <process_id> <notice_node_id> > node.json
# 编辑 node.json 里的 accounts —— 结构见 WorkflowAccounts 类型：
#   固定用户 = {"type":1, "roleId":"<accountId>"}   ← accountId 放 roleId！
#   应用角色 = {"type":2, "entityId":"<appId>", "roleId":"<roleId>"}
hap workflow node save <process_id> <notice_node_id> \
  --type 27 --config '{"accounts": [{"type":2,"entityId":"<appId>","roleId":"<roleId>"}]}'

# 2. 在审批节点之后插入「更新记录」节点
#    --app-id 这里传的是目标工作表 id,且必须在创建时就给(事后补不上)
hap workflow node add <process_id> --type 6 --action-id 2 \
  --name "更新订单状态" --after <approval_node_id> --app-id <ws_id>

# 3. 配置新节点写哪些字段（FieldWrite 结构,$模板取触发记录的值）
hap workflow node save-action <process_id> <new_node_id> \
  --fields '[{"fieldId":"<statusCtrlId>","type":11,"fieldValue":"<optKeyDone>"}]'

# 4. 重新发布使改动生效
hap workflow publish <process_id>
```

## 注意

- **收件人 type 语义反直觉**（type 1 的 accountId 放 `roleId`，type 2 的 `entityId` 是 appId），写错会显示「已删除」且发布失败——见 [WorkflowAccounts](../../scripts/types/workflow-accounts.schema.json)。
- 节点条件用 [OperateCondition](../../scripts/types/operate-condition.schema.json)，字段键是 `filedId`（不是 fieldId）。
- 改完任何节点都要 `workflow publish` 才生效；发布失败时 `hap --json workflow get <process_id>` 看校验错误。
- 分支内中间插入/复杂拓扑重排不支持——重建该流程或在页面端手工调整。
