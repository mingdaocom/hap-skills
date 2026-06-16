# 场景：修复建到一半出错的应用

目标：一个应用生成中途失败（缺表、缺字段、视图名错、角色没建全），把它补齐到可用状态。

## 总思路

先**盘点差异**（期望结构 vs 实际结构），再**按依赖顺序补**：表 → 字段 → 视图 → 角色/权限 → 工作流 → 页面。每补一层都验证后再进下一层，避免在错误地基上继续叠。

## 命令序列

```bash
# 1. 盘点现状
hap app-editor inspect <appId>          # 一眼看出缺哪些表/视图/角色/页面
hap --json worksheet fields <ws_id>     # 逐表核对字段是否齐

# 2. 补缺的表（单条命令）
hap worksheet create <appId> "退货单" --section-id <section_id>

# 3. 补缺的字段（edit-spec,可一份 spec 串多个 op,后面的能引用前面建的）
cat > fix-fields.edit.json <<'EOF'
{ "app": "<appId>", "ops": [
  { "type": "field.add", "worksheet": "退货单",
    "field": { "name": "退货原因", "type": "Text" } },
  { "type": "field.add", "worksheet": "退货单",
    "field": { "name": "状态", "type": "SingleSelect",
               "options": ["待处理", "已完成"] } } ] }
EOF
hap app-editor validate fix-fields.edit.json && hap app-editor apply fix-fields.edit.json

# 4. 修错名的视图 / 补视图
hap worksheet view update <ws_id> <view_id> --name "正确的名字"
hap worksheet view create <ws_id> "按状态" --view-type board --group-control <statusCtrlId>

# 5. 补角色与权限
hap app role list -a <appId>
hap app role create -a <appId> --name "处理员" --description "处理退货" \
  --type 0 --permission-scope 20
hap app role add-member <role_id> --user-ids <accountId> -a <appId>

# 6. 工作流没发布的发布掉
hap --json workflow list <appId>        # enabled=false 的逐个检查
hap workflow publish <process_id>

# 7. 终检
hap app-editor inspect <appId>          # 结构齐了
```

## 注意

- **顺序就是依赖**：视图引用字段、权限引用表和页面、工作流引用字段——缺哪层先补哪层的上游。
- 半成品里可能有「建了一半的脏元素」（空表、错名视图）：删除是破坏性操作，逐个跟用户确认后再 `--yes` / `confirm:true`。
- 发布工作流失败，多半是节点里引用了当时不存在的字段/收件人——按 [workflow-node-rework.md](workflow-node-rework.md) 读出节点照形修。
