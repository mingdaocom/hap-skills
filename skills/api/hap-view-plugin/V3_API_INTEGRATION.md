# HAP 视图插件中使用 V3 接口

本文档是 [hap-view-plugin](./SKILL.md) 技能的补充说明,介绍如何在视图插件中使用 HAP V3 接口。

## 数据操作方式对比

明道云 HAP 视图插件支持两种数据操作方式:

### 1. 使用插件函数和组件 (mdye API)

**适用场景:** 视图插件内的标准数据操作

**特点:**
- ✅ 已封装好鉴权,开箱即用
- ✅ 自动处理权限和上下文
- ✅ 提供完整的 TypeScript 类型定义
- ✅ 与明道云原生 UI 组件集成

**示例:**
```javascript
import { api, utils, config } from 'mdye';

// 获取数据
const result = await api.getFilterRows({ worksheetId, viewId });

// 打开记录详情
await utils.openRecordInfo({ appId, worksheetId, viewId, recordId });
```

### 2. 使用 HAP V3 接口 (REST API)

**适用场景:**
- 需要调用 mdye 未封装的接口
- 独立前端页面开发
- 跨应用数据操作
- 自定义复杂业务逻辑

**特点:**
- ✅ 完整的 RESTful API
- ✅ 支持所有明道云功能
- ✅ 可在任何环境使用(插件/独立页面)
- ⚠️ 需要手动配置鉴权(Appkey & Sign)

## 在视图插件中使用 V3 接口

### 方案1: 使用 mdye 封装的 api

推荐优先使用 `mdye` 提供的 API:

```javascript
import { api, config } from 'mdye';

const { appId, worksheetId, viewId } = config;

// 已包含鉴权,直接调用
const result = await api.getFilterRows({
  worksheetId,
  viewId,
  pageSize: 50
});
```

### 方案2: 直接调用 V3 接口

当需要调用 mdye 未封装的接口时:

```javascript
// 配置鉴权信息 (从 MCP 配置中获取)
const API_CONFIG = {
  appkey: '你的Appkey',
  sign: '你的Sign'
};

// 封装请求函数
async function callV3API(endpoint, method = 'GET', body = null) {
  const headers = {
    'Content-Type': 'application/json',
    'HAP-Appkey': API_CONFIG.appkey,
    'HAP-Sign': API_CONFIG.sign
  };

  const options = {
    method,
    headers
  };

  if (body) {
    options.body = JSON.stringify(body);
  }

  const response = await fetch(
    `https://api.mingdao.com${endpoint}`,
    options
  );

  return await response.json();
}

// 使用示例
const optionSets = await callV3API('/v3/app/optionsets', 'GET');
const roles = await callV3API('/v3/app/roles', 'GET');
```

## 常用 V3 接口

### 应用管理
- `GET /v3/app` - 获取应用信息
- `POST /v3/app/worksheets/list` - 获取工作表列表
- `GET /v3/app/worksheets/{worksheet_id}` - 获取工作表详情

### 数据查询
- `POST /v3/app/worksheets/{worksheet_id}/rows/list` - 获取记录列表
- `GET /v3/app/worksheets/{worksheet_id}/rows/{row_id}` - 获取记录详情
- `GET /v3/app/worksheets/{worksheet_id}/rows/{row_id}/relations/{field}` - 获取关联记录

### 数据操作
- `POST /v3/app/worksheets/{worksheet_id}/rows` - 创建记录
- `PUT /v3/app/worksheets/{worksheet_id}/rows/{row_id}` - 更新记录
- `DELETE /v3/app/worksheets/{worksheet_id}/rows/batch` - 删除记录

### 选项集和角色
- `GET /v3/app/optionsets` - 获取选项集列表
- `GET /v3/app/optionsets/{optionset_id}` - 获取选项集详情
- `GET /v3/app/roles` - 获取角色列表
- `GET /v3/app/roles/{role_id}/members` - 获取角色成员

### 用户和部门
- `POST /v3/users/lookup` - 查询用户
- `POST /v3/departments/lookup` - 查询部门
- `GET /v3/regions` - 获取地区列表

## 获取鉴权密钥

### 从 MCP 配置中提取

MCP 配置示例:
```json
{
  "hap-mcp-MEGA CRM": {
    "url": "https://api.mingdao.com/mcp?HAP-Appkey=你的Appkey&HAP-Sign=你的Sign",
    "type": "sse"
  }
}
```

提取出:
- **Appkey**: `你的Appkey`
- **Sign**: `你的Sign`

**重要:** 这套密钥同时适用于:
- MCP 服务器访问
- V3 接口调用
- 视图插件开发

## 完整示例

### 示例1: 获取并展示选项集

```javascript
import React, { useState, useEffect } from 'react';
import { config } from 'mdye';

const API_CONFIG = {
  appkey: '你的Appkey',
  sign: '你的Sign'
};

function OptionSetList() {
  const [optionSets, setOptionSets] = useState([]);

  useEffect(() => {
    loadOptionSets();
  }, []);

  async function loadOptionSets() {
    const headers = {
      'Content-Type': 'application/json',
      'HAP-Appkey': API_CONFIG.appkey,
      'HAP-Sign': API_CONFIG.sign
    };

    const response = await fetch(
      'https://api.mingdao.com/v3/app/optionsets',
      { method: 'GET', headers }
    );

    const result = await response.json();
    setOptionSets(result.optionSets || []);
  }

  return (
    <div>
      <h2>选项集列表</h2>
      <ul>
        {optionSets.map(optionSet => (
          <li key={optionSet.optionSetId}>
            {optionSet.optionSetName}
          </li>
        ))}
      </ul>
    </div>
  );
}

export default OptionSetList;
```

### 示例2: 跨应用数据查询

```javascript
async function getWorksheetData(worksheetId) {
  const headers = {
    'Content-Type': 'application/json',
    'HAP-Appkey': API_CONFIG.appkey,
    'HAP-Sign': API_CONFIG.sign
  };

  // 获取工作表结构
  const structureResponse = await fetch(
    `https://api.mingdao.com/v3/app/worksheets/${worksheetId}`,
    { method: 'GET', headers }
  );
  const structure = await structureResponse.json();

  // 获取记录列表
  const rowsResponse = await fetch(
    `https://api.mingdao.com/v3/app/worksheets/${worksheetId}/rows/list`,
    {
      method: 'POST',
      headers,
      body: JSON.stringify({
        pageIndex: 1,
        pageSize: 100
      })
    }
  );
  const { rows } = await rowsResponse.json();

  return {
    structure,
    rows
  };
}
```

## 选择建议

1. **优先使用 mdye API**
   - 如果功能已封装,优先使用以减少开发量
   - 享受自动鉴权和类型提示

2. **补充使用 V3 接口**
   - 当需要 mdye 未提供的功能时使用
   - 例如:选项集管理、角色管理、用户查询等

3. **独立页面开发**
   - 只能使用 V3 接口编排数据操作
   - 需要自行处理鉴权和错误

## 更多资源

- **完整 V3 接口文档**: 查看 `hap-apiv3-data` 技能文档
- **筛选器使用规范**: 参考 `hap-apiv3-data` 技能中的筛选器章节
- **API 文档查询**: 使用 Apifox MCP Server 查询完整 API 结构

```json
{
  "HAP-应用API文档": {
    "command": "npx -y apifox-mcp-server@latest --site-id=5442569",
    "args": [],
    "env": {},
    "type": "stdio"
  }
}
```
