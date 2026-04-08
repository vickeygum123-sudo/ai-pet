import { Link } from "react-router";

import { SetupProgress } from "../components/SetupProgress";
import { Callout, DefinitionList, PageScaffold, Panel, StatusPill } from "../components/ui";
import { formatDateTime } from "../lib/format";
import { getBindingCache } from "../lib/storage";

const LAUNCH_ROLE_ID = "launch-companion-v0";

export function SetupSuccessPage() {
  const bindingCache = getBindingCache();

  return (
    <PageScaffold
      eyebrow="Setup / Success"
      title="设备已经归属到当前账号"
      description="MVP-T6 要求第一次对话紧跟在绑定成功之后，所以这页不做复杂扩展，只负责确认归属、提示 launch role，并引导用户立刻开聊。"
      sidebar={<SetupProgress current="success" />}
    >
      {!bindingCache ? (
        <Callout tone="warning" title="还没有可展示的绑定结果">
          <p>当前浏览器没有找到最近一次成功绑定的本地快照。你可以回到 bind 页面重新完成一次绑定。</p>
          <div className="action-row">
            <Link className="button" to="/setup/bind">
              返回绑定页
            </Link>
          </div>
        </Callout>
      ) : (
        <>
          <Panel title="绑定确认" description="这部分来自最近一次 bind 成功响应的本地缓存。">
            <div className="inline-metadata">
              <StatusPill tone="success">绑定成功</StatusPill>
              <span>deviceId：{bindingCache.binding.deviceId}</span>
            </div>
            <DefinitionList
              items={[
                { label: "Binding ID", value: bindingCache.binding.bindingId },
                { label: "Account ID", value: bindingCache.binding.accountId },
                { label: "Bound At", value: formatDateTime(bindingCache.binding.boundAt) },
                { label: "Pairing Code", value: bindingCache.pairingCode },
              ]}
            />
          </Panel>

          <Panel title="Launch Companion 确认" description="MVP 先固定一个 launch role，不引入完整角色市场。">
            <DefinitionList
              items={[
                { label: "Role ID", value: LAUNCH_ROLE_ID },
                { label: "当前处理方式", value: "只展示固定角色说明，不提供角色选择持久化接口" },
                { label: "第一次对话提示", value: "完成绑定后，建议用户立刻对设备说第一句问候语。" },
              ]}
            />
          </Panel>

          <Callout tone="info" title="下一步应该发生什么">
            <p>1. 用户回到设备身边，对设备说第一句问候。</p>
            <p>2. 设备应该已经处于 ready-to-speak 或接近 ready 状态。</p>
            <p>3. 如果用户还没法开聊，优先回查 Wi‑Fi、pairing 状态和设备联网情况。</p>
          </Callout>

          <div className="action-row">
            <Link className="button" to={`/devices/${bindingCache.binding.deviceId}`}>
              查看 device 页面
            </Link>
            <Link className="button button-secondary" to="/account">
              查看 account 页面
            </Link>
          </div>
        </>
      )}
    </PageScaffold>
  );
}
