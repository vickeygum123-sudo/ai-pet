import { Link, useNavigate } from "react-router";
import { useState } from "react";

import { SetupProgress } from "../components/SetupProgress";
import { Callout, Field, PageScaffold, Panel, TextareaField } from "../components/ui";
import { getAccountSession, getOnboardingDraft, setOnboardingDraft } from "../lib/storage";
import { trackSetupEvent } from "../lib/telemetry";

export function SetupWifiPage() {
  const navigate = useNavigate();
  const accountSession = getAccountSession();
  const draft = getOnboardingDraft();
  const [wifiName, setWifiName] = useState(draft?.wifiName ?? "");
  const [pairingCode, setPairingCode] = useState(draft?.pairingCode ?? "");
  const [deviceNotes, setDeviceNotes] = useState(draft?.deviceNotes ?? "");

  function handleContinue() {
    setOnboardingDraft({
      wifiName: wifiName.trim(),
      pairingCode: pairingCode.trim(),
      deviceNotes: deviceNotes.trim(),
    });
    trackSetupEvent("wifi_config_submitted", {
      guideOnly: true,
      hasWifiName: Boolean(wifiName.trim()),
      hasPrefilledPairingCode: Boolean(pairingCode.trim()),
    });
    navigate("/setup/bind");
  }

  return (
    <PageScaffold
      eyebrow="Setup / Wi‑Fi Guide"
      title="先让用户知道设备该怎么入网"
      description="当前没有冻结的用户网页配网接口，所以这里明确只做 Wi‑Fi 引导态：帮助用户理解步骤、记录必要信息，再进入 bind。"
      sidebar={<SetupProgress current="wifi" />}
    >
      {!accountSession ? (
        <Callout tone="warning" title="还没有账号上下文">
          <p>绑定接口必须带账号上下文。请先回到账号占位页，建立 account session。</p>
          <div className="action-row">
            <Link className="button" to="/setup/account">
              先去建立账号会话
            </Link>
          </div>
        </Callout>
      ) : null}

      <Panel title="Wi‑Fi 引导范围" description="这页不会向设备发送 Wi‑Fi 密码，也不会轮询设备联网结果。">
        <ul className="check-list">
          <li>告诉用户设备需要进入 pairing-ready 状态。</li>
          <li>提醒用户准备 2.4G / 5G Wi‑Fi 信息与 pairing code。</li>
          <li>把可能的失败原因翻译成人话：密码错误、设备未联网、设备离线路由器太远。</li>
          <li>把可记录的信息保存在本地，方便下一步 bind 直接使用。</li>
        </ul>
      </Panel>

      <Callout tone="info" title="推荐给用户的说明">
        <p>1. 让设备进入可配网状态，确认设备已经给出 pairing cue。</p>
        <p>2. 按包装说明完成本地配网动作。</p>
        <p>3. 当设备提示已连云，再返回网页继续输入 pairing code 完成绑定。</p>
      </Callout>

      <Panel title="本地记录" description="这些信息只会保存在当前浏览器里，用于让下一步 bind 少重复输入。">
        <div className="stack-form">
          <Field
            autoComplete="off"
            hint="仅用于本地记录，不会上送后端。"
            label="Wi‑Fi 名称"
            onChange={(event) => setWifiName(event.target.value)}
            placeholder="Home-2.4G"
            value={wifiName}
          />
          <Field
            autoComplete="off"
            hint="如果用户已经拿到 pairing code，可以先记在这里，下一页会自动带过去。"
            label="Pairing Code"
            onChange={(event) => setPairingCode(event.target.value.toUpperCase())}
            placeholder="PAIR-001"
            value={pairingCode}
          />
          <TextareaField
            hint="比如：设备摆放位置、当前指示灯状态、这次遇到过什么问题。"
            label="设备备注"
            onChange={(event) => setDeviceNotes(event.target.value)}
            placeholder="例如：黄灯闪烁，已重试一次。"
            rows={4}
            value={deviceNotes}
          />
          <div className="action-row">
            <button className="button" disabled={!accountSession} onClick={handleContinue} type="button">
              保存本地记录并进入绑定
            </button>
          </div>
        </div>
      </Panel>

      <Panel title="常见失败翻译" description="MVP-T6 要求用户始终知道问题是网络、账号还是设备。">
        <div className="issue-grid">
          <div className="issue-card">
            <h4>像是网络问题</h4>
            <p>优先检查 Wi‑Fi 密码、路由器距离、设备当前是否仍在联网过程中。</p>
          </div>
          <div className="issue-card">
            <h4>像是设备问题</h4>
            <p>确认设备确实进入 pairing-ready 状态，而且 pairing code 来自当前这一台设备。</p>
          </div>
          <div className="issue-card">
            <h4>像是账号问题</h4>
            <p>如果后面 bind 时报 auth 相关错误，说明本地的 accountId 占位会话已经失效。</p>
          </div>
        </div>
      </Panel>
    </PageScaffold>
  );
}
