# 自定义页面与页面组件

## 调用范式

```bash
# 页面生命周期（第一个参数都是应用 id）
hap custom-page create <appId> "数据看板" --section-id <sectionId> --icon chart
hap custom-page rename <appId> <pageId> --section-id <sectionId> --name "新名字"
hap custom-page copy   <appId> <pageId> --section-id <sectionId> -n "看板副本"
hap custom-page delete <appId> <pageId> --section-id <sectionId> -y

# 读页面布局 —— 注意：这里的参数填【页面 id】，不是应用 id
hap custom-page info <pageId>

# 组件类型对照表
hap custom-page component-types

# 改页面描述/设置（参数也是页面 id）
hap custom-page update-config <pageId> --desc "运营周报看板"
```

**组件增删改推荐走 edit-spec**（`hap app-editor apply`）：页面布局是整体读改写——读全量组件列表、改目标、整页写回；edit-spec 的 `component.add/update/delete` 帮你处理这套流程并按名字定位组件，其余组件原样保留。一次性示例：

```json
{
  "app": "<appId 或应用名>",
  "ops": [
    { "type": "component.add", "page": "数据看板",
      "component": { "name": "公告", "type": "richText", "value": "<p>欢迎</p>",
                     "layout": { "x": 0, "y": 0, "w": 48, "h": 5 } } },
    { "type": "component.add", "page": "数据看板",
      "component": { "name": "官网", "type": "embedUrl", "value": "https://example.com" } },
    { "type": "component.update", "page": "数据看板", "component": "公告",
      "set": { "value": "<p>已更新</p>" } },
    { "type": "component.delete", "page": "数据看板", "component": "官网", "confirm": true }
  ]
}
```

```bash
hap app-editor apply page-edit.json
```

低层备选是 `hap custom-page save`，但它**要求传完整 components 数组**——漏掉的组件会被删除：

```bash
# 先 info 拿 version 和现有 components，改完整体写回
hap custom-page save <pageId> --version <N> --components '[ ...全量组件... ]'
```

坑位提示：

- `info` / `save` / `update-config` 的位置参数是**页面 id**；`create` / `rename` / `copy` / `delete` 的第一个参数才是应用 id。混填会读到空或报错。
- `save` 必须带 `info` 返回的 `version`；`components` 是整页布局的全量替换，不是增量。
- filter 组件（type=6）可以内联高层 `filtersGroup`（含 `filters[]`），保存时会先落成存储对象再替换为 id；这条路径需要 `--owner-app-id <appId>`（缺省时会尝试自动解析）。
- 组件的显示名存在 `web.title`，读回的组件**没有顶层 name**——按名字找组件要看 `web.title`。
- richText 的 `value` 是 HTML 字符串；embedUrl / image 的 `value` 是 URL。数据绑定型组件（chart 要 reportId、view 要 worksheetId/viewId、filter 要 filtersGroup）用 `raw:{<wire 键>}` 直接给 wire 对象（最后合并、优先生效）。

## 数据字典

字典生成于 2026-06-10；未覆盖的键以读命令返回的实际结构为准。

### 组件类型（type 可写名字或整数）

| 名字 | 数值 type | 含义 | 默认尺寸 (w×h) |
|---|---|---|---|
| analysis / chart | 1 | 统计图表 | 24×10 |
| richText | 2 | 富文本 | 48×5 |
| embedUrl | 3 | 嵌入网址 | 24×12 |
| button | 4 | 按钮 | 24×6 |
| view | 5 | 视图 | 48×12 |
| filter | 6 | 筛选器 | 24×3 |
| image | 8 | 图片 | 24×12 |
| carousel | 9 | 轮播 | 24×8（通用默认） |
| tabs | 10 | 标签页容器 | 24×8（通用默认） |
| card | 11 | 卡片容器 | 24×8（通用默认） |

### 组件通用键（wire 形态，info 返回 / save 提交）

| 键 | 含义 | 值形态 |
|---|---|---|
| type | 组件类型 | int（见上表） |
| value | 组件值（richText=HTML，embedUrl/image=URL，chart=reportId，filter=filtersGroupId） | string |
| web | PC 端展示块 | `{title, titleVisible, visible, layout}` |
| web.title | **组件显示名**（按名定位组件以此为准） | string |
| web.layout | 48 列栅格位置 | `{x, y, w, h, minW, minH}` |
| mobile | 移动端展示块 | 同 web 结构；layout 可为 null |
| filtersGroup | （filter 组件）内联高层筛选定义，保存时换成 id | `{filters: → [FilterCondition[]](../scripts/types/filter-condition.schema.json)}` |

### edit-spec 组件简洁形态（component.add 的 component）

| 键 | 含义 | 值形态 |
|---|---|---|
| name | 组件名（写入 web.title） | string |
| type | 组件类型 | 名字或整数（见上表） |
| value | 组件值 | string（按类型语义） |
| layout | 栅格位置，缺省按类型给默认尺寸 | `{x, y, w, h}` 一层对象 |
| raw | wire 键逃生口，最后合并覆盖 | object（按 wire 通用键） |

### 页面级选项速查

| 键/选项 | 含义 | 值形态 | 适用 |
|---|---|---|---|
| --section-id | 页面所在导航分组 | string | create/rename/copy/delete 必填 |
| --icon | 图标名 | string | create/rename |
| --remark | 描述 | string | create |
| --create-type | 创建类型，1=外链页面 | int | create |
| --url-template | 外链地址模板 | string | create/rename |
| --permanently | 彻底删除（默认进回收站） | flag | delete |
| --version | 布局版本号（info 可得） | int | save 必填 |
| --adjust-screen | 适配屏幕 | flag 对 | save/update-config |
| --url-params | URL 参数描述符 | JSON array | save/update-config |
| --config | 页面设置 | JSON object | save/update-config |
