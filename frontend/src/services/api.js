const API_URL = import.meta.env.VITE_API_URL || "http://localhost:8000";

async function request(path, options = {}) {
  const response = await fetch(`${API_URL}${path}`, {
    credentials: "include",
    headers: { "Content-Type": "application/json", ...(options.headers || {}) },
    ...options,
  });
  if (!response.ok) {
    const body = await response.json().catch(() => ({}));
    throw new Error(
      body.detail || "MediaMesh could not complete that request.",
    );
  }
  return response.status === 204 ? null : response.json();
}

export const api = {
  me: () => request("/api/auth/me"),
  login: (data) =>
    request("/api/auth/login", { method: "POST", body: JSON.stringify(data) }),
  signup: (data) =>
    request("/api/auth/signup", { method: "POST", body: JSON.stringify(data) }),
  logout: () => request("/api/auth/logout", { method: "POST" }),
  history: (sessionId = "default") =>
    request(`/api/chat/history?session_id=${encodeURIComponent(sessionId)}`),
  sessions: () => request("/api/chat/sessions"),
  createSession: () => request("/api/chat/sessions", { method: "POST" }),
  clearHistory: () => request("/api/chat/history", { method: "DELETE" }),
  chat: (message, sessionId = "default") =>
    request("/api/chat", {
      method: "POST",
      body: JSON.stringify({ message, session_id: sessionId }),
    }),
};
