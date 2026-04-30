import type { ReactNode } from 'react';
import { NavLink } from 'react-router-dom';

export function Layout({ children }: { children: ReactNode }) {
  return (
    <div className="shell">
      <aside className="sidebar">
        <div>
          <p className="eyebrow">Incident Management System</p>
          <h1>Real-time operations cockpit</h1>
        </div>
        <nav className="nav">
          <NavLink to="/" end>
            Dashboard
          </NavLink>
        </nav>
        <div className="sidebar-note">
          <p>P0 events route to paging, P1 to the incident bridge, and P2 stays in-team.</p>
        </div>
      </aside>
      <main className="content">{children}</main>
    </div>
  );
}
