import { Link, NavLink, Outlet } from "react-router";

function navClassName(isActive: boolean) {
  return isActive ? "shell-nav-link shell-nav-link-active" : "shell-nav-link";
}

export function AdminShell() {
  return (
    <div className="shell">
      <header className="shell-header">
        <div className="shell-header-inner">
          <Link className="shell-brand" to="/overview">
            <span className="shell-brand-mark">OPS</span>
            <div>
              <p className="shell-brand-eyebrow">Admin Console</p>
              <h1 className="shell-brand-title">AI Pet Observability v0</h1>
            </div>
          </Link>
          <nav className="shell-nav" aria-label="Primary">
            <NavLink className={({ isActive }) => navClassName(isActive)} to="/overview">
              Overview
            </NavLink>
            <NavLink className={({ isActive }) => navClassName(isActive)} to="/devices">
              Devices
            </NavLink>
            <NavLink className={({ isActive }) => navClassName(isActive)} to="/sessions">
              Sessions
            </NavLink>
            <NavLink className={({ isActive }) => navClassName(isActive)} to="/failures">
              Failures
            </NavLink>
            <NavLink className={({ isActive }) => navClassName(isActive)} to="/review-queue">
              Review Queue
            </NavLink>
          </nav>
          <div className="shell-badge">
            <span className="status-pill status-pill-info">MVP Admin</span>
            <span className="shell-badge-copy">仅接冻结 admin API</span>
          </div>
        </div>
      </header>
      <main className="shell-main">
        <Outlet />
      </main>
    </div>
  );
}
