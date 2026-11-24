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
import { inventoryService, supplierService } from "../services/api/domainServices.js";
import { useAsync } from "../services/api/useAsync.js";
export default function Inventory() {
  const {
      data: items,
      loading,
      error: loadError,
      reload,
    } = useAsync(() => inventoryService.list(), []),
    { data: supplierList } = useAsync(() => supplierService.list(), []),
    [saving, setSaving] = useState(false),
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
  const save = async (e) => {
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
    const body = { name, sku, category: fd.get("category"), stock, reorder, cost };
    const supplierId = Number(fd.get("supplier_id")) || null;
    if (supplierId) body.supplier_id = supplierId;
    const adding = form === "add";
    setSaving(true);
    try {
      if (adding) await inventoryService.create(body);
      else await inventoryService.update(form.id, body);
      setForm(null);
      setError("");
      await reload();
      window.showToast(adding ? "Product added." : "Product updated.");
    } catch (err) {
      setError(err.message);
    } finally {
      setSaving(false);
    }
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
                window.showToast("Inventory export is not implemented yet.")
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
        <span className="demo-dot" />{" "}
        {loadError ? `BACKEND ERROR · ${loadError}` : "LIVE DATA"}
        {!loadError && (
          <>
            {" "}
            <span className="banner-sep">·</span>{" "}
            {loading
              ? "Loading from the backend…"
              : "Changes are saved to the database."}
          </>
        )}
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
                            {p.supplier || "Unassigned"}
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
          {!loading && filtered.length === 0 && (
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
              <select
                name="supplier_id"
                defaultValue={form === "add" ? "" : (form.supplier_id ?? "")}
              >
                <option value="">Unassigned / keep current</option>
                {(supplierList || []).map((s) => (
                  <option key={s.id} value={s.id}>
                    {s.name}
                  </option>
                ))}
              </select>
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
              <Button variant="primary" type="submit" disabled={saving}>
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
              <b>{selected.supplier || "Unassigned"}</b>
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
