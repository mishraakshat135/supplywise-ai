import { useMemo, useState } from "react";
import {
  ClipboardList,
  ArrowUpDown,
  MoreHorizontal,
  CalendarDays,
  CheckCircle2,
  Clock3,
} from "lucide-react";
import PageHeader from "../components/common/PageHeader.jsx";
import {
  Badge,
  SearchInput,
  SelectField,
  Drawer,
  EmptyState,
  Button,
} from "../components/common/UI.jsx";
import { purchaseOrders as initial } from "../services/mock/data.js";
const tone = {
  Draft: "neutral",
  "Pending Approval": "amber",
  Approved: "teal",
  Ordered: "blue",
  Received: "green",
  Rejected: "red",
};
export default function PurchaseOrders() {
  const [orders, setOrders] = useState(initial),
    [q, setQ] = useState(""),
    [status, setStatus] = useState("All statuses"),
    [selected, setSelected] = useState(null);
  const rows = useMemo(
    () =>
      orders.filter(
        (o) =>
          `${o.id} ${o.supplier} ${o.items}`
            .toLowerCase()
            .includes(q.toLowerCase()) &&
          (status === "All statuses" || o.status === status),
      ),
    [orders, q, status],
  );
  return (
    <>
      <PageHeader
        eyebrow="OPERATIONS / ORDER HISTORY"
        title="Purchase orders"
        description="Track approval decisions and demo order history across purchasing."
        actions={
          <Button
            variant="secondary"
            onClick={() => window.showToast("Order export is a demo action.")}
          >
            Export history
          </Button>
        }
      />
      <div className="demo-banner">
        <span className="demo-dot" /> DEMO HISTORY{" "}
        <span className="banner-sep">·</span> “Ordered” and “Received” statuses
        represent local demo actions; no supplier was contacted.
      </div>
      <div className="order-summary-row">
        <div className="panel order-summary">
          <span className="summary-symbol amber">
            <Clock3 size={17} />
          </span>
          <div>
            <small>AWAITING APPROVAL</small>
            <b>
              {orders.filter((x) => x.status === "Pending Approval").length}
            </b>
          </div>
        </div>
        <div className="panel order-summary">
          <span className="summary-symbol teal">
            <CheckCircle2 size={17} />
          </span>
          <div>
            <small>APPROVED THIS MONTH</small>
            <b>
              {
                orders.filter((x) =>
                  ["Approved", "Ordered", "Received"].includes(x.status),
                ).length
              }
            </b>
          </div>
        </div>
        <div className="panel order-summary">
          <span className="summary-symbol blue">
            <ClipboardList size={17} />
          </span>
          <div>
            <small>TOTAL DEMO ORDERS</small>
            <b>{orders.length}</b>
          </div>
        </div>
      </div>
      <div className="table-toolbar">
        <SearchInput
          value={q}
          onChange={setQ}
          placeholder="Search order, supplier, product…"
        />
        <SelectField value={status} onChange={setStatus}>
          <option>All statuses</option>
          {[
            "Draft",
            "Pending Approval",
            "Approved",
            "Ordered",
            "Received",
            "Rejected",
          ].map((x) => (
            <option key={x}>{x}</option>
          ))}
        </SelectField>
        <button
          className="button secondary compact"
          onClick={() => setOrders([...orders].reverse())}
        >
          <ArrowUpDown size={15} /> Sort by date
        </button>
      </div>
      <section className="panel table-panel">
        <div className="table-caption">
          <div>
            <b>Order history</b>
            <span>{rows.length} orders</span>
          </div>
          <button
            className="icon-button"
            aria-label="More options"
            onClick={() =>
              window.showToast("Table options unavailable in demo.")
            }
          >
            <MoreHorizontal size={18} />
          </button>
        </div>
        <div className="table-scroll">
          <table>
            <thead>
              <tr>
                <th>ORDER</th>
                <th>SUPPLIER</th>
                <th>LINE ITEMS</th>
                <th>QUANTITY</th>
                <th>EST. COST</th>
                <th>EXPECTED DELIVERY</th>
                <th>STATUS</th>
              </tr>
            </thead>
            <tbody>
              {rows.map((o) => (
                <tr key={o.id} onClick={() => setSelected(o)}>
                  <td>
                    <b className="order-id">{o.id}</b>
                    <small className="unit-label">Created {o.date}</small>
                  </td>
                  <td>{o.supplier}</td>
                  <td>
                    <span className="line-item">{o.items}</span>
                  </td>
                  <td>{o.qty}</td>
                  <td>₹{o.cost.toLocaleString("en-IN")}</td>
                  <td>{o.delivery}</td>
                  <td>
                    <Badge tone={tone[o.status]}>{o.status}</Badge>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
          {rows.length === 0 && (
            <EmptyState
              title="No orders match"
              detail="Change the search term or status filter."
            />
          )}
        </div>
        <div className="table-bottom">
          <span>Showing {rows.length} demo records</span>
          <span className="pagination-note">
            Status changes are limited to actions shown in the order detail.
          </span>
        </div>
      </section>
      {selected && (
        <Drawer
          title="Purchase order details"
          onClose={() => setSelected(null)}
        >
          <div className="order-drawer-id">
            <ClipboardList size={19} />
            <div>
              <b>{selected.id}</b>
              <span>Created {selected.date}</span>
            </div>
            <Badge tone={tone[selected.status]}>{selected.status}</Badge>
          </div>
          <div className="detail-grid">
            <div>
              <small>SUPPLIER</small>
              <b>{selected.supplier}</b>
            </div>
            <div>
              <small>QUANTITY</small>
              <b>{selected.qty} units</b>
            </div>
            <div>
              <small>ESTIMATED COST</small>
              <b>₹{selected.cost.toLocaleString("en-IN")}</b>
            </div>
            <div>
              <small>EXPECTED DELIVERY</small>
              <b>{selected.delivery}</b>
            </div>
          </div>
          <div className="drawer-section">
            <h3>Line item</h3>
            <div className="movement">
              <span>
                <b>{selected.items.split(" · ")[0]}</b>
                <small>{selected.items.split(" · ")[1]}</small>
              </span>
              <strong>{selected.qty} units</strong>
            </div>
          </div>
          <div className="drawer-section">
            <h3>Approval history</h3>
            {selected.history.map((h, i) => (
              <div className="timeline-row" key={i}>
                <span
                  className={`timeline-dot ${i === selected.history.length - 1 ? "current" : ""}`}
                />
                <span>{h}</span>
              </div>
            ))}
          </div>
          <p className="drawer-note">
            <CalendarDays size={15} /> Demo timeline. Changes are local; the
            order was not sent to a supplier.
          </p>
          {["Draft", "Approved", "Ordered"].includes(selected.status) && (
            <div className="drawer-actions">
              {selected.status === "Draft" && (
                <Button
                  variant="primary"
                  onClick={() => change("Pending Approval")}
                >
                  Submit for approval
                </Button>
              )}
              {selected.status === "Approved" && (
                <Button variant="primary" onClick={() => change("Ordered")}>
                  Mark ordered (demo)
                </Button>
              )}
              {selected.status === "Ordered" && (
                <Button variant="primary" onClick={() => change("Received")}>
                  Mark received (demo)
                </Button>
              )}
            </div>
          )}
        </Drawer>
      )}
      {/* selected closure */}
    </>
  );
  function change(next) {
    setOrders((prev) =>
      prev.map((o) =>
        o.id === selected.id
          ? {
              ...o,
              status: next,
              history: [...o.history, `Oct 22 · ${next} (demo)`],
            }
          : o,
      ),
    );
    setSelected((prev) => ({
      ...prev,
      status: next,
      history: [...prev.history, `Oct 22 · ${next} (demo)`],
    }));
    window.showToast(`Order status changed to ${next} in this demo.`);
  }
}
