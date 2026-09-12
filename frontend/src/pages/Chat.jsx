import { useEffect, useRef, useState } from "react";
import Sidebar from "../components/Sidebar";
import ChatInput from "../components/ChatInput";
import ChatMessage from "../components/ChatMessage";
import { api } from "../services/api";

function createSessionId() {
  return crypto.randomUUID();
}

const prompts = [
  "Find an artist connected to this movie",
  "Recommend a book based on my movies",
  "Find songs from recent A24 films",
  "Discover unexpected media connections",
];

const sidebarStorageKey = "mediamess-sidebar-collapsed";

export default function Chat() {
  const [messages, setMessages] = useState([]);
  const [sessions, setSessions] = useState([]);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const [sidebarCollapsed, setSidebarCollapsed] = useState(() => {
    const saved = localStorage.getItem(sidebarStorageKey);
    return saved === null
      ? window.matchMedia("(max-width: 800px)").matches
      : saved === "true";
  });
  const [sessionId, setSessionId] = useState(createSessionId);
  const sessionIdRef = useRef(sessionId);

  const refreshSessions = () =>
    api.sessions().then(({ sessions: nextSessions }) => setSessions(nextSessions));

  useEffect(() => {
    setMessages([]);
    api
      .history(sessionId)
      .then((data) => setMessages(data.messages))
      .catch((requestError) => setError(requestError.message));
  }, [sessionId]);
  useEffect(() => {
    refreshSessions().catch(() => setSessions([]));
  }, []);
  const send = async (message) => {
    const activeSessionId = sessionIdRef.current;
    setError("");
    setBusy(true);
    setMessages((current) => [...current, { role: "user", content: message }]);
    try {
      const data = await api.chat(message, activeSessionId);
      if (sessionIdRef.current === activeSessionId) {
        setMessages((current) => [...current, data.message]);
      }
      refreshSessions().catch(() => setSessions([]));
    } catch (requestError) {
      setError(requestError.message);
    } finally {
      setBusy(false);
    }
  };
  const selectSession = (nextSessionId) => {
    if (nextSessionId === sessionIdRef.current) return;
    setError("");
    setBusy(false);
    sessionIdRef.current = nextSessionId;
    setSessionId(nextSessionId);
  };
  const clear = async () => {
    setError("");
    try {
      await api.clearHistory();
      setMessages([]);
      setSessions([]);
      return true;
    } catch (requestError) {
      setError(requestError.message);
      return false;
    }
  };
  const newSession = async () => {
    setError("");
    setBusy(false);
    try {
      const nextSession = await api.createSession();
      setMessages([]);
      sessionIdRef.current = nextSession.id;
      setSessionId(nextSession.id);
      setSessions((current) => [nextSession, ...current]);
    } catch (requestError) {
      setError(requestError.message);
    }
  };
  const toggleSidebar = () => {
    setSidebarCollapsed((collapsed) => {
      const nextCollapsed = !collapsed;
      localStorage.setItem(sidebarStorageKey, String(nextCollapsed));
      return nextCollapsed;
    });
  };
  return (
    <div className={`chat-layout${sidebarCollapsed ? " sidebar-is-collapsed" : ""}`}>
      <Sidebar
        sessions={sessions}
        onClear={clear}
        onNewSession={newSession}
        onSelectSession={selectSession}
        collapsed={sidebarCollapsed}
        onToggleCollapsed={toggleSidebar}
      />
      <main className="chat-main">
        <div className="chat-hero">
          <div className="kicker">Your media, connected</div>
          <h1>
            <span>Discover what links</span>
            <br />
            the things you love.
          </h1>
          <p>
            Ask one question across music, movies and books. MediaMesh finds the
            signal between them.
          </p>
        </div>
        {messages.length === 0 ? (
          <section className="empty-state">
            <div className="kicker">A new thread</div>
            <h2>Find the connections hiding between the things you love.</h2>
            <p>
              Try a prompt below, or ask MediaMesh anything at the bottom of the
              page.
            </p>
            <div className="prompt-grid">
              {prompts.map((prompt) => (
                <button
                  className="prompt"
                  key={prompt}
                  onClick={() => send(prompt)}
                >
                  {prompt}
                </button>
              ))}
            </div>
          </section>
        ) : (
          <section className="messages">
            {messages.map((message, index) => (
              <ChatMessage key={`${message.role}-${index}`} message={message} />
            ))}
          </section>
        )}
        {error && <div className="form-error chat-error">{error}</div>}
        {busy && (
          <div className="thinking">
            <span /> MediaMesh is exploring the media graph...
          </div>
        )}
        <ChatInput onSend={send} disabled={busy} />
      </main>
    </div>
  );
}
