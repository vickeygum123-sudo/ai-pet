import { useEffect, useState } from "react";
import { Link } from "react-router";

import { Callout, PageScaffold, Panel, StatusPill, SummaryCard } from "../components/ui";
import { getAdminOverview, listAdminDevices, listAdminSessions, type AdminOverview, type Device, type Session } from "../lib/api";
import {
  continuityStats,
  countOnlineDevices,
  failureBreakdown,
  firmwareDistribution,
  getLatestLastOnlineAt,
  medianFirstResponseLatency,
  reviewCandidates,
  safetyStats,
  sessionSuccessRate,
} from "../lib/derived";
import { describeUiError, type UiErrorState } from "../lib/errors";
import { formatDateTime, formatDurationMs, formatPercent } from "../lib/format";

export function OverviewPage() {
  const [overview, setOverview] = useState<AdminOverview | null>(null);
  const [devices, setDevices] = useState<Device[]>([]);
  const [sessions, setSessions] = useState<Session[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<UiErrorState | null>(null);

  useEffect(() => {
    let cancelled = false;

    Promise.all([getAdminOverview(), listAdminDevices({}), listAdminSessions({})])
      .then(([nextOverview, nextDevices, nextSessions]) => {
        if (cancelled) {
          return;
        }

        setOverview(nextOverview);
        setDevices(nextDevices);
        setSessions(nextSessions);
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

  const safety = safetyStats(sessions);
  const continuity = continuityStats(sessions);
  const failures = failureBreakdown(sessions);
  const reviewQueue = reviewCandidates(sessions);
  const firmwareMix = firmwareDistribution(devices);

  return (
    <PageScaffold
      eyebrow="MVP / Admin Observability"
      title="先回答系统有没有在工作、哪里在失败、哪些会话需要看"
      description="overview 只使用当前冻结的 admin endpoints，再在前端做最小聚合。缺少后端支持的数据会直接标成缺口，不伪造。"
      actions={
        <div className="action-row">
          <Link className="button" to="/sessions">
            查看 Session List
          </Link>
          <Link className="button button-secondary" to="/failures">
            查看 Failure Breakdown
          </Link>
        </div>
      }
    >
      <Callout tone="warning" title="当前已知缺口">
        <p>`setup failures by step`、正式 review workflow、人工 review tags 目前不在冻结 admin API 里，所以这版 overview 只显示缺口说明和替代观察面板。</p>
      </Callout>

      {loading ? (
        <Panel title="加载中" description="正在并行请求 overview、devices、sessions。">
          <p>请稍候...</p>
        </Panel>
      ) : null}

      {error ? (
        <Callout tone="warning" title={error.title}>
          <p>{error.body}</p>
          {error.supportCode ? <p>支持码：{error.supportCode}</p> : null}
        </Callout>
      ) : null}

      {overview ? (
        <Panel
          title="核心总览"
          description="直接对应冻结接口 `GET /v1/admin/overview`。"
          actions={<StatusPill tone="success">Frozen API</StatusPill>}
        >
          <div className="summary-grid">
            <SummaryCard helper="当前 account 总量" label="Total Accounts" value={overview.totalAccounts} />
            <SummaryCard helper="已注册设备总量" label="Total Devices" value={overview.totalDevices} />
            <SummaryCard helper="已绑定设备数量" label="Bound Devices" value={overview.boundDevices} />
            <SummaryCard helper="处于进行中的会话" label="Active Sessions" value={overview.activeSessions} />
            <SummaryCard helper="已完成会话数量" label="Completed Sessions" value={overview.completedSessions} />
            <SummaryCard helper="失败会话数量" label="Failed Sessions" value={overview.failedSessions} />
          </div>
        </Panel>
      ) : null}

      <Panel title="设备健康视角" description="由 device list 前端聚合得出。">
        <div className="summary-grid">
          <SummaryCard helper="deviceStatus 为 connected 或 ready_to_speak" label="Online Devices" value={countOnlineDevices(devices)} />
          <SummaryCard helper="设备列表里最新的 lastOnlineAt" label="Latest Last Online" value={formatDateTime(getLatestLastOnlineAt(devices))} />
          <SummaryCard
            helper={firmwareMix[0] ? `${firmwareMix[0].firmwareVersion} 占比最高` : "暂无设备数据"}
            label="Firmware Versions"
            value={firmwareMix.length}
          />
          <SummaryCard helper="setup funnel 事件尚缺" label="Setup Failures By Step" value="待后端补事件" />
        </div>
      </Panel>

      <Panel title="会话质量视角" description="对齐 MVP-T8 与冻结 session fields。">
        <div className="summary-grid">
          <SummaryCard helper="session list 当前条目数" label="Sessions Loaded" value={sessions.length} />
          <SummaryCard helper="completed / loaded sessions" label="Session Success Rate" value={formatPercent(sessionSuccessRate(sessions))} />
          <SummaryCard helper="firstResponseLatencyMs 的中位数" label="Median First Response" value={formatDurationMs(medianFirstResponseLatency(sessions))} />
          <SummaryCard helper={failures[0] ? `${failures[0].code} 最多` : "暂无失败数据"} label="Failure Codes Seen" value={failures.length} />
        </div>
      </Panel>

      <Panel title="Continuity 与 Safety 视角" description="继续只用会话列表可见字段做最小聚合。">
        <div className="summary-grid">
          <SummaryCard helper="continuityRecallUsed=true" label="Continuity Used" value={continuity.continuityUsed} />
          <SummaryCard helper="当前加载会话中的去重 account 数" label="Repeat-user Sessions" value={continuity.repeatUserSessions} />
          <SummaryCard helper="safetyFlag=true" label="Sensitive Sessions" value={safety.safetyFlagged} />
          <SummaryCard helper="fallbackUsed 或 state=fallback" label="Fallback Count" value={safety.fallbackCount} />
          <SummaryCard helper="failureCode=SAFETY_BLOCKED" label="Blocked Outputs" value={safety.blockedOutputs} />
          <SummaryCard helper="review queue 当前是 heuristic skeleton" label="Review Queue Size" value={reviewQueue.length} />
        </div>
      </Panel>
    </PageScaffold>
  );
}
