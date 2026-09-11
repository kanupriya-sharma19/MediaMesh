const sources = ['MusicBrainz', 'TMDB', 'Google Books'];

export default function Sidebar({ messages, onClear }) {
  const recent = messages.filter((item) => item.role === 'user').slice(-4).reverse();
  return <aside className="sidebar"><div className="brand">MEDIAMESH</div><div className="sidebar-caption">Cross-media intelligence</div><div className="sidebar-label">Explore</div><div className="status-line"><span>⌂</span> Discover</div><div className="status-line active"><span>✦</span> Chat</div><div className="status-line"><span>◷</span> History</div><div className="sidebar-label">Media sources</div>{sources.map((source) => <div className="status-line" key={source}><span className="source-dot">●</span> {source}</div>)}<div className="sidebar-label">Recent chats</div>{recent.length ? recent.map((item, index) => <div className="recent" key={`${item.content}-${index}`}>• {String(item.content).slice(0, 34)}</div>) : <div className="sidebar-caption">Your discoveries will appear here.</div>}<button className="outline-button clear-button" onClick={onClear}>Clear history</button><div className="private-note">Private session</div></aside>;
}
