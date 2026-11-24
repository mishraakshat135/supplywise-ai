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
import { purchaseOrderService } from "../services/api/domainServices.js";
import { useAsync } from "../services/api/useAsync.js";
const tone = {
  Draft: "neutral",
  "Pending Approval": "amber",
  Approved: "teal",
  Ordered: "blue",
  Received: "green",
  Rejected: "red",
  Cancelled: "neutral",
};
export default function PurchaseOrders() {
  const {
      data: orders,
      loading,
      error: loadError,
      reload,
      setData: setOrders,
    } = useAsync(() => purchaseOrderService.list(), []),
    [q, setQ] = useState(""),
    [status, setStatus] = useState("All statuses"),
    [selected, setSelected] = useState(null);
  const rows = useMemo(
    () =>
      orders.filter(
        (o) =>
          `${o.code} ${o.supplier} ${o.items}`
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
        description="Track approval decisions and order history across purchasing."
        actions={
          <Button
            variant="secondary"
            onClick={() => window.showToast("Order export is not implemented yet.")}
          >
            Export history
          </Button>
        }
      />
      <div className="demo-banner">
        <span className="demo-dot" />{" "}
        {loadError ? `BACKEND ERROR · ${loadError}` : "LIVE DATA"}
        {!loadError && (
          <>
            {" "}
            <span className="banner-sep">·</span> Status changes are saved to
            the database. “Ordered” only records a status; no supplier is
            contacted automatically.
          </>
        )}
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
            <small>TOTAL ORDERS</small>
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
              window.showToast("No extra table options yet.")
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
                <tr key={o.id} onClick={() => openOrder(o)}>
                  <td>
                    <b className="order-id">{o.code}</b>
                    <small className="unit-label">Created {o.date}</small>
                  </td>
                  <td>{o.supplier}</td>
                  <td>
                    <span className="line-item">{o.items}</span>
                  </td>
                  <td>{o.qty}</td>
                  <td>₹{o.cost.toLocaleString("en-IN")}</td>
                  <td>{o.delivery ?? "—"}</td>
                  <td>
                    <Badge tone={tone[o.status]}>{o.status}</Badge>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
          {!loading && rows.length === 0 && (
            <EmptyState
              title="No orders match"
              detail="Change the search term or status filter."
            />
          )}
        </div>
        <div className="table-bottom">
          <span>Showing {rows.length} records</span>
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
              <b>{selected.code}</b>
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
              <b>{selected.delivery ?? "—"}</b>
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
            <CalendarDays size={15} /> Changes are saved to the backend. The
            order is never sent to a supplier automatically.
          </p>
          {["Draft", "Pending Approval", "Approved", "Ordered"].includes(
            selected.status,
          ) && (
            <div className="drawer-actions">
              {selected.status === "Draft" && (
                <Button
                  variant="primary"
                  onClick={() => change("Pending Approval")}
                >
                  Submit for approval
                </Button>
              )}
              {selected.status === "Pending Approval" && (
                <>
                  <Button
                    variant="ghost-danger"
                    onClick={() => change("Rejected")}
                  >
                    Reject
                  </Button>
                  <Button variant="primary" onClick={() => change("Approved")}>
                    Approve order
                  </Button>
                </>
              )}
              {selected.status === "Approved" && (
                <Button variant="primary" onClick={() => change("Ordered")}>
                  Mark ordered
                </Button>
              )}
              {selected.status === "Ordered" && (
                <Button variant="primary" onClick={() => change("Received")}>
                  Mark received
                </Button>
              )}
            </div>
          )}
        </Drawer>
      )}
      {/* selected closure */}
    </>
  );
  async function openOrder(o) {
    setSelected({ ...o, history: o.history || [] });
    try {
      setSelected(await purchaseOrderService.get(o.id));
    } catch (e) {
      window.showToast(e.message);
    }
  }
  async function change(next) {
    try {
      await purchaseOrderService.updateStatus(selected.id, next);
      setSelected(await purchaseOrderService.get(selected.id));
      await reload();
      window.showToast(`Order status changed to ${next}.`);
    } catch (e) {
      window.showToast(e.message);
    }
  }
}
