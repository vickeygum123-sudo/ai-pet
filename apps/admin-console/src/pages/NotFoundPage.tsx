import { Link } from "react-router";

import { PageScaffold, Panel } from "../components/ui";

export function NotFoundPage() {
  return (
    <PageScaffold
      eyebrow="404"
      title="这个管理后台页面还没进入 MVP 边界"
      description="当前只实现 overview、devices、sessions、failures、review queue 的 MVP 骨架。"
    >
      <Panel title="返回入口" description="先回到已经在本次范围内的页面。">
        <div className="action-row">
          <Link className="button" to="/overview">
            回到 Overview
          </Link>
          <Link className="button button-secondary" to="/sessions">
            回到 Sessions
          </Link>
        </div>
      </Panel>
    </PageScaffold>
  );
}
