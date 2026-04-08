import { Panel } from "./ui";

export type SetupStepKey = "start" | "account" | "wifi" | "bind" | "success";

const steps: Array<{ key: SetupStepKey; label: string; helper: string }> = [
  {
    key: "start",
    label: "入口确认",
    helper: "从包装二维码或 URL 进入 setup 页面。",
  },
  {
    key: "account",
    label: "账号占位",
    helper: "MVP 先建立一个开发占位账号会话。",
  },
  {
    key: "wifi",
    label: "Wi‑Fi 引导",
    helper: "这里只做用户引导，不伪造真实配网闭环。",
  },
  {
    key: "bind",
    label: "设备绑定",
    helper: "通过 pairing code 调用冻结的 bind API。",
  },
  {
    key: "success",
    label: "完成与首聊",
    helper: "绑定成功后，立刻提示进入第一次对话。",
  },
];

export function SetupProgress({ current }: { current: SetupStepKey }) {
  return (
    <Panel
      title="Setup 进度"
      description="对齐 MVP-T6 冻结主线，不扩展到支付、角色市场或固件细节。"
    >
      <ol className="setup-progress-list">
        {steps.map((step) => {
          const state =
            step.key === current
              ? "current"
              : steps.findIndex((item) => item.key === current) >
                  steps.findIndex((item) => item.key === step.key)
                ? "done"
                : "upcoming";

          return (
            <li className={`setup-progress-item setup-progress-${state}`} key={step.key}>
              <div className="setup-progress-marker" aria-hidden="true" />
              <div>
                <p className="setup-progress-label">{step.label}</p>
                <p className="setup-progress-helper">{step.helper}</p>
              </div>
            </li>
          );
        })}
      </ol>
    </Panel>
  );
}
