# Seed Data — 高仿真示例数据（三段式）

建完表只是空应用。要让视图/看板/统计有内容，给应用填示例数据。**三段式，第 ② 段是你（AI）的活**：

```bash
# ① (机械) 读真实控件元数据，产出填值模板
hap app-creator seed-template <appId>
# ② (你)   读 _seed_template.json + 本文件 → 写一份 _seed_data.json
# ③ (机械) 拓扑排序逐表写入，解析 @标签，回填真实 rowId
hap app-creator seed <appId> <_seed_data.json>
```

**只读两份输入**：`_seed_template.json`（每表的可写字段 `fillableFields`、`validOptions`、`relationDeps`、`isTitle`、`isSelfRelation`、`dataSource`）和本文件。
不要去翻 design 或源码——以模板的真实控件元数据为准。

> 运行时 `hap app-creator seed-template` 也会打印一份与本文件内容一致的填值说明的路径。

## 输出文件结构（`_seed_data.json`）

```jsonc
{
  "<工作表名>": [
    { "_ref":"标签", "<字段名>": <值>, ... },
    ...
  ]
}
```
- 顶层 key = 工作表逻辑名（与模板 `worksheetName` 一致）；每个元素是一条记录，key 用**字段逻辑名**（逐字复制模板 `fillableFields[].name`）。
- **只填模板列出的可写字段**。自动编号/公式/汇总/他表/分段/条码等模板不列，**一律不要出现**。
- `_ref`：该行的逻辑标签，仅当被别的行的关联字段引用时才需要；同一文件内唯一。

## 关联字段（逻辑标签引用）——核心

模板里 `type:"Relation"` 的字段：**不要写真实 rowId**，用 `@标签` 引用目标行的 `_ref`。
```jsonc
"物料":  [ { "_ref":"M1", "物料名称":"不锈钢螺丝 M4×20" } ],
"库存":  [ { "当前数量":3200, "物料":"@M1", "仓库":"@W1" } ],     // 单条
"出库单":[ { "出库物料":["@M1","@M2"] } ]                         // 多条用数组
```
执行器按 `relationDeps` 拓扑排序逐表建、抓真实 rowId 回填下游——你只管用 `@标签`、不管顺序。
标签必须指向**同文件内真实存在**的 `_ref`。

**自关联**（模板标 `isSelfRelation:true`）：根记录不填自关联字段，子记录用 `@父级标签` 引用；**支持任意层级**（中间层给自己 `_ref`、用 `@上一级` 引父），执行器逐层创建。

## 各类型传值（传「人话」，CLI 自动序列化）

| 类型 | 传值 | 规范 |
| :-- | :-- | :-- |
| Text / RichText | string | 真实业务内容，不要「测试1」。RichText 可带简单 HTML。 |
| PhoneNumber / Email | string | 真实格式。 |
| Number / Currency | number | 纯数值，不带单位/符号。 |
| Rating | string | 星级数字字符串，如 `"4"`。 |
| SingleSelect / Dropdown | string | **单个**选项文字，**必须**来自该字段 `validOptions`，逐字匹配。 |
| MultipleSelect | string[] | 多个选项文字，每个都在 `validOptions` 内。 |
| Checkbox | bool | true/false。 |
| Date / DateTime | string | `"YYYY-MM-DD"`，**集中在当前日期 ±3 个月内**（保证看板出本月/本周数据）。 |
| Time | string | `"HH:mm:ss"`。 |
| Region | string | 行政区划代码，如 `"110100"`(北京)/`"310000"`(上海)/`"440100"`(广州)。 |
| Location | string | JSON 串 `"{\"x\":116.397,\"y\":39.905,\"address\":\"...\",\"title\":\"...\"}"`。 |
| Collaborator | 虚拟账号 token 数组 | 见下「成员字段」。 |
| Attachment | object[] | `[{"name":"封面.png","url":"https://..."}]`，执行器自动上传换真实 cell。 |
| Relation | `@标签` / `[@标签...]` | 见上。 |
| SubTable | object[] | 每个元素是一条子行 `{子字段名:值}`（子字段同样只填可写的）。 |

## 成员字段（Collaborator）

**必须**用虚拟账号 token（`virtualuser-cn-*` / `virtualuser-en-*`，编号从 1 起递增），
**不要 `@me`/当前用户**。服务端认这些虚拟账号（已 live 验证：`virtualuser-cn-1` → 真实姓名）。
中文环境用 `cn` 那组；记录之间**打散**不同的人。单选成员传 1 个 token 的数组，多选可多个：`["virtualuser-cn-3"]`、`["virtualuser-cn-2","virtualuser-cn-7"]`。

## 附件字段（Attachment）

值为 `[{"name":"显示名.ext","url":"直链"}]`（可多个）。`hap app-creator seed` 会自动下载→上传→组装真实附件 cell。
素材直链可用任意可公开访问的文档/图片直链（图片按 product/asset/location/proof/issue/marketing/avatar 等场景挑选）。
**别永远用同一张**；附件字段尽量别全空。也支持本地文件 `[{"name":"x.pdf","path":"/abs/path/x.pdf"}]`。

## 子表（SubTable）

模板里 SubTable 字段带 `childFields`（已白名单过滤）。值是子行数组，每条 `{子字段名:值}`，子字段名逐字取 `childFields[].name`；
子行里的关联子字段同样用 `@标签`。一张主单可挂多条子行（这正是「一单多明细」）。
```jsonc
"订单":[ { "_ref":"O1","订单号":"...","明细":[
  { "产品":"@P1","数量":3,"单价":12.5 }, { "产品":"@P2","数量":1,"单价":99 } ] } ]
```

## 生成条数（按表的业务定位）

| 场景 | 条数 | 判定 |
| :-- | :-- | :-- |
| 参数/配置/系统设置表 | 1 | 表名含 设置/配置/参数/系统。 |
| 字典/分类/基础数据表 | 3–5 | 作关联基础的辅助表（物料、仓库、客户级别）。 |
| 核心业务表 | 8–12 | 业务实体（订单、入库单、任务、流水…）。 |
| 自关联层级表 | 2 根 + 5 子 | 模板含 isSelfRelation 字段时。 |

## 数据质量

- **真实场景契合**：真书名+ISBN、真岗位+部门，不要「测试数据N」。中文环境用流畅中文。
- **偏态分布**：状态/选项/关联**不要均匀**（绝大多数订单「已完成」、极少「退款中」），让看板可视化好看。
- **选项严格匹配** `validOptions`，禁止编造不存在的选项文字。

## 提交前自检（每张表）

1. 每个字段 key 都来自模板该表 `fillableFields[].name`，模板外字段不出现。
2. `isTitle:true` 的字段每条都有有业务含义的值。
3. 选项字段值都在 `validOptions` 内（逐字）。
4. 关联用 `@标签` 且标签在本文件有对应 `_ref`；自关联根记录不填自关联字段。
5. 日期集中在当前 ±3 个月。
