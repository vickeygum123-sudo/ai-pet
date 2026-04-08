import { useState } from "react";
import { Link, useNavigate, useParams } from "react-router";

import { Callout, DefinitionList, PageScaffold, Panel, StatusPill } from "../components/ui";
import { unbindDevice } from "../lib/api";
import { describeUiError, type UiErrorState } from "../lib/errors";
import { formatDateTime } from "../lib/format";
import { clearBindingCache, getAccountSession, getBindingCache } from "../lib/storage";

export function DevicePage() {
  const navigate = useNavigate();
  const { deviceId = "" } = useParams();
  const accountSession = getAccountSession();
  const bindingCache = getBindingCache();
  const deviceSnapshot = bindingCache?.binding.deviceId === deviceId ? bindingCache : null;
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<UiErrorState | null>(null);

  async function handleUnbind() {
    if (!accountSession || !deviceSnapshot) {
      return;
    }

    setBusy(true);
    setError(null);

    try {
      await unbindDevice(accountSession.accountId, deviceSnapshot.binding.deviceId);
      clearBindingCache();
      navigate("/account");
    } catch (cause) {
      setError(describeUiError(cause, "unbind"));
    } finally {
      setBusy(false);
    }
  }

  return (
    <PageScaffold
      eyebrow="Device"
      title="基础 device 页面"
      description="这里暂时不是后端权威设备详情页，只能展示最近一次 bind 成功后缓存在浏览器中的最小快照，并提供 unbind 入口。"
    >
      <Callout tone="warning" title="设备详情接口仍然缺位">
        <p>当前后端没有用户侧 device detail / device list API，所以这里不会调用 admin API，也不会伪造实时设备状态。</p>
      </Callout>

      {!deviceSnapshot ? (
        <Panel title="没有可展示的设备快照" description="这通常意味着当前浏览器还没完成过一次成功绑定，或者本地缓存已被清掉。">
          <div className="action-row">
            <Link className="button" to="/setup/bind">
              重新进入绑定页
            </Link>
            <Link className="button button-secondary" to="/account">
              返回 account
            </Link>
          </div>
        </Panel>
      ) : (
        <>
          <Panel
            title="本地缓存的设备快照"
            description="这些字段来自 bind 成功响应 + 本地 onboarding 记录，不代表用户侧实时设备详情。"
            actions={<StatusPill tone="info">Local Snapshot</StatusPill>}
          >
            <DefinitionList
              items={[
                { label: "Device ID", value: deviceSnapshot.binding.deviceId },
                { label: "Binding ID", value: deviceSnapshot.binding.bindingId },
                { label: "Bind Status", value: deviceSnapshot.binding.status },
                { label: "Bound At", value: formatDateTime(deviceSnapshot.binding.boundAt) },
                { label: "Pairing Code", value: deviceSnapshot.pairingCode || "未记录" },
                { label: "Wi‑Fi 名称", value: deviceSnapshot.wifiName || "未记录" },
                { label: "设备备注", value: deviceSnapshot.deviceNotes || "未记录" },
                { label: "缓存时间", value: formatDateTime(deviceSnapshot.cachedAt) },
              ]}
            />
          </Panel>

          {!accountSession ? (
            <Callout tone="warning" title="当前没有账号占位会话">
              <p>如果你要执行 unbind，需要先重新建立当前设备所属账号的 account session。</p>
            </Callout>
          ) : (
            <Panel title="设备解绑" description="当前对齐冻结接口 `DELETE /v1/device-bindings/{deviceId}`。">
              <p>解绑成功后，本地缓存也会一并清掉，account 页面将不再展示这个设备入口。</p>
              <div className="action-row">
                <button className="button button-secondary" disabled={busy} onClick={handleUnbind} type="button">
                  {busy ? "解绑中..." : "解绑这台设备"}
                </button>
              </div>
            </Panel>
          )}
        </>
      )}

      {error ? (
        <Callout tone="warning" title={error.title}>
          <p>{error.body}</p>
          {error.supportCode ? <p>支持码：{error.supportCode}</p> : null}
        </Callout>
      ) : null}
    </PageScaffold>
  );
}
