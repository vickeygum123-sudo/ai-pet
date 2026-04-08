import { useEffect, useState } from "react";
import { Link, useParams } from "react-router";

import { Callout, DefinitionList, PageScaffold, Panel, StatusPill } from "../components/ui";
import { getAdminSessionDetail, type Session } from "../lib/api";
import { describeUiError, type UiErrorState } from "../lib/errors";
import { formatDateTime, formatDurationMs, formatNullableText } from "../lib/format";

export function SessionDetailPage() {
  const { sessionId = "" } = useParams();
  const [session, setSession] = useState<Session | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<UiErrorState | null>(null);

  useEffect(() => {
    let cancelled = false;

    setLoading(true);
    setError(null);

    getAdminSessionDetail(sessionId)
      .then((nextSession) => {
        if (!cancelled) {
          setSession(nextSession);
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
  }, [sessionId]);

  return (
    <PageScaffold
      eyebrow="Admin / Session Detail"
      title={sessionId ? `会话详情：${sessionId}` : "会话详情"}
      description="当前 detail 视图严格对齐冻结 session detail 字段：所有 list 字段加 transitions。"
      actions={
        <Link className="button button-secondary" to="/sessions">
          返回 Session List
        </Link>
      }
    >
      {loading ? (
        <Panel title="读取 session detail 中" description="正在请求指定 session。">
          <p>请稍候...</p>
        </Panel>
      ) : null}

      {error ? (
        <Callout tone="warning" title={error.title}>
          <p>{error.body}</p>
          {error.supportCode ? <p>支持码：{error.supportCode}</p> : null}
        </Callout>
      ) : null}

      {session ? (
        <>
          <Panel
            title="基础元数据"
            description="这里覆盖 inspectable session 的核心字段。"
            actions={<StatusPill tone="success">{session.state}</StatusPill>}
          >
            <DefinitionList
              items={[
                { label: "Session ID", value: session.sessionId },
                { label: "Account ID", value: session.accountId },
                { label: "Device ID", value: session.deviceId },
                { label: "Role ID", value: session.roleId },
                { label: "Entitlement Tier", value: session.entitlementTier },
                { label: "Firmware Version", value: session.firmwareVersion },
                { label: "Started At", value: formatDateTime(session.startedAt) },
                { label: "Ended At", value: formatDateTime(session.endedAt) },
                { label: "First Response Latency", value: formatDurationMs(session.firstResponseLatencyMs) },
                { label: "Failure Code", value: formatNullableText(session.failureCode) },
              ]}
            />
          </Panel>

          <Panel title="步骤与安全信号" description="基于冻结的 session step fields。">
            <DefinitionList
              items={[
                { label: "ASR Status", value: session.asrStatus },
                { label: "LLM Status", value: session.llmStatus },
                { label: "TTS Status", value: session.ttsStatus },
                { label: "Safety Flag", value: String(session.safetyFlag) },
                { label: "Fallback Used", value: String(session.fallbackUsed) },
                { label: "Continuity Recall Used", value: String(session.continuityRecallUsed) },
              ]}
            />
          </Panel>

          <Panel title="状态迁移" description="直接展示 transitions，不额外发明 review annotations。">
            <div className="table-scroll">
              <table className="data-table">
                <thead>
                  <tr>
                    <th>state</th>
                    <th>recordedAt</th>
                    <th>notes</th>
                  </tr>
                </thead>
                <tbody>
                  {session.transitions.map((transition, index) => (
                    <tr key={`${transition.recordedAt}-${index}`}>
                      <td>{transition.state}</td>
                      <td>{formatDateTime(transition.recordedAt)}</td>
                      <td>{formatNullableText(transition.notes)}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </Panel>
        </>
      ) : null}
    </PageScaffold>
  );
}
