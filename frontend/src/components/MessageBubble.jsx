import React from 'react';

export default function MessageBubble({ message }) {
  const isUser = message.role === 'user';

  return (
    <div className={`message ${isUser ? 'message--user' : 'message--bot'}`}>
      <div className={`message__avatar ${isUser ? 'message__avatar--user' : 'message__avatar--bot'}`}>
        {isUser ? '👤' : '🔍'}
      </div>
      <div className="message__body">
        <div className="message__name">{isUser ? 'You' : 'ConvoLens'}</div>
        <div className="message__text">{message.text}</div>
        {!isUser && message.confidence && (
          <div className="message__meta">
            <span className={`badge badge--${message.confidence}`}>{message.confidence}</span>
            {message.queryTime && <span>{message.queryTime}ms</span>}
            {message.sources && <span>{message.sources.length} sources</span>}
          </div>
        )}
        {!isUser && message.sources && message.sources.length > 0 && (
          <div className="message__sources">
            {message.sources.map((s, i) => (
              <div key={i} className="source-tag">
                📌 {s.topic_label} (score: {s.score})
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}
