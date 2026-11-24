import { useRef, useState } from "react";
import {
  Send,
  Paperclip,
  MessageSquareText,
  FileText,
  ChevronRight,
  Plus,
  Database,
  ExternalLink,
  Info,
  Trash2,
} from "lucide-react";
import PageHeader from "../components/common/PageHeader.jsx";
import { Badge, Button } from "../components/common/UI.jsx";
import { assistantService } from "../services/api/domainServices.js";
import { useAsync } from "../services/api/useAsync.js";

const suggestions = [
  "Which products are at risk of stockout?",
  "What does the policy say about minimum order quantities?",
  "What is the approval requirement for large purchase orders?",
];

export default function Assistant() {
  const [messages, setMessages] = useState([]),
    [text, setText] = useState(""),
    [thinking, setThinking] = useState(false),
    [uploading, setUploading] = useState(false),
    [selected, setSelected] = useState(null),
    fileRef = useRef(null);
  const {
    data: docs,
    error: docsError,
    reload: reloadDocs,
  } = useAsync(() => assistantService.documents(), []);

  const ask = async (q) => {
    if (!q.trim() || thinking) return;
    setMessages((prev) => [...prev, { role: "user", text: q }]);
    setText("");
    setThinking(true);
    try {
      const r = await assistantService.ask(q);
      setMessages((prev) => [
        ...prev,
        { role: "assistant", text: r.answer, sources: r.sources || [], mode: r.mode },
      ]);
    } catch (e) {
      setMessages((prev) => [
        ...prev,
        { role: "assistant", text: `Sorry, that failed: ${e.message}`, sources: [] },
      ]);
    } finally {
      setThinking(false);
    }
  };

  const onPick = async (e) => {
    const file = e.target.files?.[0];
    e.target.value = "";
    if (!file) return;
    setUploading(true);
    try {
      const doc = await assistantService.upload(file);
      await reloadDocs();
      window.showToast(
        doc.status === "indexed"
          ? `${doc.filename} uploaded and indexed (${doc.n_chunks} chunks).`
          : `${doc.filename} uploaded but indexing failed: ${doc.error}`,
      );
    } catch (err) {
      window.showToast(err.message);
    } finally {
      setUploading(false);
    }
  };

  const remove = async (doc) => {
    if (!window.confirm(`Delete ${doc.filename}?`)) return;
    try {
      await assistantService.removeDocument(doc.id);
      await reloadDocs();
      window.showToast("Document deleted.");
    } catch (err) {
      window.showToast(err.message);
    }
  };

  const chosen = docs.find((d) => d.filename === selected);

  return (
    <>
      <PageHeader
        eyebrow="KNOWLEDGE / DOCUMENTS"
        title="AI Assistant"
        description="Ask questions about inventory, suppliers, and your policy documents."
        actions={<Badge tone="teal">LIVE ASSISTANT</Badge>}
      />
      <div className="demo-banner">
        <Info size={15} /> Answers combine live inventory facts with a search of
        the indexed policy documents. If the language model is not configured,
        the assistant says so instead of guessing.
      </div>
      <input
        ref={fileRef}
        type="file"
        accept=".pdf,.txt"
        style={{ display: "none" }}
        onChange={onPick}
      />
      <div className="assistant-layout">
        <section className="panel conversation">
          <div className="conversation-head">
            <div className="assistant-avatar">
              <MessageSquareText size={18} />
            </div>
            <div>
              <b>SupplyWise Assistant</b>
              <span>
                <i className="status-pip" /> {thinking ? "Thinking…" : "Ready"}
              </span>
            </div>
            <button
              className="icon-button"
              onClick={() => setMessages([])}
              title="New conversation"
            >
              <Plus size={18} />
            </button>
          </div>
          {messages.length === 0 ? (
            <div className="conversation-empty">
              <div className="assistant-empty-icon">
                <MessageSquareText size={22} />
              </div>
              <h2>What can I help you find?</h2>
              <p>
                Ask about stock levels, suppliers or the procurement policy.
              </p>
              <div className="suggested-questions">
                {suggestions.map((s) => (
                  <button key={s} onClick={() => ask(s)}>
                    {s}
                    <ChevronRight size={15} />
                  </button>
                ))}
              </div>
            </div>
          ) : (
            <div className="message-list">
              {messages.map((m, i) => (
                <div className={`message ${m.role}`} key={i}>
                  <div className="message-avatar">
                    {m.role === "user" ? "AM" : "S"}
                  </div>
                  <div className="message-body">
                    <div className="message-name">
                      {m.role === "user" ? "You" : "SupplyWise Assistant"}
                    </div>
                    <p style={{ whiteSpace: "pre-wrap" }}>{m.text}</p>
                    {m.sources?.length > 0 && (
                      <div className="citations">
                        <small>SOURCES</small>
                        {m.sources.map((src) => (
                          <button
                            key={src}
                            onClick={() => setSelected(src.split(" · ")[0])}
                          >
                            <FileText size={13} />
                            {src}
                            <ExternalLink size={12} />
                          </button>
                        ))}
                      </div>
                    )}
                  </div>
                </div>
              ))}
              {thinking && (
                <div className="message assistant">
                  <div className="message-avatar">S</div>
                  <div className="message-body">
                    <p>Searching inventory and policy documents…</p>
                  </div>
                </div>
              )}
            </div>
          )}
          <form
            className="chat-composer"
            onSubmit={(e) => {
              e.preventDefault();
              ask(text);
            }}
          >
            <button
              type="button"
              className="icon-button"
              aria-label="Attach a document"
              title="Upload a PDF or TXT document"
              disabled={uploading}
              onClick={() => fileRef.current?.click()}
            >
              <Paperclip size={17} />
            </button>
            <input
              value={text}
              onChange={(e) => setText(e.target.value)}
              placeholder="Ask about inventory, suppliers, or policy…"
              aria-label="Your question"
            />
            <Button
              variant="primary"
              type="submit"
              disabled={!text.trim() || thinking}
              aria-label="Send question"
            >
              <Send size={16} />
            </Button>
          </form>
          <div className="composer-caption">
            Verify important decisions against the source documents.
          </div>
        </section>
        <aside className="assistant-side">
          <section className="panel docs-panel">
            <div className="panel-heading">
              <div>
                <h2>Knowledge sources</h2>
                <p>{docs.length} document(s) available</p>
              </div>
              <Database size={16} />
            </div>
            {docs.map((d) => (
              <div
                key={`${d.id ?? "repo"}-${d.filename}`}
                className={`document-row ${selected === d.filename ? "selected" : ""}`}
                onClick={() => setSelected(d.filename)}
              >
                <div className="file-icon">
                  <FileText size={17} />
                </div>
                <div>
                  <b>{d.filename}</b>
                  <span>
                    {d.source === "repository" ? "Built-in" : "Uploaded"} ·{" "}
                    {d.status}
                  </span>
                </div>
                {!d.readonly ? (
                  <button
                    className="icon-button"
                    aria-label={`Delete ${d.filename}`}
                    onClick={(e) => {
                      e.stopPropagation();
                      remove(d);
                    }}
                  >
                    <Trash2 size={15} />
                  </button>
                ) : (
                  <ChevronRight size={15} />
                )}
              </div>
            ))}
            {docs.length === 0 && (
              <div className="doc-note">No documents yet. Upload a PDF or TXT file.</div>
            )}
            <Button
              variant="secondary"
              className="full-button"
              disabled={uploading}
              onClick={() => fileRef.current?.click()}
            >
              <Plus size={15} /> {uploading ? "Uploading…" : "Add document"}
            </Button>
          </section>
          <section className="panel source-panel">
            <div className="panel-heading">
              <div>
                <h2>Document details</h2>
                <p>Select a document or a citation</p>
              </div>
            </div>
            <div className="source-preview">
              <div className="source-meta">
                <FileText size={14} />
                <span>{selected || "No document selected"}</span>
              </div>
              {chosen ? (
                <p>
                  Status: {chosen.status}
                  {chosen.n_chunks != null
                    ? ` · ${chosen.n_chunks} indexed chunks`
                    : ""}
                  {chosen.size_bytes != null
                    ? ` · ${Math.round(chosen.size_bytes / 1024) || 1} KB`
                    : ""}
                  {chosen.error ? ` · ${chosen.error}` : ""}
                </p>
              ) : (
                <p>Click a document above to see its indexing status.</p>
              )}
            </div>
          </section>
          <section className="panel connection-panel">
            <span className="connection-icon">
              <Database size={16} />
            </span>
            <div>
              <b>Backend connection</b>
              <span>{docsError ? docsError : "Connected to the API"}</span>
            </div>
            <Badge tone={docsError ? "red" : "green"}>
              {docsError ? "OFFLINE" : "ONLINE"}
            </Badge>
          </section>
        </aside>
      </div>
    </>
  );
}
