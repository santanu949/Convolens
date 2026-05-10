import React, { useState, useEffect } from 'react';
import { useAppState } from '../store/index.jsx';
import { getTopics } from '../services/api.js';

export default function TopicPanel() {
  const { state } = useAppState();
  const [topics, setTopics] = useState([]);
  const [page, setPage] = useState(1);
  const [totalPages, setTotalPages] = useState(1);
  const [total, setTotal] = useState(0);
  const [loading, setLoading] = useState(false);
  const [expanded, setExpanded] = useState({});

  useEffect(() => {
    if (!state.isReady) return;
    setLoading(true);
    getTopics(page, state.selectedConversationId)
      .then((data) => {
        setTopics(data.topics || []);
        setTotalPages(data.total_pages);
        setTotal(data.total);
        setLoading(false);
      })
      .catch(() => setLoading(false));
  }, [page, state.isReady, state.selectedConversationId]);

  if (!state.isReady) {
    return (
      <div className="panel">
        <div className="panel__header"><h1>Topic Segments</h1></div>
        <div className="panel__content"><div className="empty-state"><p>Process data first to see topics.</p></div></div>
      </div>
    );
  }

  return (
    <div className="panel">
      <div className="panel__header">
        <h1>Topic Segments</h1>
        <p className="panel__subtitle">{total} total segments detected</p>
      </div>
      <div className="panel__content">
        {loading && <div className="empty-state"><div className="spinner" /></div>}

        {!loading && topics.map((t) => (
          <div key={t.id} className="data-card">
            Topic {t.id} → messages {t.start_idx}–{t.end_idx} → {t.summary}
          </div>
        ))}

        {totalPages > 1 && (
          <div className="pagination">
            <button className="page-btn" disabled={page <= 1} onClick={() => setPage(page - 1)}>« Prev</button>
            {Array.from({ length: Math.min(5, totalPages) }, (_, i) => {
              const p = Math.max(1, page - 2) + i;
              if (p > totalPages) return null;
              return <button key={p} className={`page-btn ${p === page ? 'page-btn--active' : ''}`} onClick={() => setPage(p)}>{p}</button>;
            })}
            <button className="page-btn" disabled={page >= totalPages} onClick={() => setPage(page + 1)}>Next »</button>
          </div>
        )}
      </div>
    </div>
  );
}
