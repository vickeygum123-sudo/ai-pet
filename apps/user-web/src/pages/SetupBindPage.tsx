import { type FormEvent, useState } from "react";
import { Link, useNavigate } from "react-router";

import { SetupProgress } from "../components/SetupProgress";
import { Callout, Field, PageScaffold, Panel } from "../components/ui";
import { bindDevice } from "../lib/api";
import { describeUiError, type UiErrorState } from "../lib/errors";
import {
  clearOnboardingDraft,
  getAccountSession,
  getOnboardingDraft,
  setBindingCache,
} from "../lib/storage";
import { trackSetupEvent } from "../lib/telemetry";

export function SetupBindPage() {
  const navigate = useNavigate();
  const accountSession = getAccountSession();
  const draft = getOnboardingDraft();
  const [pairingCode, setPairingCode] = useState(draft?.pairingCode ?? "");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<UiErrorState | null>(null);

  async function handleBind(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();

    if (!accountSession) {
      setError({
        title: "缺少账号上下文",
        body: "先完成账号占位，再继续 bind。",
      });
      return;
    }

    setBusy(true);
    setError(null);

    try {
      const binding = await bindDevice(accountSession.accountId, pairingCode.trim());

      setBindingCache({
        binding,
        pairingCode: pairingCode.trim(),
        wifiName: draft?.wifiName ?? "",
        deviceNotes: draft?.deviceNotes ?? "",
        cachedAt: new Date().toISOString(),
      });
      clearOnboardingDraft();
      trackSetupEvent("device_bound", {
        accountId: binding.accountId,
        deviceId: binding.deviceId,
      });
      navigate("/setup/success");
    } catch (cause) {
      setError(describeUiError(cause, "bind"));
      trackSetupEvent("setup_failed", { stage: "bind" });
    } finally {
      setBusy(false);
    }
  }

  return (
    <PageScaffold
      eyebrow="Setup / Bind"
      title="用 pairing code 完成设备绑定"
      description="这一页是当前用户主线里唯一真正调用冻结后端接口的 setup 动作。成功后会拿到 binding record，并跳转到 success 页面。"
      sidebar={<SetupProgress current="bind" />}
    >
      <Callout tone="info" title="这里依赖的冻结接口">
        <p>当前只调用 `POST /v1/device-bindings`，请求体只有 `pairingCode`，账号上下文通过 `X-Account-Id` 占位 header 传递。</p>
      </Callout>

      {!accountSession ? (
        <Callout tone="warning" title="无法发起绑定">
          <p>当前浏览器里没有 account session，所以 bind 请求不会成功。请先回到账号占位页。</p>
          <div className="action-row">
            <Link className="button" to="/setup/account">
              先去建立账号会话
            </Link>
          </div>
        </Callout>
      ) : null}

      <Panel title="绑定信息" description="如果上一页已经填写过 pairing code，这里会自动带入。">
        <form className="stack-form" onSubmit={handleBind}>
          <Field
            autoComplete="off"
            hint="后端当前会把无效 pairing code 和已被占用设备都映射成 409 / BIND_TARGET_UNAVAILABLE。"
            label="Pairing Code"
            onChange={(event) => setPairingCode(event.target.value.toUpperCase())}
            placeholder="PAIR-001"
            required
            value={pairingCode}
          />
          {draft?.wifiName ? (
            <div className="summary-card">
              <p>本地记录的 Wi‑Fi：{draft.wifiName}</p>
              {draft.deviceNotes ? <p>设备备注：{draft.deviceNotes}</p> : null}
            </div>
          ) : null}
          <div className="action-row">
            <button className="button" disabled={!accountSession || busy} type="submit">
              {busy ? "绑定中..." : "绑定这台设备"}
            </button>
            <Link className="button button-secondary" to="/setup/wifi">
              返回 Wi‑Fi 引导
            </Link>
          </div>
        </form>
      </Panel>

      {error ? (
        <Callout tone="warning" title={error.title}>
          <p>{error.body}</p>
          {error.supportCode ? <p>支持码：{error.supportCode}</p> : null}
        </Callout>
      ) : null}
    </PageScaffold>
  );
}
