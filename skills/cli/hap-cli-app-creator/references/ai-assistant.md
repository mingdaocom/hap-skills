# AI Assistant — AI 助手（chatbot）

AI 助手写在顶层 `chatbots[]`。仅在有智能问答 / 数据查询 / 辅助分析需求时规划，不强制。

```jsonc
"chatbots": [
  { "name": "仓储助手",
    "section": "分析",
    "prompt": "你是仓储管理助手。回答库存、出入库、预警相关问题，引用应用内数据，用简洁中文作答。",
    "description": "面向仓管员的智能问答与数据查询助手",
    "greeting": "你好，我是仓储助手。可以问我库存水位、今日出入库、预警物料等。",
    "preset_questions": [ "现在有哪些物料低于安全库存？", "本月出库总量是多少？", "哪个仓库最满？" ] }
]
```

## 键

- `name`(**必填**，逻辑名唯一)。
- `section`：所属分组逻辑名（省略默认第一个分组）。**建议明确给 section**，让助手进导航。
- `prompt`：系统提示词，定义助手行为（省略则用 description）。**建议明确写**，决定回答质量。
- `description`：助手用途描述。
- `greeting`：开场白。
- `preset_questions`：预设引导问题数组。**建议给 3 条左右**，贴合该应用的真实数据场景。

## 写好 prompt 与 preset_questions

- prompt 要交代**角色定位 + 数据范围 + 作答风格**（中文、简洁、引用应用内数据）。
- preset_questions 用**该应用真实存在的工作表/字段语义**提问（「低于安全库存的物料」「本月出库总量」），
  不要泛泛的「你能做什么」。
- 不在 prompt/greeting 里泄露内部实现（API、控件名、模块名）。

> 强约束：chatbot **必须带 section、prompt、preset_questions** 才是一个完整可用的助手（name 之外都建议补全）。

## 角色访问权限

AI 助手默认对**所有角色**开放——建好助手后，每个角色都能访问，无需在角色里单独配置。
只有当某个角色（如外部访客）**不应**使用某助手时，才在该角色的 `chatbot_permissions`
里用白名单收紧（见 [roles.md](roles.md)）。
