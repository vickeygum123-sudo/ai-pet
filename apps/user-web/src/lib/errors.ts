import { ApiRequestError } from "./api";

export interface UiErrorState {
  title: string;
  body: string;
  supportCode?: string;
}

export function describeUiError(
  error: unknown,
  context: "account-create" | "account-login" | "account-read" | "bind" | "unbind" | "generic",
): UiErrorState {
  if (error instanceof ApiRequestError) {
    switch (error.code) {
      case "AUTH_HEADER_REQUIRED":
        return {
          title: "账号会话已失效",
          body: "当前 MVP 仍使用 X-Account-Id 作为开发占位登录态。请重新进入账号占位页，重新建立会话后再继续。",
          supportCode: error.code,
        };
      case "ACCOUNT_CONFLICT":
        return {
          title: "账号占位创建失败",
          body: "这个 auth subject 已经被创建过了。你可以换一个 subject 再试，或直接用已有 accountId 进入占位登录。",
          supportCode: error.code,
        };
      case "BIND_TARGET_UNAVAILABLE":
        return {
          title: "设备暂时无法绑定",
          body: "配对码无效，或者设备已经被其他账号占用。请先核对包装上的 pairing code，再确认设备当前处于 pairing-ready 状态。",
          supportCode: error.code,
        };
      case "VALIDATION_ERROR":
        return {
          title: "输入信息还不完整",
          body: error.message,
          supportCode: error.code,
        };
      case "NOT_FOUND":
        return {
          title: context === "account-read" ? "账号不存在" : "目标资源不存在",
          body: error.message,
          supportCode: error.code,
        };
      case "CONFLICT":
        return {
          title: context === "bind" ? "设备当前不能继续绑定" : "当前操作发生冲突",
          body: error.message,
          supportCode: error.code,
        };
      default:
        return {
          title: "请求没有成功",
          body: error.message,
          supportCode: error.code,
        };
    }
  }

  if (error instanceof TypeError) {
    return {
      title: "网络连接失败",
      body: "前端没有连到后端服务。请确认 API 地址和本地后端是否已启动。",
    };
  }

  return {
    title: "发生了未识别问题",
    body: "这次失败没有拿到稳定错误码，请结合控制台日志继续排查。",
  };
}
