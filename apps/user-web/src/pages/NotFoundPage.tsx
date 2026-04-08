import { Link } from "react-router";

import { PageScaffold, Panel } from "../components/ui";

export function NotFoundPage() {
  return (
    <PageScaffold
      eyebrow="404"
      title="这个用户页还没有定义"
      description="当前用户前端只冻结了 onboarding / bind / account / device 相关路由。"
    >
      <Panel title="可返回的入口" description="先回到已经进入本次边界的页面。">
        <div className="action-row">
          <Link className="button" to="/setup">
            回到 setup
          </Link>
          <Link className="button button-secondary" to="/account">
            回到 account
          </Link>
        </div>
      </Panel>
    </PageScaffold>
  );
}
