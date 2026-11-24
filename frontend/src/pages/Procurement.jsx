import { useState } from "react";
import {
  GitBranch,
  Package,
  Truck,
  FileSearch,
  ClipboardCheck,
  Check,
  Flag,
  X,
  ChevronRight,
  Info,
} from "lucide-react";
import PageHeader from "../components/common/PageHeader.jsx";
import { Badge, Button, Drawer, EmptyState } from "../components/common/UI.jsx";
import { procurementService } from "../services/api/domainServices.js";
import { useAsync } from "../services/api/useAsync.js";
const short = (text, n = 240) =>
  text && text.length > n ? `${text.slice(0, n)}…` : text;
const stages = [
  ["Detect need", Package],
  ["Compare suppliers", Truck],
  ["Check policy", FileSearch],
  ["Your decision", ClipboardCheck],
];
export default function Procurement() {
  const {
      data: rows,
      loading,
      error: loadError,
      reload,
    } = useAsync(() => procurementService.list(), []),
    [selected, setSelected] = useState(null),
    [busy, setBusy] = useState(false);
  const act = async (id, action) => {
    setBusy(true);
    try {
      await procurementService[action](id);
      await reload();
      setSelected(null);
      window.showToast(
        action === "approve"
          ? "Recommendation approved and purchase order created."
          : action === "reject"
            ? "Recommendation rejected."
            : "Recommendation flagged for follow-up.",
      );
    } catch (e) {
      window.showToast(e.message);
    } finally {
      setBusy(false);
    }
  };
  const runAnalysis = async () => {
    setBusy(true);
    window.showToast("Running forecast, supplier and policy analysis…");
    try {
      const res = await procurementService.generate({});
      await reload();
      const errs = res.errors?.length ? ` · ${res.errors.length} product(s) failed` : "";
      window.showToast(
        `${res.recommendations.length} recommendation(s) ready · ${res.no_action_needed} product(s) need no action${errs}.`,
      );
    } catch (e) {
      window.showToast(e.message);
    } finally {
      setBusy(false);
    }
  };
  const decidable = (r) => ["Pending review", "Flagged"].includes(r.status);
  return (
    <>
      <PageHeader
        eyebrow="OPERATIONS / DECISION WORKSPACE"
        title="AI Procurement Center"
        description="Review replenishment signals, supplier options, and policy evidence before taking action."
        actions={
          <Button variant="secondary" onClick={runAnalysis} disabled={busy}>
            ↻ {busy ? "Working…" : "Run analysis"}
          </Button>
        }
      />
      <div className="demo-banner">
        <span className="demo-dot" />{" "}
        {loadError ? `BACKEND ERROR · ${loadError}` : "LIVE WORKFLOW"}
        {!loadError && (
          <>
            {" "}
            <span className="banner-sep">·</span>{" "}
            {loading
              ? "Loading…"
              : "Click “Run analysis” to forecast demand, compare suppliers and check policy. Nothing is ordered until you approve."}
          </>
        )}
      </div>
      <section className="panel workflow-panel">
        <div className="workflow-head">
          <div>
            <h2>Recommendation workflow</h2>
            <p>Four stages keep the decision and its evidence visible.</p>
          </div>
          <Badge tone="teal">HUMAN REVIEW REQUIRED</Badge>
        </div>
        <div className="workflow-steps">
          {stages.map(([label, Icon], i) => (
            <div className="workflow-step" key={label}>
              <span className={`step-icon ${i < 3 ? "complete" : ""}`}>
                <Icon size={17} />
              </span>
              <div>
                <small>0{i + 1}</small>
                <b>{label}</b>
              </div>
              {i < 3 && <ChevronRight size={15} className="step-arrow" />}
            </div>
          ))}
        </div>
      </section>
      <div className="section-heading">
        <div>
          <h2>Replenishment recommendations</h2>
          <p>
            {rows.filter((r) => r.status === "Pending review").length} awaiting
            your decision
          </p>
        </div>
        <div className="agent-label">
          <GitBranch size={15} /> Multi-agent review
        </div>
      </div>
      {!loading && rows.length === 0 && (
        <EmptyState
          title="No recommendations yet"
          detail="Click “Run analysis” to check every product against its forecast and reorder point."
        />
      )}
      <div className="recommendation-list">
        {rows.map((r) => (
          <article className="panel recommendation" key={r.id}>
            <div className="rec-main">
              <div className="rec-product-icon">
                <Package size={19} />
              </div>
              <div className="rec-product">
                <div className="rec-id">
                  {r.code} <span>·</span> {r.product.sku}
                </div>
                <h3>{r.product.name}</h3>
                <div className="rec-stock">
                  <span>
                    On hand <b>{r.product.stock}</b>
                  </span>
                  <span>
                    Reorder point <b>{r.product.reorder}</b>
                  </span>
                  <span>
                    Forecast demand <b>{r.forecast} units</b>
                  </span>
                </div>
              </div>
              <Badge
                tone={
                  r.status === "Pending review"
                    ? "amber"
                    : r.status === "Approved"
                      ? "green"
                      : r.status === "Flagged"
                        ? "blue"
                        : "red"
                }
              >
                {r.status}
              </Badge>
            </div>
            <div className="rec-divider" />
            <div className="rec-details">
              <div className="supplier-recommend">
                <div className="small-label">
                  TOP ELIGIBLE SUPPLIER
                </div>
                <b>{r.supplier ? r.supplier.name : "No eligible supplier"}</b>
                <span>
                  {r.eta != null ? `${r.eta} day lead` : "—"} ·{" "}
                  {r.supplier
                    ? `${r.supplier.reliability}% reliability`
                    : "see warnings"}
                </span>
              </div>
              <div className="rec-numbers">
                <div>
                  <small>SUGGESTED QUANTITY</small>
                  <b>
                    {r.quantity} <em>units</em>
                  </b>
                </div>
                <div>
                  <small>ESTIMATED COST</small>
                  <b>₹{(r.cost ?? 0).toLocaleString("en-IN")}</b>
                </div>
                <div>
                  <small>EXPECTED DELIVERY</small>
                  <b>{r.eta != null ? `${r.eta} days` : "—"}</b>
                </div>
              </div>
            </div>
            <div className="agent-findings">
              <div>
                <span className="agent-dot teal" />
                <b>Procurement</b>
                <span>{short(r.reason) || "No explanation returned."}</span>
              </div>
              <div>
                <span className="agent-dot blue" />
                <b>Supplier</b>
                <span>
                  {r.ranked_suppliers?.length
                    ? `${r.ranked_suppliers.length} supplier(s) compared; top choice ${r.supplier?.name ?? "n/a"}.`
                    : "No supplier comparison available."}
                </span>
              </div>
              <div>
                <span className="agent-dot violet" />
                <b>Policy analyst</b>
                <span>
                  {short(r.policy_analysis) ||
                    "Policy check not available (see details)."}
                </span>
              </div>
            </div>
            <div className="rec-bottom">
              <button className="evidence-link" onClick={() => setSelected(r)}>
                <Info size={14} /> Recommendation details & evidence
              </button>
              <div className="rec-actions">
                {decidable(r) ? (
                  <>
                    <Button
                      variant="ghost-danger"
                      disabled={busy}
                      onClick={() => act(r.id, "reject")}
                    >
                      <X size={14} /> Reject
                    </Button>
                    {r.status !== "Flagged" && (
                      <Button
                        variant="secondary"
                        disabled={busy}
                        onClick={() => act(r.id, "flag")}
                      >
                        <Flag size={14} /> Flag
                      </Button>
                    )}
                    <Button
                      variant="primary"
                      disabled={busy || !r.supplier}
                      onClick={() => act(r.id, "approve")}
                    >
                      <Check size={15} /> Approve recommendation
                    </Button>
                  </>
                ) : (
                  <span className="toolbar-hint">
                    {r.purchase_order
                      ? `Purchase order ${r.purchase_order.po_number} created`
                      : `Decision recorded: ${r.status}`}
                  </span>
                )}
              </div>
            </div>
          </article>
        ))}
      </div>
      {selected && (
        <Drawer
          title="Recommendation details"
          onClose={() => setSelected(null)}
        >
          <div className="drawer-section">
            <Badge tone="teal">AGENT OUTPUT</Badge>
            <h3 className="drawer-title">{selected.product.name}</h3>
            <p className="drawer-copy">{selected.reason}</p>
          </div>
          <div className="drawer-section">
            <h3>Evidence & constraints</h3>
            {selected.policy_analysis ? (
              <div className="evidence-card">
                <b>Policy analysis</b>
                <p>{selected.policy_analysis}</p>
              </div>
            ) : (
              <p className="drawer-copy">
                No policy analysis was returned for this recommendation.
              </p>
            )}
            {Object.entries(selected.policy_sources || {}).map(([key, src]) => (
              <div className="evidence-card" key={key}>
                <b>
                  {src.source ?? key}
                  {src.page != null ? ` · page ${src.page}` : ""}
                </b>
                {(src.text ?? src.content ?? src.snippet) && (
                  <p>{src.text ?? src.content ?? src.snippet}</p>
                )}
              </div>
            ))}
            {(selected.warnings || []).map((w, i) => (
              <div className="evidence-card" key={`w${i}`}>
                <b>Warning</b>
                <p>{typeof w === "string" ? w : JSON.stringify(w)}</p>
              </div>
            ))}
          </div>
          <div className="drawer-section">
            <h3>Decision factors</h3>
            <div className="movement">
              <span>
                <b>Stock position</b>
                <small>
                  {selected.product.stock} available vs. reorder at{" "}
                  {selected.product.reorder}
                </small>
              </span>
              <Badge tone="red">Below threshold</Badge>
            </div>
            <div className="movement">
              <span>
                <b>Suggested order</b>
                <small>
                  {selected.quantity} units
                  {selected.supplier ? ` from ${selected.supplier.name}` : ""}
                </small>
              </span>
              <Badge tone={selected.requires_manager_approval ? "amber" : "green"}>
                {selected.requires_manager_approval
                  ? "Manager approval"
                  : "Standard approval"}
              </Badge>
            </div>
            <div className="movement">
              <span>
                <b>Estimated total</b>
                <small>{selected.quantity} × supplier unit price</small>
              </span>
              <strong>₹{(selected.cost ?? 0).toLocaleString("en-IN")}</strong>
            </div>
          </div>
          <div className="drawer-note">
            <Info size={15} /> Approving creates an internal purchase order
            record. Nothing is sent to a supplier.
          </div>
          {decidable(selected) && (
            <div className="drawer-actions">
              {selected.status !== "Flagged" && (
                <Button
                  variant="secondary"
                  disabled={busy}
                  onClick={() => act(selected.id, "flag")}
                >
                  <Flag size={14} /> Flag
                </Button>
              )}
              <Button
                variant="primary"
                disabled={busy || !selected.supplier}
                onClick={() => act(selected.id, "approve")}
              >
                <Check size={15} /> Approve
              </Button>
            </div>
          )}
        </Drawer>
      )}
    </>
  );
}
