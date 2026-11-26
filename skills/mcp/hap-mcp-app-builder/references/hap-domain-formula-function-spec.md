# HAP 公式函数计算规范（封闭白名单）

## 一、适用范围与语法红线

- **封闭白名单铁律**：文末第五节列出的 **80 个**函数是当前 HAP 线上全部合法系统函数。**清单外任何函数一律不存在，严禁猜测、臆造或以反复保存试探支持范围。**
- **适用位置**：`FunctionFormula`（Type 53）的 `config.expression`、`dynamicDefault.function`（`type: "formula"`）、`customEvents` 中的函数赋值/条件（`type: "formula"`）。
- **不可套用位置**：`Formula` 仅支持简单数值四则运算，`Concatenate` 仅支持纯占位符与固定文本拼接，工作流 `compute` 节点仅支持 `number`（纯四则运算）、`dateDiff`、`dateOffset`，均不可使用本清单函数。
- **基础语法**：函数名**全大写**，英文半角括号 `()` 与逗号 `,`；引用本表字段用 `$字段ID或alias$`（不支持跨表路径，跨表值须先经 `storeData: true` 的 `Lookup` 或 `Rollup` 落在本表）；相等用 `==`、不等用 `!=`；文本常量用单引号或双引号包裹；**公式表达式中无“当前时间”系统字段占位符，获取当前时间必须调用 `DATENOW()`**。

## 二、高危差异陷阱（同名/近名异义与必填参坑）

以下 9 项与 Excel / SQL 习惯差异极大，写错会直接报错或静默算错：

| 函数 | 常见误区 | HAP 真实行为与正确写法 |
| :--- | :--- | :--- |
| `FIND` / `FINDA` | 当作 Excel 查子串位置（返回数字） | **按起止标记正则截取中间子串**：`FIND(text, startMark, endMark)` 返回首个匹配文本（省略 `startMark` 从头截，省略 `endMark` 截到尾）；`FINDA(text, startMark, endMark)` 返回全部匹配数组（两标记均必填） |
| `DATEIF` | 当作 Excel `DATEDIF(s, e, "d")` 返回数字，或按中文单位截取 | 4 参 `DATEIF(start, end, format=1, unit="d")`：`format=1` 纯日期按 `00:00`，`2` 结束日按 `24:00` 含当天；`unit` 仅支持 `'Y'`/`'y'`/`'M'`/`'d'`/`'h'`/`'m'`；**返回随界面语言本地化的带单位文本（如中文 `"6天"`、英文 `"6day"`）**，不可直接参与数值比较或加减，也**严禁按中文单位截取转数字**（英文等非中文环境会匹配失败静默算出 `0`）。需纯数值差参与计算或比较时，必须改用不依赖语言的受支持机制（如 `DateFormula` 日期公式字段，或工作日计数使用返回纯数字的 `NETWORKDAY`） |
| `DATEADD` | 当作 SQL `DATEADD(day, 7, date)` | 3 参 `DATEADD(date, offsetExpr, format=1)`：第 2 参是带符号和单位的字符串（`'Y'`/`'M'`/`'d'`/`'h'`/`'m'`，如 `'+7d'`、`'-1M'`；动态值用 `CONCAT('+', $biz_days$, 'd')`）；第 3 参 `1` 输出 `YYYY-MM-DD`，`2` 输出 `YYYY-MM-DD HH:mm:ss` |
| `CEILING` / `FLOOR` | 传单参 `CEILING(x)` / `FLOOR(x)` | **第 2 参基数 `sig` 必填**，单参直接抛错；取整到整数必须显式写 `CEILING($x$, 1)` / `FLOOR($x$, 1)` |
| `LOG` | 传单参 `LOG(x)` 默认底数 10 | **第 2 参底数 `base` 必填**，单参返回 `NaN`；常用对数须写 `LOG($x$, 10)` |
| `WEEKDAY` | 按 Excel 默认周日=1 或传第 2 参 | 仅 1 参 `WEEKDAY(date)`，固定返回 `1`（周一）~ `7`（周日） |
| `CLEAN` | 当作 Excel 删除不可打印字符 | HAP 中为**删除全部半角空格**；仅去首尾空白用 `TRIM(text)` |
| `INCLUDE` | 期望空入参严格返回 `false` | `INCLUDE(text, sub)` 任一为空时返回空/假值，条件判断建议先配合 `ISBLANK` |
| `IF` / `IFS` | 用外层 `IF(cond, fallback, 危险表达式)` 或 `IFS(...)` 做短路保护或替代 `IFERROR` | `IF` / `IFS` 均为普通函数调用，**所有分支参数都会及早求值（无短路保护）**，无法阻止未命中分支抛错（如 `IF(OR(ISBLANK($d$), $d$ == 0), 99, MOD($n$, $d$))` 在 `$d$` 为 `0` 时仍触发 `MOD` 除数为 0 异常导致公式返回空）。必须先在危险运算的实际参数内消除非法输入（如 `IF(OR(ISBLANK($d$), $d$ == 0), 99, MOD($n$, IF(OR(ISBLANK($d$), $d$ == 0), 1, $d$)))`），或改用其他受支持机制 |

## 三、高频错名替换与不支持函数速查

### 1. 可直接替换为 HAP 原生函数

| 常见错写 / 标准名 | HAP 合法写法 | 说明 |
| :--- | :--- | :--- |
| `NOW()` | `DATENOW()` | 0 参，返回 `YYYY-MM-DD HH:mm:ss` |
| `ISEMPTY(x)` | `ISBLANK(x)` | 1 参判空（`undefined` / `null` / `""` / `[]`） |
| `LEN(x)` / `LENGTH(x)` | `COUNTCHAR(x)` | 1 参求字符数（不含 `\r\n` 换行符） |
| `CONCATENATE(...)` | `CONCAT(...)` | 可变参数文本拼接 |
| `AVG(...)` | `AVERAGE(...)` | 数值求平均 |
| `VALUE(x)` | `NUMBER(x)` | 文本转数值（最多保留 14 位小数） |
| `CONTAINS(s, sub)` / `INCLUDES(s, sub)` | `INCLUDE(s, sub)` | 判断是否包含子串 |
| `CEIL(x)` | `CEILING(x, 1)` | 向上取整（第 2 参必填） |
| `NETWORKDAYS(...)` | `NETWORKDAY(...)` | 区间工作日数 |
| `REVERSE(x)` | `STRREVERSE(x)` | 字符串反转 |
| `WORKDAY.INTL(...)` | `WORKDAY_INTL(...)` | 下划线 `_` 而非点号 `.` |
| `NORM.S.DIST(...)` | `NORM_S_DIST(...)` | 下划线 `_` 而非点号 `.` |

### 2. 明确不支持的高频函数及合法替代

| 不支持的函数 | 合法替代写法或说明 |
| :--- | :--- |
| `TODAY()` | 用 `LEFT(DATENOW(), 10)` 取 `YYYY-MM-DD` |
| `IFERROR(expr, fallback)` | 无异常捕获函数；且 `IF`/`IFS` 会对所有分支及早求值，外包 `IF` 不能保护会抛错的分支。须在危险运算参数内部消除非法输入（如 `MOD($n$, IF(OR(ISBLANK($d$), $d$ == 0), 1, $d$))`）后再由外层 `IF` 输出兜底值，或改用其他受支持机制 |
| `COALESCE(a, b)` / `IFNULL(a, b)` | `IF(ISBLANK(a), b, a)` |
| `SWITCH(x, k1, v1, ...)` | `IFS(x == k1, v1, x == k2, v2, TRUE(), defaultVal)` |
| `TEXTJOIN(sep, ...)` | `CONCAT(...)` 或 `JOIN(arr, sep)` |
| `SQRT(x)` | `POWER(x, 0.5)` |
| `DATEDIF` / `DATEDIFF` | 纯数字日期差使用不依赖语言的受支持机制（如 `DateFormula` 日期公式字段，或工作日计数用 `NETWORKDAY`）；`DATEIF` 返回随界面语言本地化的带单位文本，不可按中文单位截取转数字 |
| `TEXT(val, fmt)` | 无格式化模板函数（`STRING(x)` 仅 1 参基础转文本） |
| `SUBSTR` / `SUBSTRING` | 改用 1-based 的 `MID(str, start, len)` |
| `COUNT(...)` | 非空参数计数用 `COUNTA(...)`；数组/多选/子表项数用 `COUNTARRAY(...)` |
| `SEARCH(...)` | 无查子串位置函数（**切勿误用 `FIND`**） |
| `SECOND(t)` | 无提取秒数函数，勿编造 |

## 四、HAP 特有与常用扩展函数用法

- **`IFS(cond1, val1, cond2, val2, ...)`**：顺序匹配首个真条件并返回对应值，兜底分支放末尾 `TRUE(), defaultVal`，无匹配返回空。
- **`COUNTARRAY(arr)`**：返回数组/多选/子表元素个数（空返回 `0`）。
- **`STRING(val)`**：1 参基础转文本（数组以 `,` 拼接，不支持格式模板）。
- **`REPLACE(text, start=1, count=0, newText="")` vs `SUBSTITUTE(text, old, new, [nth])`**：`REPLACE` 按 1-based 位置与长度替换；`SUBSTITUTE` 按文本内容替换（省略 `nth` 全量替换，传正整数 `nth` 只替第 `n` 次）。
- **`SPLIT(text, sep="")` / `JOIN(arr, sep="")`**：按分隔符拆分字符串为数组 / 用分隔符连接数组为文本。
- **`WEEKNUM(date, returnType=1)`**：返回年中第几周（`1`=周日起始，`2`/`11`/`21`=周一起始）。
- **`NETWORKDAY(start, end, holidays=[], workdays=[1,2,3,4,5])`**：按闭区间（含起止日）计算工作日数，节假日列表用数组传入（如 `['2026-05-01']`）。
- **`WORKDAY(start, days, holidays=[])` / `WORKDAY_INTL(start, days, weekend=1, holidays=[])`**：推算若干工作日后的日期。
- **`DISTANCE(loc1, loc2)` / `GETPOSITION(loc, prop)`**：定位距离计算（支持定位对象或 `"lng,lat"`，返回单位为**千米**，需米数时 `* 1000`）与属性提取（`prop` 如 `"x"`、`"y"`、`"x,y"`、`"title"`、`"address"`）。

## 五、全部 80 个合法系统函数封闭白名单

- **数学函数（35）**：`SUM(...n)`、`AVERAGE(...n)`、`MIN(...n)`、`MAX(...n)`、`PRODUCT(...n)`、`COUNTA(...v)`、`COUNTBLANK(...v)`、`COUNTARRAY(arr)`、`COUNTCHAR(str)`、`ABS(n)`、`INT(n)`、`MOD(n, d)`、`ROUND(n, digits=0)`、`ROUNDUP(n, digits=0)`、`ROUNDDOWN(n, digits=0)`、`CEILING(n, sig)`、`FLOOR(n, sig)`、`POWER(n, p)`、`LOG(n, base)`、`RANDBETWEEN(min, max)`、`NUMBER(v)`、`PI()`、`RADIANS(deg)`、`DEGREES(rad)`、`SIN(rad)`、`COS(rad)`、`TAN(rad)`、`COT(rad)`、`ASIN(n)`、`ACOS(n)`、`ATAN(n)`、`ACOT(n)`、`NORM_S_DIST(z, cumulative=true)`、`PERMUT(n, k)`、`COMBIN(n, k)`
- **日期时间函数（13）**：`DATENOW()`、`DATEADD(date, offset, fmt=1)`、`DATEIF(start, end, fmt=1, unit="d")`、`YEAR(d)`、`MONTH(d)`、`DAY(d)`、`HOUR(t)`、`MINUTE(t)`、`WEEKDAY(d)`、`WEEKNUM(d, type=1)`、`NETWORKDAY(start, end, holidays=[], workdays=[1,2,3,4,5])`、`WORKDAY(start, days, holidays=[])`、`WORKDAY_INTL(start, days, weekend=1, holidays=[])`
- **文本函数（17）**：`CONCAT(...v)`、`STRING(v)`、`LEFT(str, n=1)`、`RIGHT(str, n=1)`、`MID(str, start=1, len=0)`、`REPLACE(str, start=1, len=0, newStr="")`、`SUBSTITUTE(str, old, new, [nth])`、`REPT(str, n)`、`UPPER(str)`、`LOWER(str)`、`TRIM(str)`、`CLEAN(str)`、`STRREVERSE(str)`、`FIND(str, startMark, endMark)`、`FINDA(str, startMark, endMark)`、`SPLIT(str, sep="")`、`JOIN(arr, sep="")`
- **逻辑函数（9）**：`IF(cond, thenVal, elseVal)`、`IFS(c1, v1, ...)`、`AND(...expr)`、`OR(...expr)`、`NOT(expr)`、`ISBLANK(v)`、`INCLUDE(str, sub)`、`TRUE()`、`FALSE()`
- **高级函数（6）**：`ENCODEURI(str)`、`DECODEURI(str)`、`ENCODEURICOMPONENT(str)`、`DECODEURICOMPONENT(str)`、`DISTANCE(loc1, loc2)`、`GETPOSITION(loc, prop)`
