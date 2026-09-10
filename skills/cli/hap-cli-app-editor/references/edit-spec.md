# edit-spec 总览

一个 edit-spec 是一个 JSON 文件，描述对**一个已存在应用**的一组「读改写」式局部修改。它只覆盖三类编辑——**字段、页面组件、动作按钮**——因为这三类的安全写法是「读出整体 → 改一处 → 整体写回」，由 `hap app-editor` 替你完成。其它元素（工作表、视图、角色、工作流、节点、应用与分组）直接用对应的 `hap` 命令，见各模块文档。

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
| `type` | 必填，`<元素>.<动作>`，决定用哪份模块 schema 校验。 |
| `confirm` | 破坏性 op（`field.delete` / `component.delete`）必填且必须为 `true`，否则拒绝执行。 |
| `label` | 可选，plan/apply 输出里显示的人类标签。 |

## 引用元素的方式

元素一律用**逻辑名**（工作表名、字段名、组件名…）或**真实 id** 引用——两者都行。命令每步执行前从
HAP 实时读取结构来解析。

**二级分组里的工作表现在也解析得到。** 应用的分组树会被整棵拍平（子分组一并纳入），所以
`"worksheet": "<放在子分组里的表名>"` 不会再答「worksheet not found」，`inspect` 也会把它列出来。

- 工作表：`"worksheet"` 可以写表名，也可以写 **worksheetId**——名字在两个分组里重名时用 id 最稳。
- 分组：除了名字和 id，还可以写**路径** `"组/子组"` 来区分同名分组。

## op 总表

| type | 作用 | 详见 |
|---|---|---|
| `field.add` | 新增字段（增量，保留反向控件） | [worksheets-and-fields.md](worksheets-and-fields.md) |
| `field.update` | 改字段（读全量 → 改目标 → 整表写回） | 同上 |
| `field.delete` | 删字段（整表写回，需 confirm） | 同上 |
| `field.reorder` | 重排字段（整表写回） | 同上 |
| `component.add` | 页面加组件（页面布局读改写） | [custom-pages.md](custom-pages.md) |
| `component.update` | 改页面组件 | 同上 |
| `component.delete` | 删页面组件（需 confirm） | 同上 |
| `custom-action.create` | 新建动作按钮（高层 action_spec 翻译） | [custom-actions.md](custom-actions.md) |
| `custom-action.update` | 原地改动作按钮 | 同上 |

写了不在表里的 `type`（比如 `view.update`、`node.add`），`validate` 会直接报错并给出应该改用的 `hap` 命令。

> op 的字段级 schema 在 `scripts/editspec/`（envelope + field + component + custom-action 各一份）。

## 命令

```bash
hap app-editor validate <edit-spec.json>                 # 本地校验，零网络
hap app-editor plan     <edit-spec.json> [--app <id>]    # dry-run 预演
hap app-editor apply    <edit-spec.json> [--app <id>] [--continue]  # 执行
hap app-editor inspect  <appId|名称> [--org-id <org>]    # 打印实时 名→id 结构
```

`inspect` 返回 `app_id` / `org_id` / `name` / `sections` / `worksheets` / `pages_and_chatbots` /
`roles` / `workflows`；每张工作表带着它所属的 `section`，**含二级分组里的表**。

`--app` 覆盖 spec 里写的目标应用；`--continue` 让某个 op 失败后继续跑剩下的（默认停）。

## 这个引擎继承哪些修复

`app-editor` 直接调用 CLI 的核心层，**不经过命令层**。所以命令层的行为（选项翻译、参数推导、
确认提示）与它无关：命令行上加的新选项，不会自动出现在 edit-spec 里。反过来，核心层的写入规则
（整表写回保反向控件、选项值校验、按钮填写模式推导）它都拿得到。

一处例外要记住：`custom-action.create` / `custom-action.update` 里**给 `config` 是原始逃生口，
不经适配器**——填写模式推导、门控、二次确认一概不生效。详见
[custom-actions.md](custom-actions.md) 末节。

## 示例

```json
{
  "app": "myAppId",
  "ops": [
    { "type": "field.add", "worksheet": "订单",
      "field": { "name": "优先级", "type": "SingleSelect", "options": ["高", "中", "低"] } },
    { "type": "field.update", "worksheet": "订单", "field": "金额",
      "set": { "required": true } },
    { "type": "field.delete", "worksheet": "订单", "field": "废弃备注", "confirm": true },
    { "type": "component.add", "page": "首页",
      "component": { "name": "公告", "type": "richText", "value": "<p>本周盘点</p>" } }
  ]
}
```
