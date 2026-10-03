"use client";

import { FormEvent, useEffect, useState } from "react";

type Doc = { id: string; original_filename: string; size_bytes: number; status: string; created_at: string };
type Citation = { document_id: string; filename: string; chunk_index: number; score: number };
type Message = { role: "user" | "assistant"; content: string; citations?: Citation[] };
const API = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

async function api(path: string, options: RequestInit = {}) {
  const headers = new Headers(options.headers); const token = window.localStorage.getItem("ai_ops_token");
  if (token) headers.set("Authorization", `Bearer ${token}`);
  const response = await fetch(`${API}${path}`, { ...options, headers });
  if (response.status === 401 || response.status === 403) throw new Error("ACCESS_DENIED");
  if (!response.ok) throw new Error("REQUEST_FAILED"); return response.json();
}

export default function Home() {
  const [token, setToken] = useState<string | null>(null);
  useEffect(() => setToken(window.localStorage.getItem("ai_ops_token")), []);
  if (!token) return <SignIn onSuccess={(value) => { window.localStorage.setItem("ai_ops_token", value); setToken(value); }} />;
  return <Workspace onSignOut={() => { window.localStorage.removeItem("ai_ops_token"); setToken(null); }} />;
}

function SignIn({ onSuccess }: { onSuccess: (token: string) => void }) {
  const [email, setEmail] = useState("user@example.com"); const [error, setError] = useState(""); const [loading, setLoading] = useState(false);
  const submit = async (event: FormEvent) => { event.preventDefault(); setLoading(true); setError(""); try { const data = await api("/auth/dev-login", { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ email }) }); onSuccess(data.access_token); } catch { setError("We couldn’t sign you in. Check the email and try again."); } finally { setLoading(false); } };
  return <main className="auth-shell"><section className="auth-card"><div className="brand-mark"><span>✦</span> Northstar</div><p className="eyebrow">AI operations platform</p><h1>Bring your company knowledge into focus.</h1><p className="muted">Search trusted internal documents and ask grounded questions with sources attached.</p><form onSubmit={submit} className="auth-form"><label htmlFor="email">Work email</label><input id="email" type="email" value={email} onChange={(e) => setEmail(e.target.value)} required /><button className="primary" disabled={loading}>{loading ? "Signing in…" : <>Continue <span>→</span></>}</button>{error && <p className="error" role="alert">{error}</p>}</form><p className="fine-print">Development sign-in · No password required</p></section><aside className="auth-aside"><span className="aside-label">A calmer way to work</span><div className="quote">“The answer is only as useful as the source behind it.”</div><div className="aside-rule" /><p>Keep decisions close to the context that makes them trustworthy.</p></aside></main>;
}

function Workspace({ onSignOut }: { onSignOut: () => void }) {
  const [view, setView] = useState<"chat" | "documents">("chat"); const [docs, setDocs] = useState<Doc[]>([]); const [error, setError] = useState(""); const [loading, setLoading] = useState(false);
  const load = async () => { setLoading(true); try { setDocs(await api("/api/v1/documents")); setError(""); } catch { setError("Couldn’t load your documents."); } finally { setLoading(false); } };
  useEffect(() => { load(); }, []);
  const upload = async (file: File) => { const body = new FormData(); body.append("file", file); setLoading(true); setError(""); try { const doc = await api("/api/v1/documents/upload", { method: "POST", body }); await api(`/api/v1/documents/${doc.id}/index`, { method: "POST" }); await load(); } catch { setError("Upload or indexing failed. Use a UTF-8 text or Markdown file."); } finally { setLoading(false); } };
  return <div className="app-shell"><header className="topbar"><div className="brand-mark"><span>✦</span> Northstar</div><div className="topbar-actions"><span className="status-dot">Connected</span><button className="avatar" onClick={onSignOut} aria-label="Sign out">U</button></div></header><div className="app-layout"><aside className="sidebar"><p className="eyebrow">Workspace</p><button className={`nav-item ${view === "chat" ? "active" : ""}`} onClick={() => setView("chat")}>⌁ &nbsp; Ask knowledge</button><button className={`nav-item ${view === "documents" ? "active" : ""}`} onClick={() => setView("documents")}>□ &nbsp; Documents <span className="nav-count">{docs.length}</span></button><div className="sidebar-bottom"><p className="eyebrow">Today</p><p className="sidebar-note">Your workspace is ready for a question.</p></div></aside><main className="content">{view === "chat" ? <Chat /> : <Documents docs={docs} loading={loading} error={error} upload={upload} retry={load} />}</main></div></div>;
}

function Chat() {
  const [messages, setMessages] = useState<Message[]>([]); const [input, setInput] = useState(""); const [loading, setLoading] = useState(false); const [error, setError] = useState("");
  const send = async (event: FormEvent) => { event.preventDefault(); if (!input.trim() || loading) return; const text = input.trim(); setInput(""); setMessages((m) => [...m, { role: "user", content: text }]); setLoading(true); setError(""); try { const reply = await api("/api/v1/chat", { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ message: text }) }); setMessages((m) => [...m, { role: "assistant", content: reply.content, citations: reply.citations }]); } catch (e) { setError(e instanceof Error && e.message === "ACCESS_DENIED" ? "Your session no longer has access. Sign in again." : "The assistant is unavailable."); } finally { setLoading(false); } };
  return <section className="chat-view"><div className="page-heading"><div><p className="eyebrow">Knowledge assistant</p><h2>What can I help you find?</h2><p className="muted">Ask about policies, processes, and product knowledge. Every answer keeps its sources close.</p></div><span className="source-pill">⌖ Tenant-scoped</span></div>{messages.length === 0 ? <div className="starter-grid"><button onClick={() => setInput("What is our refund policy?")}><span>01</span><strong>Find a policy</strong><small>Get a concise answer with the source.</small></button><button onClick={() => setInput("Where should production secrets be stored?")}><span>02</span><strong>Locate a process</strong><small>Surface the right internal guidance.</small></button></div> : <div className="message-list">{messages.map((m, i) => <article className={`message ${m.role}`} key={`${m.role}-${i}`}><div className="message-label">{m.role === "user" ? "You" : "Northstar"}</div><p>{m.content}</p>{m.citations?.length ? <div className="citations"><span className="citation-title">Sources</span>{m.citations.map((c) => <span className="citation" key={`${c.document_id}-${c.chunk_index}`}>↗ {c.filename} · section {c.chunk_index + 1}</span>)}</div> : null}</article>)}</div>}<form className="composer" onSubmit={send}><label htmlFor="question" className="sr-only">Ask a question</label><textarea id="question" value={input} onChange={(e) => setInput(e.target.value)} placeholder="Ask your workspace…" rows={2} disabled={loading} /><div className="composer-footer"><span className="composer-hint">Answers are grounded in indexed documents</span><button className="primary send" disabled={loading || !input.trim()}>{loading ? "Thinking…" : <>Ask <span>↗</span></>}</button></div></form>{error && <div className="error-banner" role="alert">{error} <button onClick={() => window.location.reload()}>Retry</button></div>}</section>;
}

function Documents({ docs, loading, error, upload, retry }: { docs: Doc[]; loading: boolean; error: string; upload: (file: File) => void; retry: () => void }) {
  const picker = (e: React.ChangeEvent<HTMLInputElement>) => { const file = e.target.files?.[0]; if (file) upload(file); e.currentTarget.value = ""; };
  return <section><div className="page-heading"><div><p className="eyebrow">Knowledge base</p><h2>Your documents</h2><p className="muted">Upload text or Markdown to make it searchable by your workspace.</p></div><label className="primary upload-button">{loading ? "Processing…" : "Add document"}<input type="file" accept=".txt,.md,text/plain,text/markdown" disabled={loading} onChange={picker} /></label></div>{error && <div className="error-banner" role="alert">{error} <button onClick={retry}>Retry</button></div>}<div className="document-card">{loading && !docs.length ? <div className="empty-state"><div className="spinner" />Loading your documents…</div> : !docs.length ? <div className="empty-state"><div className="empty-icon">□</div><h3>Your knowledge base is empty</h3><p>Add a text or Markdown file to start asking grounded questions.</p><label className="secondary upload-button">Choose a file<input type="file" accept=".txt,.md,text/plain,text/markdown" onChange={picker} /></label></div> : <div className="document-list">{docs.map((doc) => <div className="document-row" key={doc.id}><div className="file-icon">TXT</div><div className="document-name"><strong>{doc.original_filename}</strong><span>{Math.ceil(doc.size_bytes / 1024)} KB · Added {new Date(doc.created_at).toLocaleDateString()}</span></div><span className={`status status-${doc.status}`}>{doc.status}</span></div>)}</div>}</div></section>;
}
