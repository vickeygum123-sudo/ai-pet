import { useEffect, useState } from "react";

import { Callout, FilterField, PageScaffold, Panel, StatusPill } from "../components/ui";
import { listAdminDevices, type BindStatus, type Device } from "../lib/api";
import { describeUiError, type UiErrorState } from "../lib/errors";
import { formatDateTime, formatNullableText } from "../lib/format";

export function DevicesPage() {
  const [bindStatus, setBindStatus] = useState<BindStatus | "">("");
  const [ownerAccountId, setOwnerAccountId] = useState("");
  const [devices, setDevices] = useState<Device[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<UiErrorState | null>(null);

  useEffect(() => {
    let cancelled = false;

    setLoading(true);
    setError(null);

    listAdminDevices({ bindStatus, ownerAccountId })
      .then((nextDevices) => {
        if (!cancelled) {
          setDevices(nextDevices);
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
  }, [bindStatus, ownerAccountId]);

  return (
    <PageScaffold
      eyebrow="Admin / Devices"
      title="设备列表"
      description="只使用冻结的 `GET /v1/admin/devices` 字段和两个 query filters：`bindStatus`、`ownerAccountId`。"
    >
      <Panel title="筛选条件" description="这里不新增未冻结的过滤器。">
        <div className="filters-grid">
          <FilterField label="Bind Status">
            <select className="filter-input" onChange={(event) => setBindStatus(event.target.value as BindStatus | "")} value={bindStatus}>
              <option value="">全部</option>
              <option value="bound">bound</option>
              <option value="unbound">unbound</option>
            </select>
          </FilterField>
          <FilterField label="Owner Account ID">
            <input
              className="filter-input"
              onChange={(event) => setOwnerAccountId(event.target.value)}
              placeholder="account-123"
              value={ownerAccountId}
            />
          </FilterField>
        </div>
      </Panel>

      {loading ? (
        <Panel title="读取设备列表中" description="正在请求 admin devices。">
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
        title="设备结果"
        description={`当前共加载 ${devices.length} 台设备。`}
        actions={<StatusPill tone="info">Frozen Query Fields</StatusPill>}
      >
        <div className="table-scroll">
          <table className="data-table">
            <thead>
              <tr>
                <th>deviceId</th>
                <th>hardwareModel</th>
                <th>firmwareVersion</th>
                <th>deviceStatus</th>
                <th>bindStatus</th>
                <th>ownerAccountId</th>
                <th>pairingCode</th>
                <th>lastOnlineAt</th>
                <th>createdAt</th>
              </tr>
            </thead>
            <tbody>
              {devices.map((device) => (
                <tr key={device.deviceId}>
                  <td>{device.deviceId}</td>
                  <td>{device.hardwareModel}</td>
                  <td>{device.firmwareVersion}</td>
                  <td>{device.deviceStatus}</td>
                  <td>{device.bindStatus}</td>
                  <td>{formatNullableText(device.ownerAccountId)}</td>
                  <td>{device.pairingCode}</td>
                  <td>{formatDateTime(device.lastOnlineAt)}</td>
                  <td>{formatDateTime(device.createdAt)}</td>
                </tr>
              ))}
              {devices.length === 0 ? (
                <tr>
                  <td className="table-empty" colSpan={9}>
                    没有匹配的设备数据。
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
