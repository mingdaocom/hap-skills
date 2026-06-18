---
name: hap-cli
description: 用 hap-cli 命令行工具操作 HAP 企业平台，是 hap-cli skills 的主入口。覆盖通讯录、聊天消息、发动态、管日程，以及应用与数据操作（工作表记录增删改查、工作流、审批待办、自定义页面、角色权限、文件上传等）。只要用户想在 HAP 里查人、发消息、发动态、看/建日程、读写某张表的记录、处理审批，即使没明说工具名也应触发。
---

# hap-cli 使用导航

`hap-cli`（命令 `hap`）把 HAP 企业平台的后端能力封装成命令行。登录一次后，就能在终端里查通讯录、收发消息、发动态、管日程，也能读写工作表记录、处理审批，以及创建/修改应用。

本 skill 是**总览与导航**：先帮你把工具装好、登录、选好组织和应用，然后告诉你「哪类需求用哪个一级命令」，以及「整体建应用/改应用该切到哪个专门 skill」。具体某个命令的参数永远以 `hap <命令> --help` 为准——不要凭记忆猜参数。

## 工作方式

1. **先确认环境就绪**：装好、已登录、选好当前组织（必要时选好默认应用）。见下文「准备工作」。
2. **判断需求类型**：
   - 单点操作（查一个人、发一条消息、读一条记录、处理一个审批）→ 直接用对应一级命令，见「命令地图」。
   - 整体建一个新应用 / 改一个已有应用的元素 → 切到专门 skill，见「两个应用建设 skill」。
3. **执行**：用 `hap <命令> --help` 看清子命令和参数再跑；脚本化场景加 `--json` 拿结构化输出。

---

## 准备工作

### 1. 安装

```bash
pip install hap-cli
```

包内已自带运行所需的 v3 接口 schema，装完即用，无需额外配置。

### 2. 登录

```bash
# 明道云 SaaS（默认环境）
hap auth login

# 指定环境
hap auth login mingdao                    # 生产
hap auth login nocoly                      # Nocoly SaaS
hap auth login https://hap.example.com     # 私有部署

# 非交互（脚本 / 无界面服务器）
hap auth login https://your-server.com --token YOUR_TOKEN
```

`hap auth login` 会打开浏览器登录页并自动捕获 token。如果回调到不了 CLI（无图形界面、网络受限），中断命令即可——它会退回到「把成功页上的 token 粘进来」的提示。

登录后自检与登出：

```bash
hap auth whoami        # 当前用户 + 当前环境/账号 + 当前组织
hap auth logout        # 登出当前账号
```

> 在做实际操作前，习惯先跑一次 `hap auth whoami` 确认会话有效、环境与组织正确。报错或未登录就先 `hap auth login`。

### 2.5 多环境 / 多账号

hap-cli 支持**同时授权多个环境与账号**——Mingdao SaaS、Nocoly、私有部署，以及同一环境下的不同账号，都能各自登录保存、长期共存、随时切换，不必反复重新登录。

```bash
# 登录并起名保存（--profile 是你给这个环境/账号起的名字）
hap auth login mingdao --profile work-prod
hap auth login https://hap.example.com --profile onprem
# 省略 --profile 时按登录地址自动起名；登录一个新环境不会覆盖已保存的

hap auth accounts                   # 列出所有已保存的环境/账号，当前的带 *
hap auth use work-prod              # 切换当前使用的环境/账号
hap --profile onprem app list       # 只让这一条命令临时用某个环境/账号
HAP_PROFILE=onprem hap app list     # 整个终端会话默认用某个环境/账号

hap auth logout                     # 登出当前账号
hap auth logout -p onprem           # 登出指定账号
hap auth logout --all               # 登出全部账号
```

> 多个环境/账号并存时，**操作前先用 `hap auth accounts`（看 `*`）或 `hap auth whoami` 确认当前用的是哪个**，破坏性操作（删除、发布、改权限）尤其要核对环境与账号，别在不该动的环境上动手。需要 AI 帮你按场景自动选/切环境时，见 `hap-cli-environments` skill。

### 3. 选组织与默认应用

很多命令需要一个组织、一个应用作上下文。先把默认值定好，后面就能省掉一堆 `--org-id` / `--app-id`：

```bash
hap auth list-my-orgs               # 列出我的组织，当前组织带 *
hap auth set-current-org ORG_ID     # 切换默认组织

hap app list                        # 用当前组织列应用，默认应用带 *
hap app select APP_ID               # 设默认应用（之后可省略 --app-id）
hap app unselect                    # 清除默认应用
```

命令解析 `--app-id` 的顺序是：显式传入的 `--app-id` → `hap app select` 设的默认应用 → 否则报错并提示你先 select。`set-current-org` 只改默认**组织**，不影响默认应用，两者独立管理。

### 4. JSON 输出与 REPL

`--json` 是**全局选项，必须紧跟在 `hap` 后面、子命令前面**，不能放到子命令末尾：

```bash
hap --json worksheet record list WORKSHEET_ID   # ✅ 正确：--json 在 hap 后
hap --json chat list                            # ✅
hap chat list --json                            # ❌ 报 "No such option: --json"
hap worksheet record list WS_ID --json          # ❌ 同上
```

> 同理，`--profile` 等其它全局选项也放在 `hap` 与子命令之间（如 `hap --profile onprem app list`）。子命令自己的选项（`--page-size`、`-f` 等）才跟在子命令后面。

连续操作可进交互模式（去掉开头的 `hap`）：

```bash
hap repl
hap> worksheet record list WORKSHEET_ID
hap> --json workflow list
hap> quit
```

---

## 命令地图

下面只列 `hap` 的一级大命令，按场景分组；每个大命令下还有子命令，用 `hap <命令> --help` 展开。

### 协作与沟通

| 命令 | 用途 |
| --- | --- |
| `hap contact` | 通讯录与联系人：按关键字/姓名/邮箱/手机找人、好友关系 |
| `hap department` | 部门：组织架构树、部门成员、目录查询 |
| `hap chat` | 聊天与消息：会话列表、收发单聊/群聊消息、共享文件 |
| `hap group` | 群组：建群、加/移成员、群信息 |
| `hap post` | 动态与帖子：发动态、评论、点赞、收藏、置顶、话题 |
| `hap calendar` | 日历与日程：日程增删改查、分类、成员 |

常用示例：

```bash
hap contact search --keyword 张伟              # 找人
hap chat send-to-one --account-id USER_ID --message "下午三点开会"
hap chat send-to-group --group-id GROUP_ID --message "周报已更新"
hap post create --content "新版本已发布 🎉"
hap calendar create --title "项目评审" --start "2026-06-10 15:00"
```

#### 从一条消息/通知触达对应的应用记录

未读消息里很多是「某人在某条记录下的讨论」「工作流抄送了一条记录」。要顺着消息找到那条记录，走这条固定链路，不要去翻工作表猜：

1. `hap --json chat list` —— 每个会话都带 `category` 字段（`system/post/calendar/task/kc/hr/app/workflow`，或单聊 `user`/群聊 `group`）。**应用/工作表里的记录讨论归在 `app` 类**，工作流通知归在 `workflow` 类。
2. 按这个 `category` 拉明细：`hap --json chat messages --category app`（或 `workflow` 等）。
   - 记录讨论类的条目直接带齐 **`appId` + `worksheetId` + `rowId`**（外加 `viewId`、`comment.recordName`、`comment.entityName`）。这里的 `appId` 已是记录真实所属应用（不是消息中心那个、可能已删除的 app）。
   - 工作流**抄送/参与者**类通知会把记录链接里的 `appId/worksheetId/rowId` 一并解析出来。
   - 单聊/群聊不走 `--category`，用 `--with-user <accountId>` / `--group-id <groupId>`（id 取会话的 `value`）。
3. 拿到三元组就能直接读这条记录及其完整讨论：
   ```bash
   hap worksheet record get <worksheetId> <rowId> -a <appId>
   hap worksheet record discussions <worksheetId> <rowId> -a <appId>
   ```

> 关键点：触达记录用 `chat messages` 条目里的 `appId`（来自讨论的 `extendsId` / 链接），**不要用会话顶层那个 appId**——后者是消息中心的归属 app，常常是已删除的，拿去查记录会报「应用已删除」。

### 应用与数据

| 命令 | 用途 |
| --- | --- |
| `hap app` | 应用管理：应用/分组/角色/选项集/知识库、备份导出、使用统计 |
| `hap worksheet` | 工作表：表结构、视图、业务规则、自定义动作、图表，以及记录（`record`）增删改查 |
| `hap workflow` | 工作流：流程/节点的查看与管理、发布、触发、审批块 |
| `hap approval` | 审批与待办：处理审批、批量操作、委托 |
| `hap custom-page` | 自定义页面：读写布局、生命周期 |

常用示例：

```bash
hap app info APP_ID                                   # 看应用结构
hap worksheet list                                    # 列默认应用的表
hap worksheet record list WORKSHEET_ID --page-size 10
hap worksheet record create WORKSHEET_ID -f "c001=值1" -f "c002=值2"
hap approval todo --type 4                            # 我的待办
hap approval approve INSTANCE_ID --opinion "同意"
```
> 看工作表结构别猜命令：看字段用 `hap worksheet fields WS_ID`（**不是** get/structure），
> 看表信息用 `hap worksheet info WS_ID`，看视图用 `hap worksheet view list WS_ID`。
> `worksheet fields` 每个字段返回的 key 是：
> `id / name / alias / type / subType / dataSource / sourceField / options`
> （筛选、排序、更新里要用的字段标识取 `id`）。

> 注意：`record list/get` 可带 `--app-id`，但 `record create/update/delete` **不接受 --app-id**，
> 只走默认应用。改数据前先 `hap app select <appID>` 设一次默认应用即可，后续不必再传。

> 操作工作流节点前，先 `hap workflow structure PROCESS_ID` 看清真实结构，不要凭空捏造节点/分支/审批块 ID。

#### 子表（SubTable）数据怎么读写

SubTable 字段不在父记录里存数据，要绕一层：

- 父记录 `record get` 对 SubTable 字段只返回**子行数量**（一个数字），不含子行内容。
- 子行真实存储在该字段 `dataSource` 指向的**另一张独立工作表**里。
- 子行通过**反向 Relation 字段**（父 SubTable 字段的 `sourceField`）挂回父行。

定位关系（都用 `hap worksheet fields` 看）：

| 要素 | 来源 |
| --- | --- |
| 子表所在工作表 ID | 父表里 SubTable 字段的 `dataSource` |
| 子行→父行的关联字段 ID | 父表里 SubTable 字段的 `sourceField` |
| 子表里的目标字段（如备注）ID | 子表 `worksheet fields` 里对应字段的 `id` |

改子表两条路，按场景选：

- **改某一行的某个值 → 直接改子行（推荐）**：对子表工作表 `record update <子行rowid> -f "<字段ID>=<值>"`。
- **新增/删除子行、批量增删 → 改父记录的子表字段**：对父记录 `record update --fields-json`，子表字段值是子行数组——带 `rowid` 改、无 `rowid` 增、`{"_delete":true}` 删，未列出的行不动（详见 `record update --help`）。

> `--filter-json` 用 builder DSL：
> `{"type":"group","logic":"AND","children":[{"type":"condition","field":"<字段ID>","operator":"in","value":[...]}]}`，
> **不是** `[{controlId,dataType,filterType,values}]` 那套主站 wire 格式（会报反序列化错误）。
> 运算符是 `eq/ne/ge/le/in/notin/contains/isempty…`，复杂筛选、透视统计见 `hap-cli-data-query` skill。


### 平台资源与工具

| 命令 | 用途 |
| --- | --- |
| `hap region` | 行政区划查询（按 `--id` 或 `--search`） |
| `hap icon` | 内置图标目录（中英文关键字搜索） |
| `hap upload` | 文件上传，返回中性的文件描述符，可挂到附件字段/聊天/动态/日程/评论 |

### 认证与本地配置

| 命令 | 用途 |
| --- | --- |
| `hap auth` | 登录、登出、当前身份、多环境/多账号切换（`accounts` / `use`）、组织列表与切换 |
| `hap config` | 本地配置：`config show`、`config completion` 装 Tab 补全、`config language` 切语言、`config log on/off/view` 控制 API 日志 |
| `hap repl` | 交互式命令行 |

> 排查问题时可开日志：`hap config log on`，日志落在 `~/.hap-cli/hap-cli.log`，会记录每次 API 调用的 URL、请求/响应体，并对 `Authorization` 做脱敏。

---

## 复杂查数 skill —— `hap-cli-data-query`

查工作表数据看着简单，但**筛选器和透视参数的 JSON 很容易写错**：运算符词表（`ge`/`le`/`isempty`/`notin`…，和工作流那套不一样）、选项字段要用 key、透视的维度粒度与聚合方式等。遇到下面这些就切过去：

- **何时切过去**：「查某张表里满足…条件的记录」「按状态/日期筛选」「这个筛选器怎么写」「多条件 AND/OR、嵌套分组」「统计每个月/每个分类的合计」「做个透视/汇总」「`--filter-json` 报错或查不出来」。
- **它做什么**：把 `record list` / `record pivot` 的 filter-json 结构与完整运算符词表、`--values-json`/`--rows-json` 的维度与聚合参数讲清楚，并给可直接套用的模板和排错清单。
- **怎么用**：直接调用 `hap-cli-data-query` skill。
- **边界**：只是简单按 ID 取一条记录、或不带筛选地翻页，直接用 `hap worksheet record list/get` 即可，不必动用它。

一个典型的 HAP 工作表视图页面地址：`/app/<app_id>/<section_id>/<worksheet_id>/<view_id>`。一个典型的 HAP 工作表行记录页面地址：`/app/<app_id>/<worksheet_id>/<view_id>/row/<rowid>`。

拿到 worksheetId + rowId 即可直接 `record get/update`，`sectionId/viewId` 改数据时用不到。

## 两个应用建设 skill（重点）

当需求不是「单点操作」，而是**围绕一个应用做整体建设或结构性修改**时，不要手敲一长串命令——切到下面两个专门 skill，它们封装了经过实测的多步流程（设计校验、按逻辑名解析真实 ID、预演、执行、失败只记录不乱重跑），比手动拼命令可靠得多。

### 创建应用 —— `hap-cli-app-creator`

从一句业务需求，一站式建出**真实可用、带示例数据**的 HAP 应用。

- **何时切过去**：用户描述了一个业务场景，想从零搭出整个应用。例如「帮我做一个 CRM / 库存 / 报修 / 借阅系统」「把这个业务做成 HAP 应用」「建几张表并配好关系」。
- **它做什么**：先与用户确认业务方案（模块、工作表、字段、角色），产出 ID-free 的设计文档 `design.json` 并本地校验通过，再用 `hap` 命令一次性物理搭建应用，最后生成并填充示例数据。
- **怎么用**：直接调用 `hap-cli-app-creator` skill，把用户的业务需求交给它。

### 修改应用 —— `hap-cli-app-editor`

对一个**已存在**的应用做精确的局部修改，而不重建整个应用。

- **何时切过去**：针对已有应用做单点结构改动。例如「在某张表加个字段」「把这个视图改名」「停用那条工作流」「给某角色加查看/编辑权限」「加个自定义动作按钮」「新建分组并把页面归类进去」「删掉这张表/视图」，或「修一下建到一半出错的应用」。
- **它做什么**：每次操作前从后端读取应用实时结构，把修改表达成结构化的 edit-spec（JSON），框架负责校验、把逻辑名解析成真实 ID、预演、执行；删除/覆盖类破坏性操作必须显式确认。
- **怎么用**：直接调用 `hap-cli-app-editor` skill，告诉它目标应用和要改的元素。

> **怎么选**：
> - **从零搭整个应用** → `hap-cli-app-creator`
> - **改已有应用的某个元素**（字段/视图/表/角色/工作流/动作/页面） → `hap-cli-app-editor`
> - **复杂筛选 / 透视聚合统计查数据** → `hap-cli-data-query`
> - **简单增删改记录、不带筛选地翻页取数** → 不需要 skill，直接用 `hap worksheet record` 命令即可。
