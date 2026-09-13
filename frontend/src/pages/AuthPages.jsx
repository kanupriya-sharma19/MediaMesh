import { useState, useEffect } from "react";
import { Link, Navigate, useLocation, useNavigate } from "react-router-dom";
import { useAuth } from "../context/AuthContext";
import { api } from "../services/api";

const ROW_COUNT = 8;

function mixMedia(media) {
  const items = [
    ...(media.movies || []),
    ...(media.music || []),
    ...(media.books || []),
  ];
  return items.sort(() => Math.random() - 0.5);
}

export function AuthPage({ mode }) {
  const isSignup = mode === "signup";
  const { user, login, signup } = useAuth();
  const navigate = useNavigate();
  const location = useLocation();
  const [form, setForm] = useState({
    name: "",
    email: "",
    password: "",
    confirm_password: "",
  });
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);
  if (user) return <Navigate to="/chat" replace />;
  const update = (event) =>
    setForm({ ...form, [event.target.name]: event.target.value });
  const submit = async (event) => {
    event.preventDefault();
    setError("");
    setBusy(true);
    try {
      if (isSignup && form.password !== form.confirm_password)
        throw new Error("Passwords do not match.");
      if (isSignup) await signup(form);
      else await login({ email: form.email, password: form.password });
      navigate(location.state?.from?.pathname || "/chat");
    } catch (requestError) {
      setError(requestError.message);
    } finally {
      setBusy(false);
    }
  };

  const [media, setMedia] = useState([]);

  useEffect(() => {
    let active = true;
    api
      .landingMedia()
      .then((result) => {
        if (active) setMedia(mixMedia(result));
      })
      .catch(() => {});
    return () => {
      active = false;
    };
  }, []);

  const rows = Array.from({ length: ROW_COUNT }, (_, index) => {
    const offset = index % Math.max(media.length, 1);
    return media.length
      ? [...media.slice(offset), ...media.slice(0, offset)]
      : [];
  });

  return (
    <div className="page auth-page">
      <div className="auth-media-background" aria-hidden="true">
        {rows.map((row, rowIndex) => (
          <div
            className={`auth-media-marquee auth-media-marquee-${rowIndex + 1}`}
            key={rowIndex}
          >
            <div className="auth-media-track">
              {[...row, ...row].map((item, itemIndex) => (
                <img
                  key={`${item.type}-${item.title}-${itemIndex}`}
                  src={item.image_url}
                  alt=""
                  loading="lazy"
                  onError={(event) => {
                    event.currentTarget.style.visibility = "hidden";
                  }}
                />
              ))}
            </div>
          </div>
        ))}
      </div>
      <main className="auth-shell">
        <div className="kicker">
          {isSignup ? "Start discovering" : "Welcome back"}
        </div>
        <h1>
          {isSignup ? "Make the connections yours." : "Return to the thread."}
        </h1>
        <p>
          {isSignup
            ? "Create a private MediaMesh space for your cross-media questions."
            : "Your media graph is waiting where you left it."}
        </p>
        <form className="auth-form" onSubmit={submit}>
          {isSignup && (
            <label>
              Name
              <input name="name" value={form.name} onChange={update} required />
            </label>
          )}
          <label>
            Email
            <input
              name="email"
              type="email"
              value={form.email}
              onChange={update}
              required
            />
          </label>
          <label>
            Password
            <input
              name="password"
              type="password"
              value={form.password}
              onChange={update}
              required
              minLength="8"
            />
          </label>
          {isSignup && (
            <label>
              Confirm password
              <input
                name="confirm_password"
                type="password"
                value={form.confirm_password}
                onChange={update}
                required
                minLength="8"
              />
            </label>
          )}
          {error && <div className="form-error">{error}</div>}
          <button className="primary-button" disabled={busy}>
            {busy ? "Working..." : isSignup ? "Create account ↗" : "Login ↗"}
          </button>
        </form>
        <div className="auth-switch">
          {isSignup ? "Already have an account?" : "Don't have an account?"}{" "}
          <Link to={isSignup ? "/login" : "/signup"}>
            {isSignup ? "Login" : "Sign up"}
          </Link>
        </div>
      </main>
    </div>
  );
}
