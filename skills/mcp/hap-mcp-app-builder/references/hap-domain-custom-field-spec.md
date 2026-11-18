# HAP 自定义字段（Free Field）领域对象规范

本规范定义 HAP（明道云）表单自定义字段（Custom Control / Free Field）的沙箱运行环境、组件运行契约、存储类型与引用类型选型、底层数据格式映射、UI 视觉标准、防御性取值原则及标准组件代码骨架。

---

## 一、 沙箱运行环境与内置能力

自定义字段作为独立 React 函数式组件运行在表单沙箱中，具备以下全局内置能力：

- **React 全局 Hooks**：无需 `import React`，直接可用 `useState`、`useEffect`、`useRef`、`useCallback`、`useMemo` 等标准 Hooks。
- **TailwindCSS 样式支持**：沙箱全局支持 TailwindCSS 工具类（如 `className="w-[200px] h-[36px] ..."`），样式必须使用 Tailwind 工具类实现。
- **`LucideIcon` 内置图标组件**：沙箱全局内置 `lucide-react` 图标库，无需任何 `import`，直接在 JSX 中使用：
  ```jsx
  <LucideIcon name="AirVent" size={20} className="text-[#2196f3]" />
  ```
  `name` 必须是 `lucide-react` npm package 内真实存在的合法图标组件名称。
- **原生 SVG 支持**：支持直接在 JSX 中内嵌原生 `<svg>`、`<path>` 实现自定义图表、刻度尺、进度环或特殊形状。
- **零外部依赖约束**：**严禁 `import` 任何第三方 npm 库，严禁 `import React`，严禁 `export default`**。

---

## 二、 组件运行契约与 Props 签名

自定义字段以单个函数式组件形式导出，分为两大核心类型：

### 2.1 存储类型（Storage Type）Props 签名
当用户操作需要在当前字段中**持久化存值**（写入数据库、可在视图筛选、工作流可读取）时使用：
```typescript
interface StorageControlProps {
  value: any;                        // 当前字段持久化存储的值
  onChange: (newValue: any) => void; // 回写更新当前字段值的回调函数
  currentControl?: {                 // 当前字段元数据配置
    controlId: string;
    controlName: string;
    type: number;
    options?: Array<{ key: string; value: string; color?: string }>;
  };
  formData?: Record<string, {        // 整条记录中其他所有字段的实时数据上下文
    controlId: string;
    name: string;
    value: any;
    type: number;
  }>;
}
```

### 2.2 引用类型（Reference / Presentation Type）Props 签名
当仅需聚合展示多字段数据、只读渲染或动态计算、**无需在当前字段中持久化存值**时使用：
```typescript
interface ReferenceControlProps {
  formData: Record<string, {         // 仅传入整条记录的字段上下文
    controlId: string;
    name: string;
    value: any;
    type: number;
  }>;
}
```

> **注意**：引用类型组件无 `value`、无 `currentControl`、无 `onChange`，属于纯单向只读渲染。若用户提出在此类组件中存值，需明确告知该类型不支持持久化。

---

## 三、 选型决策准则（存储类型 vs 引用类型）

| 评估维度 | 存储类型（Storage Type） | 引用类型（Reference Type） |
| :--- | :--- | :--- |
| **选型判定** | 用户操作结果需持久化存入数据库（可在视图中筛选、在工作流中读取） | 仅从整条记录提取多个已有字段做聚合展示、卡片看板或只读计算，无需持久化 |
| **Props 参数** | `value`, `onChange`, `currentControl`, `formData` | **仅有 `formData`** |
| **典型场景** | 九宫格密码锁、定制打分器、自定义下拉选择器、带防抖的富文本输入 | 订单履约进度条、客户健康度评估卡片、多币种换算卡、信息汇总摘要 |
| **核心避坑** | 输入型组件必须做好**中文拼音输入合成保护（`isComposing`）** | **无法存值**，若用户提出存值需求需明确告知该类型不支持持久化 |

---

## 四、 常用字段类型与底层数据格式映射

| 字段类型 | Type ID | `value` 读取格式 | `onChange` 回写传参格式 | 示例说明 |
| :--- | :---: | :--- | :--- | :--- |
| **文本 (Text)** | `2` | 字符串 `string` | 字符串 `string` | `onChange("新文本内容")` |
| **数值 (Number)** | `6` | 数值 `number` | 数值 `number` | `onChange(100.5)` |
| **单选 (SingleSelect/Dropdown)** | `9` / `11` | 序列化字符串数组 | 序列化字符串数组 | `onChange(JSON.stringify(["opt_key_1"]))` |
| **多选 (MultipleSelect)** | `10` | 序列化字符串数组 | 序列化字符串数组 | `onChange(JSON.stringify(["opt_1", "opt_2"]))` |
| **日期时间 (DateTime)** | `15` / `16` | `"YYYY-MM-DD HH:mm:ss"` | `"YYYY-MM-DD HH:mm:ss"` | `onChange("2026-09-01 12:00:00")` |
| **时间 (Time)** | `46` | `"HH:mm:ss"` | `"HH:mm:ss"` | `onChange("14:30:00")` |
| **关联记录 (Relation)** | `29` | 记录数据对象列表 | 记录数据对象列表 | 关联引用的实体记录 |

---

## 五、 formData 读取与防御性取值准则

1. **`formData` 底层索引结构**：`Record<string, { controlId, name, value, type }>`，以字段 `controlId` 为 key。
2. **标准取值范式（必须使用可选链与兜底）**：
   ```javascript
   // 读取文本/字符串
   const textValue = formData?.[targetControlId]?.value ?? "";
   // 读取数值（转 Number 并防 NaN）
   const numValue = Number(formData?.[targetControlId]?.value) || 0;
   // 读取选项（反序列化）
   const selectedKeys = JSON.parse(formData?.[targetControlId]?.value || "[]");
   ```
3. **容错准则**：在取值层级较深或引用字段可能为空时，必须做存在性校验，杜绝因 `undefined` 访问导致整个记录表单白屏崩溃。

---

## 六、 UI 视觉与交互规范

为保证自定义字段与 HAP 原生表单风格一致，需严格遵循以下视觉标准：

1. **字号与文本颜色**：基础字号 `13px`（最大不超过 `15px`），文本主色 `#333333`，弱化提示色 `#999999`；
2. **尺寸与边框**：基础控件高度 `36px`，边框 `1px solid #eeeeee`，圆角 `4px`；
3. **主题强调色**：聚焦/激活强调色为 `#2196f3` 或当前应用主题色；
4. **布局风格**：控件内部优先采用紧凑的水平横向排布（`flex-row`），避免垂直方向过度撑高导致表单割裂。

---

## 七、 代码生成规范与头部元标签

1. **代码 Fence 标识符**：必须使用 ````mdy.free_field```` 代码块；
2. **头部元标签注释**：
   ```jsx
   ```mdy.free_field
   // <free_field_name>组件中文名称</free_field_name>
   // <file_name>FileName_v1.jsx</file_name>
   function ComponentName({ value, currentControl, formData, onChange }) {
     // 组件逻辑与 JSX
   }
   ```
   ```

---

## 八、 典型场景标准组件代码模版 (Canonical Templates)

### 8.1 场景一：中文输入与清除保护的文本输入框（存储类型）

```jsx
```mdy.free_field
// <free_field_name>文本输入框</free_field_name>
// <file_name>TextInput_v2.jsx</file_name>
function TextInput({ value, onChange }) {
  const [inputValue, setInputValue] = useState(value || "");
  const [isComposing, setIsComposing] = useState(false);

  useEffect(() => {
    setInputValue(value || "");
  }, [value]);

  const handleChange = (e) => {
    setInputValue(e.target.value);
    if (!isComposing) {
      onChange(e.target.value);
    }
  };

  const handleCompositionStart = () => {
    setIsComposing(true);
  };

  const handleCompositionEnd = (e) => {
    setIsComposing(false);
    onChange(e.target.value);
  };

  return (
    <input
      className="w-[200px] h-[36px] px-2 text-[13px] text-[#333] border rounded-[4px] border-gray-300 focus:outline-none focus:border-[#2196f3]"
      value={inputValue}
      onChange={handleChange}
      onCompositionStart={handleCompositionStart}
      onCompositionEnd={handleCompositionEnd}
      placeholder="请输入..."
    />
  );
}
```
```

### 8.2 场景二：单选下拉选择器（存储类型·选项映射与 JSON 序列化）

```jsx
```mdy.free_field
// <free_field_name>单选下拉框</free_field_name>
// <file_name>SelectDropdown_v1.jsx</file_name>
function SelectDropdown({ value, currentControl, onChange }) {
  const options = currentControl?.options || [];
  const selectedIds = JSON.parse(value || "[]");

  return (
    <div className="relative w-[200px]">
      <select
        value={selectedIds[0] || ""}
        onChange={(e) => onChange(JSON.stringify([e.target.value]))}
        className="w-full h-[36px] px-2 text-[13px] text-[#333] border rounded-[4px] border-gray-300 focus:outline-none focus:border-[#2196f3] appearance-none bg-white cursor-pointer"
      >
        <option value="" disabled>请选择</option>
        {options.map((option) => (
          <option key={option.key} value={option.key}>
            {option.value}
          </option>
        ))}
      </select>
      <div className="absolute right-2 top-1/2 -translate-y-1/2 pointer-events-none text-gray-400">
        <LucideIcon name="ChevronDown" size={16} />
      </div>
    </div>
  );
}
```
```

```jsx
```mdy.free_field
// <free_field_name>履约进度卡片</free_field_name>
// <file_name>ProgressCard_v1.jsx</file_name>
function ProgressCard({ formData }) {
  // 注意：此处 "601"、"602" 仅为示例。实际在 modify-app 中必须通过 get_worksheet_structure 获取目标表的真实字段 controlId
  const shipped = Number(formData?.["601"]?.value) || 0;
  const total = Number(formData?.["602"]?.value) || 1;
  const percent = Math.min(100, Math.round((shipped / total) * 100));

  return (
    <div className="flex items-center gap-3 p-2 border border-[#eee] rounded-[4px] bg-gray-50 h-[36px] w-full max-w-[360px]">
      <LucideIcon name="PackageCheck" size={18} className="text-[#2196f3] shrink-0" />
      <div className="flex-1 bg-gray-200 h-2 rounded-full overflow-hidden">
        <div
          className="bg-[#2196f3] h-full transition-all duration-300"
          style={{ width: `${percent}%` }}
        />
      </div>
      <span className="text-[13px] text-[#333] shrink-0 font-medium">{percent}%</span>
    </div>
  );
}
```
```

---

## 九、 MCP API 底层组装与落库契约（用于 modify-app / worksheet-revision-agent）

在已落地应用修改场景下，`worksheet-revision-agent` 需要通过 `create_worksheet` 或 `update_worksheet` 将自定义字段直接写入底层工作表。此时必须严格遵守以下 API 组装契约：

### 9.1 字段基础配置（`type: 48` 与 `enumDefault` 映射）
- **物理类型固定为 `type: 48`**（自定义控件 / Free Field）；
- **`enumDefault` 定义底层持久化存储格式**：必须与组件内部 `onChange` 传递的数据类型严格匹配：
  - 纯引用只读展示组件（无需存值）：`enumDefault: 2`（默认文本存储）；
  - 文本输入组件：`enumDefault: 2`；
  - 数值计算/打分组件：`enumDefault: 6`；
  - 单选选择组件：`enumDefault: 9`；
  - 多选选择组件：`enumDefault: 10`；
  - 日期时间组件：`enumDefault: 16`。

### 9.2 `customWidget` 结构定义
在向字段列表（`controls` 或 `editFields`）添加/更新自定义字段时，必须携带 `customWidget` 对象：
```json
{
  "type": 48,
  "controlName": "履约进度卡片",
  "alias": "biz_fulfillment_progress",
  "enumDefault": 6,
  "customWidget": {
    "height": 36,
    "script": "function ProgressCard({ formData }) { ... }",
    "reference": ["65a1234567890abcdef12345", "65a1234567890abcdef12346"]
  }
}
```
- **`height`（数值，必填）**：控件显示高度（单位 px，基础输入框/单行进度条填 `36`，复杂大卡片可设为 `60` ~ `120`）；
- **`script`（字符串，必填）**：纯 JavaScript/JSX 组件源码（必须遵守下方的无围栏铁律）；
- **`reference`（字符串数组，条件必填）**：引用的其他字段的真实 `controlId` 列表（必须遵守下方的引用声明铁律）。

### 9.3 纯源码无围栏铁律（Zero-Markdown Fence in `script`）
> [!CAUTION]
> **严禁将 ````mdy.free_field```` 或任何 Markdown 围栏写入 `customWidget.script`！**
> 明道云沙箱引擎直接对 `customWidget.script` 执行 `eval` / `Babel.transform`。如果字符串中包含 ```` ```mdy.free_field ```` 或反引号围栏，客户端执行时将直接抛出 `SyntaxError: Unexpected token '`'`，导致**整条记录的表单白屏崩溃**！
> 
> **正确做法**：写入 `customWidget.script` 的必须是剥离了 Markdown 围栏的**纯函数代码字符串**（保留开头的 `// <free_field_name>...` 注释是允许的，但绝对不能带反引号代码块）。

### 9.4 `reference` 显式声明铁律（无声明则无数据）
> [!IMPORTANT]
> 明道云沙箱为了运行时性能，**只会向组件的 `formData` 注入在 `customWidget.reference` 数组中显式声明了的字段**！
> 若组件代码中读取了 `formData?.["65a123..."]?.value`，但该字段 ID 未放入 `customWidget.reference` 数组，沙箱注入的 `formData` 中将不会包含该字段，组件读到的值永远是 `undefined`。
> 
> **正确做法**：凡是在脚本中读取的外部字段，其真实 `controlId` 必须 100% 录入 `customWidget.reference` 数组。

### 9.5 真实 ID 读取与替换准则（严禁生搬硬套假 ID）
在 `worksheet-revision-agent` 规划与执行落库时：
1. **真实探测先行**：复用当前有效字段索引，缺少时用 `get_worksheet_structure(responseFormat: "md")` 读取字段概览。核对字段名称（如“总金额”、“已支付金额”），将返回的真实字段 ID 用于写入接口要求的 `controlId`；
2. **动态替换**：将组件脚本代码中的字段 ID 替换为真实的 `controlId`，并放入 `customWidget.reference`；
3. **禁止假 ID**：严禁把规范文档中用于示例的 `"601"`、`"602"` 直接写入最终代码。
