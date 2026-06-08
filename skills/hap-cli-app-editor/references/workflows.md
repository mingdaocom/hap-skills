# workflow & node ops

## 进程级
- `workflow.create` — `{name, [trigger_type], [desc]}`
  trigger_type：1=工作表触发、5=定时、6=按日期。注意 type 1 未绑触发工作表前不出现在
  `workflow list`；定时/日期型创建后即可按名解析。
- `workflow.update` — `{workflow:"<名|id>", [name], [desc], [icon_color]}`
- `workflow.delete` — `{workflow:"<名|id>", confirm:true}`
- `workflow.publish` — `{workflow:"<名|id>", [disable]}`

## 节点级（追加/改配置/改名/删除，后端自动重连）
- `node.add` — `{workflow, node:{name, node_type, [after], [action_id], [worksheet], [app_type]}}`
  在 `after`（节点名/id，缺省=起始节点）之后追加节点；后端自动重算连接。node_type 见
  `hap workflow node types`（如 13=人工/审批明细）。数据动作节点给 action_id + worksheet。
- `node.update` — `{workflow, node:"<名|id>", config:{...}, [node_type], [name]}`
  **原位**改一个已存在节点的完整配置（节点 id 不变，连接/位置都保留）。`config` 是节点的
  整段 wire 配置（形状与 `hap workflow node get` 返回一致）：先 `hap workflow node get <pid> <nid>`
  读出当前配置，改掉出错的部分，原样传回即可。`node_type`（即 `--type` 枚举：0=起始、1=分支、
  4=审批、5=抄送、6=数据动作、7=查单条、13=查多条、27=站内通知…）缺省时自动取该节点当前 typeId。
- `node.rename` — `{workflow, node:"<名|id>", name}`
- `node.delete` — `{workflow, node:"<名|id>", confirm:true}`（后端自动重连）

> **修建到一半的工作流（hap-cli-app-creator 失败项）的推荐姿势**：流程进程已存在（清单里带 processId），
> 不要重建。按情况原位修：
> - 仅"未发布" → `workflow.publish`。
> - 某个节点配置写错（通知收件人/审批人/字段映射/分支条件等）→ `node.update` 改那一个节点。
> - 整条流程没建出节点（batch-add 整批失败）→ 在同一 processId 上 `node.add` 逐个补节点、再各自
>   `node.update` 配好、最后 `workflow.publish`。
>
> **不在范围内**：中间插入到分支内部、复杂分支拓扑的重排——这类需要精确控制连接关系，
> 用 hap-cli-app-creator 重建，或录制真实 payload 后用 `hap workflow node batch-add` 还原。
