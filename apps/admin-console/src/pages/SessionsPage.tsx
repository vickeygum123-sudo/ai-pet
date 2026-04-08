import { useEffect, useState } from "react";
import { Link } from "react-router";

import { Callout, FilterField, PageScaffold, Panel, StatusPill } from "../components/ui";
import { listAdminSessions, type FailureCode, type Session, type SessionState } from "../lib/api";
import { failureCodes, sessionStates } from "../lib/derived";
import { describeUiError, type UiErrorState } from "../lib/errors";
import { formatDateTime, formatDurationMs, formatNullableText } from "../lib/format";

export function SessionsPage() {
  const [state, setState] = useState<SessionState | "">("");
  const [failureCode, setFailureCode] = useState<FailureCode | "">("");
  const [accountId, setAccountId] = useState("");
  const [deviceId, setDeviceId] = useState("");
  const [sessions, setSessions] = useState<Session[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<UiErrorState | null>(null);

  useEffect(() => {
    let cancelled = false;

    setLoading(true);
    setError(null);

    listAdminSessions({ state, failureCode, accountId, deviceId })
      .then((nextSessions) => {
        if (!cancelled) {
          setSessions(nextSessions);
        }
      })
      .catch((cause) => {
        if (!cancelled) {
          setError(describeUiError(cause));
        }
      })
      .finally(() => {
        if (!cancelled) {
          setLoading(false);
        }
      });

    return () => {
      cancelled = true;
    };
  }, [state, failureCode, accountId, deviceId]);

  return (
    <PageScaffold
      eyebrow="Admin / Sessions"
      title="会话列表"
      description="只使用冻结的 session list filters 和 fields。点击 sessionId 可以进入 detail 视图。"
    >
      <Panel title="筛选条件" description="当前只允许 `state`、`failureCode`、`accountId`、`deviceId`。">
        <div className="filters-grid filters-grid-wide">
          <FilterField label="State">
            <select className="filter-input" onChange={(event) => setState(event.target.value as SessionState | "")} value={state}>
              <option value="">全部</option>
              {sessionStates.map((item) => (
                <option key={item} value={item}>
                  {item}
                </option>
              ))}
            </select>
          </FilterField>
          <FilterField label="Failure Code">
            <select className="filter-input" onChange={(event) => setFailureCode(event.target.value as FailureCode | "")} value={failureCode}>
              <option value="">全部</option>
              {failureCodes.map((item) => (
                <option key={item} value={item}>
                  {item}
                </option>
              ))}
            </select>
          </FilterField>
          <FilterField label="Account ID">
            <input className="filter-input" onChange={(event) => setAccountId(event.target.value)} placeholder="account-123" value={accountId} />
          </FilterField>
          <FilterField label="Device ID">
            <input className="filter-input" onChange={(event) => setDeviceId(event.target.value)} placeholder="device-001" value={deviceId} />
          </FilterField>
        </div>
      </Panel>

      {loading ? (
        <Panel title="读取会话列表中" description="正在请求 admin sessions。">
          <p>请稍候...</p>
        </Panel>
      ) : null}

      {error ? (
        <Callout tone="warning" title={error.title}>
          <p>{error.body}</p>
          {error.supportCode ? <p>支持码：{error.supportCode}</p> : null}
        </Callout>
      ) : null}

      <Panel
        title="会话结果"
        description={`当前共加载 ${sessions.length} 条会话。`}
        actions={<StatusPill tone="info">Session List</StatusPill>}
      >
        <div className="table-scroll">
          <table className="data-table">
            <thead>
              <tr>
                <th>sessionId</th>
                <th>accountId</th>
                <th>deviceId</th>
                <th>roleId</th>
                <th>tier</th>
                <th>state</th>
                <th>asr</th>
                <th>llm</th>
                <th>tts</th>
                <th>safety</th>
                <th>fallback</th>
                <th>continuity</th>
                <th>firstResponse</th>
                <th>failureCode</th>
                <th>firmware</th>
                <th>startedAt</th>
                <th>endedAt</th>
              </tr>
            </thead>
            <tbody>
              {sessions.map((session) => (
                <tr key={session.sessionId}>
                  <td>
                    <Link className="table-link" to={`/sessions/${session.sessionId}`}>
                      {session.sessionId}
                    </Link>
                  </td>
                  <td>{session.accountId}</td>
                  <td>{session.deviceId}</td>
                  <td>{session.roleId}</td>
                  <td>{session.entitlementTier}</td>
                  <td>{session.state}</td>
                  <td>{session.asrStatus}</td>
                  <td>{session.llmStatus}</td>
                  <td>{session.ttsStatus}</td>
                  <td>{String(session.safetyFlag)}</td>
                  <td>{String(session.fallbackUsed)}</td>
                  <td>{String(session.continuityRecallUsed)}</td>
                  <td>{formatDurationMs(session.firstResponseLatencyMs)}</td>
                  <td>{formatNullableText(session.failureCode)}</td>
                  <td>{session.firmwareVersion}</td>
                  <td>{formatDateTime(session.startedAt)}</td>
                  <td>{formatDateTime(session.endedAt)}</td>
                </tr>
              ))}
              {sessions.length === 0 ? (
                <tr>
                  <td className="table-empty" colSpan={17}>
                    没有匹配的会话数据。
                  </td>
                </tr>
              ) : null}
            </tbody>
          </table>
        </div>
      </Panel>
    </PageScaffold>
  );
}
