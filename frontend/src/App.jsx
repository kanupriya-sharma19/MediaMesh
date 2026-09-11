import { BrowserRouter, Route, Routes } from 'react-router-dom';
import { AuthProvider } from './context/AuthContext';
import ProtectedRoute from './components/ProtectedRoute';
import Landing from './pages/Landing';
import Chat from './pages/Chat';
import { AuthPage } from './pages/AuthPages';
import './styles/theme.css';

export default function App() { return <BrowserRouter><AuthProvider><Routes><Route path="/" element={<Landing />} /><Route path="/login" element={<AuthPage mode="login" />} /><Route path="/signup" element={<AuthPage mode="signup" />} /><Route element={<ProtectedRoute />}><Route path="/chat" element={<Chat />} /></Route></Routes></AuthProvider></BrowserRouter>; }
