"use client";
/* eslint-disable react-hooks/set-state-in-effect */

import { FormEvent, useEffect, useRef, useState } from "react";
import { api, Conversation, Document, Message } from "../lib/api";
import { MarkdownContent } from "./markdown-content";

export function Workspace({ onSignOut }: { onSignOut: () => void }) {
  const [view, setView] = useState<"chat" | "documents">("chat");
  const [documents, setDocuments] = useState<Document[]>([]);
  const [conversations, setConversations] = useState<Conversation[]>([]);
  const [conversationId, setConversationId] = useState<string | null>(null);
  const [openConversationMenu, setOpenConversationMenu] = useState<string | null>(null);
  const [conversationToDelete, setConversationToDelete] = useState<Conversation | null>(null);
  const [documentToDelete, setDocumentToDelete] = useState<Document | null>(null);
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);
  const logout = async () => {
    try {
      await api("/auth/logout", { method: "POST" });
    } finally {
      onSignOut();
    }
  };
  const loadDocuments = async () => {
    setLoading(true);
    try {
      setDocuments(await api("/api/v1/documents"));
      setError("");
    } catch {
      setError("Couldn’t load documents.");
    } finally {
      setLoading(false);
    }
  };
  const loadConversations = async () => {
    try {
      setConversations(await api("/api/v1/chat/conversations"));
    } catch {
      setError("Couldn’t load conversations.");
    }
  };
  useEffect(() => {
    loadDocuments();
    loadConversations();
  }, []);
  useEffect(() => {
    if (!documents.some((document) => ["uploaded", "processing"].includes(document.status))) {
      return;
    }
    const interval = window.setInterval(async () => {
      try {
        setDocuments(await api("/api/v1/documents"));
      } catch {
        // Keep the current document state; the next poll can recover.
      }
    }, 2000);
    return () => window.clearInterval(interval);
  }, [documents]);
  const upload = async (file: File) => {
    const body = new FormData();
    body.append("file", file);
    setLoading(true);
    try {
      const document = await api("/api/v1/documents/upload", {
        method: "POST",
        body,
      });
      await api(`/api/v1/documents/${document.id}/index`, { method: "POST" });
      await loadDocuments();
    } catch {
      setError("Upload failed. Use a PDF, UTF-8 text, or Markdown file.");
    } finally {
      setLoading(false);
    }
  };
  const deleteDocument = async (id: string) => {
    try {
      await api(`/api/v1/documents/${id}`, { method: "DELETE" });
      await loadDocuments();
      setDocumentToDelete(null);
    } catch {
      setError("Couldn’t delete the document.");
    }
  };
  const deleteConversation = async (id: string) => {
    try {
      await api(`/api/v1/chat/conversations/${id}`, { method: "DELETE" });
      setConversations((items) => items.filter((item) => item.id !== id));
      if (conversationId === id) setConversationId(null);
      setOpenConversationMenu(null);
      setConversationToDelete(null);
    } catch {
      setError("Couldn’t delete the conversation.");
    }
  };
  return (
    <div className="flex h-screen min-h-0 flex-col bg-[#f7faf8] text-[#17323a]">
      <header className="relative flex h-16 shrink-0 items-center justify-between border-b border-[#dce8e5] bg-white px-5 md:px-8">
        <div className="text-xl font-extrabold tracking-tight">
          <span className="text-[#e78361]">✦</span> Northstar
        </div>
        <nav className="absolute left-1/2 hidden -translate-x-1/2 gap-1 rounded-lg border border-[#dce8e5] bg-[#f2f8f5] p-1 sm:flex">
          <TopNavButton
            active={view === "chat"}
            onClick={() => setView("chat")}
          >
            Ask knowledge
          </TopNavButton>
          <TopNavButton
            active={view === "documents"}
            onClick={() => setView("documents")}
          >
            Documents{" "}
            <span className="ml-1 rounded-full bg-[#e4f2ee] px-1.5 text-[10px]">
              {documents.length}
            </span>
          </TopNavButton>
        </nav>
        <div className="flex items-center gap-4">
          <span className="hidden text-xs text-[#087f73] sm:inline">
            ● Connected
          </span>
          <button
            className="grid h-9 w-9 place-items-center rounded-full bg-[#dbeee9] font-bold text-[#056259]"
            onClick={logout}
            aria-label="Sign out"
          >
            U
          </button>
        </div>
      </header>
      <div className="flex min-h-0 flex-1">
        <aside className="hidden w-64 shrink-0 flex-col border-r border-[#dce8e5] bg-[#f2f8f5] p-4 md:flex">
          <p className="mb-3 px-2 text-[11px] font-extrabold uppercase tracking-[.13em] text-[#087f73]">
            Conversations
          </p>
          <button
            className="mb-3 rounded-lg border border-[#b9d9d1] bg-white px-3 py-2 text-left text-xs font-bold text-[#056259]"
            onClick={() => setConversationId(null)}
          >
            + New conversation
          </button>
          <div className="min-h-0 flex-1 space-y-1 overflow-y-auto overscroll-none pr-1">
            {conversations.map((item) => (
              <div
                className={`relative flex items-center rounded-lg ${conversationId === item.id ? "bg-[#dcefe9]" : "hover:bg-[#e7f3ef]"}`}
                key={item.id}
              >
                <button
                  className="min-w-0 flex-1 truncate px-3 py-2.5 text-left text-sm text-[#607476]"
                  onClick={() => {
                    setView("chat");
                    setConversationId(item.id);
                    setOpenConversationMenu(null);
                  }}
                >
                  {item.title || "Untitled conversation"}
                </button>
                <button
                  className="mr-1 grid h-7 w-7 shrink-0 place-items-center rounded text-lg leading-none text-[#6b7d80] hover:bg-[#dcefe9] hover:text-[#056259]"
                  onClick={() =>
                    setOpenConversationMenu((open) =>
                      open === item.id ? null : item.id,
                    )
                  }
                  aria-label={`Actions for ${item.title || "conversation"}`}
                  aria-expanded={openConversationMenu === item.id}
                >
                  ⋮
                </button>
                {openConversationMenu === item.id && (
                  <div className="absolute right-1 top-9 z-10 w-32 rounded-lg border border-[#dce8e5] bg-white p-1 shadow-lg">
                    <button
                      className="w-full rounded-md px-3 py-2 text-left text-xs font-bold text-[#a14d40] hover:bg-[#fff1ed]"
                      onClick={() => {
                        setConversationToDelete(item);
                        setOpenConversationMenu(null);
                      }}
                    >
                      Delete
                    </button>
                  </div>
                )}
              </div>
            ))}
          </div>
          {/* <p className="mt-4 border-t border-[#dce8e5] px-2 pt-4 text-xs leading-5 text-[#6b7d80]">
            Your workspace is ready for a question.
          </p> */}
        </aside>
        <main className="min-h-0 min-w-0 flex-1 overflow-y-auto overscroll-none">
          {error && (
            <div className="mx-auto mb-4 max-w-4xl rounded-lg border border-[#f3c5b8] bg-[#fff1ed] px-4 py-3 text-sm text-[#8f3c30]">
              {error}
            </div>
          )}
          {view === "chat" ? (
            <Chat
              conversationId={conversationId}
              onConversationCreated={(id) => {
                setConversationId(id);
                loadConversations();
              }}
            />
          ) : (
            <Documents
              documents={documents}
              loading={loading}
              upload={upload}
              onDelete={(document) => setDocumentToDelete(document)}
            />
          )}
        </main>
      </div>
      {conversationToDelete && (
        <div
          className="fixed inset-0 z-50 grid place-items-center bg-[#17323a]/35 p-4"
          role="presentation"
          onMouseDown={(event) => {
            if (event.target === event.currentTarget) setConversationToDelete(null);
          }}
        >
          <div
            className="w-full max-w-sm rounded-2xl border border-[#dce8e5] bg-white p-6 shadow-2xl"
            role="dialog"
            aria-modal="true"
            aria-labelledby="delete-conversation-title"
          >
            <h2 id="delete-conversation-title" className="text-lg font-bold text-[#17323a]">
              Delete conversation?
            </h2>
            <p className="mt-2 text-sm leading-6 text-[#6b7d80]">
              This will permanently delete “{conversationToDelete.title || "Untitled conversation"}”.
            </p>
            <div className="mt-6 flex justify-end gap-3">
              <button
                className="rounded-lg border border-[#dce8e5] px-4 py-2 text-sm font-bold text-[#607476] hover:bg-[#f2f8f5]"
                onClick={() => setConversationToDelete(null)}
              >
                Cancel
              </button>
              <button
                className="rounded-lg bg-[#a14d40] px-4 py-2 text-sm font-bold text-white hover:bg-[#8f3c30]"
                onClick={() => deleteConversation(conversationToDelete.id)}
              >
                Delete
              </button>
            </div>
          </div>
        </div>
      )}
      {documentToDelete && (
        <div
          className="fixed inset-0 z-50 grid place-items-center bg-[#17323a]/35 p-4"
          role="presentation"
          onMouseDown={(event) => {
            if (event.target === event.currentTarget) setDocumentToDelete(null);
          }}
        >
          <div
            className="w-full max-w-sm rounded-2xl border border-[#dce8e5] bg-white p-6 shadow-2xl"
            role="dialog"
            aria-modal="true"
            aria-labelledby="delete-document-title"
          >
            <h2 id="delete-document-title" className="text-lg font-bold text-[#17323a]">
              Delete document?
            </h2>
            <p className="mt-2 text-sm leading-6 text-[#6b7d80]">
              This will permanently delete “{documentToDelete.original_filename}” and its indexed content.
            </p>
            <div className="mt-6 flex justify-end gap-3">
              <button
                className="rounded-lg border border-[#dce8e5] px-4 py-2 text-sm font-bold text-[#607476] hover:bg-[#f2f8f5]"
                onClick={() => setDocumentToDelete(null)}
              >
                Cancel
              </button>
              <button
                className="rounded-lg bg-[#a14d40] px-4 py-2 text-sm font-bold text-white hover:bg-[#8f3c30]"
                onClick={() => deleteDocument(documentToDelete.id)}
              >
                Delete
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}

function TopNavButton({
  active,
  onClick,
  children,
}: {
  active: boolean;
  onClick: () => void;
  children: React.ReactNode;
}) {
  return (
    <button
      className={`rounded-md px-4 py-2 text-xs ${active ? "bg-white font-bold text-[#056259] shadow-sm" : "text-[#607476]"}`}
      onClick={onClick}
    >
      {children}
    </button>
  );
}

function Chat({
  conversationId,
  onConversationCreated,
}: {
  conversationId: string | null;
  onConversationCreated: (id: string) => void;
}) {
  const [messages, setMessages] = useState<Message[]>([]);
  const [input, setInput] = useState("");
  const [loading, setLoading] = useState(false);
  const chatEndRef = useRef<HTMLDivElement>(null);
  const [copiedMessageIndex, setCopiedMessageIndex] = useState<number | null>(null);
  useEffect(() => {
    if (!conversationId) {
      setMessages([]);
      return;
    }
    api(`/api/v1/chat/conversations/${conversationId}/messages`)
      .then(setMessages)
      .catch(() => setMessages([]));
  }, [conversationId]);
  useEffect(() => {
    chatEndRef.current?.scrollIntoView({ behavior: "smooth", block: "end" });
  }, [messages, loading]);
  const copyResponse = async (content: string, index: number) => {
    await navigator.clipboard.writeText(content);
    setCopiedMessageIndex(index);
    window.setTimeout(() => setCopiedMessageIndex(null), 1500);
  };
  const send = async (event: FormEvent) => {
    event.preventDefault();
    if (!input.trim() || loading) return;
    const text = input.trim();
    setInput("");
    setMessages((items) => [...items, { role: "user", content: text }]);
    setLoading(true);
    try {
      const reply = await api("/api/v1/chat", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          message: text,
          conversation_id: conversationId,
        }),
      });
      onConversationCreated(reply.conversation_id);
      setMessages((items) => [
        ...items,
        {
          role: "assistant",
          content: reply.content,
          citations: reply.citations,
        },
      ]);
    } finally {
      setLoading(false);
    }
  };
  const showIntro = !conversationId && !messages.length;
  return (
    <section className="mx-auto flex min-h-full max-w-4xl flex-col pt-2">
      {showIntro && (
        <div className="mb-8 flex items-start justify-between gap-4 pt-2">
          <div>
            <p className="mb-3 text-[11px] font-extrabold uppercase tracking-[.13em] text-[#087f73]">
              Knowledge assistant
            </p>
            <h1 className="text-4xl font-bold tracking-[-.06em] md:text-5xl">
              What can I help you find?
            </h1>
            <p className="mt-3 max-w-xl leading-6 text-[#6b7d80]">
              Ask about policies, processes, and product knowledge. Every answer
              keeps its sources close.
            </p>
          </div>
          <span className="hidden rounded-full border border-[#dce8e5] bg-white px-3 py-2 text-xs text-[#6b7d80] sm:block">
            ⌖ Tenant-scoped
          </span>
        </div>
      )}
      {showIntro ? (
        <div className="mb-8 grid gap-3 sm:grid-cols-2">
          <Prompt
            text="What is our refund policy?"
            label="Find a policy"
            onClick={setInput}
          />
          <Prompt
            text="Where should production secrets be stored?"
            label="Locate a process"
            onClick={setInput}
          />
        </div>
      ) : (
        <div className="mb-6 space-y-6 pt-2">
          {messages.map((message, index) => (
            <article
              className={
                message.role === "user"
                  ? "flex justify-end"
                  : "border-b border-[#dce8e5] pb-6"
              }
              key={`${message.role}-${index}`}
            >
              <div
                className={
                  message.role === "user"
                    ? "max-w-[85%] rounded-2xl rounded-br-md bg-[#087f73] px-4 py-3 text-white"
                    : "max-w-full"
                }
              >
                <MarkdownContent content={message.content} />
                {message.role === "assistant" && (
                  <button
                    className="mt-3 inline-flex items-center gap-1.5 rounded-md p-1.5 text-[#8aa09d] hover:bg-[#eaf5f1] hover:text-[#056259]"
                    onClick={() => copyResponse(message.content, index)}
                    aria-label="Copy response"
                    title="Copy response"
                  >
                    {copiedMessageIndex === index ? (
                      <span className="text-xs font-bold">Copied</span>
                    ) : (
                      <svg
                        aria-hidden="true"
                        className="h-4 w-4"
                        viewBox="0 0 24 24"
                        fill="none"
                        stroke="currentColor"
                        strokeWidth="2"
                      >
                        <rect x="9" y="9" width="11" height="11" rx="2" />
                        <path d="M5 15H4a2 2 0 0 1-2-2V4a2 2 0 0 1 2-2h9a2 2 0 0 1 2 2v1" />
                      </svg>
                    )}
                  </button>
                )}
              </div>
              {message.citations?.length ? (
                <div className="mt-4 flex flex-wrap items-center gap-2">
                  <span className="text-xs font-bold text-[#6b7d80]">
                    Sources
                  </span>
                  {message.citations.map((citation) => (
                    <span
                      className="rounded bg-[#eaf5f1] px-2 py-1 text-[11px] text-[#056259]"
                      key={`${citation.document_id}-${citation.chunk_index}`}
                    >
                      ↗ {citation.filename} · section {citation.chunk_index + 1}
                    </span>
                  ))}
                </div>
              ) : null}
            </article>
          ))}
          <div ref={chatEndRef} aria-hidden="true" />
        </div>
      )}
      <form
        className="sticky bottom-0 mt-auto rounded-xl border border-[#dce8e5] bg-white p-3 shadow-lg shadow-[#24564d]/5"
        onSubmit={send}
      >
        <input
          className="w-full resize-y border-0 p-1 leading-6 outline-none"
          aria-label="Ask a question"
          value={input}
          onChange={(event) => setInput(event.target.value)}
          onKeyDown={(event) => {
            if (event.key === "Enter" && !event.shiftKey) {
              event.preventDefault();
              event.currentTarget.form?.requestSubmit();
            }
          }}
          placeholder="Ask your workspace…"
          type="text"
          disabled={loading}
        />
        <div className="flex items-center justify-between gap-3 pt-2">
          <span className="hidden text-[11px] text-[#98a9a5] sm:block">
            Enter to send · Shift+Enter for a new line
          </span>
          <button
            className="rounded-lg bg-[#087f73] px-4 py-2 text-sm font-bold text-white hover:bg-[#056259] disabled:cursor-not-allowed disabled:opacity-50"
            disabled={loading || !input.trim()}
          >
            {loading ? "Thinking…" : "Ask ↗"}
          </button>
        </div>
      </form>
    </section>
  );
}
function capitalize(text: string) {
  return text.charAt(0).toUpperCase() + text.slice(1);
};

function Prompt({
  text,
  label,
  onClick,
}: {
  text: string;
  label: string;
  onClick: (text: string) => void;
}) {
  return (
    <button
      className="flex justify-center items-center gap-2 rounded-xl border border-[#dce8e5] bg-white p-5 text-left transition hover:-translate-y-0.5 hover:border-[#a7d6cc]"
      onClick={() => onClick(text)}
    >
      <small className="text-[#6b7d80]">{text}</small>
    </button>
  );
}

function Documents({
  documents,
  loading,
  upload,
  onDelete,
}: {
  documents: Document[];
  loading: boolean;
  upload: (file: File) => void;
  onDelete: (document: Document) => void;
}) {
  const pick = (event: React.ChangeEvent<HTMLInputElement>) => {
    const file = event.target.files?.[0];
    if (file) upload(file);
    event.currentTarget.value = "";
  };
  return (
    <section className="mx-auto max-w-4xl">
      <div className="mb-8 flex items-start justify-between gap-4 pt-2">
        <div>
          <p className="mb-3 text-[11px] font-extrabold uppercase tracking-[.13em] text-[#087f73]">
            Knowledge base
          </p>
          <h1 className="text-4xl font-bold tracking-[-.06em] md:text-5xl">
            Your documents
          </h1>
          <p className="mt-3 text-[#6b7d80]">
            Upload PDF, text, or Markdown to make it searchable by your workspace.
          </p>
        </div>
        <label className="relative inline-flex min-h-11 cursor-pointer items-center rounded-lg bg-[#087f73] px-4 text-sm font-bold text-white hover:bg-[#056259]">
          {loading ? "Processing…" : "Add document"}
          <input
            className="absolute inset-0 cursor-pointer opacity-0"
            type="file"
            accept=".pdf,.txt,.md,application/pdf,text/plain,text/markdown"
            disabled={loading}
            onChange={pick}
          />
        </label>
      </div>
      <div className="overflow-hidden rounded-xl border border-[#dce8e5] bg-white">
        {!documents.length ? (
          <div className="grid min-h-64 place-items-center p-8 text-center text-[#6b7d80]">
            <div>
              <div className="mx-auto mb-3 grid h-12 w-12 place-items-center rounded-full bg-[#e9f3f0] text-xl text-[#087f73]">
                □
              </div>
              <h2 className="font-bold text-[#17323a]">
                Your knowledge base is empty
              </h2>
              <p className="mt-2 text-sm">
                Add a text or Markdown file to start asking grounded questions.
              </p>
            </div>
          </div>
        ) : (
          documents.map((document) => (
            <div
              className="flex min-h-20 items-center gap-3 border-b border-[#edf3f1] px-4 py-4 last:border-0"
              key={document.id}
            >
              <div className="grid h-10 w-10 shrink-0 place-items-center rounded-lg bg-[#e9f3f0] text-[10px] font-bold text-[#087f73]">
                TXT
              </div>
              <div className="min-w-0 flex-1">
                <strong className="block truncate">
                  {document.original_filename}
                </strong>
                <span className="text-xs text-[#6b7d80]">
                  {Math.ceil(document.size_bytes / 1024)} KB · {capitalize(document.status)}
                </span>
              </div>
              <button
                className="rounded-lg border border-[#edc6bd] bg-[#fff7f5] px-3 py-2 text-xs font-bold text-[#a14d40] hover:bg-[#fce7e1]"
                onClick={() => onDelete(document)}
              >
                Delete
              </button>
            </div>
          ))
        )}
      </div>
    </section>
  );
}
