import { useMemo } from "react";
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
import {
  products,
  demand,
  activity,
  purchaseOrders,
} from "../services/mock/data.js";
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
  const totalValue = useMemo(
    () => products.reduce((a, p) => a + p.stock * p.cost, 0),
    [],
  );
  const low = products.filter((p) => p.stock <= p.reorder).length;
  return (
    <>
      <PageHeader
        eyebrow="THURSDAY, OCTOBER 22, 2026"
        title="Good morning, Arjun"
        description="Here’s what needs your attention across the supply chain today."
        actions={
          <>
            <button
              className="button secondary"
              onClick={() =>
                window.showToast("Report export is a demo action.")
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
        <span className="demo-dot" /> DEMO WORKSPACE{" "}
        <span className="banner-sep">·</span> Data shown is illustrative and is
        not connected to a live inventory system.
      </div>
      <div className="kpi-grid">
        <Kpi
          label="Total products"
          value="1,284"
          change="4.2%"
          up
          icon={Package}
          tone="violet"
          detail="vs. last month"
        />
        <Kpi
          label="Inventory value"
          value={fmt(totalValue + 2150000)}
          change="2.1%"
          up
          icon={Wallet}
          tone="blue"
          detail="across 3 locations"
        />
        <Kpi
          label="Below reorder point"
          value={low}
          change="3 items"
          up={false}
          icon={TriangleAlert}
          tone="amber"
          detail="require attention"
        />
        <Kpi
          label="Stockout risk"
          value="2"
          change="1 critical"
          up={false}
          icon={ShieldAlert}
          tone="red"
          detail="within 7 days"
        />
        <Kpi
          label="Pending decisions"
          value="4"
          change="2 new"
          up
          icon={ClipboardCheck}
          tone="teal"
          detail="recommendations"
        />
      </div>
      <div className="dashboard-grid">
        <section className="panel chart-panel">
          <div className="panel-heading">
            <div>
              <h2>Demand overview</h2>
              <p>Daily units · October 2026</p>
            </div>
            <div className="chart-legend">
              <span>
                <i className="legend-dot actual" />
                Actual
              </span>
              <span>
                <i className="legend-dot forecast" />
                Illustrative forecast
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
                  name="Illustrative forecast"
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
              <Activity size={14} /> Forecast boundary <b>Oct 19</b>
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
              <p>Share of active SKUs</p>
            </div>
            <button
              className="more-button"
              onClick={() =>
                window.showToast("Category breakdown shown for demo data.")
              }
            >
              •••
            </button>
          </div>
          <div className="bar-chart">
            <ResponsiveContainer width="100%" height="100%">
              <BarChart
                data={[
                  { name: "Electronics", value: 38 },
                  { name: "Packaging", value: 26 },
                  { name: "Hardware", value: 21 },
                  { name: "Chemicals", value: 15 },
                ]}
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
                  {[0, 1, 2, 3].map((x) => (
                    <Cell
                      key={x}
                      fill={["#14b8a6", "#7182ee", "#a78bfa", "#f59e0b"][x]}
                    />
                  ))}
                </Bar>
              </BarChart>
            </ResponsiveContainer>
          </div>
          <div className="distribution-foot">
            <span>
              <i className="legend-dot actual" /> 1,284 active products
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
                window.showToast("You’re viewing the latest demo activity.")
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
                <time>{item.time}</time>
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
              <b>2 products at critical stock</b>
              <span>Bearings and control relays · review replenishment</span>
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
              <b>4 recommendations pending</b>
              <span>
                {
                  purchaseOrders.filter((o) => o.status === "Pending Approval")
                    .length
                }{" "}
                purchase order awaiting approval
              </span>
            </div>
            <Link to="/procurement" aria-label="Review recommendations">
              <ArrowRight size={16} />
            </Link>
          </div>
          <div className="summary-box">
            <div className="summary-title">
              <TrendingUp size={15} /> Operations summary{" "}
              <Badge tone="teal">DEMO</Badge>
            </div>
            <p>
              Three SKUs are below their reorder points. Two are marked critical
              in this sample. A supplier comparison is ready for review; confirm
              MOQ and delivery terms before acting.
            </p>
          </div>
        </section>
      </div>
    </>
  );
}
