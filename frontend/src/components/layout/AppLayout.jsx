import { useState } from "react";
import { NavLink, Outlet, useLocation } from "react-router-dom";
import {
  LayoutDashboard,
  Boxes,
  ChartNoAxesCombined,
  Truck,
  GitBranch,
  MessageSquareText,
  ClipboardList,
  Bell,
  ChevronLeft,
  Menu,
  Search,
  PanelLeftClose,
} from "lucide-react";
const links = [
  ["/", "Dashboard", LayoutDashboard],
  ["/inventory", "Inventory", Boxes],
  ["/forecasting", "Forecasting", ChartNoAxesCombined],
  ["/suppliers", "Suppliers", Truck],
  ["/procurement", "AI Procurement", GitBranch],
  ["/assistant", "AI Assistant", MessageSquareText],
  ["/orders", "Purchase Orders", ClipboardList],
];
const titles = {
  "/": "Dashboard",
  "/inventory": "Inventory",
  "/forecasting": "Forecasting & Analytics",
  "/suppliers": "Supplier Management",
  "/procurement": "AI Procurement Center",
  "/assistant": "AI Assistant & Documents",
  "/orders": "Purchase Orders",
};
export default function AppLayout() {
  const [collapsed, setCollapsed] = useState(false),
    [mobile, setMobile] = useState(false);
  const loc = useLocation();
  return (
    <div className="app-shell">
      <aside
        className={`sidebar ${collapsed ? "collapsed" : ""} ${mobile ? "mobile-open" : ""}`}
      >
        <div className="brand">
          <div className="brand-mark">S</div>
          {!collapsed && (
            <div>
              <b>SupplyWise</b>
              <small>PROCUREMENT INTELLIGENCE</small>
            </div>
          )}
          <button
            className="collapse-btn"
            onClick={() => setCollapsed(!collapsed)}
            aria-label="Collapse sidebar"
          >
            <PanelLeftClose size={17} />
          </button>
        </div>
        <div className="workspace">
          <div className="workspace-avatar">A</div>
          {!collapsed && (
            <div>
              <b>Acme Manufacturing</b>
              <small>Operations workspace</small>
            </div>
          )}
          <ChevronLeft size={14} />
        </div>
        <div className="nav-label">WORKSPACE</div>
        <nav>
          {links.map(([to, label, Icon]) => (
            <NavLink
              key={to}
              to={to}
              end={to === "/"}
              onClick={() => setMobile(false)}
              title={collapsed ? label : undefined}
              className={({ isActive }) =>
                `nav-link ${isActive ? "active" : ""}`
              }
            >
              <Icon size={18} />
              {!collapsed && <span>{label}</span>}
              {label === "AI Procurement" && !collapsed && (
                <i className="nav-dot" />
              )}
            </NavLink>
          ))}
        </nav>
        <div className="sidebar-footer">
          <div className="avatar">AM</div>
          {!collapsed && (
            <div>
              <b>Arjun Mehta</b>
              <small>Procurement Manager</small>
            </div>
          )}
        </div>
      </aside>
      <main className="main">
        <header className="topbar">
          <button
            className="mobile-menu icon-button"
            onClick={() => setMobile(!mobile)}
            aria-label="Open navigation"
          >
            <Menu />
          </button>
          <div className="crumb">
            <span>Workspace</span>
            <span className="slash">/</span>
            <b>{titles[loc.pathname] || "Dashboard"}</b>
          </div>
          <div className="top-actions">
            <button
              className="global-search"
              onClick={() => document.querySelector("input")?.focus()}
            >
              <Search size={15} />
              <span>Search anything</span>
              <kbd>⌘ K</kbd>
            </button>
            <button
              className="icon-button notification"
              aria-label="Notifications"
            >
              <Bell size={18} />
              <i />
            </button>
            <div className="top-avatar">AM</div>
          </div>
        </header>
        <div className="page-content">
          <Outlet />
        </div>
      </main>
      {mobile && (
        <button
          className="mobile-scrim"
          aria-label="Close navigation"
          onClick={() => setMobile(false)}
        />
      )}
    </div>
  );
}
