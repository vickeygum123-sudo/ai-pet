# Admin Console MVP

MVP 管理后台工程，范围只覆盖：

- overview dashboard
- device list
- session list
- session detail
- failure breakdown
- review queue skeleton

不包含：

- 用户前端页面
- AI 编排逻辑
- 固件实现
- 正式订阅支付
- shared types 落地

## 当前路由

- `/overview`
- `/devices`
- `/sessions`
- `/sessions/:sessionId`
- `/failures`
- `/review-queue`

## 当前依赖的后端接口

- `GET /v1/admin/overview`
- `GET /v1/admin/devices`
- `GET /v1/admin/sessions`
- `GET /v1/admin/sessions/{sessionId}`

## 明确边界

- 只使用冻结的 admin query 字段，不新增 contract 字段假设
- failure breakdown 由 session list 前端聚合而成，不要求新接口
- review queue 目前是 MVP skeleton：根据 `safetyFlag`、`fallbackUsed`、`state=fallback`、`failureCode=SAFETY_BLOCKED` 生成候选列表
- `setup failures by step`、正式 review workflow、人工标注结果目前都缺少后端能力支持，因此只展示缺口说明

## 建议运行方式

1. 安装 Node.js 与 npm。
2. 在 `apps/admin-console` 下安装依赖。
3. 配置 `.env`，至少提供 `VITE_API_BASE_URL`。
4. 启动 Vite 开发服务器。

当前环境缺少 `node` / `npm`，所以这次提交只完成工程与页面代码落地，没有执行前端构建和自动化测试。
