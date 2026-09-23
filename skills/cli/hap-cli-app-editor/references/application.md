# 应用级元数据、分组与 AI 助手

## 调用范式

```bash
# 读结构：应用信息（含分组、工作表、自定义页面）/ 我管理的应用列表
hap app info -a <appId>
hap app list-managed -o <orgId>

# 改应用名 / 描述 / 配色 / PC 导航样式
hap app update <appId> -n "新名字" -d "新描述" \
  --icon-color "#2196F3" --nav-color "#1565C0" --pc-nav-style 1

# 侧边栏分组（section）
hap app add-section <appId> -n "运营"
hap app edit-section <appId> <sectionId> -n "市场"
hap app delete-section <appId> <sectionId> -y
hap app sort-sections <appId> <sectionId1> <sectionId2> <sectionId3>

# AI 助手（chatbot）
hap app chatbot create <appId> "客服助手" --section-id <sectionId> \
  --prompt "你是售后客服" --welcome-text "你好，有什么可以帮你？" \
  --preset-question "如何退货" --preset-question "查订单状态"
hap app chatbot get <chatbotId>
hap app chatbot rename <appId> <chatbotId> --section-id <sectionId> --name "售后助手"
hap app chatbot update-config <chatbotId> --welcome-text "欢迎咨询" \
  --preset-question "新问题一" --preset-question "新问题二"
hap app chatbot delete <chatbotId> -a <appId> -y

# 应用回收站：删掉的工作表 / 自定义页 / AI 助手，带删除人和时间
hap app trash -a <appId>
hap app trash -a <appId> -k 订单            # 按名称过滤

# 分组内工作表排序（按顺序传完整 ID 列表）
hap app sort-worksheets <appId> <sectionId> <wsId1> <wsId2> <wsId3>

# 操作日志：定位「这个改动是谁什么时候做的」
hap app logs <appId> --kind app --start "2026-09-01 00:00:00"
hap app logs <appId> --kind record --ip <地址> --source-id <集成ID>
hap app log-archives                      # 超出近期窗口的按时段归档
hap app logs <appId> --archived-id <归档ID>
```

坑位提示：

- **新建分组会排到侧边栏最前面**，连建多个后顺序是反的；建完用 `sort-sections` 传**完整** section id 列表一次性修正顺序。
- `app info` 返回的分组条目里 `type` 区分成员类型：0=工作表，1=自定义页面，2=子分组。按名找元素时先看这个字段。
- 改 `--pc-nav-style` 时图标显示默认随样式联动；要精确控制用 `--display-icon`（3 位开关串，如 `011`）。
- 整应用从零创建不在本 skill 范围（用 hap-mcp-app-builder）；这里只编辑已存在的应用。
- chatbot 的 `--preset-question` 可重复传，`update-config` 时是**整组替换**而非追加。
- 想让 AI 起草助手配置，先 `hap app chatbot generate <appId> "<一句话描述>"` 拿到建议的名字/图标/开场白/提示词，再喂给 `create`。
- `app logs` 不指定 `--start/--end` 时默认**最近 30 天**；更早的要先 `app log-archives` 拿归档 id
  再用 `--archived-id` 查。`--kind` 取 `all|app|record|user`。
- **备份、角色改名这类操作失败不再被当成功**：以前服务端用裸状态码表示「超限额」「重名」，CLI 照样
  报成功；现在会按状态码判定并非零退出。

### 删了之后怎么确认真的删掉了

工作表、自定义页、AI 助手的删除**默认都是进应用回收站**，不是抹掉。删完用
`hap app trash -a <appId>` 核对：能看到它，说明删成功了（还能还原）；看不到，才说明它根本没被删掉。

| 对象 | 默认 | 彻底删除 |
|---|---|---|
| 自定义页 | 进回收站 | `hap custom-page delete … --permanently` |
| AI 助手 | 进回收站 | `hap app chatbot delete … --permanent` |
| 工作表 | 进回收站 | **CLI 目前没有出口**——只能在界面上从回收站里彻底删 |

两个 `--permanent(ly)` 现在是真的彻底删（先进回收站再按回收站记录彻底删，删不掉会报错并非零退出），
所以加了它之后 `app trash` 里**看不到**才是正确结果。

## 数据字典

字典生成于 2026-06-10；未覆盖的键以读命令返回的实际结构为准。

### app update 枚举与取值

| 键/选项 | 含义 | 值形态 |
|---|---|---|
| --pc-nav-style | PC 导航样式 | int enum：0=经典，1=分组列表，2=卡片，3=树形 |
| --display-icon | 图标显示开关 | 3 位 0/1 串（如 `011`），缺省随导航样式 |
| --icon-color / --nav-color | 图标色 / 导航栏色 | 十六进制色值字符串（如 `#2196F3`） |
| -n / -d | 应用名 / 描述 | string |

### app info 返回的分组条目

| 键 | 含义 | 值形态 |
|---|---|---|
| type | 条目类型 | int enum：0=工作表，1=自定义页面，2=子分组 |
| 其余键 | 名称、id、图标等 | 以 `hap app info` 实际返回为准 |

### chatbot 配置项

| 键/选项 | 含义 | 值形态 | 适用 |
|---|---|---|---|
| --prompt | 系统提示词（定义助手行为） | string | create |
| --welcome-text | 开场白 | string | create / update-config |
| --preset-question | 预设问题（可重复，整组替换） | string ×N | create / update-config |
| --section-id | 所在导航分组 | string | create / rename / delete |
| --remark | 简介 | string | create |
| --icon / --icon-color | 图标与颜色 | string | create / rename |
| --permanent | 彻底删除；不加就进应用回收站，用 `hap app trash` 能看到也能还原 | flag | delete |
| --lang | 起草语言类型，0=默认 | int | generate |
