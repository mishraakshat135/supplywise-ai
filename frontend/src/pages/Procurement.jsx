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
import { Badge, Button, Drawer } from "../components/common/UI.jsx";
import { products, suppliers } from "../services/mock/data.js";
const recommendations = [
  {
    id: "REC-104",
    product: products[0],
    forecast: 48,
    quantity: 40,
    supplier: suppliers[0],
    cost: 99200,
    eta: 5,
    reason:
      "On-hand stock is below the reorder point. Selected supplier meets the MOQ and has the shortest feasible delivery time in this comparison.",
  },
  {
    id: "REC-102",
    product: products[6],
    forecast: 36,
    quantity: 50,
    supplier: suppliers[2],
    cost: 21500,
    eta: 3,
    reason:
      "Critical stock threshold crossed. Suggested quantity covers illustrative forecast demand; supplier MOQ is compatible.",
  },
  {
    id: "REC-099",
    product: products[5],
    forecast: 82,
    quantity: 80,
    supplier: suppliers[3],
    cost: 14880,
    eta: 4,
    reason:
      "Current stock is below reorder point. PackRight demo offer meets the proposed quantity.",
  },
];
const stages = [
  ["Detect need", Package],
  ["Compare suppliers", Truck],
  ["Check policy", FileSearch],
  ["Your decision", ClipboardCheck],
];
export default function Procurement() {
  const [rows, setRows] = useState(
      recommendations.map((r) => ({ ...r, status: "Pending review" })),
    ),
    [selected, setSelected] = useState(null);
  const act = (id, status) => {
    setRows((a) => a.map((r) => (r.id === id ? { ...r, status } : r)));
    setSelected(null);
    window.showToast(
      `Recommendation ${status.toLowerCase()} in this demo session.`,
    );
  };
  return (
    <>
      <PageHeader
        eyebrow="OPERATIONS / DECISION WORKSPACE"
        title="AI Procurement Center"
        description="Review replenishment signals, supplier options, and policy evidence before taking action."
        actions={
          <Button
            variant="secondary"
            onClick={() =>
              window.showToast(
                "This page uses precomputed demo recommendations.",
              )
            }
          >
            ↻ Refresh demo
          </Button>
        }
      />
      <div className="demo-banner">
        <span className="demo-dot" /> SIMULATED WORKFLOW{" "}
        <span className="banner-sep">·</span> Agent findings and recommendations
        below are illustrative; no agents were run for this session.
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
          <GitBranch size={15} /> Multi-agent review{" "}
          <span className="sim-tag">SIMULATED</span>
        </div>
      </div>
      <div className="recommendation-list">
        {rows.map((r) => (
          <article className="panel recommendation" key={r.id}>
            <div className="rec-main">
              <div className="rec-product-icon">
                <Package size={19} />
              </div>
              <div className="rec-product">
                <div className="rec-id">
                  {r.id} <span>·</span> {r.product.sku}
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
                  TOP ELIGIBLE SUPPLIER <span>· DEMO</span>
                </div>
                <b>{r.supplier.name}</b>
                <span>
                  {r.supplier.lead} day lead · MOQ {r.supplier.moq} ·{" "}
                  {r.supplier.reliability}% illustrative reliability
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
                  <b>₹{r.cost.toLocaleString("en-IN")}</b>
                </div>
                <div>
                  <small>EXPECTED DELIVERY</small>
                  <b>{r.eta} days</b>
                </div>
              </div>
            </div>
            <div className="agent-findings">
              <div>
                <span className="agent-dot teal" />
                <b>Procurement</b>
                <span>
                  Below reorder point; proposed quantity is illustrative.
                </span>
              </div>
              <div>
                <span className="agent-dot blue" />
                <b>Supplier</b>
                <span>
                  MOQ-feasible alternative found; price and lead time shown
                  separately.
                </span>
              </div>
              <div>
                <span className="agent-dot violet" />
                <b>Policy analyst</b>
                <span>
                  MOQ must be met; orders over ₹100,000 require manager approval
                  (sample policy).
                </span>
              </div>
            </div>
            <div className="rec-bottom">
              <button className="evidence-link" onClick={() => setSelected(r)}>
                <Info size={14} /> Recommendation details & evidence
              </button>
              <div className="rec-actions">
                {r.status === "Pending review" ? (
                  <>
                    <Button
                      variant="ghost-danger"
                      onClick={() => act(r.id, "Rejected")}
                    >
                      <X size={14} /> Reject
                    </Button>
                    <Button
                      variant="secondary"
                      onClick={() => act(r.id, "Flagged")}
                    >
                      <Flag size={14} /> Flag
                    </Button>
                    <Button
                      variant="primary"
                      onClick={() => act(r.id, "Approved")}
                    >
                      <Check size={15} /> Approve recommendation
                    </Button>
                  </>
                ) : (
                  <Button
                    variant="secondary"
                    onClick={() => act(r.id, "Pending review")}
                  >
                    Return to review
                  </Button>
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
            <Badge tone="teal">SIMULATED AGENT OUTPUT</Badge>
            <h3 className="drawer-title">{selected.product.name}</h3>
            <p className="drawer-copy">{selected.reason}</p>
          </div>
          <div className="drawer-section">
            <h3>Evidence & constraints</h3>
            <div className="evidence-card">
              <b>POL-001 · Sample Procurement Policy · §3</b>
              <p>
                “The purchase order quantity must meet the supplier's agreed
                minimum order quantity (MOQ). Any exception requires written
                approval from the procurement manager.”
              </p>
              <small>
                Sample file in repository · synthetic test document · passage
                shown for context, not retrieved in this demo.
              </small>
            </div>
            <div className="evidence-card">
              <b>POL-001 · §5 Approval Requirements</b>
              <p>
                Purchase orders exceeding ₹100,000 require procurement manager
                approval before issue.
              </p>
              <small>Quoted from the sample policy file.</small>
            </div>
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
                <b>Supplier MOQ</b>
                <small>
                  {selected.supplier.moq} units · proposed {selected.quantity}
                </small>
              </span>
              <Badge tone="green">Compatible</Badge>
            </div>
            <div className="movement">
              <span>
                <b>Estimated total</b>
                <small>{selected.quantity} × illustrative unit price</small>
              </span>
              <strong>₹{selected.cost.toLocaleString("en-IN")}</strong>
            </div>
          </div>
          <div className="drawer-note">
            <Info size={15} /> Approval updates this local demo only. No
            purchase order is created or sent.
          </div>
          <div className="drawer-actions">
            <Button
              variant="secondary"
              onClick={() => act(selected.id, "Flagged")}
            >
              <Flag size={14} /> Flag
            </Button>
            <Button
              variant="primary"
              onClick={() => act(selected.id, "Approved")}
            >
              <Check size={15} /> Approve
            </Button>
          </div>
        </Drawer>
      )}
    </>
  );
}
