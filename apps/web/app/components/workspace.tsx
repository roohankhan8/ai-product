"use client";
/* eslint-disable react-hooks/set-state-in-effect */

import { FormEvent, useEffect, useState } from "react";
import { api, Conversation, Document, Message } from "../lib/api";
import { MarkdownContent } from "./markdown-content";

export function Workspace({ onSignOut }: { onSignOut: () => void }) {
  const [view, setView] = useState<"chat" | "documents">("chat");
  const [documents, setDocuments] = useState<Document[]>([]);
  const [conversations, setConversations] = useState<Conversation[]>([]);
  const [conversationId, setConversationId] = useState<string | null>(null);
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);
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
      setError("Upload failed. Use a UTF-8 text or Markdown file.");
    } finally {
      setLoading(false);
    }
  };
  const deleteDocument = async (id: string) => {
    if (!window.confirm("Delete this document and all indexed content?"))
      return;
    try {
      await api(`/api/v1/documents/${id}`, { method: "DELETE" });
      await loadDocuments();
    } catch {
      setError("Couldn’t delete the document.");
    }
  };
  const deleteConversation = async (id: string) => {
    if (!window.confirm("Delete this conversation?")) return;
    try {
      await api(`/api/v1/chat/conversations/${id}`, { method: "DELETE" });
      setConversations((items) => items.filter((item) => item.id !== id));
      if (conversationId === id) setConversationId(null);
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
            onClick={onSignOut}
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
          <div className="min-h-0 flex-1 space-y-1 overflow-y-auto pr-1">
            {conversations.map((item) => (
              <div
                className={`group flex items-center rounded-lg ${conversationId === item.id ? "bg-[#dcefe9]" : "hover:bg-[#e7f3ef]"}`}
                key={item.id}
              >
                <button
                  className="min-w-0 flex-1 truncate px-3 py-2.5 text-left text-sm text-[#607476]"
                  onClick={() => {
                    setView("chat");
                    setConversationId(item.id);
                  }}
                >
                  {item.title || "Untitled conversation"}
                </button>
                <button
                  className="mr-1 hidden h-7 w-7 rounded text-lg text-[#8aa09d] group-hover:block hover:bg-[#f5d9d1] hover:text-[#9d493c]"
                  onClick={() => deleteConversation(item.id)}
                  aria-label="Delete conversation"
                >
                  ×
                </button>
              </div>
            ))}
          </div>
          <p className="mt-4 border-t border-[#dce8e5] px-2 pt-4 text-xs leading-5 text-[#6b7d80]">
            Your workspace is ready for a question.
          </p>
        </aside>
        <main className="min-h-0 min-w-0 flex-1 overflow-y-auto p-5 md:p-12">
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
              onDelete={deleteDocument}
            />
          )}
        </main>
      </div>
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
  useEffect(() => {
    if (!conversationId) {
      setMessages([]);
      return;
    }
    api(`/api/v1/chat/conversations/${conversationId}/messages`)
      .then(setMessages)
      .catch(() => setMessages([]));
  }, [conversationId]);
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
  return (
    <section className="mx-auto flex min-h-full max-w-4xl flex-col">
      <div className="mb-8 flex items-start justify-between gap-4">
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
      {!messages.length ? (
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
        <div className="mb-6 space-y-6">
          {messages.map((message, index) => (
            <article
              className={`border-b border-[#dce8e5] pb-6 ${message.role === "user" ? "border-l-4 border-l-[#b9ddd4] pl-4" : ""}`}
              key={`${message.role}-${index}`}
            >
              <p className="mb-2 text-[11px] font-extrabold uppercase tracking-[.12em] text-[#087f73]">
                {message.role === "user" ? "You" : "Northstar"}
              </p>
              <MarkdownContent content={message.content} />
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
        </div>
      )}
      <form
        className="sticky bottom-0 mt-auto rounded-xl border border-[#dce8e5] bg-white p-3 shadow-lg shadow-[#24564d]/5"
        onSubmit={send}
      >
        <textarea
          className="max-h-48 min-h-16 w-full resize-y border-0 p-2 leading-6 outline-none"
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
          rows={2}
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
      className="grid gap-2 rounded-xl border border-[#dce8e5] bg-white p-5 text-left transition hover:-translate-y-0.5 hover:border-[#a7d6cc]"
      onClick={() => onClick(text)}
    >
      <span className="text-[11px] font-extrabold text-[#e78361]">01</span>
      <strong>{label}</strong>
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
  onDelete: (id: string) => void;
}) {
  const pick = (event: React.ChangeEvent<HTMLInputElement>) => {
    const file = event.target.files?.[0];
    if (file) upload(file);
    event.currentTarget.value = "";
  };
  return (
    <section className="mx-auto max-w-4xl">
      <div className="mb-8 flex items-start justify-between gap-4">
        <div>
          <p className="mb-3 text-[11px] font-extrabold uppercase tracking-[.13em] text-[#087f73]">
            Knowledge base
          </p>
          <h1 className="text-4xl font-bold tracking-[-.06em] md:text-5xl">
            Your documents
          </h1>
          <p className="mt-3 text-[#6b7d80]">
            Upload text or Markdown to make it searchable by your workspace.
          </p>
        </div>
        <label className="relative inline-flex min-h-11 cursor-pointer items-center rounded-lg bg-[#087f73] px-4 text-sm font-bold text-white hover:bg-[#056259]">
          {loading ? "Processing…" : "Add document"}
          <input
            className="absolute inset-0 cursor-pointer opacity-0"
            type="file"
            accept=".txt,.md,text/plain,text/markdown"
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
                  {Math.ceil(document.size_bytes / 1024)} KB · {document.status}
                </span>
              </div>
              <span className="rounded-full bg-[#e3f4ee] px-2 py-1 text-[11px] text-[#056259]">
                {document.status}
              </span>
              <button
                className="rounded-lg border border-[#edc6bd] bg-[#fff7f5] px-3 py-2 text-xs font-bold text-[#a14d40] hover:bg-[#fce7e1]"
                onClick={() => onDelete(document.id)}
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
