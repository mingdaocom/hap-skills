# HAP V3 API 使用技能

## 简介

这是一个专业的技能，用于使用明道云 HAP V3 接口进行数据操作和页面开发。提供完整的 API 使用指南、最佳实践和常见问题解决方案。

## 适用场景

- ✅ 在自定义视图插件中调用 V3 接口操作数据
- ✅ 在独立前端页面中使用 V3 接口编排业务逻辑
- ✅ 实时获取和操作明道云应用中的数据
- ✅ 数据迁移和批量操作
- ✅ 构建基于 HAP 的完整应用

## 核心能力

1. **完整的 API 使用工作流**
   - 从零搭建应用到数据操作的完整流程
   - 详细的字段类型处理规范
   - Filter 筛选器完整语法

2. **关联字段深度查询**
   - 关联字段的创建和使用
   - 批量查询优化（避免 N+1 问题）
   - 获取关联记录的完整数据

3. **常见陷阱和解决方案**
   - 选项字段筛选必须使用 key（UUID）
   - 数值字段筛选 value 必须是字符串数组
   - 关联字段使用 in 或 eq 操作符（value 为 rowid 数组）

4. **性能优化最佳实践**
   - 查询优化建议
   - 批量操作优化
   - 关联字段优化

## 使用方法

当用户提到以下关键词时，会自动触发此技能：

- "HAP V3 接口"
- "HAP API"
- "接口调用"
- "数据接口"
- "Appkey"
- "Sign"
- "接口鉴权"

## 核心文档

### 主要文档

- **`SKILL.md`** - 技能主文档
  - 快速开始指南
  - 核心工作流程
  - Filter 筛选器规范
  - 字段类型处理规范
  - 常见陷阱与解决方案
  - 性能优化建议

- **`references/hap-api-usage-guide.md`** - HAP V3 API 使用规范完整指南
  - 详细的 API 使用流程（从零搭建应用到数据操作）
  - 字段类型参数详解
  - 创建/更新记录规范（triggerWorkflow 详解）
  - 查询筛选规范（Filter 对象结构、操作符列表）
  - 数据透视分析规范
  - 关联字段完整指南
  - 常见陷阱与解决方案
  - 性能优化建议
  - 最佳实践总结

## 关键要点

### 1. 选项字段筛选必须使用 key（UUID）

```javascript
// ❌ 错误
value: ["成交客户"]  // 显示文本

// ✅ 正确
value: ["74c7b607-864d-4cc4-b401-28acba2636e9"]  // 选项key
```

### 2. 数值字段筛选 value 必须是字符串数组

```javascript
// ❌ 错误
value: [1000000]  // 数字类型

// ✅ 正确
value: ["1000000"]  // 字符串数组
```

### 3. 关联字段使用 in 或 eq 操作符

```javascript
// ❌ 错误
operator: "belongsto"  // V3 API 无 belongsto 运算符

// ✅ 正确
operator: "in"  // 关联字段用 in（多值）或 eq（单值），value 为 rowid 数组
```

### 4. triggerWorkflow 参数

- `true` - 正常业务操作（默认）
- `false` - 数据迁移、批量初始化、测试数据

## 文件结构

```
hap-apiv3-data/
├── SKILL.md                          # 技能主文档
├── README.md                          # 本文件
└── references/
    └── hap-api-usage-guide.md         # HAP V3 API 使用规范完整指南
```

## 参考资源

### 在线文档

- [API 整体介绍](https://apifox.mingdao.com/7271706m0.md)
- [字段类型对照表](https://apifox.mingdao.com/7271709m0.md)
- [筛选器使用指南](https://apifox.mingdao.com/7271713m0.md)
- [错误码说明](https://apifox.mingdao.com/7271715m0.md)

### 相关技能

- **HAP 前后端项目搭建指南** - 使用 HAP 作为数据库搭建独立网站
- **HAP MCP 使用指南** - 了解如何使用 HAP MCP 进行应用管理
- **HAP 视图插件开发指南** - 开发 HAP 自定义视图插件

## 版本信息

- **技能版本**: v2.0
- **最后更新**: 2026-01-11
- **基于**: HAP API V3
- **详细规范**: 参考 `references/hap-api-usage-guide.md`
