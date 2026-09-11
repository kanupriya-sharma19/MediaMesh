import { useEffect, useState } from 'react';
import Sidebar from '../components/Sidebar';
import ChatInput from '../components/ChatInput';
import ChatMessage from '../components/ChatMessage';
import { api } from '../services/api';

const prompts = ['Find an artist connected to this movie', 'Recommend a book based on my movies', 'Find songs from recent A24 films', 'Discover unexpected media connections'];

export default function Chat() {
  const [messages, setMessages] = useState([]);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState('');
  useEffect(() => { api.history().then((data) => setMessages(data.messages)).catch((requestError) => setError(requestError.message)); }, []);
  const send = async (message) => { setError(''); setBusy(true); setMessages((current) => [...current, { role: 'user', content: message }]); try { const data = await api.chat(message); setMessages((current) => [...current, data.message]); } catch (requestError) { setError(requestError.message); } finally { setBusy(false); } };
  const clear = async () => { await api.clearHistory(); setMessages([]); };
  return <div className="chat-layout"><Sidebar messages={messages} onClear={clear} /><main className="chat-main"><div className="chat-hero"><div className="kicker">Your media, connected</div><h1><span>Discover what links</span><br />the things you love.</h1><p>Ask one question across music, movies and books. MediaMesh finds the signal between them.</p></div>{messages.length === 0 ? <section className="empty-state"><div className="kicker">A new thread</div><h2>Find the connections hiding between the things you love.</h2><p>Try a prompt below, or ask MediaMesh anything at the bottom of the page.</p><div className="prompt-grid">{prompts.map((prompt) => <button className="prompt" key={prompt} onClick={() => send(prompt)}>{prompt}</button>)}</div></section> : <section className="messages">{messages.map((message, index) => <ChatMessage key={`${message.role}-${index}`} message={message} />)}</section>}{error && <div className="form-error chat-error">{error}</div>}{busy && <div className="thinking"><span /> MediaMesh is exploring the media graph...</div>}<ChatInput onSend={send} disabled={busy} /></main></div>;
}
