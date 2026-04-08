import { useEffect, useState } from "react";
import { Link } from "react-router";

import { Callout, PageScaffold, Panel, StatusPill } from "../components/ui";
import { listAdminSessions, type Session } from "../lib/api";
import { failureBreakdown, safetyStats, statusBreakdown } from "../lib/derived";
import { describeUiError, type UiErrorState } from "../lib/errors";

export function FailuresPage() {
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

  const failures = failureBreakdown(sessions);
  const states = statusBreakdown(sessions);
  const safety = safetyStats(sessions);

  return (
    <PageScaffold
      eyebrow="Admin / Failures"
      title="Failure Breakdown"
      description="当前没有专门的 failure aggregation API，这一页基于冻结 session list 前端聚合失败码、fallback 与状态分布。"
      actions={
        <Link className="button button-secondary" to="/sessions">
          回到 Session List
        </Link>
      }
    >
      <Callout tone="warning" title="当前没法回答的问题">
        <p>ASR / LLM / TTS 的独立 latency slices 还不在冻结 contract 里，`setup failures by step` 也缺少 setup funnel 事件接口，所以这里不会伪造图表。</p>
      </Callout>

      {loading ? (
        <Panel title="加载中" description="正在读取会话数据用于聚合失败分布。">
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
        title="按 Failure Code 聚合"
        description="`failureCode` 为 null 的会显示成 `NO_FAILURE_CODE`，方便判断当前多少会话没有失败码。"
        actions={<StatusPill tone="info">Frontend Aggregation</StatusPill>}
      >
        <div className="table-scroll">
          <table className="data-table">
            <thead>
              <tr>
                <th>failureCode</th>
                <th>count</th>
              </tr>
            </thead>
            <tbody>
              {failures.map((item) => (
                <tr key={item.code}>
                  <td>{item.code}</td>
                  <td>{item.count}</td>
                </tr>
              ))}
              {failures.length === 0 ? (
                <tr>
                  <td className="table-empty" colSpan={2}>
                    暂无会话数据。
                  </td>
                </tr>
              ) : null}
            </tbody>
          </table>
        </div>
      </Panel>

      <Panel title="按 Session State 聚合" description="用于快速判断失败、fallback、completed 的占比。">
        <div className="table-scroll">
          <table className="data-table">
            <thead>
              <tr>
                <th>state</th>
                <th>count</th>
              </tr>
            </thead>
            <tbody>
              {states.map((item) => (
                <tr key={item.state}>
                  <td>{item.state}</td>
                  <td>{item.count}</td>
                </tr>
              ))}
              {states.length === 0 ? (
                <tr>
                  <td className="table-empty" colSpan={2}>
                    暂无会话数据。
                  </td>
                </tr>
              ) : null}
            </tbody>
          </table>
        </div>
      </Panel>

      <Panel title="安全与 fallback 观察" description="这里是 failure breakdown 的补充观察切片。">
        <div className="summary-grid">
          <div className="summary-card">
            <p className="summary-label">Safety Flagged</p>
            <p className="summary-value">{safety.safetyFlagged}</p>
          </div>
          <div className="summary-card">
            <p className="summary-label">Fallback Count</p>
            <p className="summary-value">{safety.fallbackCount}</p>
          </div>
          <div className="summary-card">
            <p className="summary-label">Blocked Outputs</p>
            <p className="summary-value">{safety.blockedOutputs}</p>
          </div>
        </div>
      </Panel>
    </PageScaffold>
  );
}
