function MediaCard({ kind, item }) {
  const title = item.title || item.name || item.artist_name || 'Untitled';
  const image = item.poster_url || item.thumbnail || item.cover_url;
  const meta = kind === 'movie' ? item.release_date || 'Movie' : kind === 'book' ? (item.authors || []).slice(0, 2).join(', ') || 'Google Books' : kind === 'music' ? (item.artists || []).map((artist) => artist.artist_name).slice(0, 2).join(', ') || 'MusicBrainz' : item.country || 'Artist';
  return <article className="media-card">{image ? <img src={image} alt="" /> : <div className="media-placeholder">{kind === 'movie' ? '🎬' : kind === 'book' ? '📚' : '🎵'}</div>}<div className="media-card-body"><strong>{title}</strong><span>{meta}</span><small>{(item.overview || item.categories?.[0] || item.disambiguation || 'MediaMesh result').slice(0, 110)}</small></div></article>;
}

export default function ChatMessage({ message }) {
  if (message.role === 'user') return <div className="message user"><div className="message-head">You</div><div className="answer">{message.content}</div></div>;
  const result = typeof message.content === 'string' ? { answer: message.content } : message.content;
  const records = [];
  (result.sources || []).filter((source) => source.type === 'tool_result').forEach((source) => Object.entries({ movies: 'movie', books: 'book', recordings: 'music', artists: 'artist' }).forEach(([key, kind]) => (source.result?.[key] || []).slice(0, 6).forEach((item) => records.push({ kind, item }))));
  return <div className="message assistant"><div className="message-head">✦ MediaMesh</div><div className="answer">{result.answer || 'No answer returned.'}</div>{result.warnings?.map((warning) => <div className="warning" key={warning}>{warning}</div>)}{records.length > 0 && <><div className="section-title">Similar media</div><div className="media-grid">{records.map(({ kind, item }, index) => <MediaCard key={`${kind}-${index}`} kind={kind} item={item} />)}</div></>}</div>;
}
