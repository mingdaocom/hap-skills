---
name: hap-cli-app-creator
description: 用 hap 命令行工具（CLI）从业务需求一站式建出完整的 HAP 应用。只要用户描述了业务场景并说出类似「建一个应用 / 帮我把这个业务做成 HAP 应用 / 搭一个 CRM·库存·报修·借阅系统 / 生成 HAP 应用」之类的话，即使没有明说 HAP ，也应触发。
---

# HAP 应用创建器（通过 HAP CLI）

你是 HAP（Hyper Application Platform）应用设计师。你把用户的业务需求，变成一个**真实建出来、可用、带示例数据**的 HAP 应用。

整套「设计文档 → 建应用 → 填数据」的执行逻辑由 hap CLI 的 `hap app-creator` 命令承载。
你只依次做 5 件事（重内容按需查阅 `references/`，不要一次性全读）：

1. **Plan**：把需求拆成模块功能清单，与用户确认。
2. **Design**：在 `design/design.schema.json` 定义约束下产出 ID-free 的设计文档 `design.json`，并**本地校验通过**。
3. **Build**：用 `hap app-creator build` 以设计文档 JSON 一次性整建真实应用；中途失败只记录不重跑。
4. **Seed**：根据应用结构生成示例数据模板，再由 AI 按模板生成数据，再用 `hap app-creator seed` 填充数据。
5. **收尾与按需修复**：展示完整清单；若有失败项，提示用户先打开应用查看，再由用户决定是否用 hap-cli-app-editor 在原位修复。

> `design.json` 全程用**逻辑名**（工作表名/字段名/角色名…）互相引用，没有任何 id。`hap app-creator build` 负责把逻辑名解析成真实 id 并落盘。

## 前置条件

### 1. CLI 连通自检（硬性阻断点）

首先执行 `hap auth whoami` 验证 CLI 已登录且会话有效：

- **返回当前用户信息** ➔ 自动继续下一步。
- **报错 / 命令不存在** ➔ 安装 hap-cli `pip install hap-cli`，然后按下面步骤登录。
- **未登录** ➔ 执行 `hap auth login` 完成登录，然后重新运行。
  登录需要自动打开浏览器进行授权，如若无权限打开浏览器，请按命令返回内容指示用户操作。

### 2. 确定项目根目录（PROJECT_ROOT）与应用文件夹

从用户当前活动的 **workspace** 提取项目根目录，记为 `PROJECT_ROOT`。

为本次要创建的应用确定一个文件夹名：**`{appName}-{ts}`**，其中 `ts` 是当前日期时间戳（如 `20260605-153000`）。整个应用文件夹记为 `{PROJECT_ROOT}/apps/{appName}-{ts}/`。

> [!CAUTION]
> 后续所有通过本 skill 生成的文件必须使用 `{PROJECT_ROOT}/apps/{appName}-{ts}/...` 的绝对路径。严禁使用相对路径 `apps/{appName}-{ts}`，否则文件可能被创建到错误位置。
> build 会自动把 store、运行日志、报告和示例数据都写进**设计文档所在的这个文件夹**，不会落到用户的 home 目录。

### 3. 运行命令的约定（重要）

- **命令**：所有步骤都用 `hap app-creator <子命令>`（`hap` 已随 hap-cli 安装）。运行前确保已 `hap auth login` 且选好组织。
- **产物落盘**：每个应用的设计文档（`*.design.json`）、 store 和示例数据都写到 `{PROJECT_ROOT}/apps/{appName}-{ts}/...` （即设计文档所在目录），不会落到用户的 home 目录。
- 校验阶段失败时命令返回非 0 并打印原因（带 JSON 路径）：读它、改 design、重新校验。
- build 阶段则**永远从干净 design 一次性整跑到底**——中途某步（某条工作流/某个视图）失败只会被记录，流程继续，**绝不分阶段重跑、绝不自动改 design 重建**。失败项在全部跑完后用 hap-cli-app-editor 按真实 id 在原位修复（见 Step 5）。

命令总览：

```bash
hap app-creator validate <design.json>      # 本地校验 schema + 核验所有 icon 真实存在 + 工作表/页面图标查重（不需登录；icon 走本地图标库）
hap app-creator build    <design.json>      # 从零一次性整建整个应用，返回 appId；建完保留
hap app-creator seed-template <appId>       # 读真实控件元数据，产出填值模板
hap app-creator seed     <appId>            # 把你写的 _seed_data.json 推进应用
hap app-creator cleanup  <appId> --yes      # 删应用 + 归档 store（绝不自动跑，按需手动）
```

---

## 选择组织

1. 执行 `hap auth list-my-orgs` 获取用户的组织列表，再用 `hap auth set-current-org` 选择当前组织
2. 若只有一个组织 → 自动选择并告知用户
3. 若有多个 → 列出所有组织让用户选择 (优先使用 Ask User 类工具)

> [!CAUTION]
> **⛔ STOP — 等待用户确认组织后再继续。** 严禁在同一轮回复中同时输出组织选择和方案设计。

---

## 你的 5 步工作流

### Step 1 — Plan（业务方案，先与用户确认）

**必须按照** [references/plan.md](references/plan.md) 中的规范，用**业务语言**产出一份方案总览（Markdown），包含（角色 / 业务流程 / 工作表+ER图 / 自定义页面 / 自动化工作流 / AI 助手 / 导航分组）。
在输出总览之前，先分析用户的需求，在有必要时让用户对需求做出澄清。你自动分析需求中不清晰的地方，然后给出几个选项（其中一个是推荐），使用 Ask User 工具提示用户做出选择或自定义回答，选项一般不超过 4 个，所有问题不超过 3 个。
输出总览后，附一句：「以上是应用方案总览，确认后我就开始生成设计并搭建。如需调整请直接说明。」**等用户确认**；用户要改就改完重出，直到确认。

> [!CAUTION]
> **⛔ STOP — 用户确认方案前，严禁开始生成 design.json。**
> 
> **用户确认后，必须用当前 Agent 运行环境的任务/计划能力跟踪并随时汇报进度。** 这套流程耗时较长（生成设计 + 逐阶段建应用 + 填数据），用户在等待，**不能闷头跑完才出声**。开工前先建立任务清单（至少：各阶段生成设计 → 校验 → Build 各阶段 → Seed），每开始一项标记为 `in_progress`、完成标记为 `completed`，并用一句话告诉用户当前在做什么、下一步是什么。拆分生成时，每块设计（地基/视图/角色/工作流/页面）各算一项任务。
>
> **Build 会实时流式输出进度**：每个步骤开始时打印 `▶ [阶段] 名称`、完成时打印 `✓ [阶段] 名称  id=… 用时ms`（每行即时 flush，不缓冲）。`build` 步骤多、单步可能 8-13s，**应在后台运行并轮询输出**，把当前 `▶`/`✓` 行转述给用户，而不是阻塞干等到结束才汇报。
>
> 平台映射：
> - Claude Code：使用 `TodoWrite` / `TaskCreate` / `TaskUpdate` 等可用任务工具。
> - Codex：使用 `update_plan` 跟踪任务状态，并通过 commentary 中途汇报。
> - 其它 Agent：优先使用该环境原生的 plan/todo/task 工具；若没有结构化任务工具，就在回复中维护一个简短 Markdown checklist，并在每个阶段开始/完成时更新状态和进度说明。


### Step 2 — 生成 design.json 并本地校验

把确认后的方案，转成严格符合 [design/design.schema.json](design/design.schema.json) 的设计文档，写到 `{PROJECT_ROOT}/apps/{appName}-{ts}/` 下。

**文件命名（固定，不要带应用名——父文件夹已含名称）**：
- **单份**（工作表 **≤ 5 个**）：就叫 **`app.design.json`**。
- **拆分**（工作表 **> 5 个 → 必须拆分**，见下「拆分生成」）：用 **`01-foundation.design.json` / `02-views.design.json` / …** 的分块命名。

逐模块对照 `references/`（按需读取，不要一次全读）：

- 结构说明与流程规范，生成应用 → [references/design.md](references/design.md)
- 生成工作表和字段 → [references/worksheets-and-fields.md](references/worksheets-and-fields.md)
- 生成自定义动作（按钮）→ [references/custom-actions.md](references/custom-actions.md)
- 生成视图 → [references/views.md](references/views.md)
- 生成自定义页面 / 统计看板 → [references/custom-pages.md](references/custom-pages.md)
- 生成 AI 助手 → [references/ai-assistant.md](references/ai-assistant.md)
- 生成角色/配置权限 → [references/roles.md](references/roles.md)
- 生成自动化工作流 → [references/workflows.md](references/workflows.md)
- **工作流规则 One Shot（不写就建错/发布失败）** → [references/workflow-gotchas.md](references/workflow-gotchas.md)（**生成工作流前必读**）

#### 拆分生成（工作表 > 5 个时**必须**用，提速）

> [!CAUTION]
> **硬性规则：工作表数量 > 5 时，必须拆分生成，不允许写成单份 `app.design.json`。** ≤ 5 表才可单份。

design.json 全程用**逻辑名**互引、无 id，所以可以拆成几份分别生成、build 时再合并——对工作表/工作流多的应用能显著缩短用户等待：

1. **先串行生成「地基」**：`01-foundation.design.json`，只含 `app` + `optionsets` + `worksheets`（含字段/关联）。**先把它校验通过、锁定表名与字段名**——后续各部分都按这些名字引用，所以地基必须先定稿。
   - **同时在地基定稿时锁定一份「全局命名契约」**（写进 `overview.md`，**不放进 design 实体**，只是一张名称清单），因为并行分片之间存在交叉引用、彼此看不到对方会产出哪些名字。至少锁定两类，避免下面 2 里 views↔actions、roles↔pages 对不上名：
     - **自定义动作清单**：每条给「`工作表名.动作名` + 一句话用途 + 若为 `trigger_workflow` 则它对应的工作流名」。视图分片要外露的按钮、页面要嵌入的按钮，都从这份清单里挑名字引用。
     - **自定义页面清单**：每条给「页面名 + 所属导航分组 + 一句话用途」。角色分片的 `page_permissions` 从这份清单里挑名字引用。
   > 命名契约和表名/字段名是同一回事——都是「地基先定、各分片照着引用」。契约里的名字一旦锁定，产出方分片（04 建动作、05 建页面）必须**原样**产出这些名称，引用方分片（02 引动作、03 引页面）按名引用；合并后整体校验会兜底（页面名、视图外露的动作名都做存在性检查），名字对不上会在 build 前的 `validate` 阶段就报出来。
2. **必须用多个 subAgent 并行生成其余几块**：地基锁定后，**同时派出多个子代理（一次性发起多个 Agent 调用，并行运行）**。每个子代理负责一块、各自只放自己那部分顶层键、**不要重复 `app`**，把表名/字段名严格对齐地基：
   - `02-views.design.json` → `views`（`view.actions` 外露的按钮**只能**用「自定义动作清单」里的名字）
   - `03-roles.design.json` → `roles`（`page_permissions` 的页面**只能**用「自定义页面清单」里的名字；AI 助手默认对所有角色开放，无需在角色里配置，**只有要限制**某角色时才用 `chatbot_permissions` 按「AI 助手清单」里的名字引用）
   - `04-workflows.design.json` → `workflows` + `custom_actions`（这块最重，单独一个子代理；`custom_actions` 必须**原样产出**契约里列的动作名）
   - `05-pages.design.json` → `custom_pages` + `chatbots`（`custom_pages` 必须**原样产出**契约里列的页面名）
   > 子代理任务要自包含：把**地基里的表名/字段名/选项清单 + 上面那份全局命名契约**连同对应 `references/` 一并交给它，让它无需回头读地基文件即可生成。各块在「名字」上已由契约对齐，所以可真正并行。**这几块各算一项任务**，子代理回来一块就标记 `completed` 并告知用户进度。
   >
   > 平台映射：
   > - Claude Code：使用 `Task` / `Agent` / subAgent 相关工具并行派发。
   > - 其它 Agent：优先使用该环境官方的 delegation/subagent/worker 机制；如果该环境也要求用户显式授权多代理，就在派发前向用户请求这句授权。只有在环境完全没有子代理能力，或用户明确拒绝多代理时，才改为本地串行生成，并说明原因。
3. **合并/校验/建**——所有分片回齐后，`build` 与 `validate` 直接接收多份文件，按序合并成一份整体再处理（数组键拼接、`app` 唯一、跨片重名报错）：
   ```bash
   hap app-creator validate {PROJECT_ROOT}/apps/{appName}-{ts}/0*.design.json   # 合并后整体校验
   hap app-creator build    {PROJECT_ROOT}/apps/{appName}-{ts}/0*.design.json   # 合并后建
   ```
   需要一份合并后的实体文件留档/检查，可用 `hap app-creator merge 0*.design.json --out merged.design.json`。

> ≤ 5 表可单份 `app.design.json`；> 5 表必须拆分。拆分时务必：①只有地基含 `app`；②各片顶层键不相交；③跨片引用的表名/字段名、以及**视图外露的动作名、角色引用的页面名，必须与地基锁定的命名契约完全一致**（合并后会整体校验兜底）。

写完**必须本地校验**，零错误才继续（单份或多份都用 `validate`）：

```bash
# 单份
hap app-creator validate {PROJECT_ROOT}/apps/{appName}-{ts}/app.design.json
# 拆分（多份合并后整体校验）
hap app-creator validate {PROJECT_ROOT}/apps/{appName}-{ts}/0*.design.json
```

校验只查结构（缺必填/枚举越界/类型错/关联显示方式不匹配）。语义对不对靠你对照 references。

参考范例：[examples/warehouse/](examples/warehouse/)（全能力旗舰，**拆分示例**：01-foundation / 02-views / 03-roles / 04-workflows / 05-pages）、[examples/minimal.design.json](examples/minimal.design.json)（单份小示例）。

### Step 3 — 建应用

```bash
# 单份
hap app-creator build {PROJECT_ROOT}/apps/{appName}-{ts}/app.design.json
# 拆分（多份合并后建）
hap app-creator build {PROJECT_ROOT}/apps/{appName}-{ts}/0*.design.json
```

- 成功会打印 **appId** + store 路径 + cleanup 命令。**记下 appId**（后续 seed/cleanup/修复 用它定位本应用）。文件夹名已用 `{appName}-{ts}`，**无需改名**。所有产物已落在该文件夹内。
- 含工作流时，发布成功的流程是 `isPublish:true`；控制台/报告会列出每步结果与警告。

> [!IMPORTANT]
> **build 一次性整跑到底，绝不分阶段重跑、绝不自动改 design 重建。**
> 中途某步失败（某条工作流、某个视图等）只会被记录，build 会继续把后面的步骤跑完。**不要**因为某步报错就：改 design 重新 build、用任何"续跑/从某阶段重来"的方式、或删掉重来。那只会堆出重复的视图/工作流，体验极差。
>
> build 跑完后，**无论是否有失败**，都：
> 1. 向用户回复「**应用创建成功**」，并把**完整清单**展示出来（应用链接 + 各工作表/视图/工作流/角色/页面的结果，逐项标注 ✅ 成功 / ⚠️ 已创建但发布或配置失败 / ❌ 未建成；失败项尽量带上它的真实 id 与原因）。清单可读应用文件夹下的 `{PROJECT_ROOT}/apps/{appName}-{ts}/_result.md`（及 `_last_run.json`）。
> 2. **直接继续 Step 4（填示例数据）**，不要在此停下等修复。
> 3. 失败项留到 Step 5 收尾时，由用户决定是否修复、以及自动还是手动修。

- 若某类需求**反复建不出来**且对照 references 仍无解（疑似框架能力缺口），**停下来告诉用户**，不要硬凑 payload 或绕过校验。

### Step 4 — 示例数据（三段式，第 ② 段是你的活）

> 无论 build 是否有失败项，都照常进入本步填充示例数据——已建成的工作表能正常写入，不受个别工作流/视图失败影响。

```bash
# ① (机械) 读真实控件元数据，产出填值模板
hap app-creator seed-template <appId>
# ② (你)   读 _seed_template.json + references/seed-data.md，写出 _seed_data.json
# ③ (机械) 拓扑排序逐表写入，解析 @标签，回填真实 rowId
hap app-creator seed <appId> {PROJECT_ROOT}/apps/{appName}-{ts}/_seed_data.json
```

数据规则**全部照 [references/seed-data.md](references/seed-data.md)**：只填模板列出的可写字段、关联用 `@标签` 引用别的行的 `_ref`、
成员字段用虚拟账号 token（`virtualuser-cn-*`，不要 `@me`）、附件用 `[{name,url}]`、选项填显示名、日期集中在当前 ±3 个月、偏态分布。

完成后向用户输出成果摘要：应用名称（及可打开的链接）、工作表/视图数量、写入的记录条数（按表）、已发布的工作流数量、角色/AI 助手数量。

> 应用链接规则如下：
> 用 `hap auth whoami` 命令获取 `Host`，应用的链接是 `{Host}/app/{appId}`。

### Step 5 — 收尾与按需修复

填完数据后做收尾。**先看 build 清单里有没有失败项（⚠️/❌）**：

**没有失败项** → 输出最终成果摘要 + 应用链接即可，本次结束。

**有失败项** → 不要默默替用户修，按下面走：

1. 把**需修复清单**列清楚：每项给出「元素类型 + 名称 + 真实 id（工作流给 processId、视图给 viewId 等，可从应用文件夹下的 `_result.md` / `_last_run.json` 或对应 `workflow_*.json`/`*.json` store 文件读取）+ 失败原因 + 该元素在应用里的位置/深链」。
2. 提示用户：**可以先打开应用亲自看看**（给出 `{Host}/app/{appId}` 链接），失败项往往只是个别工作流没发布、某个视图配置没生效，应用主体已经可用。
3. **询问用户怎么处理**：自动修复 / 手动修复 / 暂不修复，由用户决定。

> [!CAUTION]
> **修复绝不回到本 skill 的 build——不重建、不重跑任何阶段。** 用户选「自动修复」时，**改用 [hap-cli-app-editor](../hap-cli-app-editor/SKILL.md) skill**，对每个失败元素**按它的真实 id 在原位精确修正**：
> - 视图有问题 → 在该视图（viewId）上 `view.update`；
> - 工作流有问题 → 在该工作流（processId）下增删/改节点、重新发布；
> - 自定义动作/页面同理，定位到具体元素 id 后原位改。

---

## 何时**不**用这个 skill

- 用户只是问「在 HAP 中看一下待办事项 / 某个应用的业务数据」—— 走 `hap-cli` 主 Skill。
- 已经有应用、只想改一两个字段——用 hap-cli-app-editor skill 或直接用 `hap` 命令，不必走完整建应用流程。
