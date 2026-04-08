import { type FormEvent, useState } from "react";
import { Link, useNavigate } from "react-router";

import { SetupProgress } from "../components/SetupProgress";
import { Callout, Field, PageScaffold, Panel } from "../components/ui";
import { createAccount, getAccountMe } from "../lib/api";
import { describeUiError, type UiErrorState } from "../lib/errors";
import { formatDateTime } from "../lib/format";
import { getAccountSession, setAccountSession } from "../lib/storage";
import { trackSetupEvent } from "../lib/telemetry";

type Mode = "create" | "login";

export function SetupAccountPage() {
  const navigate = useNavigate();
  const existingSession = getAccountSession();
  const [mode, setMode] = useState<Mode>(existingSession ? "login" : "create");
  const [authSubject, setAuthSubject] = useState("auth0|pilot-user-001");
  const [displayName, setDisplayName] = useState("Pilot User");
  const [accountId, setAccountId] = useState(existingSession?.accountId ?? "");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<UiErrorState | null>(null);

  async function handleCreate(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setBusy(true);
    setError(null);

    try {
      const account = await createAccount({
        authSubject: authSubject.trim(),
        displayName: displayName.trim() || undefined,
      });

      setAccountSession({
        accountId: account.accountId,
        authMode: "placeholder-create",
        createdAt: new Date().toISOString(),
      });
      trackSetupEvent("account_created", { accountId: account.accountId });
      navigate("/setup/wifi");
    } catch (cause) {
      setError(describeUiError(cause, "account-create"));
      trackSetupEvent("setup_failed", { stage: "account-create" });
    } finally {
      setBusy(false);
    }
  }

  async function handleLogin(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setBusy(true);
    setError(null);

    try {
      const account = await getAccountMe(accountId.trim());

      setAccountSession({
        accountId: account.accountId,
        authMode: "placeholder-login",
        createdAt: new Date().toISOString(),
      });
      navigate("/setup/wifi");
    } catch (cause) {
      setError(describeUiError(cause, "account-login"));
      trackSetupEvent("setup_failed", { stage: "account-login" });
    } finally {
      setBusy(false);
    }
  }

  return (
    <PageScaffold
      eyebrow="Setup / Account"
      title="建立 MVP 账号占位会话"
      description="真实登录态还没进入这条实现边界，所以这里只做开发占位：创建一个账号记录，或直接输入已有 accountId 验证进入。"
      sidebar={<SetupProgress current="account" />}
    >
      <Callout tone="warning" title="这里不是正式登录系统">
        <p>后端冻结文档已经明确：`X-Account-Id` 只是开发占位，不代表正式 token / session 设计。</p>
        <p>这一页的目标只有一个：给后续 bind API 一个明确的 account context。</p>
      </Callout>

      {existingSession ? (
        <Panel title="已存在本地账号会话" description="你可以继续沿用，也可以切换到别的占位账号。">
          <p>当前 accountId：{existingSession.accountId}</p>
          <p>建立时间：{formatDateTime(existingSession.createdAt)}</p>
          <div className="action-row">
            <button className="button" onClick={() => navigate("/setup/wifi")} type="button">
              继续后续 setup
            </button>
          </div>
        </Panel>
      ) : null}

      <Panel
        title="选择方式"
        description="MVP 只保留两个最短路径：创建账号占位，或输入已有 accountId 进入。"
        actions={
          <div className="segmented-control" role="tablist" aria-label="账号方式">
            <button
              className={mode === "create" ? "segment-active" : ""}
              onClick={() => setMode("create")}
              type="button"
            >
              创建
            </button>
            <button
              className={mode === "login" ? "segment-active" : ""}
              onClick={() => setMode("login")}
              type="button"
            >
              进入
            </button>
          </div>
        }
      >
        {mode === "create" ? (
          <form className="stack-form" onSubmit={handleCreate}>
            <Field
              autoComplete="off"
              hint="当前直接映射到 POST /v1/accounts 的 authSubject。"
              label="Auth Subject"
              onChange={(event) => setAuthSubject(event.target.value)}
              placeholder="auth0|pilot-user-001"
              required
              value={authSubject}
            />
            <Field
              autoComplete="off"
              hint="可选，会展示在 account 页面。"
              label="Display Name"
              onChange={(event) => setDisplayName(event.target.value)}
              placeholder="Pilot User"
              value={displayName}
            />
            <div className="action-row">
              <button className="button" disabled={busy} type="submit">
                {busy ? "创建中..." : "创建账号并继续"}
              </button>
            </div>
          </form>
        ) : (
          <form className="stack-form" onSubmit={handleLogin}>
            <Field
              autoComplete="off"
              hint="会先请求 GET /v1/accounts/me 校验这个占位 accountId 是否存在。"
              label="Existing Account ID"
              onChange={(event) => setAccountId(event.target.value)}
              placeholder="account-123"
              required
              value={accountId}
            />
            <div className="action-row">
              <button className="button" disabled={busy} type="submit">
                {busy ? "校验中..." : "进入这个账号"}
              </button>
            </div>
          </form>
        )}
      </Panel>

      {error ? (
        <Callout tone="warning" title={error.title}>
          <p>{error.body}</p>
          {error.supportCode ? <p>支持码：{error.supportCode}</p> : null}
        </Callout>
      ) : null}

      <div className="action-row">
        <Link className="button button-secondary" to="/setup">
          返回 setup 首页
        </Link>
      </div>
    </PageScaffold>
  );
}
