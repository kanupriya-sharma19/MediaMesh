import { useState } from 'react';
import { Link, Navigate, useLocation, useNavigate } from 'react-router-dom';
import Navbar from '../components/Navbar';
import { useAuth } from '../context/AuthContext';

export function AuthPage({ mode }) {
  const isSignup = mode === 'signup';
  const { user, login, signup } = useAuth();
  const navigate = useNavigate();
  const location = useLocation();
  const [form, setForm] = useState({ name: '', email: '', password: '', confirm_password: '' });
  const [error, setError] = useState('');
  const [busy, setBusy] = useState(false);
  if (user) return <Navigate to="/chat" replace />;
  const update = (event) => setForm({ ...form, [event.target.name]: event.target.value });
  const submit = async (event) => { event.preventDefault(); setError(''); setBusy(true); try { if (isSignup && form.password !== form.confirm_password) throw new Error('Passwords do not match.'); if (isSignup) await signup(form); else await login({ email: form.email, password: form.password }); navigate(location.state?.from?.pathname || '/chat'); } catch (requestError) { setError(requestError.message); } finally { setBusy(false); } };
  return <div className="page auth-page"><Navbar /><main className="auth-shell"><div className="kicker">{isSignup ? 'Start discovering' : 'Welcome back'}</div><h1>{isSignup ? 'Make the connections yours.' : 'Return to the thread.'}</h1><p>{isSignup ? 'Create a private MediaMesh space for your cross-media questions.' : 'Your media graph is waiting where you left it.'}</p><form className="auth-form" onSubmit={submit}>{isSignup && <label>Name<input name="name" value={form.name} onChange={update} required /></label>}<label>Email<input name="email" type="email" value={form.email} onChange={update} required /></label><label>Password<input name="password" type="password" value={form.password} onChange={update} required minLength="8" /></label>{isSignup && <label>Confirm password<input name="confirm_password" type="password" value={form.confirm_password} onChange={update} required minLength="8" /></label>}{error && <div className="form-error">{error}</div>}<button className="primary-button" disabled={busy}>{busy ? 'Working...' : isSignup ? 'Create account ↗' : 'Login ↗'}</button></form><div className="auth-switch">{isSignup ? 'Already have an account?' : "Don't have an account?"} <Link to={isSignup ? '/login' : '/signup'}>{isSignup ? 'Login' : 'Sign up'}</Link></div></main></div>;
}
