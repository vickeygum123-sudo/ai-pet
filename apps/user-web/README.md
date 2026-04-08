# User Web MVP

MVP 用户网页工程，范围只覆盖：

- 账号创建 / 登录占位
- onboarding 落地页
- Wi-Fi 配网引导态
- 设备绑定
- 绑定成功页
- 基础 account / device 页面

不包含：

- 管理后台
- AI 编排逻辑
- 固件实现
- 正式订阅支付
- shared types 落地

## 当前路由

- `/setup`
- `/setup/account`
- `/setup/wifi`
- `/setup/bind`
- `/setup/success`
- `/account`
- `/devices/:deviceId`

## 当前依赖的后端接口

- `POST /v1/accounts`
- `GET /v1/accounts/me`
- `POST /v1/device-bindings`
- `DELETE /v1/device-bindings/{deviceId}`
- `GET /v1/entitlements/me`

## 明确写死的边界

- 登录态仍然使用 MVP 开发占位 header `X-Account-Id`
- Wi-Fi 页面只做“引导态”，不伪造真实配网闭环
- device 页面目前没有用户侧设备详情接口可读，只能展示最近一次绑定成功后缓存下来的本地快照
- setup 埋点目前只做前端本地 stub，不向后端发送事件
- 不消费任何 admin API

## 建议运行方式

1. 安装 Node.js 与 npm。
2. 在 `apps/user-web` 下安装依赖。
3. 配置 `.env`，至少提供 `VITE_API_BASE_URL`。
4. 启动 Vite 开发服务器。

本地环境当前缺少 `node` / `npm`，所以这次提交只完成工程与页面代码落地，没有执行前端构建和自动化测试。
