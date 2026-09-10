# 统计图（chart）— 改一张已有的图

统计图挂在**一张工作表**上，命令都在 `hap worksheet chart` 下。图表规格本身（`xaxes` /
`yaxisList` / `filter` / reportType 取值表）以 **`hap guide chart`** 为准，它是随 CLI 版本走的；
本篇只讲「改已有的图」在 app-editor 场景下必须知道的几条。

```bash
hap worksheet chart list <worksheetId>                # 个人图 + 共享图，全都列
hap worksheet chart list <worksheetId> --owner-only   # 只看自己的个人图
hap --json worksheet chart get <reportId> --app-id <worksheetId>
hap worksheet chart update <reportId> --app-id <worksheetId> --name "新名字" --report-type 1 \
  -j '{"yaxisList":[{"controlId":"<金额字段>","controlType":6,"normType":4}]}'
hap worksheet chart delete <reportId> ...
```

## 四条容易搞错的

1. **`--app-id` 要的是工作表 ID，不是应用 ID。** HAP 的图表规格里 `appId` 指的就是工作表。
   真正的应用 ID 只在 `--owner-app-id` 上，且只有规格里带 `filter.items` 时才需要。
2. **`update` 只传要改的项。** 它先把这张图当前配置读出来再把你写的盖上去，所以没提到的维度、
   数值、排序、样式、时间范围都原样保留。`--app-id`、`--name`、`--report-type` 三项**每次都要带**。
3. **默认时间筛选只在新建时注入。** 一张图没有 `filter` 块也能保存成功，但渲染时没有东西给查询
   定范围，页面就显示「无法形成图表 / 构成要素不存在或已删除」——编辑界面正常，一保存就空白。
   `chart create` 会自动补一个「全部时间」的默认范围；**`chart update` 不补**（否则会覆盖这张图
   原本设好的时间范围）。所以改图时不要把 `filter` 整块删掉。
4. **`chart list` 不加选项就是全部**（个人的和共享的都列），`--owner-only` 才是只看自己的。
   `-k/--keyword` 是**在本次取回的结果里按名称过滤**，不是让服务端去搜；配合 `--page-size` 用时
   它只在这一页里筛。图挂在聚合表上时加 `--app-type 2`。

大改结构时仍然推荐读-改-写：`chart get` 导出 → 编辑 → `chart update -f chart.json`。
`get` 返回的 `controls` / `account` / `createdDate` 等多余字段可以原样带回，服务端会忽略。

把图摆到自定义页上（组件形状、48 栅格、version 语义）见 [custom-pages.md](custom-pages.md)。
