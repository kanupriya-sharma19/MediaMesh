import { Link } from "react-router-dom";
import { useAuth } from "../context/AuthContext";

export default function Navbar() {
  const { user, logout } = useAuth();
  return (
    <nav className="topbar">
      <Link className="brand" to={user ? "/chat" : "/"}>
        MEDIAMESH
      </Link>
      <span className="topbar-note">Cross-media intelligence</span>
      {user && (
        <button className="text-button" onClick={logout}>
          Sign out
        </button>
      )}
    </nav>
  );
}
