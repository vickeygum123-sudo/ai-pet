import { useEffect, useState } from "react";
import { Link, useNavigate } from "react-router";

import { Callout, DefinitionList, PageScaffold, Panel, StatusPill } from "../components/ui";
import { getAccountMe, getEntitlement, type Account, type EntitlementSnapshot } from "../lib/api";
import { describeUiError, type UiErrorState } from "../lib/errors";
import { formatDateTime, formatNullableText } from "../lib/format";
import {
  clearAccountSession,
  clearBindingCache,
  clearOnboardingDraft,
  getAccountSession,
  getBindingCache,
} from "../lib/storage";

export function AccountPage() {
  const navigate = useNavigate();
  const accountSession = getAccountSession();
  const bindingCache = getBindingCache();
  const [account, setAccount] = useState<Account | null>(null);
  const [entitlement, setEntitlement] = useState<EntitlementSnapshot | null>(null);
  const [loading, setLoading] = useState(Boolean(accountSession));
  const [error, setError] = useState<UiErrorState | null>(null);

  useEffect(() => {
    let cancelled = false;

    if (!accountSession) {
      setLoading(false);
      return;
    }

    setLoading(true);
    setError(null);

    Promise.all([
      getAccountMe(accountSession.accountId),
      getEntitlement(accountSession.accountId),
    ])
      .then(([nextAccount, nextEntitlement]) => {
        if (cancelled) {
          return;
        }

        setAccount(nextAccount);
        setEntitlement(nextEntitlement);
      })
      .catch((cause) => {
        if (cancelled) {
          return;
        }

        setError(describeUiError(cause, "account-read"));
      })
      .finally(() => {
        if (!cancelled) {
          setLoading(false);
        }
      });

    return () => {
      cancelled = true;
    };
  }, [accountSession?.accountId]);

  function handleClearPlaceholderSession() {
    clearAccountSession();
    clearBindingCache();
    clearOnboardingDraft();
    navigate("/setup/account");
  }

  return (
    <PageScaffold
      eyebrow="Account"
      title="账号与订阅占位视图"
      description="这里先展示 MVP 已冻结的账号字段和 entitlement snapshot，不引入正式支付逻辑，也不扩展到订阅购买闭环。"
    >
      <Callout tone="warning" title="当前还是占位 auth">
        <p>这个 account 页面依赖本地保存的 `X-Account-Id` 占位会话，不代表正式登录态。</p>
      </Callout>

      {!accountSession ? (
        <Panel title="还没有账号会话" description="先进入 setup account 页面，建立一个可用的 account context。">
          <div className="action-row">
            <Link className="button" to="/setup/account">
              去建立账号会话
            </Link>
          </div>
        </Panel>
      ) : null}

      {loading ? (
        <Panel title="读取账号信息中" description="正在并行请求 account profile 和 entitlement snapshot。">
          <p>请稍候...</p>
        </Panel>
      ) : null}

      {error ? (
        <Callout tone="warning" title={error.title}>
          <p>{error.body}</p>
          {error.supportCode ? <p>支持码：{error.supportCode}</p> : null}
        </Callout>
      ) : null}

      {account ? (
        <Panel
          title="账号信息"
          description="字段直接对齐当前冻结的 `/v1/accounts/me` 响应。"
          actions={<StatusPill tone="success">读取成功</StatusPill>}
        >
          <DefinitionList
            items={[
              { label: "Account ID", value: account.accountId },
              { label: "Auth Subject", value: account.authSubject },
              { label: "Display Name", value: formatNullableText(account.displayName) },
              { label: "Default Role ID", value: account.defaultRoleId },
              { label: "Entitlement Tier", value: account.entitlementTier },
              { label: "Created At", value: formatDateTime(account.createdAt) },
            ]}
          />
        </Panel>
      ) : null}

      {entitlement ? (
        <Panel title="订阅能力占位" description="只展示 entitlement flags，不进入正式购买和支付。">
          <DefinitionList
            items={[
              { label: "Tier", value: entitlement.tier },
              { label: "voiceSession", value: String(entitlement.features.voiceSession) },
              {
                label: "recentContinuityMemory",
                value: String(entitlement.features.recentContinuityMemory),
              },
              {
                label: "priorityGeneration",
                value: String(entitlement.features.priorityGeneration),
              },
            ]}
          />
        </Panel>
      ) : null}

      <Panel title="设备入口" description="当前没有用户侧设备列表接口，所以这里只能挂最近一次绑定成功的本地快照。">
        {bindingCache ? (
          <>
            <p>最近一次绑定设备：{bindingCache.binding.deviceId}</p>
            <div className="action-row">
              <Link className="button" to={`/devices/${bindingCache.binding.deviceId}`}>
                查看 device 页面
              </Link>
            </div>
          </>
        ) : (
          <>
            <p>还没有本地设备快照。先完成一次 bind，才能进入基础 device 页面。</p>
            <div className="action-row">
              <Link className="button" to="/setup/bind">
                去绑定设备
              </Link>
            </div>
          </>
        )}
      </Panel>

      {accountSession ? (
        <div className="action-row">
          <button className="button button-secondary" onClick={handleClearPlaceholderSession} type="button">
            清除占位账号会话
          </button>
        </div>
      ) : null}
    </PageScaffold>
  );
}
