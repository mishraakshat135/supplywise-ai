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
} from "../components/common/UI.jsx";
import { suppliers } from "../services/mock/data.js";
export default function Suppliers() {
  const [q, setQ] = useState(""),
    [cat, setCat] = useState("All categories"),
    [selected, setSelected] = useState(null),
    [compare, setCompare] = useState([]),
    [rank, setRank] = useState("Balanced");
  const filtered = useMemo(
    () =>
      suppliers.filter(
        (s) =>
          `${s.name} ${s.id} ${s.categories.join(" ")}`
            .toLowerCase()
            .includes(q.toLowerCase()) &&
          (cat === "All categories" || s.categories.includes(cat)),
      ),
    [q, cat],
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
            onClick={() =>
              window.showToast(
                "Supplier creation requires a connected backend.",
              )
            }
          >
            ＋ Add supplier
          </Button>
        }
      />
      <div className="demo-banner">
        <span className="demo-dot" /> DEMO DATA{" "}
        <span className="banner-sep">·</span> Illustrative supplier attributes,
        not live offers or performance records.
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
                <span>{s.id}</span>
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
                <b>{s.price}</b>
              </div>
              <div>
                <small>LEAD TIME</small>
                <b>
                  <Clock3 size={14} />
                  {s.lead} days
                </b>
              </div>
              <div>
                <small>MIN. ORDER</small>
                <b>
                  <PackageCheck size={14} />
                  {s.moq} units
                </b>
              </div>
            </div>
            <div className="supplier-card-foot">
              <span className="reliability">
                <ShieldCheck size={15} />
                <b>{s.reliability}%</b> demo reliability
              </span>
              <Badge tone={s.availability === "Available" ? "green" : "amber"}>
                {s.availability}
              </Badge>
            </div>
          </article>
        ))}
      </div>
      {filtered.length === 0 && (
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
      {selected && (
        <Drawer title="Supplier details" onClose={() => setSelected(null)}>
          <div className="drawer-product">
            <div className="supplier-logo large">
              <Truck size={22} />
            </div>
            <div>
              <h3>{selected.name}</h3>
              <span>{selected.id} · Illustrative demo record</span>
            </div>
          </div>
          <div className="detail-grid">
            <div>
              <small>PRICE BASIS</small>
              <b>{selected.price}</b>
            </div>
            <div>
              <small>LEAD TIME</small>
              <b>{selected.lead} days</b>
            </div>
            <div>
              <small>MINIMUM ORDER</small>
              <b>{selected.moq} units</b>
            </div>
            <div>
              <small>RELIABILITY</small>
              <b>{selected.reliability}% demo</b>
            </div>
          </div>
          <div className="drawer-section">
            <h3>Ranking criteria</h3>
            <p className="drawer-copy">
              The repository's supplier agent scores normalized price (40%),
              lead time (25%), and reliability (35%), then ranks MOQ-feasible
              suppliers first. This screen displays illustrative values; it does
              not execute that agent.
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
