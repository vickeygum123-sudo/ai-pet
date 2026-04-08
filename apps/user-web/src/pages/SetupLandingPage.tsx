import { Link } from "react-router";
import { useEffect } from "react";

import { SetupProgress } from "../components/SetupProgress";
import { Callout, PageScaffold, Panel, StatusPill } from "../components/ui";
import { getAccountSession, getBindingCache } from "../lib/storage";
import { trackSetupEvent } from "../lib/telemetry";

export function SetupLandingPage() {
  const accountSession = getAccountSession();
  const bindingCache = getBindingCache();

  useEffect(() => {
    trackSetupEvent("setup_started", {
      hasAccountSession: Boolean(accountSession),
      hasCachedBinding: Boolean(bindingCache),
    });
  }, [accountSession, bindingCache]);

  return (
    <PageScaffold
      eyebrow="MVP / User Onboarding"
      title="先把设备带进你的账号，再把第一次对话走通"
      description="这条流程只覆盖 MVP-T6 冻结范围：账号占位、Wi‑Fi 引导、pairing code 绑定、绑定成功和基础 account / device 页面。"
      sidebar={<SetupProgress current="start" />}
    >
      <Panel
        title="当前主线包含什么"
        description="目标是让用户从打开网页到绑定成功，尽量少跳出、少猜测、少填表。"
      >
        <ul className="check-list">
          <li>账号创建 / 登录先按开发占位方案接入，不假装成正式 auth。</li>
          <li>Wi‑Fi 页面只负责清晰引导，不伪造不存在的配网 API。</li>
          <li>绑定动作只调用冻结的 `POST /v1/device-bindings`。</li>
          <li>绑定成功后立刻引导用户进入第一次对话。</li>
        </ul>
      </Panel>

      <Callout tone="warning" title="当前已知边界">
        <p>后端暂时没有用户网页可用的配网闭环接口，也没有用户侧设备详情接口。</p>
        <p>因此这版 Wi‑Fi 是引导态，device 页面是最近一次绑定成功后的本地快照视图。</p>
      </Callout>

      {accountSession ? (
        <Callout tone="success" title="已检测到本地账号会话">
          <p>当前 accountId：{accountSession.accountId}</p>
          <p>你可以直接继续 Wi‑Fi 引导和绑定流程。</p>
        </Callout>
      ) : (
        <Callout tone="info" title="还没有账号占位会话">
          <p>MVP 目前用 `X-Account-Id` 做开发占位登录。先创建或输入一个 accountId，后面的绑定接口才能带上账号上下文。</p>
        </Callout>
      )}

      {bindingCache ? (
        <Panel title="最近一次绑定快照" description="这不是后端实时查询，而是本地缓存的绑定结果。">
          <div className="inline-metadata">
            <StatusPill tone="success">设备已绑定</StatusPill>
            <span>{bindingCache.binding.deviceId}</span>
            <span>{bindingCache.binding.boundAt}</span>
          </div>
          <div className="action-row">
            <Link className="button button-secondary" to={`/devices/${bindingCache.binding.deviceId}`}>
              查看 device 页面
            </Link>
          </div>
        </Panel>
      ) : null}

      <div className="action-row">
        <Link className="button" to={accountSession ? "/setup/wifi" : "/setup/account"}>
          {accountSession ? "继续 setup" : "开始账号占位"}
        </Link>
        <Link className="button button-secondary" to="/account">
          查看 account 页面
        </Link>
      </div>
    </PageScaffold>
  );
}
