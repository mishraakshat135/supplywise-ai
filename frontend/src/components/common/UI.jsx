import { X, Search, ChevronDown, Check, AlertCircle } from "lucide-react";
export function Button({ children, variant = "", className = "", ...props }) {
  return (
    <button className={`button ${variant} ${className}`} {...props}>
      {children}
    </button>
  );
}
export function Badge({ children, tone = "neutral" }) {
  return <span className={`badge ${tone}`}>{children}</span>;
}
export function SearchInput({ value, onChange, placeholder = "Search…" }) {
  return (
    <label className="search-input">
      <Search size={16} />
      <input
        value={value}
        onChange={(e) => onChange(e.target.value)}
        placeholder={placeholder}
      />
    </label>
  );
}
export function SelectField({ value, onChange, children, label }) {
  return (
    <label className="select-wrap">
      {label && <span className="sr-only">{label}</span>}
      <select value={value} onChange={(e) => onChange(e.target.value)}>
        {children}
      </select>
      <ChevronDown size={14} />
    </label>
  );
}
export function Modal({ title, onClose, children, wide = false }) {
  return (
    <div
      className="overlay"
      onMouseDown={(e) => e.target === e.currentTarget && onClose()}
    >
      <section
        className={`modal ${wide ? "wide" : ""}`}
        role="dialog"
        aria-modal="true"
        aria-label={title}
      >
        <header>
          <h2>{title}</h2>
          <button className="icon-button" onClick={onClose} aria-label="Close">
            <X size={18} />
          </button>
        </header>
        {children}
      </section>
    </div>
  );
}
export function Drawer({ title, onClose, children }) {
  return (
    <div
      className="overlay"
      onMouseDown={(e) => e.target === e.currentTarget && onClose()}
    >
      <aside
        className="drawer"
        role="dialog"
        aria-modal="true"
        aria-label={title}
      >
        <header>
          <h2>{title}</h2>
          <button className="icon-button" onClick={onClose} aria-label="Close">
            <X size={18} />
          </button>
        </header>
        {children}
      </aside>
    </div>
  );
}
export function Toast({ message, tone = "success", onClose }) {
  return (
    <div className={`toast ${tone}`} role="status">
      {tone === "success" ? <Check size={17} /> : <AlertCircle size={17} />}
      <span>{message}</span>
      <button onClick={onClose} aria-label="Dismiss">
        <X size={15} />
      </button>
    </div>
  );
}
export function EmptyState({ title, detail }) {
  return (
    <div className="empty-state">
      <div className="empty-icon">
        <Search size={19} />
      </div>
      <strong>{title}</strong>
      <p>{detail}</p>
    </div>
  );
}
