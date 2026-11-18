# Progress 状态机与原子子任务生命周期 (PROGRESS)

本文档定义 HAP App Builder 的**全局阶段状态机 (Global Stage FSM)** 与 **原子子任务生命周期状态**。

---

## 一、 全局阶段状态机 (`hap-context.json.progress`)

所有阶段推进均由 `scripts/build_runtime.py advance` 在 `finalize` 生成的 `.build/phase-report.json` 放行（`canAdvance: true`）后独占原子写入。

`progress` 记录已完整验收的全局阶段进度。除后台异步任务 `Step 5`（示例数据）与主链路并行重叠外，其余阶段严格按门禁顺序完成校验后再原子推进；局部失败任务的回执与已完成产物均予以保留，修复续作规则见 [Build 调度流程](../workflows/build.md)，严禁手工涂改进度或将未完成任务伪造为成功。

阶段验收只检查该阶段负责的对象配置及其证据：无规划的可选对象不生成任务；角色成员为空或未指定、后台示例数据缺失及尚未进行跨阶段业务试跑，应记录限制，不能据此否定已核实的角色、页面或其他对象配置。核心配置、安全权限与真实 ID 仍须落实，不以独立步骤尚未执行来虚称端到端业务已可用。

| 状态值 | 含义 | 前置状态 | 阶段包含任务 |
|---|---|---|---|
| _(空/不存在)_ | 初始状态 | — | `build_runtime.py init` |
| `app_created` | 应用、导航分组、页面空壳与使用手册已就绪 | _(空)_ | Step 1 + Step 1b（主调度器内联完成） |
| `step2a_done` | 基础工作表已创建，待回填跨表关联 | `app_created` | Step 2a（存在 `relationLayout` 时进入） |
| `worksheets_created` | 所有工作表及跨表关联/子表均已落定 | `app_created` / `step2a_done` | Step 2b 完成（或无跨表关联直接由 Step 2a 跃迁） |
| `fields_refreshed` | 字段分片强校验合并完成，动作/视图/规则/助手空壳已就绪 | `worksheets_created` | Step 3（单表全要素）+ Step 4a（AI 助手创建） |
| `config_completed` | 导航内联排序及助手节点、页面、角色并发完成（`Step 5` 后台灌数非阻塞并行） | `fields_refreshed` | Step 7（内联）+ Step 4b + Step 6 + Step 8（`Step 5` 后台不阻塞推进） |
| `completed` | 阻塞型步骤均有成功回执，工作流逐项发布状态见交付报告 | `config_completed` | Step 10 + Step 11（无工作流时直接放行，Step 5 后台继续） |
| `failed` / `blocked` | 历史异常标记，恢复时核对具体未完成任务 | _(任意)_ | 局部技术错误记入任务回执，不因此将全局置为终止 |

---

## 二、 原子子任务状态与推进铁律

1. **子任务生命周期**：`planned` ➔ `ready` ➔ `dispatching` ➔ `running`（容量满则暂置 `pending_capacity`，不计入失败次数，空槽即时补位）➔ `succeeded`（临时错误先由当前执行器排查续作；执行器中断时核对已完成结果后进入 `retry_pending` 恢复或重新派发，确实无法完成的任务记为 `failed`）。
2. **单向原子推进**：`progress` 严禁手工涂改或跳步，一律以 `.build/receipts/` 下的真实校验回执为准。
3. **轻重职责严明**：Step 1、Step 1b、Step 7 轻量全局动作由主调度器内联完成；Step 2a ～ Step 6、Step 8、Step 10 ～ Step 11 重资产任务必须由独立 Subagent 执行，子任务可由原 Subagent 自主修复后继续；需要重新派发时，仍使用独立 Subagent 并从已核实的完成状态续作。

`finalize` 分别列出 `plannedTaskIds`（待派发，含已重置）、`pendingCapacityTaskIds`（等待槽位）和 `runningTaskIds`（运行中）。前两类应在有空槽时重新 `prepare`。报告的 `deliveryNotes` 汇集本次运行各阶段最新回执中的问题、未完成页面和未确认发布的流程。旧工作流回执仅有流程 ID 时，发布状态为 `unknown`，需回读线上发布版本才能向用户报告已上线。
