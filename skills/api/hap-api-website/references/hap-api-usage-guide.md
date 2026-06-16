# HAP V3 API 使用规范完整指南

> 本文档总结了HAP V3 API的核心使用规范、最佳实践和常见陷阱,基于实际测试验证

## 📚 如何获取最新的 API V3 文档

在开始使用 HAP API V3 之前,建议先通过以下方式获取最新的 API 文档:

### 方式一: 使用应用 API MCP 服务器 (推荐)

通过 MCP 服务器直接访问最新的 API V3 文档结构。当你看到以下 JSON 代表是 官方API文档的 MCP配置


**配置方法**:

```json
{
  "mcpServers": {
    "应用 API - API 文档": {
      "command": "npx",
      "args": [
        "-y",
        "apifox-mcp-server@latest",
        "--site-id=5442569"
      ]
    }
  }
}
```

**💡 关于其他 MCP 配置**: 如需配置 HAP 应用 MCP (用于操作 HAP 数据),请参考 HAP MCP 使用指南。

---

### 方式二: 访问在线文档

如果无法通过 MCP访问到应用 API文档,可以通过以下在线地址直接访问 API V3 文档:

**概述文档**:
- [API 整体介绍](https://apifox.mingdao.com/7271706m0.md)
- [字段类型对照表](https://apifox.mingdao.com/7271709m0.md)
- [筛选器使用指南](https://apifox.mingdao.com/7271713m0.md)
- [错误码说明](https://apifox.mingdao.com/7271715m0.md)

**API 端点文档**: 完整的 API 端点列表见文档后面的"在线文档资源"章节。

---

## 在线文档资源

优先使用 MCP 服务器访问最新的 API 文档结构。如果 MCP 不可用,可以通过以下官方在线文档获取。

### 应用 API V3 文档

#### 概述文档
- [V3-beta (AI 友好) 概述](https://apifox.mingdao.com/7271706m0.md) - API 整体介绍和使用说明
- [V3-beta (AI 友好) 字段类型对照表](https://apifox.mingdao.com/7271709m0.md) - 完整的字段类型说明
- [V3-beta (AI 友好) 筛选器使用指南](https://apifox.mingdao.com/7271713m0.md) - Filter 对象详细说明
- [V3-beta (AI 友好) 错误码](https://apifox.mingdao.com/7271715m0.md) - API 错误码说明

#### 应用 API 端点文档
- **应用**: [获取应用信息](https://apifox.mingdao.com/339496583e0.md)
- **工作表**:
  - [获取工作表列表](https://apifox.mingdao.com/359328827e0.md)
  - [获取工作表结构信息](https://apifox.mingdao.com/339496584e0.md)
  - [编辑工作表](https://apifox.mingdao.com/339496585e0.md)
  - [删除工作表](https://apifox.mingdao.com/339496586e0.md)
  - [新建工作表](https://apifox.mingdao.com/339496587e0.md)
- **工作表行记录**:
  - [获取行记录列表](https://apifox.mingdao.com/339496588e0.md)
  - [获取行记录详情](https://apifox.mingdao.com/339496589e0.md)
  - [新建行记录](https://apifox.mingdao.com/339496593e0.md)
  - [更新行记录](https://apifox.mingdao.com/339496590e0.md)
  - [删除行记录](https://apifox.mingdao.com/339496591e0.md)
  - [批量新增行记录](https://apifox.mingdao.com/339496594e0.md)
  - [批量更新行记录](https://apifox.mingdao.com/339496595e0.md)
  - [批量删除行记录](https://apifox.mingdao.com/339496596e0.md)
  - [获取关联记录](https://apifox.mingdao.com/339496592e0.md)
  - [获取行记录透视数据](https://apifox.mingdao.com/339496597e0.md)
  - [获取记录分享链接](https://apifox.mingdao.com/339496598e0.md)
  - [获取行记录日志](https://apifox.mingdao.com/339496599e0.md)
  - [获取行记录讨论](https://apifox.mingdao.com/339496600e0.md)
- **选项集**:
  - [获取选项集列表](https://apifox.mingdao.com/339496601e0.md)
  - [创建选项集](https://apifox.mingdao.com/339496602e0.md)
  - [编辑选项集](https://apifox.mingdao.com/339496603e0.md)
  - [停用选项集](https://apifox.mingdao.com/339496604e0.md)
- **工作流**:
  - [获取流程列表](https://apifox.mingdao.com/339496605e0.md)
  - [获取流程详情](https://apifox.mingdao.com/339496606e0.md)
  - [触发流程](https://apifox.mingdao.com/339496607e0.md)
- **角色**:
  - [获取角色列表](https://apifox.mingdao.com/339496608e0.md)
  - [创建角色](https://apifox.mingdao.com/339496609e0.md)
  - [获取角色详情](https://apifox.mingdao.com/339496610e0.md)
  - [删除角色](https://apifox.mingdao.com/339496611e0.md)
  - [添加角色成员](https://apifox.mingdao.com/339496612e0.md)
  - [移除角色成员](https://apifox.mingdao.com/339496613e0.md)
  - [成员退出所有角色](https://apifox.mingdao.com/339496614e0.md)
- **公共查询**:
  - [查找成员](https://apifox.mingdao.com/339496615e0.md)
  - [查找部门](https://apifox.mingdao.com/339496616e0.md)
  - [获取地区信息](https://apifox.mingdao.com/339496617e0.md)

### 使用建议

1. **优先使用 MCP**: 通过配置好的 MCP 服务器可以直接在 Claude Code 中访问最新的 API 结构,无需手动查阅文档
2. **在线文档作为补充**: 当需要详细说明或示例时,可以访问上述在线文档
3. **关注字段类型**: 字段类型对照表和筛选器使用指南是最常用的参考文档
4. **错误排查**: 遇到 API 调用问题时,先查看错误码文档

---

## 目录

0. [快速开始 - API 使用流程](#零快速开始---api-使用流程)
1. [创建工作表规范](#一创建工作表规范)
2. [字段类型参数详解](#二字段类型参数详解)
3. [创建/更新记录规范](#三创建更新记录规范)
4. [查询筛选规范](#四查询筛选规范)
5. [数据透视分析规范](#五数据透视分析规范)
6. [关联字段完整指南](#六关联字段完整指南)
7. [常见陷阱与解决方案](#七常见陷阱与解决方案)

---

## 零、快速开始 - API 使用流程

### 0.1 HAP V3 API 整体架构

```
明道云组织
  └── 应用 (Application)
       ├── 角色 (Role)
       ├── 工作流 (Workflow)
       ├── 工作表分组 (Section)
       └── 工作表 (Worksheet)
            ├── 字段 (Field/Control)
            ├── 视图 (View)
            └── 记录 (Row/Record)
```

---

### 0.2 从零搭建应用的完整流程

#### **阶段一: 准备工作**

**Step 1: 获取 API 凭证**

1. 登录明道云管理后台
2. 进入「API 管理」
3. 获取以下信息:
   - **AppKey**: 应用标识
   - **Sign**: 签名密钥
   - **应用 ID (app_id)**: 目标应用的ID

**Step 2: 配置 API 请求头**

所有 HAP V3 API 请求都需要以下请求头:

```javascript
const headers = {
  'Content-Type': 'application/json',
  'AppKey': 'your-app-key',
  'Sign': 'your-sign-key'
};
```

---

#### **阶段二: 创建应用结构**

**Step 3: 获取应用信息(可选)**

查看应用现有结构:

```bash
GET /v3/app/info
```

返回应用的分组、工作表、自定义页面等信息。

---

**Step 4: 创建工作表**

```javascript
// 示例: 创建客户信息表
POST /v3/app/worksheets
{
  "name": "客户信息表",
  "alias": "customers",
  "fields": [
    {
      "name": "客户名称",
      "alias": "customer_name",
      "type": "Text",
      "isTitle": true,
      "required": true
    },
    {
      "name": "客户类型",
      "alias": "customer_type",
      "type": "SingleSelect",
      "options": [
        {"value": "潜在客户", "index": 1},
        {"value": "意向客户", "index": 2},
        {"value": "成交客户", "index": 3}
      ]
    },
    {
      "name": "年度预算",
      "alias": "annual_budget",
      "type": "Number",
      "precision": 2
    }
  ]
}

// 返回: { "worksheet_id": "你的worksheetID" }
```

**关键点**:
- ✅ 一次性定义所有基础字段
- ✅ 使用 `alias` 便于后续引用
- ✅ 至少要有一个字段设置 `isTitle: true`

---

**Step 5: 添加关联字段(如需要)**

如果需要关联其他工作表:

```javascript
// 先创建目标表(如上一步)
// 然后创建关联字段

POST /v3/app/worksheets/{worksheet_id}
{
  "addFields": [
    {
      "name": "关联客户",
      "alias": "related_customer",
      "type": "Relation",
      "subType": "1",  // 单条关联
      "dataSource": "你的worksheetID",  // 客户表ID
      "relation": {
        "bidirectional": false,
        "showFields": ["customer_name", "customer_type"]
      }
    }
  ]
}
```

---

#### **阶段三: 填充数据**

**Step 6: 准备选项字段映射**

对于单选/多选字段,需要先获取选项的 key:

```javascript
// 方法1: 查询工作表结构
GET /v3/app/worksheets/{worksheet_id}

// 从返回的 fields 中找到 options:
{
  "fields": [
    {
      "id": "customer_type",
      "type": "SingleSelect",
      "options": [
        {"key": "74c7b607-864d-4cc4-b401-28acba2636e9", "value": "成交客户"},
        {"key": "f488d4db-5046-4b10-978f-7869c4c70a71", "value": "意向客户"}
      ]
    }
  ]
}

// 建立映射表
const optionMap = {
  "成交客户": "74c7b607-864d-4cc4-b401-28acba2636e9",
  "意向客户": "f488d4db-5046-4b10-978f-7869c4c70a71"
};
```

---

**Step 7: 创建记录**

```javascript
POST /v3/app/worksheets/{worksheet_id}/rows
{
  "fields": [
    {
      "id": "customer_name",
      "value": "明道云科技有限公司"
    },
    {
      "id": "customer_type",
      "value": ["74c7b607-864d-4cc4-b401-28acba2636e9"]  // 使用选项key
    },
    {
      "id": "annual_budget",
      "value": 1000000.50
    }
  ],
  "triggerWorkflow": true  // 是否触发工作流
}

// 返回: { "row_id": "c74a29f0-f694-4501-9ba0-936e259daa9d" }
```

**关键点**:
- ⚠️ 选项字段必须用 key,不能用显示文本
- ⚠️ 选项字段即使单选也要用数组格式
- ✅ 数值字段写入时传数字,读取时返回字符串

---

**Step 8: 批量创建记录(可选)**

```javascript
POST /v3/app/worksheets/{worksheet_id}/rows/batch
{
  "rows": [
    {
      "fields": [
        {"id": "customer_name", "value": "客户A"},
        {"id": "customer_type", "value": ["key1"]}
      ]
    },
    {
      "fields": [
        {"id": "customer_name", "value": "客户B"},
        {"id": "customer_type", "value": ["key2"]}
      ]
    }
  ],
  "triggerWorkflow": true
}
```

**建议**: 一次批量创建不超过 100 条记录

---

#### **阶段四: 查询和分析数据**

**Step 9: 查询记录列表**

```javascript
POST /v3/app/worksheets/{worksheet_id}/rows/list
{
  "filter": {
    "type": "group",
    "logic": "AND",
    "children": [
      {
        "type": "condition",
        "field": "customer_type",
        "operator": "eq",
        "value": ["74c7b607-864d-4cc4-b401-28acba2636e9"]  // 成交客户
      },
      {
        "type": "condition",
        "field": "annual_budget",
        "operator": "gte",
        "value": ["500000"]  // 预算>=50万
      }
    ]
  },
  "sorts": [
    {
      "field": "annual_budget",
      "isAsc": false  // 降序
    }
  ],
  "pageIndex": 1,
  "pageSize": 20
}
```

---

**Step 10: 数据透视分析**

```javascript
POST /v3/app/worksheets/{worksheet_id}/rows/pivot
{
  "rows": [
    {
      "field": "customer_type",
      "displayName": "客户类型"
    }
  ],
  "values": [
    {
      "field": "rowid",
      "aggregation": "COUNT",
      "displayName": "客户数量"
    },
    {
      "field": "annual_budget",
      "aggregation": "SUM",
      "displayName": "预算总额"
    }
  ],
  "includeSummary": true
}
```

---

#### **阶段五: 更新和维护数据**

**Step 11: 更新记录**

```javascript
POST /v3/app/worksheets/{worksheet_id}/rows/{row_id}
{
  "fields": [
    {
      "id": "customer_type",
      "value": ["new-option-key"]  // 更改客户类型
    },
    {
      "id": "annual_budget",
      "value": 1500000  // 更新预算
    }
  ],
  "triggerWorkflow": true
}
```

---

**Step 12: 删除记录**

```javascript
// 单条删除
DELETE /v3/app/worksheets/{worksheet_id}/rows/{row_id}
{
  "permanent": false,  // false=逻辑删除(可恢复), true=永久删除
  "triggerWorkflow": true
}

// 批量删除
DELETE /v3/app/worksheets/{worksheet_id}/rows/batch
{
  "rowIds": ["row-id-1", "row-id-2"],
  "permanent": false,
  "triggerWorkflow": true
}
```

⚠️ **警告**: `permanent: true` 会永久删除数据,无法恢复!

---

### 0.3 API 调用最佳实践

#### **初始化阶段的建议步骤**

```javascript
// 1. 获取应用结构
const appInfo = await getAppInfo();

// 2. 获取所有工作表结构
const worksheets = {};
for (const ws of appInfo.worksheets) {
  worksheets[ws.alias] = await getWorksheetStructure(ws.worksheet_id);
}

// 3. 建立选项字段映射
const optionMaps = {};
for (const [alias, structure] of Object.entries(worksheets)) {
  optionMaps[alias] = {};
  structure.fields.forEach(field => {
    if (field.type === 'SingleSelect' || field.type === 'MultipleSelect') {
      optionMaps[alias][field.alias] = {};
      field.options.forEach(opt => {
        optionMaps[alias][field.alias][opt.value] = opt.key;
      });
    }
  });
}

// 4. 缓存字段ID映射
const fieldMaps = {};
for (const [alias, structure] of Object.entries(worksheets)) {
  fieldMaps[alias] = {};
  structure.fields.forEach(field => {
    fieldMaps[alias][field.alias] = field.id;
  });
}
```

---

#### **运行时的建议**

1. **使用字段ID而不是别名**: 性能更好
2. **缓存选项映射**: 避免重复查询
3. **合理使用分页**: pageSize 建议 100-500
4. **批量操作分批**: 每批不超过 100 条
5. **异步处理附件**: 上传后等待 5-10 秒

---

### 0.4 常见场景快速参考

| 场景 | API 端点 | 关键参数 |
|-----|---------|---------|
| 创建工作表 | `POST /v3/app/worksheets` | fields |
| 添加字段 | `POST /v3/app/worksheets/{id}` | addFields |
| 创建记录 | `POST /v3/app/worksheets/{id}/rows` | fields |
| 批量创建 | `POST /v3/app/worksheets/{id}/rows/batch` | rows |
| 查询记录 | `POST /v3/app/worksheets/{id}/rows/list` | filter, sorts |
| 更新记录 | `POST /v3/app/worksheets/{id}/rows/{row_id}` | fields |
| 批量更新 | `PUT /v3/app/worksheets/{id}/rows/batch` | rowIds, fields |
| 删除记录 | `DELETE /v3/app/worksheets/{id}/rows/{row_id}` | permanent |
| 批量删除 | `DELETE /v3/app/worksheets/{id}/rows/batch` | rowIds, permanent |
| 透视分析 | `POST /v3/app/worksheets/{id}/rows/pivot` | rows, values |
| 查找用户 | `POST /v3/users/lookup` | name |
| 查找部门 | `POST /v3/departments/lookup` | name |

---

### 0.5 关键概念速查

**字段类型 (type)**:
- 基础: `Text`, `Number`, `Date`, `Time`
- 选择: `SingleSelect`, `MultipleSelect`
- 关系: `Relation`, `Collaborator`, `Department`
- 其他: `Attachment`, `Rating`

**筛选操作符 (operator)**:
- 比较: `eq`, `ne`, `gt`, `gte`, `lt`, `lte`
- 文本: `contains`, `startswith`, `endswith`
- 范围: `between`, `in`
- 关联字段(Relation): `in` 或 `eq`（value = 关联记录 rowid 字符串数组）
- 部门字段(Department): `belongsto` / `notbelongsto`（value = 部门 ID 数组）
- 空值: `isempty`, `isnotempty`

**subType 参数**:
- Collaborator: `0`=单选, `1`=多选
- Relation: `1`=单条, `2`=多条
- Time: `1`=时:分, `6`=时:分:秒
- Date: `3`=年月日, `6`=年月日时分秒

---

## 一、创建工作表规范

### 1.1 基础工作表创建

**API**: `POST /v3/app/worksheets`

**基本结构**:
```json
{
  "name": "工作表名称",
  "alias": "worksheet_alias",  // 可选,建议使用英文别名
  "sectionId": "group-id",     // 可选,指定分组
  "fields": [
    // 字段定义数组
  ]
}
```

**示例 - 创建客户信息表**:
```json
{
  "name": "客户信息表",
  "alias": "customers",
  "fields": [
    {
      "name": "客户名称",
      "alias": "customer_name",
      "type": "Text",
      "isTitle": true,      // 标题字段
      "required": true      // 必填
    },
    {
      "name": "客户评级",
      "alias": "rating",
      "type": "Rating",
      "max": 5,             // 最大等级0-10
      "required": false
    }
  ]
}
```

---

### 1.2 特殊字段类型处理

#### 1.2.1 单选/多选字段 (SingleSelect/MultipleSelect)

**创建时必须提供选项**:

```json
{
  "name": "客户类型",
  "alias": "customer_type",
  "type": "SingleSelect",
  "options": [
    {"value": "潜在客户", "index": 1},
    {"value": "意向客户", "index": 2},
    {"value": "成交客户", "index": 3}
  ],
  "required": false
}
```

**关键点**:
- ✅ 必须提供 `options` 数组
- ✅ 每个选项需要 `value` (显示文本) 和 `index` (排序)
- ⚠️ 系统会自动为每个选项生成唯一的 `key` (UUID)
- ⚠️ 后续查询/更新时必须使用 `key`,不能用 `value`

---

#### 1.2.2 关联字段 (Relation) ⭐重点

**关联字段配置项**:

| 参数 | 类型 | 必填 | 说明 |
|-----|------|------|------|
| `type` | string | ✅ | 必须为 "Relation" |
| `dataSource` | string | ✅ | 关联的目标工作表ID |
| `subType` | string | ✅ | "1"=单条记录, "2"=多条记录 |
| `relation` | object | ❌ | 关联配置详情 |
| `relation.bidirectional` | boolean | ❌ | 是否双向关联 |
| `relation.showFields` | array | ❌ | 关联卡片显示的字段ID列表 |

**示例 - 创建单条关联字段**:
```json
{
  "name": "关联客户",
  "alias": "related_customer",
  "type": "Relation",
  "subType": "1",                          // 单条记录
  "dataSource": "你的worksheetID", // 目标表ID
  "relation": {
    "bidirectional": false,                // 单向关联
    "showFields": [                        // 显示字段
      "customer_name",
      "customer_type"
    ]
  },
  "required": false
}
```

**示例 - 创建多条关联字段**:
```json
{
  "name": "关联项目",
  "alias": "related_projects",
  "type": "Relation",
  "subType": "2",                          // 多条记录
  "dataSource": "你的worksheetID2",
  "relation": {
    "bidirectional": true,                 // 双向关联
    "showFields": ["project_name", "project_status"]
  },
  "required": false
}
```

**⚠️ 关联字段重要注意事项**:

1. **dataSource不可修改**: 一旦创建,关联的目标表不能更改,只能删除重建
2. **必须先创建目标表**: `dataSource` 的工作表ID必须已存在
3. **双向关联自动创建**: `bidirectional: true` 会在目标表自动创建反向关联字段
4. **showFields可为空**: 不提供时使用目标表的标题字段
5. **建议使用字段ID**: `showFields` 使用字段ID比别名更稳定

---

#### 1.2.3 成员字段 (Collaborator)

```json
{
  "name": "负责人",
  "alias": "owner",
  "type": "Collaborator",
  "subType": "0",  // 0=单选, 1=多选
  "required": false
}
```

---

#### 1.2.4 日期/时间字段 (Date/DateTime/Time)

**Date字段 - subType控制精度**:

```json
{
  "name": "成立日期",
  "alias": "founded_date",
  "type": "Date",
  "subType": "3",  // 5=年, 4=年月, 3=年月日, 2=年月日时, 1=年月日时分, 6=年月日时分秒
  "required": false
}
```

**Time字段**:
```json
{
  "name": "工作时间",
  "alias": "work_time",
  "type": "Time",
  "subType": "1",  // 1=时:分, 6=时:分:秒
  "required": false
}
```

---

#### 1.2.5 数值字段 (Number)

```json
{
  "name": "年度预算",
  "alias": "annual_budget",
  "type": "Number",
  "precision": 2,  // 小数位数 0-14
  "required": false
}
```

---

#### 1.2.6 等级字段 (Rating)

```json
{
  "name": "客户评级",
  "alias": "customer_rating",
  "type": "Rating",
  "max": 5,  // 最大等级 0-10
  "required": false
}
```

---

#### 1.2.7 附件字段 (Attachment)

```json
{
  "name": "附件",
  "alias": "attachments",
  "type": "Attachment",
  "required": false
}
```

**说明**: 附件字段创建时无需额外参数

---

### 1.3 完整创建工作表示例

**场景**: 创建销售机会表,包含关联客户

```json
{
  "name": "销售机会表",
  "alias": "opportunities",
  "fields": [
    {
      "name": "机会名称",
      "alias": "opportunity_name",
      "type": "Text",
      "isTitle": true,
      "required": true
    },
    {
      "name": "关联客户",
      "alias": "related_customer",
      "type": "Relation",
      "subType": "1",
      "dataSource": "你的worksheetID",  // 客户表ID
      "relation": {
        "bidirectional": false,
        "showFields": ["customer_name", "customer_type"]
      },
      "required": true
    },
    {
      "name": "销售阶段",
      "alias": "stage",
      "type": "SingleSelect",
      "options": [
        {"value": "初次接触", "index": 1},
        {"value": "需求确认", "index": 2},
        {"value": "方案报价", "index": 3},
        {"value": "商务谈判", "index": 4},
        {"value": "赢单", "index": 5}
      ],
      "required": false
    },
    {
      "name": "预计金额",
      "alias": "expected_amount",
      "type": "Number",
      "precision": 2,
      "required": false
    },
    {
      "name": "预计成交日期",
      "alias": "close_date",
      "type": "Date",
      "subType": "3",
      "required": false
    },
    {
      "name": "成单概率",
      "alias": "win_probability",
      "type": "SingleSelect",
      "options": [
        {"value": "30%", "index": 1},
        {"value": "50%", "index": 2},
        {"value": "70%", "index": 3},
        {"value": "90%", "index": 4}
      ],
      "required": false
    }
  ]
}
```

---

## 二、字段类型参数详解

### 2.1 字段类型对照表

| 字段类型 | type值 | 必需参数 | 可选参数 | 说明 |
|---------|--------|---------|---------|------|
| 文本 | Text | name | alias, required, isTitle, isUnique, isReadOnly, isHidden, isHiddenOnCreate | 基础文本字段 |
| 数值 | Number | name | precision (0-14), alias, required | 支持小数 |
| 单选 | SingleSelect | name, options | alias, required | 必须提供选项 |
| 多选 | MultipleSelect | name, options | alias, required | 必须提供选项 |
| 日期 | Date | name | subType (5/4/3/2/1/6), alias, required | 不同精度 |
| 日期时间 | DateTime | name | subType (5/4/3/2/1/6), alias, required | 同Date,用于兼容 |
| 时间 | Time | name | subType (1/6), alias, required | 时分或时分秒 |
| 成员 | Collaborator | name | subType (0/1), alias, required | 单选或多选 |
| 部门 | Department | name | subType (0/1), alias, required | 单选或多选部门 |
| 地区 | Region | name | alias, required | 省市区选择 |
| 关联记录 | Relation | name, dataSource, subType | relation, alias, required | 必须指定目标表 |
| 附件 | Attachment | name | alias, required | 支持URL和base64 |
| 等级 | Rating | name | max (0-10), alias, required | 星级评分 |

---

### 2.2 subType参数详解

**Collaborator (成员字段)**:
- `"0"` - 单选成员
- `"1"` - 多选成员

**Relation (关联字段)**:
- `"1"` - 单条记录
- `"2"` - 多条记录

**Time (时间字段)**:
- `"1"` - 时:分 (HH:mm)
- `"6"` - 时:分:秒 (HH:mm:ss)

**Date/DateTime (日期字段)**:
- `"5"` - 年 (YYYY)
- `"4"` - 年月 (YYYY-MM)
- `"3"` - 年月日 (YYYY-MM-DD)
- `"2"` - 年月日时 (YYYY-MM-DD HH)
- `"1"` - 年月日时分 (YYYY-MM-DD HH:mm)
- `"6"` - 年月日时分秒 (YYYY-MM-DD HH:mm:ss)

---

### 2.3 字段约束参数

| 参数 | 类型 | 说明 | 适用字段 |
|-----|------|------|---------|
| `required` | boolean | 是否必填 | 所有字段 |
| `isTitle` | boolean | 是否为标题字段 | Text |
| `isUnique` | boolean | 是否唯一 | Text, Number |
| `isReadOnly` | boolean | 是否只读 | 所有字段 |
| `isHidden` | boolean | 是否隐藏 | 所有字段 |
| `isHiddenOnCreate` | boolean | 创建时隐藏 | 所有字段 |

---

## 三、创建/更新记录规范

### 3.1 创建记录 API

**API**: `POST /v3/app/worksheets/{worksheet_id}/rows`

**请求体结构**:
```json
{
  "fields": [
    {"id": "field_id_or_alias", "value": "对应值"}
  ],
  "triggerWorkflow": true  // 是否触发工作流,默认true
}
```

---

### 3.2 triggerWorkflow 参数详解 ⭐重要

`triggerWorkflow` 参数控制是否在数据操作时触发工作表相关的工作流。

**适用范围**:
- ✅ 创建记录: `POST /v3/app/worksheets/{worksheet_id}/rows`
- ✅ 批量创建: `POST /v3/app/worksheets/{worksheet_id}/rows/batch`
- ✅ 更新记录: `POST /v3/app/worksheets/{worksheet_id}/rows/{row_id}`
- ✅ 批量更新: `PUT /v3/app/worksheets/{worksheet_id}/rows/batch`
- ✅ 删除记录: `DELETE /v3/app/worksheets/{worksheet_id}/rows/{row_id}`
- ✅ 批量删除: `DELETE /v3/app/worksheets/{worksheet_id}/rows/batch`

**参数说明**:

| 参数值 | 说明 | 默认值 | 使用场景 |
|-------|------|--------|----------|
| `true` | 触发工作流 | ✅ 是 | 正常业务操作,需要执行自动化流程 |
| `false` | 不触发工作流 | ❌ 否 | 数据迁移、批量初始化、测试数据 |

**工作流触发时机**:

工作流根据触发条件配置决定是否执行:
- **新增记录时**: 触发"当记录被新增时"类型的工作流
- **更新记录时**: 触发"当记录被更新时"类型的工作流
- **删除记录时**: 触发"当记录被删除时"类型的工作流
- **字段变更时**: 触发特定字段值变化的工作流

**使用建议**:

**✅ 应该设置为 `true` 的场景**:

1. **正常业务操作**
```javascript
// 创建销售机会,触发自动分配负责人工作流
await createRecord({
  fields: [...],
  triggerWorkflow: true  // 触发工作流
});
```

2. **用户提交表单**
```javascript
// 客户提交订单,触发通知和审批流程
await createRecord({
  fields: orderData,
  triggerWorkflow: true
});
```

3. **需要自动化处理的操作**
```javascript
// 更新客户状态,触发客户跟进提醒
await updateRecord(worksheetId, rowId, {
  fields: [{id: "status", value: ["已成交"]}],
  triggerWorkflow: true  // 触发跟进工作流
});
```

**❌ 应该设置为 `false` 的场景**:

1. **数据迁移和导入**
```javascript
// 从旧系统迁移数据,不需要触发通知
await batchCreateRecords({
  rows: migratedData,
  triggerWorkflow: false  // 避免大量工作流执行
});
```

2. **批量数据初始化**
```javascript
// 初始化测试数据
await batchCreateRecords({
  rows: testData,
  triggerWorkflow: false  // 不触发工作流
});
```

3. **定时同步任务**
```javascript
// 定时从外部系统同步数据
async function syncExternalData() {
  const externalData = await fetchFromExternalSystem();

  await batchCreateRecords({
    rows: externalData,
    triggerWorkflow: false  // 避免重复触发工作流
  });
}
```

4. **测试和调试**
```javascript
// 测试数据写入逻辑
await createRecord({
  fields: testFields,
  triggerWorkflow: false  // 测试时不触发工作流
});
```

**性能影响**:

工作流执行会增加API响应时间:
- ✅ `triggerWorkflow: false` - API 响应快,通常 < 500ms
- ⚠️ `triggerWorkflow: true` - 需要等待工作流执行,可能需要 1-5 秒

**批量操作时的注意事项**:

```javascript
// ❌ 错误: 批量操作时触发大量工作流可能导致超时
await batchCreateRecords({
  rows: Array(1000).fill({...}),  // 1000条记录
  triggerWorkflow: true  // 会触发1000次工作流!
});

// ✅ 正确: 分批处理,或关闭工作流触发
// 方案1: 关闭工作流
await batchCreateRecords({
  rows: records,
  triggerWorkflow: false
});

// 方案2: 分批处理,控制并发
for (let i = 0; i < records.length; i += 50) {
  const batch = records.slice(i, i + 50);
  await batchCreateRecords({
    rows: batch,
    triggerWorkflow: true
  });
  await sleep(2000);  // 批次间延迟
}
```

**工作流触发异常处理**:

```javascript
async function createRecordWithWorkflow(fields) {
  try {
    const result = await createRecord({
      fields: fields,
      triggerWorkflow: true
    });

    // API成功不代表工作流执行成功
    // 工作流异常不会影响记录创建
    console.log('记录创建成功:', result.row_id);

    // 如需确认工作流执行结果,需查看工作流执行日志

  } catch (error) {
    console.error('记录创建失败:', error);
  }
}
```

**⚠️ 重要提示**:

1. **记录操作与工作流执行是异步的**
   - API 返回成功只表示记录操作成功
   - 工作流在后台异步执行
   - 工作流执行失败不会影响记录操作

2. **工作流触发条件**
   - 即使设置 `triggerWorkflow: true`,工作流也需要满足自身配置的触发条件
   - 例如:设置了"仅当状态=已完成"的工作流,创建草稿记录不会触发

3. **工作流执行限制**
   - 明道云对工作流执行有频率限制
   - 短时间内大量触发可能被限流
   - 批量操作时建议关闭工作流触发

4. **删除操作的工作流**
   - 逻辑删除(`permanent: false`)会触发"记录被删除"工作流
   - 物理删除(`permanent: true`)可能无法触发工作流,因为记录已彻底删除

**最佳实践**:

```javascript
// 封装记录创建函数,根据场景决定是否触发工作流
async function smartCreateRecord(fields, options = {}) {
  const {
    isMigration = false,     // 是否为数据迁移
    isBatch = false,          // 是否为批量操作
    isTest = false            // 是否为测试
  } = options;

  // 自动判断是否触发工作流
  const triggerWorkflow = !(isMigration || (isBatch && fields.length > 50) || isTest);

  return await createRecord({
    fields: fields,
    triggerWorkflow: triggerWorkflow
  });
}

// 使用示例
await smartCreateRecord(fields, { isMigration: true });  // 迁移数据,不触发
await smartCreateRecord(fields, { isBatch: true });       // 批量操作,自动判断
await smartCreateRecord(fields);                          // 正常操作,触发工作流
```

---

### 3.3 各字段类型传参示例

#### 3.3.1 文本字段 (Text)

```json
{
  "id": "customer_name",
  "value": "明道云科技有限公司"
}
```

---

#### 3.3.2 数值字段 (Number)

**写入**: 传数字类型
```json
{
  "id": "annual_budget",
  "value": 1000000.50
}
```

**读取**: 返回字符串
```json
{
  "annual_budget": "1000000.50"
}
```

⚠️ **注意**: 写入数字,读取字符串

---

#### 3.3.3 单选字段 (SingleSelect) ⭐重点

**写入**: 必须传选项key的数组
```json
{
  "id": "customer_type",
  "value": ["74c7b607-864d-4cc4-b401-28acba2636e9"]  // 选项key
}
```

**读取**: 返回包含key和value的对象数组
```json
{
  "customer_type": [
    {
      "key": "74c7b607-864d-4cc4-b401-28acba2636e9",
      "value": "成交客户"
    }
  ]
}
```

**⚠️ 关键点**:
1. 即使是单选,也要用数组 `["key"]`
2. 不能传显示文本 `["成交客户"]`,必须用key
3. 新增选项时可设置 `type` 参数

**支持的type参数**:
```json
{
  "id": "customer_type",
  "type": "2",  // 1=不允许新增选项(默认), 2=允许新增选项
  "value": ["新选项名称"]
}
```

---

#### 3.3.4 多选字段 (MultipleSelect)

**写入**: 传多个选项key的数组
```json
{
  "id": "customer_tags",
  "value": [
    "705de83e-b929-43e4-82ff-fff2f7dd6888",  // 重点客户
    "422b4e56-263f-4bfa-bc88-77c09811080e",  // VIP
    "a2ef7406-a9b1-4fc8-ba02-33aa172998d0"   // 长期合作
  ]
}
```

**读取**: 返回对象数组
```json
{
  "customer_tags": [
    {"key": "705de83e-b929-43e4-82ff-fff2f7dd6888", "value": "重点客户"},
    {"key": "422b4e56-263f-4bfa-bc88-77c09811080e", "value": "VIP"},
    {"key": "a2ef7406-a9b1-4fc8-ba02-33aa172998d0", "value": "长期合作"}
  ]
}
```

---

#### 3.3.5 日期字段 (Date)

**写入**: 传字符串格式
```json
{
  "id": "founded_date",
  "value": "2025-01-11"  // YYYY-MM-DD
}
```

**日期时间格式**:
```json
{
  "id": "created_datetime",
  "value": "2025-01-11 14:30:45"  // YYYY-MM-DD HH:mm:ss
}
```

**读取**: 返回字符串
```json
{
  "founded_date": "2025-01-11"
}
```

---

#### 3.3.6 时间字段 (Time)

```json
{
  "id": "work_time",
  "value": "14:30:45"  // HH:mm:ss 或 HH:mm
}
```

---

#### 3.3.7 等级字段 (Rating)

**写入**: 传字符串格式的数字
```json
{
  "id": "customer_rating",
  "value": "5"  // 字符串格式
}
```

**读取**: 返回字符串
```json
{
  "customer_rating": "5"
}
```

---

#### 3.3.8 成员字段 (Collaborator) ⭐重点

**写入**: 传用户ID数组
```json
{
  "id": "owner",
  "value": ["user-account-id-123"]  // 用户ID,不是用户名
}
```

**获取用户ID**: 使用查找用户API
```bash
POST /v3/users/lookup
{
  "name": "张三"  // 精确匹配姓名
}

# 返回
{
  "accountId": "user-account-id-123",
  "fullname": "张三",
  "email": "zhangsan@example.com"
}
```

**读取**: 返回用户对象或对象数组
```json
{
  "owner": {
    "accountId": "user-account-id-123",
    "fullname": "张三",
    "avatar": "https://...",
    "email": "zhangsan@example.com",
    "status": 1
  }
}
```

---

#### 3.3.9 部门字段 (Department) ⭐新增

部门字段用于选择组织架构中的部门,与成员字段类似,也支持单选和多选。

**字段创建**:
```json
{
  "name": "所属部门",
  "alias": "department",
  "type": "Department",
  "subType": "0",  // 0=单选, 1=多选
  "required": false
}
```

**单选部门写入**: 传部门ID数组
```json
{
  "id": "department",
  "value": ["department-id-123"]  // 部门ID,不是部门名称
}
```

**多选部门写入**: 传多个部门ID
```json
{
  "id": "departments",
  "value": [
    "department-id-123",
    "department-id-456"
  ]
}
```

**获取部门ID**: 使用查找部门API

**方法1: 通过名称查找**
```bash
POST /v3/departments/lookup
{
  "name": "销售部"  // 精确匹配部门名称
}

# 返回
{
  "success": true,
  "data": {
    "departmentId": "department-id-123",
    "departmentName": "销售部",
    "parentId": "parent-dept-id",
    "level": 2
  }
}
```

**方法2: 获取部门列表**
```bash
GET /v3/departments

# 返回组织架构树
{
  "success": true,
  "data": [
    {
      "departmentId": "dept-001",
      "departmentName": "总裁办",
      "children": [
        {
          "departmentId": "dept-002",
          "departmentName": "行政部"
        }
      ]
    },
    {
      "departmentId": "dept-003",
      "departmentName": "销售中心",
      "children": [
        {
          "departmentId": "dept-004",
          "departmentName": "华东区销售部"
        }
      ]
    }
  ]
}
```

**单选部门读取**: 返回部门对象
```json
{
  "department": {
    "departmentId": "department-id-123",
    "departmentName": "销售部"
  }
}
```

**多选部门读取**: 返回部门对象数组
```json
{
  "departments": [
    {
      "departmentId": "department-id-123",
      "departmentName": "销售部"
    },
    {
      "departmentId": "department-id-456",
      "departmentName": "市场部"
    }
  ]
}
```

**部门字段筛选**:
```json
{
  "type": "group",
  "logic": "AND",
  "children": [
    {
      "type": "condition",
      "field": "department",
      "operator": "eq",
      "value": ["department-id-123"]  // 使用部门ID
    }
  ]
}
```

**⚠️ 关键点**:
1. 必须使用部门ID,不能使用部门名称
2. 需要先通过 `/v3/departments/lookup` 查找部门ID
3. 部门ID格式通常为 UUID 字符串
4. 支持单选(`subType: "0"`)和多选(`subType: "1"`)
5. 筛选时使用 `eq` 操作符

**使用示例**:
```javascript
// 1. 查找部门ID
const dept = await findDepartment({ name: "销售部" });
const deptId = dept.data.departmentId;

// 2. 创建记录时设置部门
await createRecord({
  fields: [
    {
      "id": "department",
      "value": [deptId]
    }
  ]
});

// 3. 筛选某个部门的记录
const records = await queryRecords({
  filter: {
    type: "group",
    logic: "AND",
    children: [{
      type: "condition",
      field: "department",
      operator: "eq",
      value: [deptId]
    }]
  }
});
```

---

#### 3.2.10 地区字段 (Region) ⭐新增

地区字段用于选择省市区等地理区域,支持不同级别的地区选择。

**字段创建**:
```json
{
  "name": "所在地区",
  "alias": "region",
  "type": "Region",
  "required": false
}
```

**地区字段写入**: 传地区编码字符串
```json
{
  "id": "region",
  "value": "310100"  // 上海市市辖区的地区编码
}
```

**获取地区编码**: 使用地区信息API

**方法1: 通过名称搜索地区**
```bash
POST /v3/regions
{
  "search": "上海"
}

# 返回匹配的地区列表
{
  "success": true,
  "data": [
    {
      "id": "310000",
      "name": "上海市",
      "parentId": null,
      "level": 1  // 1=省, 2=市, 3=区县
    },
    {
      "id": "310100",
      "name": "市辖区",
      "parentId": "310000",
      "level": 2
    }
  ]
}
```

**方法2: 获取子级地区**
```bash
POST /v3/regions
{
  "id": "310000"  // 上海市的ID
}

# 返回上海市下的所有区县
{
  "success": true,
  "data": [
    {
      "id": "310100",
      "name": "市辖区",
      "parentId": "310000",
      "level": 2
    },
    {
      "id": "310101",
      "name": "黄浦区",
      "parentId": "310100",
      "level": 3
    },
    {
      "id": "310104",
      "name": "徐汇区",
      "parentId": "310100",
      "level": 3
    }
  ]
}
```

**地区字段读取**:
```json
{
  "region": {
    "id": "310100",
    "name": "上海市-市辖区",
    "code": "310100"
  }
}
```

**地区字段筛选**:
```json
{
  "type": "group",
  "logic": "AND",
  "children": [
    {
      "type": "condition",
      "field": "region",
      "operator": "eq",
      "value": ["310100"]  // 使用地区编码
    }
  ]
}
```

**数据透视分析中使用地区字段**:

地区字段支持按不同粒度进行统计:

```json
{
  "rows": [
    {
      "field": "region",
      "displayName": "所在地区",
      "granularity": 1,  // 1=省, 2=省/市, 3=省/市/区县
      "includeEmpty": false
    }
  ],
  "values": [
    {
      "field": "rowid",
      "aggregation": "COUNT",
      "displayName": "客户数量"
    }
  ]
}
```

**granularity 参数说明**:
- `1` - 按省统计(例如: 上海市、北京市)
- `2` - 按省/市统计(例如: 上海市-市辖区、北京市-市辖区)
- `3` - 按省/市/区县统计(例如: 上海市-市辖区-黄浦区)

**⚠️ 关键点**:
1. 地区字段值是地区编码字符串,不是地区名称
2. 需要先通过 `/v3/regions` API 查找地区编码
3. 地区编码是国家标准行政区划代码
4. 筛选时使用 `eq` 操作符
5. 透视分析时可使用 `granularity` 参数控制统计粒度

**使用示例**:
```javascript
// 1. 搜索地区编码
const regions = await getRegions({ search: "上海" });
const regionCode = regions.data[0].id;  // "310000"

// 2. 创建记录时设置地区
await createRecord({
  fields: [
    {
      "id": "region",
      "value": regionCode
    }
  ]
});

// 3. 筛选某个地区的记录
const records = await queryRecords({
  filter: {
    type: "group",
    logic: "AND",
    children: [{
      type: "condition",
      field: "region",
      operator: "eq",
      value: [regionCode]
    }]
  }
});

// 4. 按省统计客户分布
const pivotData = await getPivotData({
  rows: [{
    field: "region",
    granularity: 1  // 按省统计
  }],
  values: [{
    field: "rowid",
    aggregation: "COUNT"
  }]
});
```

**地区数据层级结构示例**:
```
中国
  ├── 北京市 (110000) - 直辖市
  │    └── 市辖区 (110100)
  │         ├── 东城区 (110101)
  │         ├── 西城区 (110102)
  │         └── ...
  ├── 上海市 (310000) - 直辖市
  │    └── 市辖区 (310100)
  │         ├── 黄浦区 (310101)
  │         ├── 徐汇区 (310104)
  │         └── ...
  └── 广东省 (440000) - 省
       ├── 广州市 (440100)
       │    ├── 越秀区 (440103)
       │    └── ...
       ├── 深圳市 (440300)
       │    ├── 罗湖区 (440303)
       │    └── ...
       └── ...
```

**常见地区编码**:
- 北京市: `110000`
- 上海市: `310000`
- 广东省: `440000`
- 浙江省: `330000`

**💡 提示**:
- 建议缓存常用地区的编码映射,避免频繁调用地区API
- 地区编码是6位数字字符串
- 直辖市的"市辖区"层级是必需的(例如上海市需要先选市辖区,再选具体区)
- 使用 `granularity` 参数可以实现灵活的地区维度分析

---

#### 3.2.11 关联字段 (Relation) ⭐重点

**单条关联写入**: 传记录ID数组
```json
{
  "id": "related_customer",
  "value": ["945e6503-3823-4e91-9d84-a53f8bdd6fc5"]  // 客户记录ID
}
```

**多条关联写入**: 传多个记录ID
```json
{
  "id": "related_projects",
  "value": [
    "2df27f5e-6b8a-462c-bb6f-3de224b50bc3",
    "741c2c54-584f-49e4-9e96-01620da53e29",
    "c2e726e4-1392-4730-9c71-e5737f8503d8"
  ]
}
```

**单条关联读取**: 返回对象数组
```json
{
  "related_customer": [
    {
      "sid": "945e6503-3823-4e91-9d84-a53f8bdd6fc5",
      "name": "明道云科技有限公司"
    }
  ]
}
```

**多条关联读取**: 返回ID数组
```json
{
  "related_projects": [
    "2df27f5e-6b8a-462c-bb6f-3de224b50bc3",
    "741c2c54-584f-49e4-9e96-01620da53e29",
    "c2e726e4-1392-4730-9c71-e5737f8503d8"
  ]
}
```

**获取关联记录完整数据**: 使用专用API
```bash
POST /v3/app/worksheets/{worksheet_id}/rows/{row_id}/relations/{field_id}

# 返回完整关联记录详情
{
  "data": {
    "rows": [
      {
        "rowid": "945e6503-3823-4e91-9d84-a53f8bdd6fc5",
        "customer_name": "明道云科技有限公司",
        "customer_type": "成交客户",
        "annual_budget": "1000000.00"
      }
    ],
    "total": 1
  }
}
```

---

#### 3.2.12 附件字段 (Attachment) ⭐重点

**写入**: 支持URL和base64两种格式
```json
{
  "id": "attachments",
  "type": "0",  // 0=覆盖已有附件, 1=追加新附件
  "value": [
    {
      "name": "产品宣传册.pdf",
      "url": "https://example.com/brochure.pdf"
    },
    {
      "name": "公司介绍.png",
      "url": "data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAA..."
    }
  ]
}
```

**type参数**:
- `"0"` - 覆盖模式:删除已有附件,上传新附件
- `"1"` - 追加模式:保留已有附件,新增附件

**读取**: 返回附件对象数组
```json
{
  "attachments": [
    {
      "file_id": "7b866bd5-8541-40b7-976f-276081bdddcd",
      "file_name": "70f9836904834c3eb44c75c587c3fcac.pdf",
      "original_file_name": "产品宣传册.pdf",
      "file_size": 2048576,
      "file_type": 4,
      "DownloadUrl": "https://p1.mingdaoyun.cn/doc/20260111/xxx.pdf",
      "preview_url": "https://...",
      "thumbnail_full_path": "https://..."
    }
  ]
}
```

**⚠️ 重要提示**:
1. 附件上传是**异步处理**,通常需要5-10秒
2. API返回成功不代表附件已上传完成
3. 建议使用明道云内部URL,外部URL可能有跨域限制
4. 支持base64编码的图片直接上传

---

### 3.4 完整创建记录示例

**场景**: 创建一条销售机会记录

```json
{
  "fields": [
    {
      "id": "opportunity_name",
      "value": "明道云-企业版年度续费"
    },
    {
      "id": "related_customer",
      "value": ["c74a29f0-f694-4501-9ba0-936e259daa9d"]
    },
    {
      "id": "stage",
      "value": ["a9ac7988-7603-4f03-86d5-985bd1f0cb66"]  // 商务谈判
    },
    {
      "id": "expected_amount",
      "value": 1200000
    },
    {
      "id": "close_date",
      "value": "2026-02-28"
    },
    {
      "id": "win_probability",
      "value": ["b9a6e559-7595-41f8-b0ad-febfb2daa4d5"]  // 90%
    },
    {
      "id": "competitor",
      "value": ""
    },
    {
      "id": "description",
      "value": "年度续约项目,增购100个账户"
    }
  ],
  "triggerWorkflow": true
}
```

---

### 3.5 更新记录 API

**API**: `POST /v3/app/worksheets/{worksheet_id}/rows/{row_id}`

**请求体**: 与创建记录相同
```json
{
  "fields": [
    {"id": "stage", "value": ["new-stage-key"]},
    {"id": "expected_amount", "value": 1500000}
  ],
  "triggerWorkflow": true
}
```

**⚠️ 注意**:
- 只传需要更新的字段
- 更新操作会覆盖原有值(除附件type=1追加模式)
- 关联字段更新会覆盖原有关联关系

---

### 3.6 批量操作完整指南

批量操作可以显著提高数据处理效率,但需要注意性能和错误处理。

---

#### 3.6.1 批量创建记录

**API**: `POST /v3/app/worksheets/{worksheet_id}/rows/batch`

**请求体结构**:
```json
{
  "rows": [
    {
      "fields": [
        {"id": "customer_name", "value": "客户A"},
        {"id": "customer_type", "value": ["option-key-1"]},
        {"id": "annual_budget", "value": 500000}
      ]
    },
    {
      "fields": [
        {"id": "customer_name", "value": "客户B"},
        {"id": "customer_type", "value": ["option-key-2"]},
        {"id": "annual_budget", "value": 800000}
      ]
    },
    {
      "fields": [
        {"id": "customer_name", "value": "客户C"},
        {"id": "customer_type", "value": ["option-key-1"]},
        {"id": "annual_budget", "value": 1200000}
      ]
    }
  ],
  "triggerWorkflow": true
}
```

**返回结果**:
```json
{
  "success": true,
  "error_code": 1,
  "data": {
    "successCount": 3,
    "failCount": 0,
    "rows": [
      {"row_id": "abc123..."},
      {"row_id": "def456..."},
      {"row_id": "ghi789..."}
    ]
  }
}
```

**使用场景**:
- ✅ 初始数据导入
- ✅ 数据迁移
- ✅ 定期批量同步
- ✅ Excel/CSV 数据批量上传

**性能建议**:
- 📊 **单次数量限制**: 建议每批 50-100 条记录
- 📊 **总量超过500条**: 分批处理,每批间隔 1-2 秒
- 📊 **包含关联字段**: 减少到每批 30-50 条
- 📊 **包含附件**: 建议单独处理,不要批量

**错误处理示例**:
```javascript
async function batchCreateRecords(allData, batchSize = 100) {
  const results = [];
  const errors = [];

  // 分批处理
  for (let i = 0; i < allData.length; i += batchSize) {
    const batch = allData.slice(i, i + batchSize);

    try {
      const response = await createBatch({
        rows: batch,
        triggerWorkflow: true
      });

      results.push(...response.data.rows);

      // 记录失败的记录
      if (response.data.failCount > 0) {
        errors.push({
          batchIndex: i / batchSize,
          failCount: response.data.failCount
        });
      }

      // 批次间延迟
      if (i + batchSize < allData.length) {
        await sleep(1000);  // 等待1秒
      }

    } catch (error) {
      console.error(`Batch ${i / batchSize} failed:`, error);
      errors.push({
        batchIndex: i / batchSize,
        error: error.message
      });
    }
  }

  return { results, errors };
}
```

---

#### 3.6.2 批量更新记录

**API**: `PUT /v3/app/worksheets/{worksheet_id}/rows/batch`

**请求体结构**:
```json
{
  "rowIds": [
    "c74a29f0-f694-4501-9ba0-936e259daa9d",
    "945e6503-3823-4e91-9d84-a53f8bdd6fc5",
    "2df27f5e-6b8a-462c-bb6f-3de224b50bc3"
  ],
  "fields": [
    {
      "id": "stage",
      "value": ["new-stage-key"]
    },
    {
      "id": "rating",
      "value": "5"
    },
    {
      "id": "last_contact_date",
      "value": "2026-01-11"
    }
  ],
  "triggerWorkflow": true
}
```

**返回结果**:
```json
{
  "success": true,
  "error_code": 1,
  "data": {
    "successCount": 3,
    "failCount": 0
  }
}
```

**⚠️ 重要限制**:
1. **相同值应用**: 批量更新会将相同的字段值应用到所有指定记录
2. **不支持差异化**: 如果需要为不同记录设置不同值,必须单独更新
3. **覆盖模式**: 更新操作会覆盖原有值(附件 type=1 除外)

**使用场景**:
- ✅ 批量修改状态(如:全部设为"已完成")
- ✅ 批量分配负责人
- ✅ 批量更新同一字段
- ❌ 不适合:为不同记录设置不同值

**正确示例 - 批量分配负责人**:
```json
{
  "rowIds": ["id1", "id2", "id3"],
  "fields": [
    {
      "id": "owner",
      "value": ["user-account-id-123"]  // 将3条记录的负责人都改为同一人
    }
  ]
}
```

**错误示例 - 尝试差异化更新**:
```json
// ❌ 这样不行!批量更新不支持为每条记录设置不同值
{
  "rowIds": ["id1", "id2"],
  "fields": [
    {"id": "rating", "value": "5"},   // id1和id2都会被设为5
    {"id": "rating", "value": "3"}    // 后面的值会被忽略或覆盖前面的
  ]
}
```

**需要差异化更新时的解决方案**:
```javascript
// 方案1: 单独更新每条记录
async function updateRecordsWithDifferentValues(updates) {
  const promises = updates.map(({rowId, fields}) =>
    updateRecord(worksheetId, rowId, { fields })
  );
  return await Promise.all(promises);
}

// 用法
await updateRecordsWithDifferentValues([
  { rowId: "id1", fields: [{ id: "rating", value: "5" }] },
  { rowId: "id2", fields: [{ id: "rating", value: "3" }] },
  { rowId: "id3", fields: [{ id: "rating", value: "4" }] }
]);
```

---

#### 3.6.3 批量删除记录

**API**: `DELETE /v3/app/worksheets/{worksheet_id}/rows/batch`

**请求体结构**:
```json
{
  "rowIds": [
    "c74a29f0-f694-4501-9ba0-936e259daa9d",
    "945e6503-3823-4e91-9d84-a53f8bdd6fc5"
  ],
  "permanent": false,  // false=逻辑删除(可恢复), true=物理删除(不可恢复)
  "triggerWorkflow": true
}
```

**返回结果**:
```json
{
  "success": true,
  "error_code": 1,
  "data": {
    "successCount": 2,
    "failCount": 0
  }
}
```

**permanent 参数说明**:

| 参数值 | 删除方式 | 可恢复 | 数据去向 | 使用场景 |
|-------|---------|--------|---------|---------|
| `false` (默认) | 逻辑删除 | ✅ 可以 | 进入回收站 | 日常数据清理 |
| `true` | 物理删除 | ❌ 不可恢复 | 永久删除 | 敏感数据清除 |

**⚠️ 严重警告**:
```javascript
// 🚨 危险操作!永久删除无法恢复!
DELETE /v3/app/worksheets/{worksheet_id}/rows/batch
{
  "rowIds": ["id1", "id2"],
  "permanent": true,  // ⚠️ 永久删除!
  "triggerWorkflow": true
}
```

**安全删除的最佳实践**:
```javascript
async function safeDeleteRecords(rowIds, options = {}) {
  const {
    permanent = false,
    confirmCallback = null,
    backupFirst = true
  } = options;

  // 1. 永久删除需要二次确认
  if (permanent) {
    const confirmed = confirmCallback
      ? await confirmCallback(rowIds.length)
      : confirm(`确定要永久删除 ${rowIds.length} 条记录吗?此操作不可恢复!`);

    if (!confirmed) {
      return { cancelled: true };
    }
  }

  // 2. 可选:删除前备份数据
  if (backupFirst) {
    const records = await getRecords({ rowIds });
    await saveBackup(records);  // 保存到本地或备份库
  }

  // 3. 执行删除
  return await deleteBatch({
    rowIds,
    permanent,
    triggerWorkflow: true
  });
}
```

**使用场景**:
- ✅ 逻辑删除(`permanent: false`):
  - 日常数据清理
  - 测试数据清理
  - 可能需要恢复的数据

- ⚠️ 物理删除(`permanent: true`):
  - GDPR 数据删除要求
  - 敏感信息彻底清除
  - 已确认不再需要的历史数据
  - **必须经过授权审批**

---

#### 3.6.4 批量操作性能优化

**推荐配置**:

```javascript
const BATCH_CONFIG = {
  // 基础配置
  CREATE_BATCH_SIZE: 100,      // 创建批次大小
  UPDATE_BATCH_SIZE: 100,      // 更新批次大小
  DELETE_BATCH_SIZE: 100,      // 删除批次大小

  // 特殊场景配置
  WITH_RELATION_SIZE: 50,      // 包含关联字段时
  WITH_ATTACHMENT_SIZE: 20,    // 包含附件时

  // 延迟配置
  BATCH_DELAY: 1000,           // 批次间延迟(毫秒)
  LARGE_BATCH_DELAY: 2000,     // 大批次延迟(>500条时)

  // 重试配置
  MAX_RETRIES: 3,              // 最大重试次数
  RETRY_DELAY: 3000            // 重试延迟
};
```

**性能优化技巧**:

1. **动态调整批次大小**:
```javascript
function calculateBatchSize(records) {
  let batchSize = BATCH_CONFIG.CREATE_BATCH_SIZE;

  // 检查是否包含关联字段
  const hasRelation = records.some(r =>
    r.fields.some(f => f.type === 'Relation')
  );
  if (hasRelation) {
    batchSize = Math.min(batchSize, BATCH_CONFIG.WITH_RELATION_SIZE);
  }

  // 检查是否包含附件
  const hasAttachment = records.some(r =>
    r.fields.some(f => f.type === 'Attachment')
  );
  if (hasAttachment) {
    batchSize = Math.min(batchSize, BATCH_CONFIG.WITH_ATTACHMENT_SIZE);
  }

  return batchSize;
}
```

2. **并发控制**:
```javascript
async function batchProcessWithConcurrency(items, batchSize, maxConcurrency = 3) {
  const batches = [];
  for (let i = 0; i < items.length; i += batchSize) {
    batches.push(items.slice(i, i + batchSize));
  }

  const results = [];
  for (let i = 0; i < batches.length; i += maxConcurrency) {
    const concurrentBatches = batches.slice(i, i + maxConcurrency);
    const batchResults = await Promise.all(
      concurrentBatches.map(batch => processBatch(batch))
    );
    results.push(...batchResults);

    // 并发批次之间也要有延迟
    if (i + maxConcurrency < batches.length) {
      await sleep(BATCH_CONFIG.BATCH_DELAY);
    }
  }

  return results;
}
```

3. **进度追踪**:
```javascript
async function batchCreateWithProgress(records, onProgress) {
  const batchSize = calculateBatchSize(records);
  const totalBatches = Math.ceil(records.length / batchSize);
  let processedCount = 0;

  for (let i = 0; i < totalBatches; i++) {
    const batch = records.slice(i * batchSize, (i + 1) * batchSize);

    await createBatch({ rows: batch });

    processedCount += batch.length;
    onProgress({
      current: processedCount,
      total: records.length,
      percentage: Math.round((processedCount / records.length) * 100),
      batchIndex: i + 1,
      totalBatches
    });

    if (i < totalBatches - 1) {
      await sleep(BATCH_CONFIG.BATCH_DELAY);
    }
  }
}

// 使用
await batchCreateWithProgress(records, (progress) => {
  console.log(`进度: ${progress.percentage}% (${progress.current}/${progress.total})`);
});
```

---

#### 3.6.5 批量操作错误处理

**常见错误类型**:

| 错误码 | 说明 | 处理方案 |
|-------|------|---------|
| `10` | 参数错误 | 检查字段ID、值格式 |
| `4` | 权限不足 | 检查API权限配置 |
| `-1` | 通用失败 | 查看error_msg详情 |
| `超时` | 请求超时 | 减少批次大小,重试 |

**健壮的批量处理实现**:
```javascript
async function robustBatchCreate(records, options = {}) {
  const {
    batchSize = 100,
    maxRetries = 3,
    onError = null,
    continueOnError = true
  } = options;

  const results = {
    success: [],
    failed: [],
    errors: []
  };

  for (let i = 0; i < records.length; i += batchSize) {
    const batch = records.slice(i, i + batchSize);
    let retries = 0;
    let success = false;

    while (retries < maxRetries && !success) {
      try {
        const response = await createBatch({ rows: batch });

        if (response.success) {
          results.success.push(...response.data.rows);
          success = true;
        } else {
          throw new Error(response.error_msg || 'Unknown error');
        }

      } catch (error) {
        retries++;

        const errorInfo = {
          batchIndex: i / batchSize,
          attempt: retries,
          error: error.message,
          records: batch
        };

        if (retries >= maxRetries) {
          // 达到最大重试次数
          results.failed.push(...batch);
          results.errors.push(errorInfo);

          if (onError) {
            await onError(errorInfo);
          }

          if (!continueOnError) {
            throw new Error(`Batch ${i / batchSize} failed after ${maxRetries} retries`);
          }
        } else {
          // 等待后重试
          console.log(`Batch ${i / batchSize} failed, retrying (${retries}/${maxRetries})...`);
          await sleep(BATCH_CONFIG.RETRY_DELAY * retries);
        }
      }
    }

    // 批次间延迟
    if (i + batchSize < records.length) {
      await sleep(BATCH_CONFIG.BATCH_DELAY);
    }
  }

  return results;
}

// 使用示例
const result = await robustBatchCreate(records, {
  batchSize: 50,
  maxRetries: 3,
  continueOnError: true,
  onError: async (errorInfo) => {
    // 记录错误日志
    await logError(errorInfo);
    // 发送通知
    await notifyAdmin(`批次 ${errorInfo.batchIndex} 失败`);
  }
});

console.log(`成功: ${result.success.length}, 失败: ${result.failed.length}`);
if (result.failed.length > 0) {
  // 导出失败记录
  await exportFailedRecords(result.failed);
}
```

**失败记录重试策略**:
```javascript
async function retryFailedRecords(failedRecords, originalBatchSize) {
  // 策略1: 减小批次大小
  const smallerBatchSize = Math.max(10, Math.floor(originalBatchSize / 2));

  // 策略2: 逐条重试
  if (failedRecords.length <= 10) {
    return await retryOneByOne(failedRecords);
  }

  // 策略3: 使用更小的批次
  return await robustBatchCreate(failedRecords, {
    batchSize: smallerBatchSize,
    maxRetries: 2
  });
}

async function retryOneByOne(records) {
  const results = { success: [], failed: [] };

  for (const record of records) {
    try {
      const response = await createRecord({ fields: record.fields });
      results.success.push(response.row_id);
    } catch (error) {
      results.failed.push({ record, error: error.message });
    }
  }

  return results;
}
```

---

#### 3.6.6 批量操作最佳实践总结

**✅ 推荐做法**:

1. **合理分批**:
   - 基础数据: 100条/批
   - 包含关联: 50条/批
   - 包含附件: 20条/批,或单独处理

2. **添加延迟**:
   - 批次间隔: 1-2秒
   - 大量数据: 增加到2-3秒

3. **错误处理**:
   - 实现重试机制
   - 记录失败数据
   - 提供恢复方案

4. **进度反馈**:
   - 显示处理进度
   - 记录处理日志
   - 通知完成状态

5. **性能监控**:
   - 记录API响应时间
   - 监控成功率
   - 调整批次大小

**❌ 避免的做法**:

1. ❌ 一次性批量超过200条
2. ❌ 批量操作附件字段
3. ❌ 不做错误处理和重试
4. ❌ 批量更新用于差异化更新
5. ❌ 物理删除(`permanent: true`)未经确认
6. ❌ 无延迟连续批量请求
7. ❌ 忽略API返回的error_code

---

## 四、查询筛选规范

### 4.1 查询记录 API

**API**: `POST /v3/app/worksheets/{worksheet_id}/rows/list`

**基本请求体**:
```json
{
  "filter": {},           // 筛选条件,见下文
  "sorts": [],            // 排序,见下文
  "fields": [],           // 返回字段ID数组,可选
  "search": "",           // 关键词搜索,可选
  "pageIndex": 1,         // 页码
  "pageSize": 100,        // 每页数量,最大1000
  "viewId": "",           // 视图ID,可选
  "includeSystemFields": false,  // 是否返回系统字段
  "useFieldIdAsKey": false       // 返回数据key用字段ID还是别名
}
```

---

### 4.2 Filter对象结构

**基础结构**:
```typescript
Filter = {
  type: 'group' | 'condition';

  // type='group' 时的字段
  logic?: 'AND' | 'OR';
  children?: Filter[];  // 子条件,最多两层嵌套

  // type='condition' 时的字段
  field?: string;       // 字段ID或别名
  operator?: string;    // 操作符
  value?: any[];        // 值数组
}
```

**规则**:
1. 顶层必须是 `group` 类型
2. 最多两层嵌套: group → group → condition
3. 同一group的children必须类型一致(全是group或全是condition)
4. group必须指定 `logic` (AND/OR)
5. condition必须指定 `field`, `operator`
6. 部分操作符不需要 `value` (如isempty)

---

### 4.3 操作符完整列表

| 操作符 | 说明 | 需要value | value格式 | 适用字段 |
|-------|------|----------|----------|---------|
| `eq` | 等于 | ✅ | `["值"]` | 所有类型 |
| `ne` | 不等于 | ✅ | `["值"]` | 所有类型 |
| `contains` | 包含 | ✅ | `["值"]` | Text, MultipleSelect |
| `notcontains` | 不包含 | ✅ | `["值"]` | Text, MultipleSelect |
| `startswith` | 开头是 | ✅ | `["值"]` | Text |
| `endswith` | 结尾是 | ✅ | `["值"]` | Text |
| `gt` | 大于 | ✅ | `["值"]` | Number, Date |
| `gte` | 大于等于 | ✅ | `["值"]` | Number, Date |
| `lt` | 小于 | ✅ | `["值"]` | Number, Date |
| `lte` | 小于等于 | ✅ | `["值"]` | Number, Date |
| `between` | 介于之间 | ✅ | `["最小值", "最大值"]` | Number, Date |
| `isempty` | 为空 | ❌ | 不需要 | 所有类型 |
| `isnotempty` | 不为空 | ❌ | 不需要 | 所有类型 |
| `belongsto` | 属于 | ✅ | `["部门ID1", "部门ID2"]` | 部门(Department) |
| `in` | 在...中 | ✅ | `["值1", "值2"]` | 所有类型（关联字段 Relation 用此，value = rowid 数组） |
| `concurrent` | 同时包含 | ✅ | `["值1", "值2"]` | MultipleSelect |

---

### 4.4 各字段类型筛选示例

#### 4.4.1 文本字段筛选

**包含查询**:
```json
{
  "type": "group",
  "logic": "AND",
  "children": [
    {
      "type": "condition",
      "field": "customer_name",
      "operator": "contains",
      "value": ["明道"]
    }
  ]
}
```

**开头匹配**:
```json
{
  "type": "condition",
  "field": "customer_name",
  "operator": "startswith",
  "value": ["北京"]
}
```

---

#### 4.4.2 数值字段筛选 ⭐重点

**范围查询**:
```json
{
  "type": "condition",
  "field": "annual_budget",
  "operator": "between",
  "value": ["500000", "2000000"]  // ⚠️ 必须是字符串数组
}
```

**大于查询**:
```json
{
  "type": "condition",
  "field": "expected_amount",
  "operator": "gt",
  "value": ["1000000"]  // ⚠️ 字符串格式
}
```

**⚠️ 关键点**: 数值字段的value必须是字符串数组!

---

#### 4.4.3 单选字段筛选 ⭐⭐⭐重点

**等于查询** (最常用):
```json
{
  "type": "condition",
  "field": "customer_type",
  "operator": "eq",
  "value": ["74c7b607-864d-4cc4-b401-28acba2636e9"]  // ⚠️ 必须用选项key
}
```

**❌ 错误示例**:
```json
{
  "type": "condition",
  "field": "customer_type",
  "operator": "eq",
  "value": ["成交客户"]  // ❌ 不能用显示文本!
}
```

**如何获取选项key**?

**方法1**: 先查询一条记录
```bash
POST /v3/app/worksheets/{worksheet_id}/rows/list
{
  "pageIndex": 1,
  "pageSize": 1
}

# 返回数据中包含选项key
{
  "customer_type": [
    {"key": "74c7b607-864d-4cc4-b401-28acba2636e9", "value": "成交客户"}
  ]
}
```

**方法2**: 查询工作表结构
```bash
GET /v3/app/worksheets/{worksheet_id}

# 返回字段定义,包含options的key
{
  "fields": [
    {
      "id": "customer_type",
      "type": "SingleSelect",
      "options": [
        {"key": "74c7b607-864d-4cc4-b401-28acba2636e9", "value": "成交客户"},
        {"key": "f488d4db-5046-4b10-978f-7869c4c70a71", "value": "意向客户"}
      ]
    }
  ]
}
```

**💡 最佳实践**: 应用初始化时缓存所有选项字段的key-value映射

---

#### 4.4.4 多选字段筛选

**包含某个选项**:
```json
{
  "type": "condition",
  "field": "customer_tags",
  "operator": "contains",
  "value": ["705de83e-b929-43e4-82ff-fff2f7dd6888"]  // 重点客户的key
}
```

**同时包含多个选项**:
```json
{
  "type": "condition",
  "field": "customer_tags",
  "operator": "concurrent",
  "value": [
    "705de83e-b929-43e4-82ff-fff2f7dd6888",  // 重点客户
    "422b4e56-263f-4bfa-bc88-77c09811080e"   // VIP
  ]
}
```

---

#### 4.4.5 日期字段筛选

**日期范围**:
```json
{
  "type": "condition",
  "field": "founded_date",
  "operator": "between",
  "value": ["2020-01-01", "2025-12-31"]
}
```

**晚于某日期**:
```json
{
  "type": "condition",
  "field": "close_date",
  "operator": "gte",
  "value": ["2026-01-01"]
}
```

**日期格式**: `YYYY-MM-DD` 或 `YYYY-MM-DD HH:mm:ss`

---

#### 4.4.6 关联字段筛选 ⭐⭐重点

**等于某个关联记录**:
```json
{
  "type": "condition",
  "field": "related_customer",
  "operator": "eq",  // 关联字段用 in 或 eq + rowid 数组
  "value": ["945e6503-3823-4e91-9d84-a53f8bdd6fc5"]  // 客户记录的 rowid
}
```

**是多个关联记录之一**:
```json
{
  "type": "condition",
  "field": "related_customer",
  "operator": "in",
  "value": [
    "945e6503-3823-4e91-9d84-a53f8bdd6fc5",
    "c74a29f0-f694-4501-9ba0-936e259daa9d"
  ]
}
```

**⚠️ 关键点**:
1. 关联字段(Relation)用 `in` 或 `eq` 操作符
2. value 传入关联记录的 rowid 字符串数组（不能用关联显示的标题文本去匹配）
3. `belongsto` / `notbelongsto` 仅用于部门(Department)字段，value = 部门 ID 数组

---

#### 4.4.7 成员字段筛选

```json
{
  "type": "condition",
  "field": "owner",
  "operator": "eq",
  "value": ["user-account-id-123"]  // 用户ID,不是姓名
}
```

---

#### 4.4.8 等级字段筛选

```json
{
  "type": "condition",
  "field": "customer_rating",
  "operator": "gte",
  "value": ["4"]  // 字符串格式
}
```

---

### 4.5 组合条件示例

#### 4.5.1 简单AND条件

**查询**: 评级≥4星 且 客户类型=成交客户

```json
{
  "type": "group",
  "logic": "AND",
  "children": [
    {
      "type": "condition",
      "field": "customer_rating",
      "operator": "gte",
      "value": ["4"]
    },
    {
      "type": "condition",
      "field": "customer_type",
      "operator": "eq",
      "value": ["74c7b607-864d-4cc4-b401-28acba2636e9"]
    }
  ]
}
```

---

#### 4.5.2 简单OR条件

**查询**: 客户类型=成交客户 或 客户类型=意向客户

```json
{
  "type": "group",
  "logic": "OR",
  "children": [
    {
      "type": "condition",
      "field": "customer_type",
      "operator": "eq",
      "value": ["74c7b607-864d-4cc4-b401-28acba2636e9"]  // 成交
    },
    {
      "type": "condition",
      "field": "customer_type",
      "operator": "eq",
      "value": ["f488d4db-5046-4b10-978f-7869c4c70a71"]  // 意向
    }
  ]
}
```

---

#### 4.5.3 嵌套条件 (AND + OR)

**查询**: (类型=成交 或 类型=意向) 且 预算>50万

```json
{
  "type": "group",
  "logic": "AND",
  "children": [
    {
      "type": "group",
      "logic": "OR",
      "children": [
        {
          "type": "condition",
          "field": "customer_type",
          "operator": "eq",
          "value": ["74c7b607-864d-4cc4-b401-28acba2636e9"]
        },
        {
          "type": "condition",
          "field": "customer_type",
          "operator": "eq",
          "value": ["f488d4db-5046-4b10-978f-7869c4c70a71"]
        }
      ]
    },
    {
      "type": "condition",
      "field": "annual_budget",
      "operator": "gt",
      "value": ["500000"]
    }
  ]
}
```

---

#### 4.5.4 复杂业务场景

**查询**: 互联网行业的成交客户,且(预算>100万 或 评级=5星)

```json
{
  "type": "group",
  "logic": "AND",
  "children": [
    {
      "type": "condition",
      "field": "industry",
      "operator": "eq",
      "value": ["4f28cae6-6a76-4b0b-b6e8-62cc724c677d"]  // 互联网
    },
    {
      "type": "condition",
      "field": "customer_type",
      "operator": "eq",
      "value": ["74c7b607-864d-4cc4-b401-28acba2636e9"]  // 成交客户
    },
    {
      "type": "group",
      "logic": "OR",
      "children": [
        {
          "type": "condition",
          "field": "annual_budget",
          "operator": "gt",
          "value": ["1000000"]
        },
        {
          "type": "condition",
          "field": "customer_rating",
          "operator": "eq",
          "value": ["5"]
        }
      ]
    }
  ]
}
```

---

### 4.6 排序 (Sorts)

**基本格式**:
```json
{
  "sorts": [
    {
      "field": "annual_budget",
      "isAsc": false  // false=降序, true=升序
    },
    {
      "field": "customer_rating",
      "isAsc": false
    }
  ]
}
```

**多字段排序**: 按数组顺序优先级排序

---

### 4.7 完整查询示例

**业务场景**: 查询互联网行业的高价值客户,按预算降序

```json
{
  "filter": {
    "type": "group",
    "logic": "AND",
    "children": [
      {
        "type": "condition",
        "field": "industry",
        "operator": "eq",
        "value": ["4f28cae6-6a76-4b0b-b6e8-62cc724c677d"]
      },
      {
        "type": "condition",
        "field": "customer_rating",
        "operator": "gte",
        "value": ["4"]
      },
      {
        "type": "condition",
        "field": "annual_budget",
        "operator": "gt",
        "value": ["500000"]
      }
    ]
  },
  "sorts": [
    {
      "field": "annual_budget",
      "isAsc": false
    }
  ],
  "fields": ["customer_name", "customer_type", "annual_budget", "customer_rating"],
  "pageIndex": 1,
  "pageSize": 20,
  "includeSystemFields": false
}
```

---

## 五、数据透视分析规范

### 5.1 透视分析 API

**API**: `POST /v3/app/worksheets/{worksheet_id}/rows/pivot`

**基本请求体**:
```json
{
  "rows": [],       // 行维度
  "columns": [],    // 列维度(可选)
  "values": [],     // 值/指标
  "filter": {},     // 筛选条件(可选)
  "sorts": [],      // 排序(可选)
  "includeSummary": true,  // 是否包含汇总
  "pageIndex": 1,
  "pageSize": 1000
}
```

---

### 5.2 维度配置

**行/列维度结构**:
```json
{
  "field": "industry",          // 字段ID或别名
  "displayName": "所属行业",    // 显示名称(可选)
  "granularity": 1,             // 粒度(日期/地区字段)
  "includeEmpty": false         // 是否包含空值
}
```

**granularity参数** (仅日期和地区字段):

**日期字段**:
- `1` - 按天
- `2` - 按周
- `3` - 按月

**地区字段**:
- `1` - 省
- `2` - 省/市
- `3` - 省/市/区县

---

### 5.3 值/指标配置

**值配置结构**:
```json
{
  "field": "annual_budget",     // 字段ID或别名
  "aggregation": "SUM",         // 聚合函数
  "displayName": "预算总额",    // 显示名称(可选)
  "includeEmpty": false         // 是否包含空值
}
```

**聚合函数** (不区分大小写):

| 函数 | 说明 | 适用字段 |
|-----|------|---------|
| `COUNT` | 计数 | 所有字段 |
| `DISTINCTCOUNT` | 去重计数 | 所有字段 |
| `SUM` | 求和 | Number |
| `AVG` | 平均值 | Number |
| `MIN` | 最小值 | Number, Date |
| `MAX` | 最大值 | Number, Date |

**⚠️ 注意**:
- 统计行数时,`field` 使用 `"rowid"`
- `aggregation` 不区分大小写

---

### 5.4 透视分析示例

#### 5.4.1 单维度统计

**场景**: 按行业统计客户数量和预算总额

```json
{
  "rows": [
    {
      "field": "industry",
      "displayName": "所属行业",
      "includeEmpty": false
    }
  ],
  "values": [
    {
      "field": "rowid",
      "aggregation": "COUNT",
      "displayName": "客户数量"
    },
    {
      "field": "annual_budget",
      "aggregation": "SUM",
      "displayName": "预算总额"
    }
  ],
  "includeSummary": true,
  "pageIndex": 1,
  "pageSize": 50
}
```

**返回结果**:
```json
{
  "data": {
    "pivot": [
      {
        "rows": {"industry": "互联网"},
        "values": {"rowid": 4.0, "annual_budget": 2150000.0}
      },
      {
        "rows": {"industry": "金融"},
        "values": {"rowid": 1.0, "annual_budget": 2000000.0}
      }
    ],
    "summary": {
      "rowid": 12.0,
      "annual_budget": 7900000.0
    }
  }
}
```

---

#### 5.4.2 多指标统计

**场景**: 按销售阶段统计机会的数量、金额总计、平均金额

```json
{
  "rows": [
    {
      "field": "opportunity_stage",
      "displayName": "销售阶段"
    }
  ],
  "values": [
    {
      "field": "rowid",
      "aggregation": "COUNT",
      "displayName": "机会数量"
    },
    {
      "field": "expected_amount",
      "aggregation": "SUM",
      "displayName": "金额总计"
    },
    {
      "field": "expected_amount",
      "aggregation": "AVG",
      "displayName": "平均金额"
    }
  ],
  "includeSummary": true
}
```

**返回结果**:
```json
{
  "data": {
    "pivot": [
      {
        "rows": {"opportunity_stage": "商务谈判"},
        "values": {
          "rowid": 3.0,
          "expected_amount": 2710000.0,
          "expected_amount_avg": 903333.33
        }
      }
    ],
    "summary": {
      "rowid": 10.0,
      "expected_amount": 8990000.0,
      "expected_amount_avg": 899000.0
    }
  }
}
```

---

#### 5.4.3 多维度交叉分析

**场景**: 按客户类型和行业交叉统计客户数

```json
{
  "rows": [
    {
      "field": "customer_type",
      "displayName": "客户类型"
    },
    {
      "field": "industry",
      "displayName": "所属行业"
    }
  ],
  "values": [
    {
      "field": "rowid",
      "aggregation": "COUNT",
      "displayName": "客户数"
    }
  ],
  "includeSummary": true
}
```

**返回结果**: 二维交叉数据
```json
{
  "data": {
    "pivot": [
      {
        "rows": {
          "customer_type": "成交客户",
          "industry": "互联网"
        },
        "values": {"rowid": 3.0}
      },
      {
        "rows": {
          "customer_type": "意向客户",
          "industry": "制造业"
        },
        "values": {"rowid": 2.0}
      }
    ],
    "summary": {"rowid": 12.0}
  }
}
```

---

#### 5.4.4 带筛选的透视分析

**场景**: 统计2026年Q1预计成交的机会

```json
{
  "filter": {
    "type": "group",
    "logic": "AND",
    "children": [
      {
        "type": "condition",
        "field": "expected_close_date",
        "operator": "between",
        "value": ["2026-01-01", "2026-03-31"]
      }
    ]
  },
  "rows": [
    {
      "field": "opportunity_stage",
      "displayName": "销售阶段"
    }
  ],
  "values": [
    {
      "field": "rowid",
      "aggregation": "COUNT",
      "displayName": "机会数量"
    },
    {
      "field": "expected_amount",
      "aggregation": "SUM",
      "displayName": "金额总计"
    }
  ],
  "includeSummary": true
}
```

---

## 六、关联字段完整指南

### 6.1 关联字段设计原则

**创建关联字段前需考虑**:
1. 关联方向:单向还是双向?
2. 关联数量:单条还是多条?
3. 显示字段:关联卡片显示哪些信息?
4. 数据依赖:目标表必须先存在

---

### 6.2 关联字段创建步骤

**Step 1**: 创建目标工作表(如客户表)
```json
{
  "name": "客户信息表",
  "fields": [
    {"name": "客户名称", "type": "Text", "isTitle": true},
    {"name": "客户类型", "type": "SingleSelect", "options": [...]}
  ]
}

// 返回: {"worksheet_id": "你的worksheetID"}
```

**Step 2**: 在源工作表创建关联字段(如机会表)
```json
{
  "name": "销售机会表",
  "fields": [
    {"name": "机会名称", "type": "Text", "isTitle": true},
    {
      "name": "关联客户",
      "alias": "related_customer",
      "type": "Relation",
      "subType": "1",  // 单条关联
      "dataSource": "你的worksheetID",  // 客户表ID
      "relation": {
        "bidirectional": false,
        "showFields": ["customer_name", "customer_type"]
      }
    }
  ]
}
```

---

### 6.3 单向 vs 双向关联

**单向关联** (`bidirectional: false`):
- 只在源表创建关联字段
- 目标表不会自动创建反向字段
- 适用场景:机会→客户,任务→项目

**双向关联** (`bidirectional: true`):
- 源表和目标表都有关联字段
- 系统自动在目标表创建反向字段
- 适用场景:客户↔联系人,项目↔任务

**示例 - 双向关联**:
```json
{
  "name": "关联项目",
  "type": "Relation",
  "subType": "2",  // 多条关联
  "dataSource": "project-table-id",
  "relation": {
    "bidirectional": true,  // 双向
    "showFields": ["project_name", "project_status"]
  }
}
```

**效果**:
- 联系人表:显示"关联项目"字段
- 项目表:自动创建"关联联系人"反向字段

---

### 6.4 关联字段写入完整流程

**场景**: 为销售机会关联客户

**Step 1**: 查询客户记录,获取rowid
```bash
POST /v3/app/worksheets/你的worksheetID/rows/list
{
  "filter": {
    "type": "group",
    "logic": "AND",
    "children": [
      {
        "type": "condition",
        "field": "customer_name",
        "operator": "contains",
        "value": ["明道云"]
      }
    ]
  },
  "pageSize": 1
}

# 返回
{
  "data": {
    "rows": [
      {"rowid": "c74a29f0-f694-4501-9ba0-936e259daa9d", ...}
    ]
  }
}
```

**Step 2**: 创建机会记录,传入客户rowid
```bash
POST /v3/app/worksheets/你的worksheetID2/rows
{
  "fields": [
    {
      "id": "opportunity_name",
      "value": "明道云-年度续费"
    },
    {
      "id": "related_customer",
      "value": ["c74a29f0-f694-4501-9ba0-936e259daa9d"]  // 客户rowid
    }
  ]
}
```

**Step 3**: 读取验证
```bash
GET /v3/app/worksheets/你的worksheetID2/rows/{row_id}

# 返回
{
  "related_customer": [
    {
      "sid": "c74a29f0-f694-4501-9ba0-936e259daa9d",
      "name": "明道云科技有限公司"
    }
  ]
}
```

---

### 6.5 获取关联记录完整数据

#### 6.5.1 关联字段返回的数据结构

当读取包含关联字段的记录时,HAP API 返回的数据结构如下:

```javascript
{
  "示例控件ID": [  // 关联字段ID
    {
      "sid": "9dd9272b-e7e5-40d5-8a6d-d2403d1e45c2",  // 关联记录的ID (等同于 rowid)
      "name": "实木衣柜"  // 关联记录的标题字段值
    }
  ]
}
```

**关键属性说明**:
- **`sid`**: 关联记录的唯一标识符,等同于目标表中的 `rowid`
- **`name`**: 关联记录的标题字段值(仅显示用途)

**⚠️ 重要提示**:
- 默认情况下,关联字段只返回 `sid` 和 `name` 两个属性
- 如果需要展示关联表的其他信息(如图片、价格、描述等),需要进行**深度查询**
- 深度查询步骤:
  1. 找到该关联字段对应的目标工作表 ID
  2. 使用 `sid` (等同于 `rowid`) 去目标表查询完整数据

---

#### 6.5.2 方法1: 使用 get_record_relations API (推荐)

**适用场景**: 获取单条记录的关联详情

```bash
POST /v3/app/worksheets/{worksheet_id}/rows/{row_id}/relations/{field_id}
{
  "pageIndex": 1,
  "pageSize": 10,
  "isReturnSystemFields": false
}

# 返回完整关联记录详情
{
  "data": {
    "rows": [
      {
        "rowid": "c74a29f0-f694-4501-9ba0-936e259daa9d",
        "customer_name": "明道云科技有限公司",
        "customer_type": [{"key": "...", "value": "成交客户"}],
        "annual_budget": "1000000.00",
        "customer_rating": "5"
      }
    ],
    "total": 1
  }
}
```

**优点**: 一次请求获取完整数据,无需手动查询目标表

---

#### 6.5.3 方法2: 先读取关联ID,再查询目标表

**适用场景**: 批量查询多条记录的关联详情(避免 N+1 查询问题)

**Step 1**: 读取包含关联字段的记录
```bash
GET /v3/app/worksheets/你的worksheetID2/rows/{row_id}

# 返回
{
  "related_customer": [
    {
      "sid": "c74a29f0-f694-4501-9ba0-936e259daa9d",
      "name": "明道云科技有限公司"
    }
  ]
}
```

**Step 2**: 使用 `sid` 查询目标表完整数据

⚠️ **关键**: 使用 `rowid` 字段 + `in` 操作符进行查询

```bash
POST /v3/app/worksheets/你的worksheetID/rows/list
{
  "filter": {
    "type": "group",
    "logic": "AND",
    "children": [
      {
        "type": "condition",
        "field": "rowid",  // ⚠️ 使用系统字段 rowid
        "operator": "in",  // ⚠️ 使用 in 操作符
        "value": ["c74a29f0-f694-4501-9ba0-936e259daa9d"]  // 传入 sid 值
      }
    ]
  }
}

# 返回完整数据
{
  "data": {
    "rows": [
      {
        "rowid": "c74a29f0-f694-4501-9ba0-936e259daa9d",
        "customer_name": "明道云科技有限公司",
        "customer_type": [{"key": "...", "value": "成交客户"}],
        "customer_logo": [{"downloadUrl": "https://..."}],
        "annual_budget": "1000000.00",
        "customer_rating": "5",
        "customer_address": "上海市徐汇区"
      }
    ]
  }
}
```

---

#### 6.5.4 批量查询优化示例

**场景**: 产品列表页面,需要显示每个产品的完整分类信息(包括分类图标、描述等)

**问题**: 如果有 100 个产品,逐个查询分类会产生 N+1 查询问题(1次产品查询 + N次分类查询)

**解决方案**: 批量收集所有分类 ID,一次性查询所有分类

```javascript
// Step 1: 获取产品列表
const products = await getRows('products-worksheet-id', {
  pageSize: 100
});

// Step 2: 收集所有产品的分类 ID (使用 Set 自动去重)
const categoryIds = new Set();
products.rows.forEach(product => {
  const categories = product['category_field_id'];  // 关联字段
  if (Array.isArray(categories)) {
    categories.forEach(cat => {
      categoryIds.add(cat.sid);  // 收集 sid
    });
  }
});

// Step 3: 批量查询所有分类的完整数据 (1次请求!)
const categoriesData = await getRows('categories-worksheet-id', {
  filter: {
    type: 'group',
    logic: 'AND',
    children: [{
      type: 'condition',
      field: 'rowid',
      operator: 'in',
      value: Array.from(categoryIds)  // 传入所有 sid 数组
    }]
  }
});

// Step 4: 建立分类 ID → 分类数据的映射 (O(1) 查找)
const categoryMap = {};
categoriesData.rows.forEach(cat => {
  categoryMap[cat.rowid] = cat;
});

// Step 5: 渲染产品列表,直接从 map 中取分类数据
products.rows.forEach(product => {
  const categories = product['category_field_id'];
  const categoryData = categoryMap[categories[0].sid];

  console.log({
    productName: product.name,
    categoryName: categoryData.name,
    categoryIcon: categoryData.icon[0].downloadUrl,
    categoryDesc: categoryData.description
  });
});
```

**性能对比**:
- ❌ 逐个查询: 1 + 100 = 101 次 API 请求
- ✅ 批量查询: 1 + 1 = 2 次 API 请求 (性能提升 50 倍!)

---

#### 6.5.5 方法选择建议

| 场景 | 推荐方法 | 原因 |
|------|---------|------|
| 单条记录详情页 | 方法1 (get_record_relations) | 简单直接,一次请求 |
| 列表页批量渲染 | 方法2 (批量查询) | 避免 N+1 查询,性能最优 |
| 需要自定义筛选条件 | 方法2 | 可以在查询目标表时添加额外筛选 |
| 只需要显示 name | 直接使用 | 无需额外查询 |

---

### 6.6 关联字段更新

**覆盖关联**:
```json
{
  "fields": [
    {
      "id": "related_customer",
      "value": ["new-customer-id"]  // 覆盖原有关联
    }
  ]
}
```

**清空关联**:
```json
{
  "fields": [
    {
      "id": "related_customer",
      "value": []  // 空数组=清空关联
    }
  ]
}
```

**多条关联追加**: 需要先读取原有ID,再合并
```bash
# Step 1: 读取原有关联
GET /v3/app/worksheets/{worksheet_id}/rows/{row_id}
# 返回: {"related_projects": ["id1", "id2"]}

# Step 2: 合并新ID并更新
POST /v3/app/worksheets/{worksheet_id}/rows/{row_id}
{
  "fields": [
    {
      "id": "related_projects",
      "value": ["id1", "id2", "id3"]  // 原有+新增
    }
  ]
}
```

---

### 6.7 关联字段常见问题

**Q1: 关联字段返回的 `sid` 和 `name` 有什么区别?**

- **`sid`**: 关联记录的唯一标识符,等同于目标表的 `rowid`,用于查询完整数据
- **`name`**: 关联记录的标题字段值,仅用于显示

**关键理解**:
```javascript
// 读取产品记录
{
  "category_field": [
    {
      "sid": "9dd9272b-e7e5-40d5-8a6d-d2403d1e45c2",  // 用于查询
      "name": "实木衣柜"  // 用于显示
    }
  ]
}

// 如果需要获取分类的图标、描述等其他信息,必须使用 sid 查询
// sid === 目标表中的 rowid
```

**使用场景**:
- 只需要显示名称 → 直接使用 `name`
- 需要显示其他字段(图片、价格、描述等) → 使用 `sid` 查询目标表

---

**Q2: 关联字段创建后能修改dataSource吗?**

❌ 不能。dataSource一旦设置不可修改,只能删除字段重建。

---

**Q3: 如何实现级联删除?**

通过工作流实现。当源记录删除时,触发工作流删除关联记录。

---

**Q4: 关联字段能跨应用吗?**

✅ 可以。只要有目标工作表的ID,即使在不同应用也能关联。

---

**Q5: 双向关联的反向字段名称可以自定义吗?**

❌ 不能。系统自动生成,格式为"关联{源表名}"。

---

**Q6: 关联记录被删除后,关联字段会怎样?**

关联字段会自动清空该关联关系,不会报错。

---

**Q7: 为什么查询关联记录要用 `rowid` 字段而不是其他字段?**

因为 `rowid` 是 HAP 系统字段,每条记录都有唯一的 `rowid`。关联字段返回的 `sid` 就是目标记录的 `rowid`。

**示例**:
```javascript
// 关联字段返回的 sid
const categoryId = product.category[0].sid;  // "9dd9272b-..."

// 查询目标表时,使用 rowid 字段匹配
{
  "filter": {
    "type": "condition",
    "field": "rowid",  // 必须用 rowid
    "operator": "in",
    "value": [categoryId]  // 传入 sid
  }
}
```

---

## 七、常见陷阱与解决方案

### 7.1 选项字段陷阱 ⭐⭐⭐

**问题**: 筛选单选/多选字段时返回空结果

**错误示例**:
```json
{
  "field": "customer_type",
  "operator": "eq",
  "value": ["成交客户"]  // ❌ 使用了显示文本
}
```

**正确做法**:
```json
{
  "field": "customer_type",
  "operator": "eq",
  "value": ["74c7b607-864d-4cc4-b401-28acba2636e9"]  // ✅ 使用选项key
}
```

**解决方案**:
1. 初始化时查询工作表结构,缓存选项映射
2. 或先查询一条记录,从返回数据获取key
3. 建立 value → key 的映射表

---

### 7.2 数值字段陷阱

**问题**: 数值筛选无结果或报错

**错误示例**:
```json
{
  "field": "annual_budget",
  "operator": "gt",
  "value": [1000000]  // ❌ 数字类型
}
```

**正确做法**:
```json
{
  "field": "annual_budget",
  "operator": "gt",
  "value": ["1000000"]  // ✅ 字符串数组
}
```

**记忆口诀**: 筛选条件的value永远是字符串数组

---

### 7.3 关联字段陷阱 ⭐⭐⭐

**问题1**: 使用错误的操作符筛选关联字段

**错误示例**:
```json
{
  "field": "related_customer",
  "operator": "contains",  // ❌ 关联字段不要用 contains，也不要用 belongsto（belongsto 是部门字段专用）
  "value": ["客户名称"]  // ❌ 也不要用关联显示的标题文本去匹配
}
```

**正确做法**:
```json
{
  "field": "related_customer",
  "operator": "in",  // ✅ 关联字段用 in 或 eq + rowid 数组
  "value": ["customer-id"]  // 传入关联记录的 rowid (即 sid)
}
```

**关联字段支持的操作符**:
- `in` / `eq`: 是指定的关联记录之一（value = 关联记录 rowid 字符串数组）
- `isempty`: 关联字段为空
- `isnotempty`: 关联字段不为空

---

**问题2**: 混淆 `sid` 和字段名

**错误示例**:
```javascript
// 错误:尝试从关联字段直接获取目标表的其他字段
const categoryIcon = product.category[0].icon;  // ❌ undefined!
```

**正确理解**:
```javascript
// 关联字段只返回 sid 和 name
const category = product.category[0];
console.log(category);
// {
//   "sid": "9dd9272b-...",  // 关联记录ID
//   "name": "实木衣柜"      // 标题字段值
// }

// 如果需要 icon 等其他字段,必须查询目标表
const categoryData = await getRows('category-worksheet-id', {
  filter: {
    type: 'condition',
    field: 'rowid',
    operator: 'in',
    value: [category.sid]  // 使用 sid 查询
  }
});

console.log(categoryData.rows[0].icon);  // ✅ 正确获取
```

---

**问题3**: 在列表页逐个查询关联数据 (N+1 问题)

**错误示例**:
```javascript
// ❌ 性能灾难:100个产品 = 1 + 100 = 101次请求
const products = await getProductList();  // 1次请求

for (const product of products) {
  const categoryId = product.category[0].sid;
  const category = await getCategoryById(categoryId);  // 100次请求!
  console.log(category.name);
}
```

**正确做法**: 批量查询 (参见 Section 6.5.4)
```javascript
// ✅ 性能优化:100个产品 = 1 + 1 = 2次请求
const products = await getProductList();  // 1次请求

// 收集所有分类ID
const categoryIds = new Set();
products.forEach(p => {
  if (p.category && p.category.length > 0) {
    categoryIds.add(p.category[0].sid);
  }
});

// 批量查询所有分类
const categories = await getRows('category-worksheet-id', {
  filter: {
    type: 'condition',
    field: 'rowid',
    operator: 'in',
    value: Array.from(categoryIds)
  }
});  // 1次请求

// 建立映射
const categoryMap = {};
categories.rows.forEach(cat => {
  categoryMap[cat.rowid] = cat;
});

// O(1) 查找
products.forEach(p => {
  const category = categoryMap[p.category[0].sid];
  console.log(category.name, category.icon);
});
```

---

### 7.4 附件字段陷阱

**问题**: 附件上传后立即读取返回空数组

**原因**: 附件上传是异步处理,需要5-10秒

**解决方案**:
```javascript
// 上传附件
await updateRecord({
  fields: [{
    id: "attachments",
    type: "0",
    value: [{name: "file.pdf", url: "https://..."}]
  }]
});

// 等待5秒
await sleep(5000);

// 再读取记录
const record = await getRecord(rowId);
console.log(record.attachments);  // 现在有数据了
```

**建议**: 使用明道云内部URL,外部URL可能有跨域限制

---

### 7.5 日期字段陷阱

**问题**: 日期写入时带时间,读取时只返回日期

**原因**: Date字段的subType决定返回精度

**示例**:
```json
// 创建字段
{
  "type": "Date",
  "subType": "3"  // 年月日
}

// 写入
{
  "value": "2025-01-11 14:30:00"
}

// 读取返回
{
  "date_field": "2025-01-11"  // 时间被截断
}
```

**解决方案**: 如需保留时间,使用 `subType: "6"` (年月日时分秒)

---

### 7.6 Filter嵌套陷阱

**问题**: 过度嵌套导致查询失败

**错误示例**:
```json
{
  "type": "group",
  "children": [
    {
      "type": "group",
      "children": [
        {
          "type": "group",  // ❌ 第三层嵌套
          "children": [...]
        }
      ]
    }
  ]
}
```

**限制**: 最多两层嵌套 (group → group → condition)

**解决方案**: 重新设计查询逻辑,合并条件

---

### 7.7 成员字段陷阱

**问题**: 使用姓名查询成员字段失败

**错误示例**:
```json
{
  "field": "owner",
  "operator": "eq",
  "value": ["张三"]  // ❌ 姓名无效
}
```

**正确做法**:
```bash
# Step 1: 通过姓名查找用户ID
POST /v3/users/lookup
{"name": "张三"}

# 返回: {"accountId": "user-123"}

# Step 2: 使用用户ID筛选
{
  "field": "owner",
  "operator": "eq",
  "value": ["user-123"]  // ✅ 用户ID
}
```

---

### 7.8 批量操作陷阱

**问题**: 批量更新时误覆盖不同记录

**场景**: 想给不同客户设置不同评级

**错误做法**:
```json
{
  "rowIds": ["id1", "id2", "id3"],
  "fields": [
    {"id": "rating", "value": "5"}  // ❌ 所有记录都变成5星
  ]
}
```

**解决方案**: 使用单条更新或批量创建时分别指定

---

## 八、性能优化建议

### 8.1 查询优化

1. **合理使用分页**: pageSize不要超过1000
2. **指定返回字段**: 使用fields参数,只返回需要的字段
3. **使用字段ID**: 比别名查询性能更好
4. **避免过度嵌套**: Filter嵌套控制在2层以内
5. **善用视图**: 复杂筛选可先创建视图,再查询视图

---

### 8.2 批量操作优化

1. **批量创建**: 一次最多100条
2. **批量更新**: 一次最多100条
3. **异步处理**: 大批量操作使用队列异步处理

---

### 8.3 关联字段优化

1. **减少嵌套查询**: 使用 get_record_relations API 一次获取
2. **缓存关联数据**: 频繁访问的关联数据可缓存
3. **控制showFields**: 只显示必要字段,减少数据量

---

## 九、最佳实践总结

### 9.1 初始化阶段

**必做事项**:
1. 查询所有工作表结构
2. 缓存所有选项字段的key-value映射
3. 缓存工作表ID和字段ID
4. 建立用户姓名→ID映射

**示例代码逻辑**:
```javascript
// 1. 获取工作表结构
const structure = await getWorksheetStructure(worksheetId);

// 2. 提取选项字段映射
const optionMaps = {};
structure.fields.forEach(field => {
  if (field.type === 'SingleSelect' || field.type === 'MultipleSelect') {
    optionMaps[field.id] = {};
    field.options.forEach(opt => {
      optionMaps[field.id][opt.value] = opt.key;  // value → key
    });
  }
});

// 3. 使用时查找key
const customerTypeKey = optionMaps['customer_type']['成交客户'];
```

---

### 9.2 查询阶段

**建议**:
1. 优先使用字段ID而不是别名
2. 选项字段必须用key,提前转换
3. 数值字段value用字符串
4. 关联字段用 in 或 eq 操作符 + rowid 数组（belongsto 仅用于部门字段）
5. 合理设置pageSize(建议100-500)

---

### 9.3 写入阶段

**检查清单**:
- [ ] 选项字段value是数组格式
- [ ] 选项字段传的是key不是value
- [ ] 数值字段传数字类型
- [ ] 关联字段传的是rowid
- [ ] 成员字段传的是accountId
- [ ] 附件字段设置了type参数

---

### 9.4 错误处理

**常见错误码**:
- `error_code: 1` - 成功
- `error_code: -1` - 失败,查看error_msg
- `error_code: 4` - 权限不足
- `error_code: 10` - 参数错误

**建议**: 所有API调用都要检查error_code和success

---

## 十、完整示例:构建CRM应用

### 10.1 创建工作表

```bash
# 1. 创建客户表
POST /v3/app/worksheets
{
  "name": "客户信息表",
  "fields": [
    {"name": "客户名称", "type": "Text", "isTitle": true},
    {"name": "客户类型", "type": "SingleSelect", "options": [...]},
    {"name": "年度预算", "type": "Number", "precision": 2}
  ]
}

# 2. 创建机会表(关联客户)
POST /v3/app/worksheets
{
  "name": "销售机会表",
  "fields": [
    {"name": "机会名称", "type": "Text", "isTitle": true},
    {
      "name": "关联客户",
      "type": "Relation",
      "subType": "1",
      "dataSource": "{customer_table_id}"
    }
  ]
}
```

---

### 10.2 创建数据

```bash
# 1. 创建客户
POST /v3/app/worksheets/{customer_table_id}/rows
{
  "fields": [
    {"id": "customer_name", "value": "明道云科技"},
    {"id": "customer_type", "value": ["{成交客户key}"]},
    {"id": "annual_budget", "value": 1000000}
  ]
}

# 2. 创建机会(关联客户)
POST /v3/app/worksheets/{opportunity_table_id}/rows
{
  "fields": [
    {"id": "opportunity_name", "value": "年度续费"},
    {"id": "related_customer", "value": ["{customer_rowid}"]}
  ]
}
```

---

### 10.3 查询分析

```bash
# 1. 查询重点客户
POST /v3/app/worksheets/{customer_table_id}/rows/list
{
  "filter": {
    "type": "group",
    "logic": "AND",
    "children": [
      {"type": "condition", "field": "customer_type", "operator": "eq", "value": ["{成交key}"]},
      {"type": "condition", "field": "annual_budget", "operator": "gte", "value": ["500000"]}
    ]
  }
}

# 2. 按行业统计客户
POST /v3/app/worksheets/{customer_table_id}/rows/pivot
{
  "rows": [{"field": "industry"}],
  "values": [
    {"field": "rowid", "aggregation": "COUNT"},
    {"field": "annual_budget", "aggregation": "SUM"}
  ]
}
```

---

## 附录A:字段类型速查表

| 类型 | type值 | 写入格式 | 读取格式 | 关键参数 |
|-----|--------|---------|---------|---------|
| 文本 | Text | 字符串 | 字符串 | - |
| 数值 | Number | 数字 | 字符串 | precision |
| 单选 | SingleSelect | 数组[key] | 对象数组 | options |
| 多选 | MultipleSelect | 数组[key...] | 对象数组 | options |
| 日期 | Date | 字符串 | 字符串 | subType |
| 时间 | Time | 字符串 | 字符串 | subType |
| 成员 | Collaborator | 数组[id] | 对象/数组 | subType |
| 关联 | Relation | 数组[rowid] | 对象/数组 | dataSource, subType |
| 附件 | Attachment | 对象数组 | 对象数组 | - |
| 等级 | Rating | 字符串 | 字符串 | max |

---

## 附录B:操作符速查表

| 操作符 | 适用字段 | value格式 | 说明 |
|-------|---------|----------|------|
| eq | 所有 | ["值"] | 等于 |
| ne | 所有 | ["值"] | 不等于 |
| contains | Text, Multi | ["值"] | 包含 |
| startswith | Text | ["值"] | 开头是 |
| gt/gte/lt/lte | Number, Date | ["值"] | 比较 |
| between | Number, Date | ["最小", "最大"] | 范围 |
| isempty | 所有 | 无 | 为空 |
| in / eq | Relation | ["rowid"...] | 关联字段筛选（value = 关联记录 rowid 数组）|
| belongsto | 部门(Department) | ["部门id"...] | 属于（仅部门字段）|

---

## 附录C:错误排查清单

**筛选无结果**:
- [ ] 选项字段是否用了key而不是value?
- [ ] 数值字段value是否用了字符串?
- [ ] 关联字段是否用了 in 或 eq + rowid 数组？(belongsto 仅用于部门字段)
- [ ] Filter嵌套是否超过2层?
- [ ] 字段ID是否正确?

**创建/更新失败**:
- [ ] 必填字段是否都提供了?
- [ ] 关联字段的dataSource是否存在?
- [ ] 选项字段的key是否有效?
- [ ] 成员字段的accountId是否有效?
- [ ] 数值字段是否超出范围?

**数据异常**:
- [ ] 附件是否等待了5-10秒?
- [ ] 日期精度subType是否正确?
- [ ] 关联记录是否已删除?

---

**文档版本**: v1.0
**生成时间**: 2026-01-11
**基于**: HAP API V3
**测试验证**: 完整CRM应用场景测试
