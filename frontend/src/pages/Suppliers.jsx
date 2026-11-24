import { useMemo, useState } from "react";
import {
  Truck,
  SlidersHorizontal,
  ArrowUpDown,
  Clock3,
  PackageCheck,
  ShieldCheck,
} from "lucide-react";
import PageHeader from "../components/common/PageHeader.jsx";
import {
  Badge,
  SearchInput,
  SelectField,
  Drawer,
  Button,
  EmptyState,
  Modal,
} from "../components/common/UI.jsx";
import { supplierService } from "../services/api/domainServices.js";
import { post } from "../services/api/apiClient.js";
import { useAsync } from "../services/api/useAsync.js";
export default function Suppliers() {
  const {
    data: suppliers,
    loading,
    error: loadError,
    reload,
  } = useAsync(() => supplierService.list(), []);
  const [adding, setAdding] = useState(false),
    [formError, setFormError] = useState("");
  const addSupplier = async (e) => {
    e.preventDefault();
    const fd = new FormData(e.currentTarget);
    try {
      await post("/api/suppliers", {
        name: fd.get("name"),
        categories: String(fd.get("categories") || "")
          .split(",")
          .map((c) => c.trim())
          .filter(Boolean),
        reliability: Number(fd.get("reliability")),
        availability: fd.get("availability"),
      });
      setAdding(false);
      setFormError("");
      await reload();
      window.showToast("Supplier added.");
    } catch (err) {
      setFormError(err.message);
    }
  };
  const [q, setQ] = useState(""),
    [cat, setCat] = useState("All categories"),
    [selected, setSelected] = useState(null),
    [compare, setCompare] = useState([]),
    [rank, setRank] = useState("Balanced");
  const filtered = useMemo(
    () =>
      suppliers.filter(
        (s) =>
          `${s.name} ${s.code} ${s.categories.join(" ")}`
            .toLowerCase()
            .includes(q.toLowerCase()) &&
          (cat === "All categories" || s.categories.includes(cat)),
      ),
    [q, cat, suppliers],
  );
  return (
    <>
      <PageHeader
        eyebrow="OPERATIONS / SOURCING"
        title="Supplier management"
        description="Compare suppliers across price, lead time, MOQ, and documented reliability."
        actions={
          <Button
            variant="primary"
            onClick={() => setAdding(true)}
          >
            ＋ Add supplier
          </Button>
        }
      />
      <div className="demo-banner">
        <span className="demo-dot" />{" "}
        {loadError ? `BACKEND ERROR · ${loadError}` : "LIVE DATA"}
        {!loadError && (
          <>
            {" "}
            <span className="banner-sep">·</span>{" "}
            {loading
              ? "Loading from the backend…"
              : "Price, lead time and MOQ show each supplier's cheapest offer."}
          </>
        )}
      </div>
      <div className="table-toolbar">
        <SearchInput
          value={q}
          onChange={setQ}
          placeholder="Search suppliers or category…"
        />
        <SelectField value={cat} onChange={setCat}>
          <option>All categories</option>
          {["Electronics", "Packaging", "Hardware", "Chemicals"].map((x) => (
            <option key={x}>{x}</option>
          ))}
        </SelectField>
        <button
          className="button secondary compact"
          onClick={() =>
            setRank(rank === "Balanced" ? "Lowest price" : "Balanced")
          }
        >
          <ArrowUpDown size={15} /> Rank: {rank}
        </button>
        <span className="toolbar-spacer" />
        <span className="toolbar-hint">
          <SlidersHorizontal size={14} /> Criteria shown separately
        </span>
      </div>
      <div className="supplier-grid">
        {filtered.map((s) => (
          <article
            className="panel supplier-card"
            key={s.id}
            onClick={() => setSelected(s)}
          >
            <div className="supplier-card-head">
              <div className="supplier-logo">
                <Truck size={19} />
              </div>
              <div className="supplier-title">
                <h2>{s.name}</h2>
                <span>{s.code}</span>
              </div>
              <button
                className={`compare-check ${compare.includes(s.id) ? "checked" : ""}`}
                aria-label={`Select ${s.name} for comparison`}
                onClick={(e) => {
                  e.stopPropagation();
                  setCompare((prev) =>
                    prev.includes(s.id)
                      ? prev.filter((x) => x !== s.id)
                      : prev.length < 3
                        ? [...prev, s.id]
                        : prev,
                  );
                }}
              >
                {compare.includes(s.id) ? "✓" : "+"}
              </button>
            </div>
            <div className="supplier-categories">
              {s.categories.map((c) => (
                <Badge key={c}>{c}</Badge>
              ))}
            </div>
            <div className="supplier-metrics">
              <div>
                <small>UNIT PRICE</small>
                <b>{s.price ?? "—"}</b>
              </div>
              <div>
                <small>LEAD TIME</small>
                <b>
                  <Clock3 size={14} />
                  {s.lead != null ? `${s.lead} days` : "—"}
                </b>
              </div>
              <div>
                <small>MIN. ORDER</small>
                <b>
                  <PackageCheck size={14} />
                  {s.moq != null ? `${s.moq} units` : "—"}
                </b>
              </div>
            </div>
            <div className="supplier-card-foot">
              <span className="reliability">
                <ShieldCheck size={15} />
                <b>{s.reliability}%</b> on-time reliability
              </span>
              <Badge tone={s.availability === "Available" ? "green" : "amber"}>
                {s.availability}
              </Badge>
            </div>
          </article>
        ))}
      </div>
      {!loading && filtered.length === 0 && (
        <EmptyState
          title="No suppliers found"
          detail="Try a different search or category filter."
        />
      )}
      {compare.length > 0 && (
        <div className="compare-bar">
          <span>
            <b>{compare.length}</b> suppliers selected for comparison
          </span>
          <button
            className="button secondary compact"
            onClick={() => setCompare([])}
          >
            Clear
          </button>
          <button
            className="button primary compact"
            onClick={() => {
              const selectedRows = suppliers.filter((x) =>
                compare.includes(x.id),
              );
              window.showToast(
                `Compared ${selectedRows.length} suppliers: price, lead time, MOQ and reliability.`,
              );
            }}
          >
            Compare suppliers
          </button>
        </div>
      )}
      {adding && (
        <Modal title="Add supplier" onClose={() => setAdding(false)}>
          <form className="form" onSubmit={addSupplier}>
            <label>
              Supplier name
              <input name="name" required placeholder="e.g. Delta Components" />
            </label>
            <label>
              Categories (comma separated)
              <input name="categories" placeholder="Electronics, Hardware" />
            </label>
            <div className="form-row">
              <label>
                On-time reliability (%)
                <input
                  type="number"
                  name="reliability"
                  min="0"
                  max="100"
                  defaultValue="90"
                  required
                />
              </label>
              <label>
                Availability
                <select name="availability" defaultValue="Available">
                  <option>Available</option>
                  <option>Limited</option>
                  <option>Unavailable</option>
                </select>
              </label>
            </div>
            {formError && <p className="form-error">{formError}</p>}
            <div className="modal-actions">
              <Button
                variant="secondary"
                type="button"
                onClick={() => setAdding(false)}
              >
                Cancel
              </Button>
              <Button variant="primary" type="submit">
                Add supplier
              </Button>
            </div>
          </form>
        </Modal>
      )}
      {selected && (
        <Drawer title="Supplier details" onClose={() => setSelected(null)}>
          <div className="drawer-product">
            <div className="supplier-logo large">
              <Truck size={22} />
            </div>
            <div>
              <h3>{selected.name}</h3>
              <span>{selected.code}</span>
            </div>
          </div>
          <div className="detail-grid">
            <div>
              <small>PRICE BASIS</small>
              <b>{selected.price ?? "—"}</b>
            </div>
            <div>
              <small>LEAD TIME</small>
              <b>{selected.lead != null ? `${selected.lead} days` : "—"}</b>
            </div>
            <div>
              <small>MINIMUM ORDER</small>
              <b>{selected.moq != null ? `${selected.moq} units` : "—"}</b>
            </div>
            <div>
              <small>RELIABILITY</small>
              <b>{selected.reliability}%</b>
            </div>
          </div>
          <div className="drawer-section">
            <h3>Ranking criteria</h3>
            <p className="drawer-copy">
              The supplier agent scores normalized price (40%), lead time
              (25%), and reliability (35%), then ranks MOQ-feasible suppliers
              first. It runs automatically on the AI Procurement page.
            </p>
          </div>
          <Button
            variant="secondary"
            className="full-button"
            onClick={() => {
              setCompare((p) =>
                p.includes(selected.id) ? p : [...p, selected.id],
              );
              setSelected(null);
            }}
          >
            Add to comparison
          </Button>
        </Drawer>
      )}
    </>
  );
}
