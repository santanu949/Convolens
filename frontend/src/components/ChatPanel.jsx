import React, { useState, useRef, useEffect } from 'react';
import { useChat } from '../hooks/useChat.js';
import MessageBubble from './MessageBubble.jsx';

export default function ChatPanel() {
  const { messages, isTyping, send } = useChat();
  const [input, setInput] = useState('');
  const bottomRef = useRef(null);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages, isTyping]);

  const handleSend = () => {
    if (input.trim()) {
      send(input);
      setInput('');
    }
  };

  const handleKey = (e) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSend();
    }
  };

  return (
    <div className="panel chat-panel">
      <div className="panel__header">
        <h1>Chat</h1>
        <p className="panel__subtitle">Ask questions about the conversations</p>
      </div>

      <div className="chat-messages">
        {messages.length === 0 && (
          <div className="empty-state">
            <div className="empty-state__icon">💬</div>
            <p>Start chatting! Try asking:</p>
            <div className="suggestions">
              {['What kind of person is this user?', 'What are their habits?', 'How do they communicate?'].map((q) => (
                <button key={q} className="suggestion-btn" onClick={() => { setInput(q); send(q); }}>
                  {q}
                </button>
              ))}
            </div>
          </div>
        )}

        {messages.map((msg, i) => (
          <MessageBubble key={i} message={msg} />
        ))}

        {isTyping && (
          <div className="message message--bot">
            <div className="message__avatar message__avatar--bot">🔍</div>
            <div className="message__body">
              <div className="typing-indicator">
                <span /><span /><span />
              </div>
            </div>
          </div>
        )}
        <div ref={bottomRef} />
      </div>

      <div className="chat-input">
        <div className="chat-input__wrapper">
          <input
            id="chat-input-field"
            type="text"
            className="chat-input__field"
            placeholder="Ask about conversations, habits, personality..."
            value={input}
            onChange={(e) => setInput(e.target.value)}
            onKeyDown={handleKey}
          />
          <button
            id="chat-send-btn"
            className="chat-input__send"
            onClick={handleSend}
            disabled={!input.trim()}
          >
            ➤
          </button>
        </div>
      </div>
    </div>
  );
}
