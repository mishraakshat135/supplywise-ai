import { useState } from "react";
import {
  AreaChart,
  Area,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
  ReferenceLine,
} from "recharts";
import { CalendarDays, Info, TrendingUp } from "lucide-react";
import PageHeader from "../components/common/PageHeader.jsx";
import { Badge, SelectField } from "../components/common/UI.jsx";
import { demand, products } from "../services/mock/data.js";
export default function Forecasting() {
  const [horizon, setHorizon] = useState("30 days"),
    [product, setProduct] = useState("EL-2048");
  return (
    <>
      <PageHeader
        eyebrow="ANALYTICS / PLANNING"
        title="Forecasting & analytics"
        description="Explore illustrative demand patterns to support replenishment planning."
        actions={<Badge tone="amber">ILLUSTRATIVE DATA</Badge>}
      />
      <div className="demo-banner">
        <Info size={15} /> This forecast is demo data. No production
        predictions, accuracy metrics, or confidence intervals are available.
      </div>
      <div className="forecast-controls">
        <label>
          <span>PRODUCT</span>
          <SelectField value={product} onChange={setProduct}>
            {products.map((p) => (
              <option key={p.sku} value={p.sku}>
                {p.sku} · {p.name}
              </option>
            ))}
          </SelectField>
        </label>
        <label>
          <span>FORECAST HORIZON</span>
          <SelectField value={horizon} onChange={setHorizon}>
            <option>7 days</option>
            <option>30 days</option>
            <option>90 days</option>
          </SelectField>
        </label>
        <div className="forecast-meta">
          <CalendarDays size={16} />
          <span>Demo data generated Oct 22, 2026</span>
        </div>
      </div>
      <div className="forecast-kpis">
        <div className="panel forecast-stat">
          <span>Selected product</span>
          <b>{products.find((p) => p.sku === product)?.name}</b>
          <small>{product}</small>
        </div>
        <div className="panel forecast-stat">
          <span>Current stock</span>
          <b>{products.find((p) => p.sku === product)?.stock} units</b>
          <small>Illustrative inventory</small>
        </div>
        <div className="panel forecast-stat">
          <span>Forecast horizon</span>
          <b>{horizon}</b>
          <small>Sample chart window</small>
        </div>
        <div className="panel forecast-stat">
          <span>Model metadata</span>
          <b>Unavailable</b>
          <small>Not connected to model service</small>
        </div>
      </div>
      <section className="panel forecast-chart-panel">
        <div className="panel-heading">
          <div>
            <h2>Observed and predicted demand</h2>
            <p>Units per day · illustrative sample series</p>
          </div>
          <div className="chart-legend">
            <span>
              <i className="legend-dot actual" />
              Observed (demo)
            </span>
            <span>
              <i className="legend-dot forecast" />
              Predicted (demo)
            </span>
          </div>
        </div>
        <div className="big-chart">
          <ResponsiveContainer width="100%" height="100%">
            <AreaChart
              data={demand}
              margin={{ top: 18, right: 18, left: -16, bottom: 0 }}
            >
              <defs>
                <linearGradient id="forecastFill" x1="0" y1="0" x2="0" y2="1">
                  <stop offset="0%" stopColor="#818cf8" stopOpacity={0.16} />
                  <stop offset="100%" stopColor="#818cf8" stopOpacity={0} />
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
                }}
              />
              <ReferenceLine
                x="Oct 19"
                stroke="#75839a"
                strokeDasharray="4 4"
                label={{
                  value: "FORECAST START",
                  fill: "#9ca9ba",
                  fontSize: 10,
                  position: "insideTopRight",
                }}
              />
              <Area
                dataKey="actual"
                name="Observed demand (demo)"
                stroke="#14b8a6"
                fill="#14b8a6"
                fillOpacity={0.09}
                strokeWidth={2.5}
              />
              <Area
                dataKey="forecast"
                name="Predicted demand (demo)"
                stroke="#818cf8"
                fill="url(#forecastFill)"
                strokeWidth={2.5}
                strokeDasharray="6 4"
              />
            </AreaChart>
          </ResponsiveContainer>
        </div>
        <div className="forecast-chart-note">
          <TrendingUp size={16} />
          <span>
            The dotted boundary marks the start of illustrative predictions.
            Historical values and forecast series are sample data for interface
            demonstration.
          </span>
        </div>
      </section>
      <section className="panel forecast-detail">
        <div className="panel-heading">
          <div>
            <h2>Planning context</h2>
            <p>Related inventory and service metadata</p>
          </div>
        </div>
        <div className="context-grid">
          <div>
            <small>REORDER POINT</small>
            <b>{products.find((p) => p.sku === product)?.reorder} units</b>
          </div>
          <div>
            <small>SUPPLIER LEAD TIME</small>
            <b>Demo value · see supplier directory</b>
          </div>
          <div>
            <small>MAE / WAPE</small>
            <b>Not available</b>
            <span>No evaluation data provided</span>
          </div>
          <div>
            <small>MODEL VERSION</small>
            <b>Not connected</b>
            <span>Backend integration pending</span>
          </div>
        </div>
      </section>
    </>
  );
}
