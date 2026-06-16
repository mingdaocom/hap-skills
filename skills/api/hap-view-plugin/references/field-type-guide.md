# HAP 视图插件开发 - 字段类型处理经验总结

## 🎯 核心发现

在开发明道云 HAP 自定义视图插件时,发现了一个**非常重要的字段类型映射问题**:

### ⚠️ 关键问题:单选字段的 type 是 9,不是 11!

**官方文档可能存在误导:**
- 文档中可能暗示单选是 type 11
- 但实际上 **type 9 = 单选 (SingleSelect)**
- type 10 = 多选 (MultipleSelect)
- type 11 = 下拉 (Dropdown)

## 📋 完整字段类型对照表

| Type | 字段类型 | 说明 |
|------|---------|------|
| 2 | 文本框 | Text |
| 3 | 手机 | PhoneNumber |
| 4 | 座机 | LandlinePhone |
| 5 | 邮箱 | Email |
| 6 | 数值 | Number |
| 7 | 证件 | Certificate |
| 8 | 金额 | Currency |
| **9** | **单选** | **SingleSelect** ⚠️ |
| 10 | 多选 | MultipleSelect |
| 11 | 下拉 | Dropdown |
| 14 | 附件 | Attachment |
| 15 | 日期 | Date |
| 16 | 时间 | DateTime |
| 19/23/24 | 地区 | Region |
| 26 | 成员 | Collaborator |
| 27 | 部门 | Department |
| 28 | 等级 | Rating |
| 29 | 连接他表 | Relation |
| 36 | 检查框 | Checkbox |
| 40 | 定位 | Location |
| 41 | 富文本 | RichText |
| 42 | 签名 | Signature |
| 46 | 时间 | Time |
| 48 | 组织角色 | OrgRole |

## 🔧 实际应用场景

### 场景:按行业分组显示客户

**问题现象:**
- 代码查找行业字段时返回 `undefined`
- 所有客户都被归入"未分类"
- 控制台显示 `行业字段: undefined`

**错误代码:**
```javascript
// ❌ 只查找 type 10 和 11,遗漏了 type 9
const industryField = controls?.find(ctrl =>
  ctrl.controlName?.includes('行业') && (ctrl.type === 10 || ctrl.type === 11)
);
```

**正确代码:**
```javascript
// ✅ 包含 type 9, 10, 11 所有选项字段
const industryField = controls?.find(ctrl =>
  ctrl.controlName?.includes('行业') && (ctrl.type === 9 || ctrl.type === 10 || ctrl.type === 11)
);
```

## 💡 选项字段值解析

### 数据格式

选项字段返回的原始值格式:
```javascript
// 原始值(JSON字符串)
"[\"42ad38bf-d3e6-441f-a960-670e704abe4a\"]"

// 解析后
["42ad38bf-d3e6-441f-a960-670e704abe4a"]

// 这是选项的 key,需要从 options 中查找对应的 value
```

### 完整解析函数

```javascript
// 解析单选字段
function parseSingleSelect(value, control) {
  try {
    if (!value) return { key: "", text: "" };

    // 解析选项key值 - 支持多种格式
    let keys = [];
    if (typeof value === 'string') {
      try {
        keys = JSON.parse(value);
      } catch {
        keys = [value];
      }
    } else if (Array.isArray(value)) {
      keys = value;
    } else {
      keys = [value];
    }

    const selectedKey = keys[0] || "";

    // 从控件选项中查找对应的文本值
    let selectedText = "";
    if (control && control.options) {
      const option = control.options.find(opt => opt.key === selectedKey);
      selectedText = option ? option.value : selectedKey; // 找不到时返回key
    } else {
      selectedText = selectedKey;
    }

    return { key: selectedKey, text: selectedText };
  } catch (err) {
    console.error("解析单选字段失败:", err, value);
    return { key: "", text: "" };
  }
}

// 字段类型映射
function getFieldTypeByControlType(controlType) {
  const typeMap = {
    2: 'text',           // 文本框
    3: 'phone',          // 手机
    4: 'phone',          // 座机
    5: 'email',          // 邮箱
    6: 'number',         // 数值
    7: 'certificate',    // 证件
    8: 'number',         // 金额
    9: 'select',         // 单选 ⚠️ 重要
    10: 'multiselect',   // 多选
    11: 'select',        // 下拉
    14: 'attachment',    // 附件
    15: 'date',          // 日期
    16: 'datetime',      // 时间
    19: 'region',        // 地区
    23: 'region',        // 地区
    24: 'region',        // 地区
    26: 'user',          // 成员
    27: 'department',    // 部门
    28: 'rating',        // 等级
    29: 'relation',      // 连接他表
    36: 'boolean',       // 检查框
    40: 'location',      // 定位
    41: 'richtext',      // 富文本
    42: 'signature',     // 签名
    46: 'time',          // 时间
    48: 'role',          // 组织角色
  };

  return typeMap[controlType] || 'unknown';
}

// 通用字段值获取函数
function getFieldValue(fieldId, record, controls) {
  if (!fieldId || !record) return null;
  const rawValue = record[fieldId];
  if (rawValue === undefined || rawValue === null) return null;

  // 获取字段控件定义
  const control = controls?.find(ctrl => ctrl.controlId === fieldId);
  if (!control) return rawValue;

  // 根据控件类型进行处理
  const fieldType = getFieldTypeByControlType(control.type);

  switch (fieldType) {
    case 'text':
    case 'email':
    case 'phone':
      return rawValue;

    case 'number':
      return parseFloat(rawValue) || 0;

    case 'select':
      return parseSingleSelect(rawValue, control);

    case 'multiselect':
      return parseMultiSelect(rawValue, control);

    case 'boolean':
      return rawValue === "1" || rawValue === 1 || rawValue === true;

    default:
      return rawValue;
  }
}
```

## 🐛 调试技巧

### 1. 打印所有字段信息

```javascript
useEffect(() => {
  console.log('=== 所有字段详细信息 ===');
  controls?.forEach((ctrl, index) => {
    console.log(`字段${index}:`, {
      id: ctrl.controlId,
      name: ctrl.controlName,
      type: ctrl.type,
      hasOptions: !!ctrl.options,
      optionsCount: ctrl.options?.length || 0
    });
    if (ctrl.options && ctrl.options.length > 0) {
      console.log(`  选项:`, ctrl.options);
    }
  });
  console.log('=== 字段信息结束 ===');
}, [controls]);
```

### 2. 打印字段解析过程

```javascript
// 获取原始值
const rawValue = record[fieldId];
console.log('原始值:', rawValue);

// 解析值
const parsedValue = getFieldValue(fieldId, record, controls);
console.log('解析值:', parsedValue);

// 最终显示值
const displayValue = parsedValue?.text || parsedValue;
console.log('显示值:', displayValue);
```

## ✅ 最佳实践

1. **总是包含 type 9 查找选项字段**
   ```javascript
   // 查找所有选项字段
   (ctrl.type === 9 || ctrl.type === 10 || ctrl.type === 11)
   ```

2. **从 config.controls 获取字段定义**
   ```javascript
   const control = config.controls.find(ctrl => ctrl.controlId === fieldId);
   ```

3. **使用 options 匹配显示文本**
   ```javascript
   const option = control.options.find(opt => opt.key === selectedKey);
   const displayText = option ? option.value : selectedKey;
   ```

4. **容错处理**
   ```javascript
   // 找不到时返回 key 而不是空字符串
   selectedText = option ? option.value : selectedKey;
   ```

## 📚 相关资源

- HAP 视图插件开发文档
- 明道云 API V3 文档
- 字段类型完整列表

## 🎓 经验教训

1. **不要完全依赖文档** - 实际的字段类型编号可能与文档不一致
2. **使用调试日志** - 打印所有字段信息有助于发现问题
3. **完整的类型映射** - 建立完整的 type 到字段类型的映射表
4. **容错处理** - 总是考虑找不到选项的情况

---

**更新时间:** 2026-01-01
**适用版本:** 明道云 API V3
**开发环境:** mdye-cli beta-0.0.37
