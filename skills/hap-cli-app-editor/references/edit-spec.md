# edit-spec 总览

一个 edit-spec 是一个 JSON 文件，描述对**一个已存在应用**的一组局部修改。

## 信封

```json
{
  "app": "<appId 或 应用名>",
  "org": "<组织 id，可选；默认当前会话组织>",
  "ops": [ { "type": "...", "...": "..." } ]
}
```

- `app`：优先用真实 appId；也可用应用名（命令会在当前组织里解析）。
- `ops`：按声明顺序执行。同一 spec 内后面的 op 可引用前面 op 刚创建的元素。

## op 通用字段

| 字段 | 说明 |
|---|---|
| `type` | 必填，`<元素>.<动作>`，决定用哪份模块 schema 校验与哪个执行器。 |
| `confirm` | 破坏性 op（删除/覆盖）必填且必须为 `true`，否则拒绝执行。 |
| `label` | 可选，plan/apply 输出里显示的人类标签。 |

## 引用元素的方式

元素一律用**逻辑名**（工作表名、字段名、视图名…）或**真实 id** 引用——两者都行（editor 场景 ID 不敏感，可先建后改）。命令每步执行前从 HAP 实时读取结构来解析。

## op 总表（按阶段交付）

| type | 作用 | 阶段 |
|---|---|---|
| `worksheet.create` | 新建工作表 | ✅ |
| `worksheet.update` | 改工作表名/别名/描述/图标 | ✅ |
| `worksheet.delete` | 删除工作表（需 confirm） | ✅ |
| `view.create` | 新建视图 | ✅ |
| `view.update` | 局部更新视图属性（editAttrs） | ✅ |
| `view.delete` | 删除视图（需 confirm） | ✅ |
| `field.add` | 新增字段（增量，保留反向控件） | ✅ |
| `field.update` | 改字段（读全量→改→整表写回） | ✅ |
| `field.delete` | 删字段（读全量→去掉→整表写回，需 confirm） | ✅ |
| `field.reorder` | 重排字段（整表写回） | ✅ |
| `role.{create,update,delete,add_member,remove_member}` | 角色与成员，见 roles.md | ✅ |
| `custom-action.{create,update,delete}` | 记录按钮，见 custom-actions.md | ✅ |
| `chatbot.{create,update,delete}` | AI 助手，见 application.md | ✅ |
| `custom-page.{create,update,delete}` | 自定义页面，见 custom-pages.md | ✅ |
| `component.{add,update,delete}` | 页面组件，见 custom-pages.md | ✅ |
| `workflow.{create,update,delete,publish}` | 工作流进程级，见 workflows.md | ✅ |
| `node.{add,update,rename,delete}` | 工作流节点（追加/原位改配置/改名/删，后端自动重连），见 workflows.md | ✅ |
| `app.update` / `section.{add,update,delete}` | 应用级元数据与分组，见 application.md | ✅ |
| workflow 分支内中间插入/复杂拓扑 | — | 不在范围（creator/录 payload，见 workflows.md） |

> 详见各元素 reference 与 `scripts/editspec/<元素>.schema.json`。新增元素类型 = 新增一份独立 schema 文件 + envelope 的 `type` enum 加一项（schema 按模块拆分，禁止合并成单一大文件）。

## 命令

```bash
hap app-editor validate <edit-spec.json>                 # 本地校验，零网络
hap app-editor plan     <edit-spec.json> [--app <id>]    # dry-run 预演
hap app-editor apply    <edit-spec.json> [--app <id>] [--continue]  # 执行
hap app-editor inspect  <appId|名称> [--org-id <org>]    # 打印实时 名→id 结构
```

## 示例

```json
{
  "app": "myAppId",
  "ops": [
    { "type": "worksheet.create", "name": "订单", "section": "默认" },
    { "type": "view.create", "worksheet": "订单", "name": "按状态", "view_type": "board" },
    { "type": "view.update", "worksheet": "订单", "view": "按状态", "name": "看板", "edit_attrs": ["name"] },
    { "type": "view.delete", "worksheet": "订单", "view": "看板", "confirm": true }
  ]
}
```
