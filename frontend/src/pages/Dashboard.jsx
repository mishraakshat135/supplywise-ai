import {
  AreaChart,
  Area,
  BarChart,
  Bar,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
  Cell,
} from "recharts";
import {
  ArrowUpRight,
  ArrowDownRight,
  ArrowRight,
  Package,
  Wallet,
  TriangleAlert,
  ShieldAlert,
  ClipboardCheck,
  Clock3,
  Activity,
  TrendingUp,
} from "lucide-react";
import { Link } from "react-router-dom";
import PageHeader from "../components/common/PageHeader.jsx";
import { Badge } from "../components/common/UI.jsx";
import { dashboardService } from "../services/api/domainServices.js";
import { useAsync } from "../services/api/useAsync.js";
const timeAgo = (iso) => {
  const mins = Math.max(0, Math.round((Date.now() - new Date(iso)) / 60000));
  if (Number.isNaN(mins)) return "";
  if (mins < 60) return `${mins} min ago`;
  if (mins < 1440) return `${Math.round(mins / 60)} h ago`;
  return new Date(iso).toLocaleDateString("en-IN", { day: "numeric", month: "short" });
};
const fmt = (n) =>
  new Intl.NumberFormat("en-IN", {
    style: "currency",
    currency: "INR",
    maximumFractionDigits: 0,
  }).format(n);
const Kpi = ({ label, value, change, up, icon: Icon, tone, detail }) => (
  <article className="kpi-card">
    <div className="kpi-top">
      <span>{label}</span>
      <div className={`kpi-icon ${tone}`}>
        <Icon size={17} />
      </div>
    </div>
    <div className="kpi-value">{value}</div>
    <div className="kpi-foot">
      <span className={up ? "positive" : "negative"}>
        {up ? <ArrowUpRight size={14} /> : <ArrowDownRight size={14} />}{" "}
        {change}
      </span>
      <span>{detail}</span>
    </div>
  </article>
);
export default function Dashboard() {
  const { data: s, loading, error } = useAsync(() => dashboardService.summary(), null);
  const k = s?.kpis ?? {};
  const demand = s?.demand ?? [];
  const activity = s?.activity ?? [];
  const categories = s?.category_distribution ?? [];
  const lowStock = s?.low_stock ?? [];
  return (
    <>
      <PageHeader
        eyebrow={new Date()
          .toLocaleDateString("en-IN", {
            weekday: "long",
            year: "numeric",
            month: "long",
            day: "numeric",
          })
          .toUpperCase()}
        title="Good morning, Arjun"
        description="Here’s what needs your attention across the supply chain today."
        actions={
          <>
            <button
              className="button secondary"
              onClick={() =>
                window.showToast("Report export is not implemented yet.")
              }
            >
              Export report
            </button>
            <Link className="button primary" to="/procurement">
              Review recommendations <ArrowRight size={15} />
            </Link>
          </>
        }
      />
      <div className="demo-banner">
        <span className="demo-dot" />{" "}
        {error ? `BACKEND ERROR · ${error}` : "LIVE DATA"}
        {!error && (
          <>
            {" "}
            <span className="banner-sep">·</span>{" "}
            {loading
              ? "Loading from the backend…"
              : "Figures come from your PostgreSQL database."}
          </>
        )}
      </div>
      <div className="kpi-grid">
        <Kpi
          label="Total products"
          value={k.total_products ?? 0}
          change="Active"
          up
          icon={Package}
          tone="violet"
          detail="SKUs tracked"
        />
        <Kpi
          label="Inventory value"
          value={fmt(k.inventory_value ?? 0)}
          change="Live"
          up
          icon={Wallet}
          tone="blue"
          detail="stock × unit cost"
        />
        <Kpi
          label="Below reorder point"
          value={k.below_reorder_point ?? 0}
          change={`${k.below_reorder_point ?? 0} items`}
          up={false}
          icon={TriangleAlert}
          tone="amber"
          detail="require attention"
        />
        <Kpi
          label="Stockout risk"
          value={k.stockout_risk ?? 0}
          change="critical"
          up={false}
          icon={ShieldAlert}
          tone="red"
          detail="≤ 45% of reorder point"
        />
        <Kpi
          label="Pending decisions"
          value={k.pending_decisions ?? 0}
          change={`${k.pending_recommendations ?? 0} recs`}
          up
          icon={ClipboardCheck}
          tone="teal"
          detail={`${k.pending_purchase_orders ?? 0} POs awaiting`}
        />
      </div>
      <div className="dashboard-grid">
        <section className="panel chart-panel">
          <div className="panel-heading">
            <div>
              <h2>Demand overview</h2>
              <p>Daily units sold · last 30 days</p>
            </div>
            <div className="chart-legend">
              <span>
                <i className="legend-dot actual" />
                Actual
              </span>
              <span>
                <i className="legend-dot forecast" />
                Forecast
              </span>
            </div>
          </div>
          <div className="chart-wrap">
            <ResponsiveContainer width="100%" height="100%">
              <AreaChart
                data={demand}
                margin={{ top: 10, right: 8, left: -22, bottom: 0 }}
              >
                <defs>
                  <linearGradient id="areaTeal" x1="0" y1="0" x2="0" y2="1">
                    <stop offset="0%" stopColor="#14b8a6" stopOpacity={0.18} />
                    <stop offset="100%" stopColor="#14b8a6" stopOpacity={0} />
                  </linearGradient>
                </defs>
                <CartesianGrid
                  stroke="#243047"
                  strokeDasharray="3 5"
                  vertical={false}
                />
                <XAxis
                  dataKey="day"
                  tick={{ fill: "#8190a8", fontSize: 11 }}
                  tickLine={false}
                  axisLine={false}
                />
                <YAxis
                  tick={{ fill: "#8190a8", fontSize: 11 }}
                  tickLine={false}
                  axisLine={false}
                />
                <Tooltip
                  contentStyle={{
                    background: "#111a2c",
                    border: "1px solid #26334b",
                    borderRadius: 9,
                    color: "#e5ebf4",
                  }}
                />
                <Area
                  dataKey="actual"
                  name="Actual"
                  stroke="#14b8a6"
                  fill="url(#areaTeal)"
                  strokeWidth={2.4}
                  connectNulls={false}
                />
                <Area
                  dataKey="forecast"
                  name="Forecast"
                  stroke="#818cf8"
                  fill="none"
                  strokeWidth={2}
                  strokeDasharray="5 5"
                  connectNulls={false}
                />
              </AreaChart>
            </ResponsiveContainer>
          </div>
          <div className="chart-foot">
            <span>
              <Activity size={14} /> Sales history <b>last 30 days</b>
            </span>
            <Link to="/forecasting">
              View forecast <ArrowRight size={14} />
            </Link>
          </div>
        </section>
        <section className="panel distribution">
          <div className="panel-heading">
            <div>
              <h2>Inventory by category</h2>
              <p>Number of active SKUs</p>
            </div>
            <button
              className="more-button"
              onClick={() =>
                window.showToast("Showing live category counts.")
              }
            >
              •••
            </button>
          </div>
          <div className="bar-chart">
            <ResponsiveContainer width="100%" height="100%">
              <BarChart
                data={categories}
                layout="vertical"
                margin={{ top: 5, right: 14, left: 0, bottom: 0 }}
              >
                <CartesianGrid stroke="#243047" horizontal={false} />
                <XAxis
                  type="number"
                  tick={{ fill: "#8190a8", fontSize: 10 }}
                  axisLine={false}
                  tickLine={false}
                />
                <YAxis
                  type="category"
                  dataKey="name"
                  width={78}
                  tick={{ fill: "#a6b1c1", fontSize: 11 }}
                  axisLine={false}
                  tickLine={false}
                />
                <Tooltip
                  contentStyle={{
                    background: "#111a2c",
                    border: "1px solid #26334b",
                    borderRadius: 9,
                  }}
                />
                <Bar dataKey="value" radius={[0, 5, 5, 0]} barSize={13}>
                  {categories.map((c, x) => (
                    <Cell
                      key={c.name}
                      fill={["#14b8a6", "#7182ee", "#a78bfa", "#f59e0b"][x % 4]}
                    />
                  ))}
                </Bar>
              </BarChart>
            </ResponsiveContainer>
          </div>
          <div className="distribution-foot">
            <span>
              <i className="legend-dot actual" /> {k.total_products ?? 0} active products
            </span>
            <Link to="/inventory">
              View inventory <ArrowRight size={14} />
            </Link>
          </div>
        </section>
        <section className="panel activity-panel">
          <div className="panel-heading">
            <div>
              <h2>Recent activity</h2>
              <p>Latest inventory and purchasing updates</p>
            </div>
            <button
              className="text-button"
              onClick={() =>
                window.showToast("You’re viewing the latest activity.")
              }
            >
              View all <ArrowRight size={14} />
            </button>
          </div>
          <div className="activity-list">
            {activity.map((item, i) => (
              <div className="activity-row" key={i}>
                <div className={`activity-icon ${item.tone}`}>
                  <Activity size={15} />
                </div>
                <div className="activity-copy">
                  <b>{item.title}</b>
                  <span>{item.detail}</span>
                </div>
                <time>{timeAgo(item.time)}</time>
              </div>
            ))}
          </div>
        </section>
        <section className="panel actions-panel">
          <div className="panel-heading">
            <div>
              <h2>Needs your attention</h2>
              <p>Open decisions and urgent items</p>
            </div>
            <Link to="/procurement" className="text-button">
              See queue <ArrowRight size={14} />
            </Link>
          </div>
          <div className="attention-card urgent">
            <span className="attention-mark">
              <TriangleAlert size={16} />
            </span>
            <div>
              <b>{k.stockout_risk ?? 0} products at critical stock</b>
              <span>
                {lowStock
                  .slice(0, 2)
                  .map((p) => p.name)
                  .join(", ") || "Nothing is below its reorder point"}
              </span>
            </div>
            <Link to="/inventory" aria-label="View critical stock">
              <ArrowRight size={16} />
            </Link>
          </div>
          <div className="attention-card">
            <span className="attention-mark blue">
              <Clock3 size={16} />
            </span>
            <div>
              <b>{k.pending_recommendations ?? 0} recommendations pending</b>
              <span>
                {k.pending_purchase_orders ?? 0} purchase order(s) awaiting
                approval
              </span>
            </div>
            <Link to="/procurement" aria-label="Review recommendations">
              <ArrowRight size={16} />
            </Link>
          </div>
          <div className="summary-box">
            <div className="summary-title">
              <TrendingUp size={15} /> Operations summary{" "}
              <Badge tone="teal">LIVE</Badge>
            </div>
            <p>
              {k.below_reorder_point ?? 0} SKU(s) are below their reorder point
              and {k.stockout_risk ?? 0} are critical. Open the AI Procurement
              Center to generate recommendations, then confirm MOQ and delivery
              terms before approving.
            </p>
          </div>
        </section>
      </div>
    </>
  );
}
