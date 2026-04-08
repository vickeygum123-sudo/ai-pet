import { ApiRequestError } from "./api";

export interface UiErrorState {
  title: string;
  body: string;
  supportCode?: string;
}

export function describeUiError(error: unknown): UiErrorState {
  if (error instanceof ApiRequestError) {
    return {
      title: "管理后台请求失败",
      body: error.message,
      supportCode: error.code,
    };
  }

  if (error instanceof TypeError) {
    return {
      title: "无法连接后端服务",
      body: "请确认本地后端是否已启动，以及 VITE_API_BASE_URL 是否正确。",
    };
  }

  return {
    title: "发生了未识别问题",
    body: "这次失败没有拿到稳定错误码，请结合浏览器控制台继续排查。",
  };
}
