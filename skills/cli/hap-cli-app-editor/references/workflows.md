# 工作流（workflow）— 流程与节点基础操作

操作对象分两层：**流程**（process，一条工作流本身）与**节点**（node，流程内的步骤）。
节点的逐类型深度配置见 [nodes.md](nodes.md)；本篇只覆盖流程级命令、节点增删改名、触发器配置。

**术语：PBP = 封装业务流程（Packaged Business Process）。** 用户说「封装业务流程」「PBP」时，
一律对应 `workflow create --type pbp` + `batch-add --trigger-pbp`。

**全局规则**：改节点配置前先 `hap --json workflow node get <process_id> <node_id>` 导出现状，在真实结构上改，再写回。

## 调用范式

### 流程级

```bash
# 列出一个应用下的工作流（app_id 是位置参数，不是 --app-id）
hap workflow list <app_id> [-k 关键字] [--enabled|--disabled] [-n 50] [-p 1]

# 查看流程详情 / 节点结构
hap --json workflow get <process_id>
hap workflow structure <process_id>

# 新建流程（-c 是组织 ID，不是应用 ID；--type 见数据字典「触发类型」，
# 支持名称值：worksheet / scheduled / date / webhook / pbp）
hap workflow create -c <org_id> -n "流程名" -a <app_id> --type worksheet

# 改名 / 描述 / 图标色
hap workflow update <process_id> -n "新名" -d "描述" --icon-color "#2196F3"

# 复制 / 删除
hap workflow copy <process_id> -n "副本名" [--sub-process]
hap workflow delete <process_id> -y

# 发布（启用）/ 停用
hap workflow publish <process_id>
hap workflow publish <process_id> --disable

# 手动触发一次（-s 传源记录 rowId）
hap workflow trigger <process_id> [-s <row_id>]
```

坑位提示：

- `hap workflow list <app_id>` 的应用 ID 是**位置参数**。新建的 `--type 1`（工作表触发）流程在触发器绑定工作表之前**不会出现在该列表里**——拿好 `create` 返回的 `id`，别靠列表反查。
- `publish` 失败时会打印校验诊断并以非零码退出。最常见的两个原因：触发器没配置（见下文「触发器配置」）、人员类节点的收件人编码错误导致显示为「已删除」（见 [nodes.md](nodes.md) 的 accounts 坑位）。
- `delete` / `node delete` 都需要 `-y` 跳过确认；删除流程不可恢复。

### 节点基础（增 / 删 / 改名 / 读配置）

```bash
# 列出全部节点（拿 nodeId、typeId、连接关系）
hap --json workflow node list <process_id>

# 读单个节点的完整配置（--type 传该节点的 typeId，来自 node list）
hap --json workflow node get <process_id> <node_id> --type 6

# 追加节点：--after 必填，传上游节点 ID（接在触发器后就传触发节点 ID）
hap workflow node add <process_id> --type 6 -n "写入记录" --after <prev_node_id> \
  -a 1 --app-id <worksheet_id>

# 改名 / 删除（删除后两侧自动重连）
hap workflow node rename <process_id> <node_id> -n "新名"
hap workflow node delete <process_id> <node_id> -y

# 节点类型枚举速查
hap workflow node list-types
```

坑位提示：

- **数据类节点（type 6 / 7 / 13）的目标工作表 `--app-id` 必须在 `node add` 时给定**；建好后再用 `node save` 补传会被静默丢弃，节点只能删了重建。
- `node get` 建议总是带 `--type <typeId>`（从 `node list` 读），不同类型返回的结构差异很大。
- 单独改一个已存在节点的配置：`node get` 读出 → 改你要改的键 → `node save` 整段写回（节点 ID、连接、位置都保留）。具体每类节点的键表见 [nodes.md](nodes.md)。

### 批量建节点 + 触发器配置（batch-add）

`node batch-add` 一次完成「绑触发器 + 按顺序建多个节点并配好」。节点间用别名互相引用，物理 ID 自动解析：

```bash
# 工作表触发：绑定触发表 + 事件，再顺序建两个节点
hap workflow node batch-add <process_id> \
  --trigger-worksheet <worksheet_id> --trigger-event create \
  --nodes '[
    {"nodeAlias":"find",  "nodeType":7, "config":{...}},
    {"nodeAlias":"write", "nodeType":6, "config":{...}}
  ]'

# 只配触发器、不建节点：--nodes 传空数组
hap workflow node batch-add <process_id> --nodes '[]' \
  --trigger-schedule '{"repeat":"day","interval":1,"start_time":"2026-06-11 08:00"}'
```

触发器相关选项按流程类型选用其一：

- `--trigger-worksheet` + `--trigger-event create|update|create_or_update|delete`（工作表事件型）；`--trigger-fields f1,f2` 把 update 触发收窄到指定字段；`--trigger-filter '<条件组JSON>'` 只放行满足条件的记录，条件结构 → [OperateCondition](../scripts/types/operate-condition.schema.json)。
- `--trigger-schedule '{repeat,interval,week_days,start_time,end_time,config}'`（定时型）。
- `--trigger-date '{worksheet,date_field_id,offset_type,offset_number,offset_unit,time,repeat}'`（按日期字段型）。
- `--trigger-webhook '{"sample":{...}}'`（Webhook 型：用样例请求体推导入参结构）。
- `--trigger-pbp '{"inputs":[{name,type,required,alias,desc,default,options,children}]}'`（PBP/封装业务流程型：定义输入参数。type 取 text/number/date/radio/checkbox/member/department/org_role/attachment/object/array/object_array，默认 text；radio 的 options 传字符串数组；object_array 用 children 嵌一层子参数）。

```bash
# PBP：定义两个输入参数（建流程时 --type pbp）
hap workflow node batch-add <process_id> --nodes '[]' \
  --trigger-pbp '{"inputs":[
    {"name":"订单号","type":"text","required":true},
    {"name":"数量","type":"number"}
  ]}'
```

坑位提示：

- 新建的工作表触发流程，**触发器未绑定前无法发布**——建完流程第一件事就是绑触发器。
- 修「建到一半」的流程时不要重建：流程已存在就在原 process_id 上补——缺节点用 `node add` / `batch-add` 补，节点配置错用 `node get` + `node save` 原位修，最后 `workflow publish`。需要精确控制分支内部拓扑的复杂重排不在此范围。

## 数据字典

字典生成于 2026-06-10；未覆盖的键以 `hap workflow node get` 返回的实际结构为准。

### 触发类型（`workflow create --type`）

`--type` 接受名称或数字码，优先用名称：

| 值 | 含义 | 触发器配置方式 |
|---|---|---|
| `worksheet`（1） | 工作表事件触发 | `batch-add --trigger-worksheet/--trigger-event/--trigger-fields/--trigger-filter` |
| `scheduled`（5） | 定时（周期）触发 | `batch-add --trigger-schedule` |
| `date`（6） | 按日期字段触发 | `batch-add --trigger-date` |
| `webhook`（7） | Webhook 触发（外部 HTTP 请求） | `batch-add --trigger-webhook` |
| `pbp`（17） | **封装业务流程（PBP）**，供其他流程/页面按钮调用 | `batch-add --trigger-pbp`；手动触发用 `workflow trigger-pbp` |

### 发布 / 启用语义

| 键 / 操作 | 含义 | 值形态 |
|---|---|---|
| `enabled` | 流程是否已启用（`workflow list` / `get` 返回） | bool；`publish` 置 true，`publish --disable` 置 false |
| `publish` 结果 | 启用成功与否 + 校验诊断 | 失败时输出告警明细并非零退出；阻断级告警必须修复后重发 |
| `workflow rollback / history` | 回滚到历史版本 / 查看发布历史 | `hap workflow history <pid>`、`hap workflow rollback <pid> -y` |

### 节点类型 ID（`hap workflow node list-types` 完整枚举）

带 → 的 8 类在 [nodes.md](nodes.md) 有逐键深度字典。

| typeId | 名称 | 说明 |
|---|---|---|
| 0 | START | 触发节点（每流程一个，不可增删） |
| 1 | BRANCH | 分支网关 |
| 2 | BRANCH_ITEM | 分支项（条件挂在这层）→ nodes.md |
| 3 | FILL | 填写 |
| 4 | APPROVAL | 审批 → nodes.md |
| 5 | CC | 抄送 → nodes.md |
| 6 | ACTION | 数据动作（增/改/删记录等）→ nodes.md |
| 7 | SEARCH | 查询单条记录 → nodes.md |
| 8 | WEBHOOK | 发送 HTTP 请求 → nodes.md |
| 9 | FORMULA | 公式 |
| 10 | MESSAGE | 短信 |
| 11 | EMAIL | 发送邮件 → nodes.md |
| 12 | DELAY | 延时 → nodes.md |
| 13 | GET_MORE_RECORD | 获取多条记录 / 批量操作（`save-get-more` 配置） |
| 14 | CODE | 代码块 |
| 15 | LINK | 获取链接 |
| 16 | SUB_PROCESS | 子流程 |
| 17 | PUSH | 界面推送 |
| 18 | FILE | 生成文件 |
| 19 | TEMPLATE | 服务号消息 |
| 20 | PBP | 调用封装业务流程（在流程里调一个已发布的 PBP） |
| 21 | JSON_PARSE | JSON 解析 |
| 22 | AUTHENTICATION | API 鉴权 |
| 23 | PARAMETER | 参数 |
| 24 | API_PACKAGE | API 包 |
| 25 | API | 调用已集成 API |
| 26 | APPROVAL_PROCESS | 发起审批流程 |
| 27 | NOTICE | 站内通知 |
| 28 | SNAPSHOT | 记录快照 |
| 29 | LOOP | 循环 |
| 30 | RETURN | 返回 |
| 31 | AIGC | AI 生成 |
| 32 | PLUGIN | 插件 |
| 33 | AGENT | AI Agent |
