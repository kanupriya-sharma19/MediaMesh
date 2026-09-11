import { useEffect, useRef, useState } from "react";
import { useNavigate } from "react-router-dom";
import { useAuth } from "../context/AuthContext";

const sources = ["MusicBrainz", "TMDB", "Google Books"];

export default function Sidebar({
  sessions,
  onClear,
  onNewSession,
  onSelectSession,
}) {
  const [profileOpen, setProfileOpen] = useState(false);
  const [search, setSearch] = useState("");
  const profileRef = useRef(null);
  const { user, logout } = useAuth();
  const navigate = useNavigate();
  const userLabel = user?.name || user?.email || "Profile";

  useEffect(() => {
    const closeProfile = (event) => {
      if (profileRef.current && !profileRef.current.contains(event.target)) {
        setProfileOpen(false);
      }
    };
    document.addEventListener("mousedown", closeProfile);
    return () => document.removeEventListener("mousedown", closeProfile);
  }, []);

  const filteredSessions = sessions.filter((session) =>
    session.title.toLowerCase().includes(search.trim().toLowerCase()),
  );

  const handleLogout = async () => {
    await logout();
    navigate("/", { replace: true });
  };

  return (
    <aside className="sidebar">
      <div className="sidebar-header">
        <div className="brand">MEDIAMESH</div>
        <div className="sidebar-caption">Cross-media intelligence</div>
        <button className="new-session-button" onClick={onNewSession}>
          <span aria-hidden="true">+</span> New session
        </button>
        <label className="chat-search">
          <span aria-hidden="true">⌕</span>
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
          <span>⌂</span> Discover
        </div>
        <div className="status-line active">
          <span>✦</span> Chat
        </div>
        <div className="status-line">
          <span>◷</span> History
        </div>
        <div className="sidebar-label">Media sources</div>
        {sources.map((source) => (
          <div className="status-line" key={source}>
            <span className="source-dot">●</span> {source}
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
        {profileOpen && (
          <div className="profile-menu">
            <div className="profile-name">{userLabel}</div>
            {user?.name && user?.email && (
              <div className="profile-email">{user.email}</div>
            )}
            <div className="profile-actions">
              <button className="text-button profile-logout" onClick={onClear}>
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
          onClick={() => setProfileOpen((open) => !open)}
          aria-expanded={profileOpen}
        >
          {userLabel}
        </button>
        <div className="private-note">Private session</div>
      </div>
    </aside>
  );
}
