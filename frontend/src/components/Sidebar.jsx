import React, { useState, useEffect, useRef } from 'react';
import { useAppState } from '../store/index.jsx';
import { useProcessing } from '../hooks/useProcessing.js';
import { getConversations } from '../services/api.js';

export default function Sidebar() {
  const { state, dispatch } = useAppState();
  const { isReady, isProcessing, progress, stage, handleUpload, handleProcess } = useProcessing();
  const [convos, setConvos] = useState([]);
  const [convPage, setConvPage] = useState(1);
  const [totalConvos, setTotalConvos] = useState(0);
  const fileRef = useRef(null);

  useEffect(() => {
    if (isReady) {
      getConversations(convPage)
        .then((data) => { setConvos(data.conversations || []); setTotalConvos(data.total); })
        .catch(() => {});
    }
  }, [isReady, convPage]);

  const onFileChange = async (e) => {
    const file = e.target.files?.[0];
    if (file) {
      const ok = await handleUpload(file);
      if (ok) handleProcess();
    }
  };

  const navItems = [
    { id: 'chat', icon: '💬', label: 'Chat' },
    { id: 'persona', icon: '👤', label: 'Persona' },
    { id: 'topics', icon: '📑', label: 'Topics' },
    { id: 'checkpoints', icon: '⏱️', label: 'Checkpoints' },
  ];

  return (
    <>
      {/* Mobile hamburger */}
      <button
        id="sidebar-toggle"
        className="sidebar-toggle"
        onClick={() => dispatch({ type: 'TOGGLE_SIDEBAR' })}
        aria-label="Toggle sidebar"
      >
        ☰
      </button>

      {/* Overlay for mobile */}
      {state.sidebarOpen && (
        <div className="sidebar-overlay" onClick={() => dispatch({ type: 'CLOSE_SIDEBAR' })} />
      )}

      <aside className={`sidebar ${state.sidebarOpen ? 'sidebar--open' : ''}`}>
        <div className="sidebar__header">
          <div className="logo">
            <div className="logo__icon">🔍</div>
            <div>
              <span className="logo__name">ConvoLens</span>
              <span className="logo__tag">Conversation AI</span>
            </div>
          </div>
        </div>

        <nav className="sidebar__nav">
          {navItems.map((item) => (
            <button
              key={item.id}
              className={`nav-item ${state.activePanel === item.id ? 'nav-item--active' : ''}`}
              onClick={() => { dispatch({ type: 'SET_PANEL', panel: item.id }); dispatch({ type: 'CLOSE_SIDEBAR' }); }}
            >
              <span>{item.icon}</span>
              <span>{item.label}</span>
            </button>
          ))}
        </nav>

        {/* Conversation selector */}
        {isReady && convos.length > 0 && (
          <div className="sidebar__conversations">
            <div className="sidebar__section-title">Conversation</div>
            <select
              id="conversation-select"
              className="conversation-select"
              value={state.selectedConversationId ?? ''}
              onChange={(e) => dispatch({ type: 'SET_CONVERSATION', id: e.target.value ? parseInt(e.target.value) : null })}
            >
              <option value="">All conversations</option>
              {convos.map((c) => (
                <option key={c.conversation_id} value={c.conversation_id}>
                  #{c.conversation_id} ({c.message_count} msgs)
                </option>
              ))}
            </select>
            {totalConvos > 20 && (
              <div className="conv-nav">
                <button disabled={convPage <= 1} onClick={() => setConvPage(convPage - 1)}>‹</button>
                <span>Page {convPage}</span>
                <button onClick={() => setConvPage(convPage + 1)}>›</button>
              </div>
            )}
          </div>
        )}

        <div className="sidebar__footer">
          {!isReady && !isProcessing && (
            <>
              <input ref={fileRef} type="file" accept=".csv" style={{ display: 'none' }} onChange={onFileChange} />
              <button id="upload-btn" className="process-btn" onClick={() => fileRef.current?.click()}>
                📁 Upload & Process CSV
              </button>
              {/* If data exists in server, allow just processing */}
              <button className="process-btn process-btn--secondary" onClick={handleProcess} style={{ marginTop: 8 }}>
                ▶ Process Existing Data
              </button>
            </>
          )}

          {isProcessing && (
            <div className="progress-section">
              <div className="progress-bar">
                <div className="progress-bar__fill" style={{ width: `${progress}%` }} />
              </div>
              <div className="progress-text">{stage || 'Processing...'} ({progress}%)</div>
            </div>
          )}

          {isReady && (
            <div className="ready-badge">✓ System Ready</div>
          )}
        </div>
      </aside>
    </>
  );
}
