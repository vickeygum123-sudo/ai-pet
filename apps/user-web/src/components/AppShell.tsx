import { Link, NavLink, Outlet } from "react-router";

import { getAccountSession, getBindingCache } from "../lib/storage";

function navClassName(isActive: boolean) {
  return isActive ? "shell-nav-link shell-nav-link-active" : "shell-nav-link";
}

export function AppShell() {
  const accountSession = getAccountSession();
  const bindingCache = getBindingCache();

  return (
    <div className="shell">
      <header className="shell-header">
        <div className="shell-header-inner">
          <Link className="shell-brand" to="/setup">
            <span className="shell-brand-mark">AI</span>
            <div>
              <p className="shell-brand-eyebrow">User Web</p>
              <h1 className="shell-brand-title">AI Pet MVP</h1>
            </div>
          </Link>
          <nav className="shell-nav" aria-label="Primary">
            <NavLink className={({ isActive }) => navClassName(isActive)} to="/setup">
              Onboarding
            </NavLink>
            <NavLink className={({ isActive }) => navClassName(isActive)} to="/account">
              Account
            </NavLink>
            {bindingCache ? (
              <NavLink
                className={({ isActive }) => navClassName(isActive)}
                to={`/devices/${bindingCache.binding.deviceId}`}
              >
                Device
              </NavLink>
            ) : null}
          </nav>
          <div className="shell-session">
            {accountSession ? (
              <>
                <span className="status-pill status-pill-success">占位登录中</span>
                <span className="shell-session-value">{accountSession.accountId}</span>
              </>
            ) : (
              <span className="status-pill status-pill-warning">未建立账号会话</span>
            )}
          </div>
        </div>
      </header>
      <main className="shell-main">
        <Outlet />
      </main>
    </div>
  );
}
