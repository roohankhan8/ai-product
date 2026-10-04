export type Document = {
  id: string;
  original_filename: string;
  size_bytes: number;
  status: string;
  created_at: string;
};
export type Conversation = {
  id: string;
  title: string | null;
  created_at: string;
  updated_at: string;
};
export type Citation = {
  document_id: string;
  filename: string;
  chunk_index: number;
  score: number;
};
export type Message = {
  role: "user" | "assistant";
  content: string;
  citations?: Citation[];
};
export type Approval = {
  id: string;
  action: string;
  status: "pending" | "approved" | "rejected" | "executed" | "expired";
  arguments: Record<string, string>;
  expires_at: string;
  idempotency_key: string;
};

const API = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

export async function api(path: string, options: RequestInit = {}) {
  const headers = new Headers(options.headers);
  const token = window.localStorage.getItem("ai_ops_token");
  if (token) headers.set("Authorization", `Bearer ${token}`);
  const response = await fetch(`${API}${path}`, { ...options, headers });
  if (response.status === 401 || response.status === 403)
    throw new Error("ACCESS_DENIED");
  if (!response.ok) throw new Error("REQUEST_FAILED");
  return response.status === 204 ? null : response.json();
}
