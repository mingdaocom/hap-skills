# role / permission ops

- `role.create` — `{name, [description], [permission_scope], [hide_app_for_members],
  [global_permissions], [worksheet_permissions], [page_permissions]}`
  permission_scope：80=全部可查看编辑删除；60=查看全部/仅改自己；30=仅加入项；20=仅查看；
  0=逐项权限。**默认 20**。**scope 0 必须带非空 worksheet_permissions**，否则后端报 10002。
- `role.update` — `{role:"<名|id>", [rename], [permissions:{…}], [permission_way]}`
  rename 走 GetRoleDetail→EditAppRole 读改写。
- `role.delete` — `{role, confirm:true}`
- `role.add_member` / `role.remove_member` — `{role, members:{[user_ids],[department_ids],
  [department_tree_ids],[job_ids],[org_role_ids]}}`
