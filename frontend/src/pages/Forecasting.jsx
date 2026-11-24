import { useEffect, useState } from "react";
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
import { inventoryService, forecastService } from "../services/api/domainServices.js";
import { useAsync } from "../services/api/useAsync.js";

const metric = (m, ...keys) => {
  for (const k of keys) if (m && m[k] != null) return Number(m[k]).toFixed(2);
  return "Not available";
};

export default function Forecasting() {
  const { data: products, error: productsError } = useAsync(
    () => inventoryService.list(),
    [],
  );
  const [horizon, setHorizon] = useState(30),
    [productId, setProductId] = useState(null),
    [fc, setFc] = useState(null),
    [busy, setBusy] = useState(false),
    [error, setError] = useState("");

  useEffect(() => {
    if (products.length && productId == null) setProductId(products[0].id);
  }, [products, productId]);

  // Load the latest forecast for the product; create one if none exists or the horizon differs.
  useEffect(() => {
    if (productId == null) return undefined;
    let alive = true;
    (async () => {
      setBusy(true);
      setError("");
      try {
        let f;
        try {
          f = await forecastService.latest(productId);
          if (f.horizon_days !== horizon) {
            f = await forecastService.predict(productId, horizon);
          }
        } catch (e) {
          if (e.status !== 404) throw e;
          f = await forecastService.predict(productId, horizon);
        }
        if (alive) setFc(f);
      } catch (e) {
        if (alive) {
          setFc(null);
          setError(e.message);
        }
      } finally {
        if (alive) setBusy(false);
      }
    })();
    return () => {
      alive = false;
    };
  }, [productId, horizon]);

  const product = products.find((p) => p.id === productId);
  const series = fc?.series ?? [];
  const boundary = [...series].reverse().find((d) => d.actual != null)?.day;

  return (
    <>
      <PageHeader
        eyebrow="ANALYTICS / PLANNING"
        title="Forecasting & analytics"
        description="Explore demand history and predicted demand to support replenishment planning."
        actions={
          <Badge tone={fc ? "teal" : "amber"}>
            {fc ? "LIVE FORECAST" : "NO FORECAST"}
          </Badge>
        }
      />
      <div className="demo-banner">
        <Info size={15} />{" "}
        {productsError || error
          ? `BACKEND ERROR · ${productsError || error}`
          : busy
            ? "Generating forecast…"
            : fc
              ? `Forecast provider: ${fc.provider}${fc.model_version ? ` (${fc.model_version})` : ""}. Observed values are your recorded sales.`
              : "Select a product to load its forecast."}
      </div>
      <div className="forecast-controls">
        <label>
          <span>PRODUCT</span>
          <SelectField
            value={productId ?? ""}
            onChange={(v) => setProductId(Number(v))}
          >
            {products.map((p) => (
              <option key={p.id} value={p.id}>
                {p.sku} · {p.name}
              </option>
            ))}
          </SelectField>
        </label>
        <label>
          <span>FORECAST HORIZON</span>
          <SelectField value={horizon} onChange={(v) => setHorizon(Number(v))}>
            <option value={7}>7 days</option>
            <option value={30}>30 days</option>
            <option value={90}>90 days</option>
          </SelectField>
        </label>
        <div className="forecast-meta">
          <CalendarDays size={16} />
          <span>
            {fc
              ? `Generated ${new Date(fc.generated_at).toLocaleString("en-IN")}`
              : "No forecast generated yet"}
          </span>
        </div>
      </div>
      <div className="forecast-kpis">
        <div className="panel forecast-stat">
          <span>Selected product</span>
          <b>{product?.name ?? "—"}</b>
          <small>{product?.sku}</small>
        </div>
        <div className="panel forecast-stat">
          <span>Current stock</span>
          <b>{product ? `${product.stock} units` : "—"}</b>
          <small>From the inventory database</small>
        </div>
        <div className="panel forecast-stat">
          <span>Forecast horizon</span>
          <b>{horizon} days</b>
          <small>
            {fc ? `≈ ${fc.daily_average} units/day · ${fc.total} total` : ""}
          </small>
        </div>
        <div className="panel forecast-stat">
          <span>Model metadata</span>
          <b>{fc?.provider ?? "Unavailable"}</b>
          <small>{fc?.model_version ?? ""}</small>
        </div>
      </div>
      <section className="panel forecast-chart-panel">
        <div className="panel-heading">
          <div>
            <h2>Observed and predicted demand</h2>
            <p>Units per day · last 30 days observed, then forecast</p>
          </div>
          <div className="chart-legend">
            <span>
              <i className="legend-dot actual" />
              Observed
            </span>
            <span>
              <i className="legend-dot forecast" />
              Predicted
            </span>
          </div>
        </div>
        <div className="big-chart">
          <ResponsiveContainer width="100%" height="100%">
            <AreaChart
              data={series}
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
                interval="preserveStartEnd"
                minTickGap={24}
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
              {boundary && (
                <ReferenceLine
                  x={boundary}
                  stroke="#75839a"
                  strokeDasharray="4 4"
                  label={{
                    value: "FORECAST START",
                    fill: "#9ca9ba",
                    fontSize: 10,
                    position: "insideTopRight",
                  }}
                />
              )}
              <Area
                dataKey="actual"
                name="Observed demand"
                stroke="#14b8a6"
                fill="#14b8a6"
                fillOpacity={0.09}
                strokeWidth={2.5}
              />
              <Area
                dataKey="forecast"
                name="Predicted demand"
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
            The dotted line marks where observed sales end and predictions
            begin. Predictions come from the forecasting provider shown above;
            the team's trained ML model can replace it without changing this
            page.
          </span>
        </div>
      </section>
      <section className="panel forecast-detail">
        <div className="panel-heading">
          <div>
            <h2>Planning context</h2>
            <p>Related inventory and model metadata</p>
          </div>
        </div>
        <div className="context-grid">
          <div>
            <small>REORDER POINT</small>
            <b>{product ? `${product.reorder} units` : "—"}</b>
          </div>
          <div>
            <small>AVERAGE DAILY DEMAND</small>
            <b>{fc ? `${fc.daily_average} units` : "—"}</b>
          </div>
          <div>
            <small>MAE / WAPE</small>
            <b>
              {metric(fc?.metrics, "mae", "MAE")} /{" "}
              {metric(fc?.metrics, "wape", "WAPE")}
            </b>
          </div>
          <div>
            <small>MODEL VERSION</small>
            <b>{fc?.model_version ?? "—"}</b>
            <span>{fc?.provider ?? ""}</span>
          </div>
        </div>
      </section>
    </>
  );
}
