import React, { useState, useEffect } from 'react';
import { useAppState } from '../store/index.jsx';
import { getPersona } from '../services/api.js';

export default function PersonaPanel() {
  const { state } = useAppState();
  const [persona, setPersona] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const [expandedEvidence, setExpandedEvidence] = useState({});

  const convId = state.selectedConversationId;

  useEffect(() => {
    if (convId === null) { setPersona(null); return; }
    setLoading(true);
    setError(null);
    getPersona(convId)
      .then((data) => { setPersona(data); setLoading(false); })
      .catch((err) => { setError(err.message); setLoading(false); });
  }, [convId]);

  const toggleEvidence = (key) => {
    setExpandedEvidence((prev) => ({ ...prev, [key]: !prev[key] }));
  };

  if (convId === null) {
    return (
      <div className="panel">
        <div className="panel__header"><h1>User Persona</h1></div>
        <div className="panel__content">
          <div className="empty-state">
            <div className="empty-state__icon">👤</div>
            <p>Select a conversation from the sidebar to see the persona analysis.</p>
          </div>
        </div>
      </div>
    );
  }

  if (loading) {
    return (
      <div className="panel">
        <div className="panel__header"><h1>User Persona</h1></div>
        <div className="panel__content"><div className="empty-state"><div className="spinner" /><p>Analyzing persona...</p></div></div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="panel">
        <div className="panel__header"><h1>User Persona</h1></div>
        <div className="panel__content"><div className="empty-state"><p>Error: {error}</p></div></div>
      </div>
    );
  }

  return (
    <div className="panel">
      <div className="panel__header">
        <h1>User Persona</h1>
        <p className="panel__subtitle">Conversation #{convId} — {persona?.total_messages_analyzed || 0} messages analyzed</p>
      </div>
      <div className="panel__content">
        <div className="persona-json">
          <pre style={{ background: 'var(--bg-input)', padding: '20px', borderRadius: '8px', overflowX: 'auto', fontSize: '13px' }}>
            {JSON.stringify(persona, null, 2)}
          </pre>
        </div>
      </div>
    </div>
  );
}
