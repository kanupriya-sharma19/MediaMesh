import { useState } from 'react';

export default function ChatInput({ onSend, disabled }) {
  const [value, setValue] = useState('');
  const submit = (event) => { event.preventDefault(); if (!value.trim() || disabled) return; onSend(value.trim()); setValue(''); };
  return <form className="chat-input" onSubmit={submit}><input value={value} onChange={(event) => setValue(event.target.value)} placeholder="Ask about movies, music, books, or unexpected connections..." disabled={disabled} /><button className="send-button" disabled={disabled || !value.trim()} aria-label="Send message">↗</button></form>;
}
