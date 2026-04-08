import { useEffect, useState } from "react";
import { Link } from "react-router";

import { Callout, PageScaffold, Panel, StatusPill } from "../components/ui";
import { listAdminSessions, type Session } from "../lib/api";
import { reviewCandidates } from "../lib/derived";
import { describeUiError, type UiErrorState } from "../lib/errors";
import { formatDateTime, formatDurationMs, formatNullableText } from "../lib/format";

function reviewReason(session: Session) {
  const reasons: string[] = [];

  if (session.safetyFlag) {
    reasons.push("safetyFlag");
  }

  if (session.fallbackUsed) {
    reasons.push("fallbackUsed");
  }

  if (session.state === "fallback") {
    reasons.push("state=fallback");
  }

  if (session.failureCode === "SAFETY_BLOCKED") {
    reasons.push("failureCode=SAFETY_BLOCKED");
  }

  return reasons.join(", ");
}

export function ReviewQueuePage() {
  const [sessions, setSessions] = useState<Session[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<UiErrorState | null>(null);

  useEffect(() => {
    let cancelled = false;

    listAdminSessions({})
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
  }, []);

  const candidates = reviewCandidates(sessions);

  return (
    <PageScaffold
      eyebrow="Admin / Review Queue"
      title="Review Queue Skeleton"
      description="当前 review queue 只是 MVP 骨架：基于已冻结 session fields 推出候选会话，不假装成正式审核工作流。"
      actions={
        <Link className="button button-secondary" to="/sessions">
          查看全部 Sessions
        </Link>
      }
    >
      <Callout tone="warning" title="这里是骨架，不是正式审核系统">
        <p>当前没有 review item API、审核状态流转、人工标签保存接口，所以这里只能给团队一个“优先看哪些会话”的候选列表。</p>
      </Callout>

      {loading ? (
        <Panel title="加载中" description="正在读取会话数据生成候选队列。">
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
        title="候选会话"
        description={`当前 heuristic queue 共 ${candidates.length} 条。`}
        actions={<StatusPill tone="warning">Heuristic Queue</StatusPill>}
      >
        <div className="table-scroll">
          <table className="data-table">
            <thead>
              <tr>
                <th>sessionId</th>
                <th>reviewReason</th>
                <th>accountId</th>
                <th>deviceId</th>
                <th>state</th>
                <th>firstResponse</th>
                <th>failureCode</th>
                <th>startedAt</th>
              </tr>
            </thead>
            <tbody>
              {candidates.map((session) => (
                <tr key={session.sessionId}>
                  <td>
                    <Link className="table-link" to={`/sessions/${session.sessionId}`}>
                      {session.sessionId}
                    </Link>
                  </td>
                  <td>{reviewReason(session)}</td>
                  <td>{session.accountId}</td>
                  <td>{session.deviceId}</td>
                  <td>{session.state}</td>
                  <td>{formatDurationMs(session.firstResponseLatencyMs)}</td>
                  <td>{formatNullableText(session.failureCode)}</td>
                  <td>{formatDateTime(session.startedAt)}</td>
                </tr>
              ))}
              {candidates.length === 0 ? (
                <tr>
                  <td className="table-empty" colSpan={8}>
                    当前没有进入 heuristic review queue 的会话。
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
