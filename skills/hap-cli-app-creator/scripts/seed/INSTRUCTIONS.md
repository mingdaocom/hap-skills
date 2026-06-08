# 测试数据生成指令（scripts seed）

> 本文件是 **AI 生成测试数据时必须遵从的指令**。用户会在每次生成数据时明确
> 让你读它。你的产出是一份**声明式数据文件** `_seed_data.json`，由
> `python -m scripts seed <appId>` 机械地推送进真实应用。
>
> 数据由 store 落盘的真实字段元数据驱动，关联用**逻辑标签**引用，执行器解析。

## 工作流（你在第 ② 步）

```
① (机械) python -m scripts seed-template <appId>   → {PROJECT_ROOT}/apps/{appName}-{ts}/_seed_template.json
② (你)   读 _seed_template.json + 本文件 → 写 {PROJECT_ROOT}/apps/{appName}-{ts}/_seed_data.json
③ (机械) python -m scripts seed <appId>            → 逐表 batch-create，解析 @标签
```

> 这三步产生的文件（`_seed_template.json` / `_seed_data.json` / `_seed_rows.json`）
> 都落在**该应用自己的项目文件夹** `{PROJECT_ROOT}/apps/{appName}-{ts}/`（即建应用时设计文档
> 所在的目录）内，不会写到用户 home 目录。`seed-template` / `seed` 按 `<appId>` 自动定位
> 到这个文件夹，你无需关心绝对路径。

**只读这两份输入**：`{PROJECT_ROOT}/apps/{appName}-{ts}/_seed_template.json`（每表可写字段、
validOptions、relationDeps、isTitle、isSelfRelation、dataSource）和本指令文件。**不要**去翻设计文档或源码。

## 输出文件结构（`_seed_data.json`）

```jsonc
{
  "<工作表名>": [
    { "_ref": "标签", "<字段名>": <值>, ... },
    ...
  ]
}
```

- 顶层 key = 工作表逻辑名（与模板的 `worksheetName` 一致）。
- 每个元素是一条记录：key 用**字段逻辑名**（模板 `fillableFields[].name`，逐字复制）。
- **只填模板列出的可写字段**。模板没列的字段（自动编号/公式/汇总/他表/分段/条码…）**一律不要出现**。
- `_ref`：该行的**逻辑标签**，仅当被其他行的关联字段引用时才需要；同一文件内唯一。

## 关联字段（逻辑标签引用）—— 核心

模板里 `type: "Relation"` 的字段：**不要写真实 rowId**，用 `@标签` 引用目标行的 `_ref`。

```jsonc
"物料": [ { "_ref": "M1", "物料名称": "不锈钢螺丝 M4×20", ... } ],
"库存": [ { "当前数量": 3200, "物料": "@M1", "仓库": "@W1" } ]   // 单条
"出库单": [ { "出库物料": ["@M1", "@M2"] } ]                      // 多条用数组
```

- 执行器按 `relationDeps` **拓扑排序**逐表创建，先建被引用的表、抓真实 rowId 回填下游，所以你
  只管用 `@标签`、不用管顺序。
- 标签必须指向**同一份数据文件里真实存在**的 `_ref`，否则 seed 报错。
- 目标行可以为空关联（不填该字段即可）。

### 自关联（指向本表，模板标 `isSelfRelation: true`）

把"根记录"和"子记录"作为同表里的不同行：根记录**不填**自关联字段，子记录用 `@父级标签` 引用。
**支持任意层级**——执行器逐层创建（先根、再它们的子、再子的子…）。**中间层既是子又是父**：给它一个 `_ref`，自己用 `@上一级` 引父，下一级再 `@它` 引它。

```jsonc
"组织架构": [
  { "_ref": "ROOT",  "名称": "总公司" },
  { "_ref": "EAST",  "名称": "华东大区", "上级": "@ROOT" },
  { "_ref": "SH",    "名称": "上海分公司", "上级": "@EAST" },
  { "名称": "浦东办事处", "上级": "@SH" }
]
```

## 各字段类型传值格式（传"人话"，CLI 自动序列化）

| 类型(CODE) | 传值 | 规范 |
| :-- | :-- | :-- |
| Text / RichText | `string` | 真实业务内容，不要 `测试1`/`测试2`。RichText 可带简单 HTML。 |
| PhoneNumber / LandlinePhone | `string` | 真实格式号码，如 `"13800138000"`。 |
| Email | `string` | 真实格式邮箱。 |
| Number / Currency / Certificate | `number` | 纯数值，不带单位/符号。 |
| Rating | `string` | 星级数字字符串，如 `"4"`。 |
| SingleSelect / Dropdown | `string` | **单个**选项文字，**必须**来自该字段 `validOptions`，逐字匹配。 |
| MultipleSelect | `string[]` | 多个选项文字数组，每个都来自 `validOptions`。 |
| CascadingSelect | `string` | 级联选项文字（按目标表的选项值）。 |
| Checkbox | `bool` | `true` / `false`。 |
| Date / DateTime | `string` | `"YYYY-MM-DD"`。**集中在当前日期前后 3 个月内**，保证看板/图表能出本月本周数据。 |
| Time | `string` | `"HH:mm:ss"`。 |
| Region | `string` | 行政区划代码，如 `"110100"`(北京)、`"310000"`(上海)、`"440100"`(广州)。 |
| Location | `string` | JSON 字符串：`"{\"x\":116.397,\"y\":39.905,\"address\":\"...\",\"title\":\"...\"}"`。 |
| Collaborator | 虚拟用户 token 数组 | **必须**用虚拟账号，见下「成员字段」。 |
| Department / OrgRole | 直接跳过或给真实 id | 无把握就不填（这些需真实组织 id）。 |
| Attachment | `object[]` | `[{"name":"封面.png","url":"https://..."}]`，见下「附件」。执行器会自动上传换成真实 cell。 |
| Relation | `@标签` / `[@标签...]` | 见上「关联字段」。 |
| SubTable | `object[]` | 每个元素是一条子行 `{子字段名: 值}`（子字段同样只填可写的），见下「子表」。 |

## 成员字段（Collaborator）

- **必须**用 `resources/attachments.json` 里的虚拟账号 token（`virtualuser-cn-*` / `virtualuser-en-*`），
  **不要用 `@me`/当前用户**。服务端认这些虚拟账号（已 live 验证：`virtualuser-cn-1` → 赵子轩）。
- 中文环境优先用 `cn` 那组；记录之间**打散**不同的人，体现真实协作（不要每条都同一个人）。
- 单选成员传 1 个 token 的数组，多选可传多个：`["virtualuser-cn-3"]`、`["virtualuser-cn-2","virtualuser-cn-7"]`。

## 附件字段（Attachment）

值为 `[{"name":"显示名.ext","url":"直链"}]` 或 `[{"name":"显示名.ext","path":"本地文件"}]`（可多个）。
执行器会**自动取文件（远程直链下载 / 本地文件读取）→上传到文件存储→组装成真实附件 cell**
（走通用 `hap upload`，Qiniu/GetUploadToken + 七牛直传）。素材来源：
- **文档（本地，推荐）**：`resources/attachments.json` 的 `documents[]`——直接照抄其 `{name, path}`，
  `path` 用**相对文件名**（如 `sample.pdf`）即可，执行器自动解析到 `resources/` 目录。`name` 可按业务改名。
- **图片**：`resources/sample_images.json` 按分类(product/asset/location/proof/issue/marketing/avatar)挑最贴合的关键词取 `url`。
  **不要永远用同一张**，让列表/看板配图丰富。
- 没有 100% 契合的也挑一个最不违和的；附件字段尽量别全空。
- 也可用**自定义本地文件**：`[{"name":"x.pdf","path":"/绝对路径/x.pdf"}]`（绝对路径或相对当前目录）；或**远程直链**：`[{"name":"x.png","url":"https://…"}]`。

## 子表（SubTable）

模板里 `type: "SubTable"` 的字段带 `childFields`（已按白名单过滤好的子字段清单）。值是
**子行数组**，每条子行是 `{子字段名: 值}`，子字段名逐字取自该字段的 `childFields[].name`。
子行里若有关联子字段，同样用 `@标签` 引用其他表的 `_ref`。一张主单可挂多条子行（这正是
"一单多物料"的建模）。

```jsonc
"订单": [ { "_ref": "O1", "订单号": "...", "明细": [
  { "产品": "@P1", "数量": 3, "单价": 12.5 },
  { "产品": "@P2", "数量": 1, "单价": 99 }
] } ]
```

## 生成条数规则（按表的业务定位）

| 表场景 | 条数 | 判定 |
| :-- | :-- | :-- |
| 参数/配置/系统设置表 | 1 | 表名含 `设置`/`配置`/`参数`/`系统`，多为全局单值。 |
| 字典/分类/标签/基础数据表 | 3–5 | 作为关联基础的辅助表（如 物料、仓库、客户级别）。 |
| 核心业务表 | 8–12 | 业务实体（订单、入库单、任务、流水…），尽量丰富多样。 |
| 自关联层级表 | 2 根 + 5 子 | 模板含 `isSelfRelation` 字段时。 |

## 数据质量要求

- **真实场景契合**：用真实存在的名称/术语（真书名+ISBN、真岗位+部门），不要 `测试数据N`。
- **中文环境用流畅中文**。
- **偏态分布**：状态/选项/关联**不要均匀分配**。模拟真实业态（绝大多数订单"已完成"、极少"退款中"），
  让统计看板出好看的可视化。
- **选项严格匹配** `validOptions`，禁止编造不存在的选项文字。

## 提交前自检（每张表）

1. 每个字段 key 都来自模板该表的 `fillableFields[].name`，模板外字段不出现。
2. `isTitle: true` 的字段每条记录都有有业务含义的值。
3. 选项字段值都在该字段 `validOptions` 内（逐字）。
4. 关联字段用 `@标签`，且标签在本文件有对应 `_ref`；自关联根记录不填自关联字段。
5. 日期集中在当前 ±3 个月。
