import { useState } from "react";
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
} from "lucide-react";
import PageHeader from "../components/common/PageHeader.jsx";
import { Badge, Button } from "../components/common/UI.jsx";
const suggestions = [
  "Which products are at risk of stockout?",
  "What does the sample policy say about minimum order quantities?",
  "Why was Northstar recommended?",
];
const answers = [
  {
    match: /stockout|risk|replenish/i,
    text: "In this illustrative inventory snapshot, 3 products are below their reorder points: Industrial pressure sensor (18 available, reorder at 30), Motor control relay (9 vs. 24), and Precision bearing 6204 (7 vs. 20). These are demo fixtures, not live stock levels.",
    sources: [
      "Inventory demo fixture · EL-2048",
      "Inventory demo fixture · EL-3091",
      "Inventory demo fixture · MT-0904",
    ],
  },
  {
    match: /policy|minimum|moq/i,
    text: "The sample procurement policy says purchase quantities must meet the supplier’s agreed minimum order quantity (MOQ). An exception requires written approval from the procurement manager. The file is labeled synthetic and is not an official company policy.",
    sources: [
      "procurement_policy.txt · §3 Minimum Order Quantity · sample document",
    ],
  },
  {
    match: /northstar|supplier|recommended|compare/i,
    text: "For the illustrative EL-2048 scenario, Northstar has a 5-day lead time, MOQ of 10, and 96% demo reliability. The repository supplier agent ranks on normalized price (40%), lead time (25%), and reliability (35%), prioritizing MOQ-feasible offers. No agent was run for this response.",
    sources: [
      "Supplier demo fixture · SUP-014",
      "backend/app/agents/supplier_agent.py · ranking weights",
    ],
  },
];
export default function Assistant() {
  const [messages, setMessages] = useState([]),
    [text, setText] = useState(""),
    [selected, setSelected] = useState("procurement_policy.txt");
  const ask = (q) => {
    if (!q.trim()) return;
    const answer = answers.find((a) => a.match.test(q)) || {
      text: "I don’t have enough evidence in the available sample data to answer that reliably. Try asking about the demo inventory, supplier fields, or the sample procurement policy.",
      sources: [],
    };
    setMessages((prev) => [
      ...prev,
      { role: "user", text: q },
      { role: "assistant", text: answer.text, sources: answer.sources },
    ]);
    setText("");
  };
  return (
    <>
      <PageHeader
        eyebrow="KNOWLEDGE / DOCUMENTS"
        title="AI Assistant"
        description="Ask questions about inventory, suppliers, and the sample policy documents."
        actions={<Badge tone="teal">DEMO ASSISTANT</Badge>}
      />
      <div className="demo-banner">
        <Info size={15} /> Responses are simulated from the included sample
        data. No RAG retrieval or language model is called from this frontend.
      </div>
      <div className="assistant-layout">
        <section className="panel conversation">
          <div className="conversation-head">
            <div className="assistant-avatar">
              <MessageSquareText size={18} />
            </div>
            <div>
              <b>SupplyWise Assistant</b>
              <span>
                <i className="status-pip" /> Sample knowledge enabled
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
                Ask a question to explore the sample inventory and procurement
                context.
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
                    <p>{m.text}</p>
                    {m.sources?.length > 0 && (
                      <div className="citations">
                        <small>DEMO SOURCES</small>
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
              title="Uploads are not enabled in this demo"
              onClick={() =>
                window.showToast("Document upload requires backend processing.")
              }
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
              disabled={!text.trim()}
              aria-label="Send question"
            >
              <Send size={16} />
            </Button>
          </form>
          <div className="composer-caption">
            Demo responses are illustrative. Verify decisions against source
            documents.
          </div>
        </section>
        <aside className="assistant-side">
          <section className="panel docs-panel">
            <div className="panel-heading">
              <div>
                <h2>Knowledge sources</h2>
                <p>Available in this demo</p>
              </div>
              <Database size={16} />
            </div>
            <div
              className="document-row selected"
              onClick={() => setSelected("procurement_policy.txt")}
            >
              <div className="file-icon">
                <FileText size={17} />
              </div>
              <div>
                <b>procurement_policy.txt</b>
                <span>Sample policy · synthetic</span>
              </div>
              <ChevronRight size={15} />
            </div>
            <div className="doc-note">
              One sample policy document is present in the repository. Citations
              in this UI are illustrative; they are not fetched using the RAG
              system.
            </div>
            <Button
              variant="secondary"
              className="full-button"
              onClick={() =>
                window.showToast(
                  "File upload is not enabled until document API contracts are defined.",
                )
              }
            >
              <Plus size={15} /> Add document
            </Button>
          </section>
          <section className="panel source-panel">
            <div className="panel-heading">
              <div>
                <h2>Evidence preview</h2>
                <p>Sample document excerpt</p>
              </div>
              <Badge tone="amber">SYNTHETIC</Badge>
            </div>
            <div className="source-preview">
              <div className="source-meta">
                <FileText size={14} />
                <span>{selected || "procurement_policy.txt"}</span>
              </div>
              <h3>Minimum Order Quantity</h3>
              <p>
                “The purchase order quantity must meet the supplier's agreed
                minimum order quantity (MOQ). Any exception requires written
                approval from the procurement manager.”
              </p>
              <span className="page-ref">Sample file · section 3</span>
            </div>
            <div className="source-warning">
              <Info size={14} /> Test document only. Not official company
              policy.
            </div>
          </section>
          <section className="panel connection-panel">
            <span className="connection-icon">
              <Database size={16} />
            </span>
            <div>
              <b>Backend connection</b>
              <span>Not configured · demo mode</span>
            </div>
            <Badge>OFFLINE</Badge>
          </section>
        </aside>
      </div>
    </>
  );
}
