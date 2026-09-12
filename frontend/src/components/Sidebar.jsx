import { useEffect, useRef, useState } from "react";
import { useNavigate } from "react-router-dom";
import { useAuth } from "../context/AuthContext";

const sources = ["MusicBrainz", "TMDB", "Google Books"];

export default function Sidebar({
  sessions,
  onClear,
  onNewSession,
  onSelectSession,
  collapsed,
  onToggleCollapsed,
}) {
  const [isProfileOpen, setIsProfileOpen] = useState(false);
  const [search, setSearch] = useState("");
  const profileRef = useRef(null);
  const { user, logout } = useAuth();
  const navigate = useNavigate();
  const userLabel = user?.name || user?.email || "Profile";

  useEffect(() => {
    const closeProfile = (event) => {
      if (profileRef.current && !profileRef.current.contains(event.target)) {
      setIsProfileOpen(false);
      }
    };
    document.addEventListener("mousedown", closeProfile);
    return () => document.removeEventListener("mousedown", closeProfile);
  }, []);

  const filteredSessions = sessions.filter((session) =>
    session.title.toLowerCase().includes(search.trim().toLowerCase()),
  );

  const handleLogout = async () => {
    setIsProfileOpen(false);
    await logout();
    navigate("/", { replace: true });
  };

  const handleClearHistory = async () => {
    const cleared = await onClear();
    if (cleared !== false) {
      setIsProfileOpen(false);
    }
  };

  return (
    <aside className={`sidebar${collapsed ? " sidebar-collapsed" : ""}`}>
      <div className="sidebar-header">
        <div className="sidebar-topline">
          <button
            className="sidebar-toggle"
            onClick={onToggleCollapsed}
            aria-label={collapsed ? "Expand sidebar" : "Collapse sidebar"}
            title={collapsed ? "Expand sidebar" : "Collapse sidebar"}
          >
            <span aria-hidden="true">{collapsed ? "»" : "«"}</span>
          </button>
          <div className="brand">MEDIAMESH</div>
        </div>
        <div className="sidebar-caption">Cross-media intelligence</div>
        <button className="new-session-button" onClick={onNewSession}>
          <span className="sidebar-icon" aria-hidden="true">
            +
          </span>
          <span className="sidebar-item-label">New session</span>
        </button>
        <label className="chat-search">
          <span className="sidebar-icon" aria-hidden="true">⌕</span>
          <input
            value={search}
            onChange={(event) => setSearch(event.target.value)}
            placeholder="Search chats"
            aria-label="Search chats"
          />
        </label>
      </div>
      <div className="sidebar-content">
        <div className="sidebar-label">Explore</div>
        <div className="status-line">
          <span className="sidebar-icon">⌂</span>
          <span className="sidebar-item-label">Discover</span>
        </div>
        <div className="status-line active">
          <span className="sidebar-icon">✦</span>
          <span className="sidebar-item-label">Chat</span>
        </div>
        <div className="status-line">
          <span className="sidebar-icon">◷</span>
          <span className="sidebar-item-label">History</span>
        </div>
        <div className="sidebar-label">Media sources</div>
        {sources.map((source) => (
          <div className="status-line" key={source}>
            <span className="sidebar-icon source-dot">●</span>
            <span className="sidebar-item-label">{source}</span>
          </div>
        ))}
        <div className="sidebar-label">Recent chats</div>
        {filteredSessions.length ? (
          filteredSessions.map((session) => (
            <button
              className="recent"
              key={session.id}
              onClick={() => onSelectSession(session.id)}
            >
              <span aria-hidden="true">•</span>
              <span className="recent-title">{session.title}</span>
            </button>
          ))
        ) : search.trim() ? (
          <div className="sidebar-caption">No chats found</div>
        ) : (
          <div className="sidebar-caption">
            Your discoveries will appear here.
          </div>
        )}
      </div>
      <div className="sidebar-account" ref={profileRef}>
        {isProfileOpen && (
          <div className="profile-menu">
            <div className="profile-name">{userLabel}</div>
            {user?.name && user?.email && (
              <div className="profile-email">{user.email}</div>
            )}
            <div className="profile-actions">
              <button
                className="text-button profile-logout"
                onClick={handleClearHistory}
              >
                Clear history
              </button>

              <button
                className="text-button profile-logout"
                onClick={handleLogout}
              >
                Logout
              </button>
            </div>
          </div>
        )}
        <button
          className="outline-button profile-button"
          onClick={() => setIsProfileOpen((open) => !open)}
          aria-expanded={isProfileOpen}
        >
          <span className="profile-avatar" aria-hidden="true">
            {userLabel.charAt(0).toUpperCase()}
          </span>
          <span className="sidebar-item-label">{userLabel}</span>
        </button>
        <div className="private-note">Private session</div>
      </div>
    </aside>
  );
}
