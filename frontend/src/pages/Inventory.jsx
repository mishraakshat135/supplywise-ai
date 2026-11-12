import { useMemo, useState } from "react";
import {
  Plus,
  ArrowUpDown,
  MoreHorizontal,
  Package,
  Download,
} from "lucide-react";
import PageHeader from "../components/common/PageHeader.jsx";
import {
  Badge,
  Button,
  SearchInput,
  SelectField,
  Modal,
  Drawer,
  EmptyState,
} from "../components/common/UI.jsx";
import { products as initial } from "../services/mock/data.js";
export default function Inventory() {
  const [items, setItems] = useState(initial),
    [q, setQ] = useState(""),
    [category, setCategory] = useState("All categories"),
    [status, setStatus] = useState("All status"),
    [sort, setSort] = useState(false),
    [selected, setSelected] = useState(null),
    [form, setForm] = useState(null),
    [error, setError] = useState("");
  const filtered = useMemo(
    () =>
      items
        .filter(
          (p) =>
            `${p.name} ${p.sku} ${p.supplier}`
              .toLowerCase()
              .includes(q.toLowerCase()) &&
            (category === "All categories" || p.category === category) &&
            (status === "All status" ||
              (status === "Low stock"
                ? p.stock <= p.reorder
                : p.stock <= p.reorder * 0.45)),
        )
        .sort((a, b) =>
          sort ? a.name.localeCompare(b.name) : a.stock - b.stock,
        ),
    [items, q, category, status, sort],
  );
  const save = (e) => {
    e.preventDefault();
    const fd = new FormData(e.currentTarget),
      name = fd.get("name").trim(),
      sku = fd.get("sku").trim(),
      stock = Number(fd.get("stock")),
      reorder = Number(fd.get("reorder")),
      cost = Number(fd.get("cost"));
    if (!name || !sku || stock < 0 || reorder < 0 || cost <= 0) {
      setError(
        "Enter a name, SKU, non-negative quantities and a unit cost above zero.",
      );
      return;
    }
    const row = {
      id: Date.now(),
      name,
      sku,
      category: fd.get("category"),
      stock,
      reorder,
      cost,
      supplier: fd.get("supplier") || "Unassigned",
      movements: [["Today", "Product created", "—"]],
    };
    setItems((prev) =>
      form === "add"
        ? [row, ...prev]
        : prev.map((p) => (p.id === form.id ? { ...p, ...row, id: p.id } : p)),
    );
    setForm(null);
    setError("");
    window.showToast(
      form === "add"
        ? "Product added to this demo session."
        : "Product updated in this demo session.",
    );
  };
  return (
    <>
      <PageHeader
        eyebrow="OPERATIONS / CATALOG"
        title="Inventory"
        description="Track stock levels, replenishment thresholds, and product movement."
        actions={
          <>
            <Button
              variant="secondary"
              onClick={() =>
                window.showToast("Inventory export is a demo action.")
              }
            >
              <Download size={15} /> Export
            </Button>
            <Button variant="primary" onClick={() => setForm("add")}>
              <Plus size={16} /> Add product
            </Button>
          </>
        }
      />
      <div className="demo-banner">
        <span className="demo-dot" /> DEMO DATA{" "}
        <span className="banner-sep">·</span> Changes stay in this browser
        session and are not sent to a backend.
      </div>
      <div className="table-toolbar">
        <SearchInput
          value={q}
          onChange={setQ}
          placeholder="Search SKU, product, supplier…"
        />
        <SelectField value={category} onChange={setCategory}>
          <option>All categories</option>
          {[...new Set(items.map((p) => p.category))].map((x) => (
            <option key={x}>{x}</option>
          ))}
        </SelectField>
        <SelectField value={status} onChange={setStatus}>
          <option>All status</option>
          <option>Low stock</option>
          <option>Critical</option>
        </SelectField>
        <button
          className="button secondary compact"
          onClick={() => setSort(!sort)}
        >
          <ArrowUpDown size={15} /> Sort {sort ? "A–Z" : "by stock"}
        </button>
      </div>
      <section className="panel table-panel">
        <div className="table-caption">
          <div>
            <b>Products</b>
            <span>
              {filtered.length} of {items.length} items
            </span>
          </div>
          <button
            className="icon-button"
            aria-label="More table options"
            onClick={() =>
              window.showToast("Table options are not configured in this demo.")
            }
          >
            <MoreHorizontal size={18} />
          </button>
        </div>
        <div className="table-scroll">
          <table>
            <thead>
              <tr>
                <th>PRODUCT</th>
                <th>CATEGORY</th>
                <th>AVAILABLE</th>
                <th>REORDER POINT</th>
                <th>UNIT COST</th>
                <th>STATUS</th>
                <th></th>
              </tr>
            </thead>
            <tbody>
              {filtered.map((p) => {
                const critical = p.stock <= p.reorder * 0.45,
                  low = p.stock <= p.reorder;
                return (
                  <tr key={p.id} onClick={() => setSelected(p)}>
                    <td>
                      <div className="product-cell">
                        <div className="product-avatar">
                          <Package size={16} />
                        </div>
                        <div>
                          <b>{p.name}</b>
                          <small>
                            {p.sku} <span className="muted-dot">·</span>{" "}
                            {p.supplier}
                          </small>
                        </div>
                      </div>
                    </td>
                    <td>{p.category}</td>
                    <td>
                      <b>{p.stock}</b>
                      <small className="unit-label">units</small>
                    </td>
                    <td>
                      {p.reorder} <small className="unit-label">units</small>
                    </td>
                    <td>
                      ₹
                      {p.cost.toLocaleString("en-IN", {
                        maximumFractionDigits: 2,
                      })}
                    </td>
                    <td>
                      <Badge tone={critical ? "red" : low ? "amber" : "green"}>
                        {critical ? "Critical" : low ? "Low stock" : "Healthy"}
                      </Badge>
                    </td>
                    <td>
                      <button
                        className="row-menu"
                        onClick={(e) => {
                          e.stopPropagation();
                          setForm(p);
                        }}
                        aria-label={`Edit ${p.name}`}
                      >
                        <MoreHorizontal size={18} />
                      </button>
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
          {filtered.length === 0 && (
            <EmptyState
              title="No products match"
              detail="Try changing your search or filters."
            />
          )}
        </div>
        <div className="table-bottom">
          <span>
            Showing {filtered.length ? 1 : 0}–{filtered.length} of{" "}
            {filtered.length} products
          </span>
          <div>
            <button className="button secondary compact" disabled>
              Previous
            </button>
            <button className="button secondary compact" disabled>
              Next
            </button>
          </div>
        </div>
      </section>
      {(form === "add" || (form !== null && typeof form === "object")) && (
        <Modal
          title={form === "add" ? "Add product" : "Edit product"}
          onClose={() => {
            setForm(null);
            setError("");
          }}
        >
          <form className="form" onSubmit={save}>
            <label>
              Product name
              <input
                name="name"
                defaultValue={form === "add" ? "" : form.name}
                required
                placeholder="e.g. Hydraulic pump"
              />
            </label>
            <label>
              SKU
              <input
                name="sku"
                defaultValue={form === "add" ? "" : form.sku}
                required
                placeholder="e.g. MT-1024"
              />
            </label>
            <label>
              Category
              <select
                name="category"
                defaultValue={form === "add" ? "Electronics" : form.category}
              >
                {["Electronics", "Packaging", "Hardware", "Chemicals"].map(
                  (c) => (
                    <option key={c}>{c}</option>
                  ),
                )}
              </select>
            </label>
            <div className="form-row">
              <label>
                Available units
                <input
                  type="number"
                  min="0"
                  name="stock"
                  defaultValue={form === "add" ? "" : form.stock}
                  required
                />
              </label>
              <label>
                Reorder point
                <input
                  type="number"
                  min="0"
                  name="reorder"
                  defaultValue={form === "add" ? "" : form.reorder}
                  required
                />
              </label>
            </div>
            <label>
              Unit cost (₹)
              <input
                type="number"
                min="0.01"
                step="0.01"
                name="cost"
                defaultValue={form === "add" ? "" : form.cost}
                required
              />
            </label>
            <label>
              Supplier
              <input
                name="supplier"
                defaultValue={form === "add" ? "" : form.supplier}
                placeholder="Supplier name"
              />
            </label>
            {error && <p className="form-error">{error}</p>}
            <div className="modal-actions">
              <Button
                variant="secondary"
                type="button"
                onClick={() => setForm(null)}
              >
                Cancel
              </Button>
              <Button variant="primary" type="submit">
                {form === "add" ? "Add product" : "Save changes"}
              </Button>
            </div>
          </form>
        </Modal>
      )}
      {selected && (
        <Drawer title="Product details" onClose={() => setSelected(null)}>
          <div className="drawer-product">
            <div className="product-avatar large">
              <Package size={21} />
            </div>
            <div>
              <h3>{selected.name}</h3>
              <span>
                {selected.sku} · {selected.category}
              </span>
            </div>
          </div>
          <div className="detail-grid">
            <div>
              <small>AVAILABLE</small>
              <b>{selected.stock} units</b>
            </div>
            <div>
              <small>REORDER POINT</small>
              <b>{selected.reorder} units</b>
            </div>
            <div>
              <small>UNIT COST</small>
              <b>₹{selected.cost.toLocaleString("en-IN")}</b>
            </div>
            <div>
              <small>SUPPLIER</small>
              <b>{selected.supplier}</b>
            </div>
          </div>
          <div className="drawer-section">
            <h3>Stock movement</h3>
            {selected.movements.map((m, i) => (
              <div className="movement" key={i}>
                <span>
                  <b>{m[1]}</b>
                  <small>{m[0]}</small>
                </span>
                <strong
                  className={m[2].startsWith("+") ? "positive" : "negative"}
                >
                  {m[2]}
                </strong>
              </div>
            ))}
          </div>
          <Button
            variant="secondary"
            className="full-button"
            onClick={() => {
              setForm(selected);
              setSelected(null);
            }}
          >
            Edit product
          </Button>
        </Drawer>
      )}
    </>
  );
}
