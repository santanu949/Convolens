import React, { useState, useEffect } from 'react';
import { useAppState } from '../store/index.jsx';
import { getCheckpoints } from '../services/api.js';

export default function CheckpointPanel() {
  const { state } = useAppState();
  const [checkpoints, setCheckpoints] = useState([]);
  const [page, setPage] = useState(1);
  const [totalPages, setTotalPages] = useState(1);
  const [total, setTotal] = useState(0);
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    if (!state.isReady) return;
    setLoading(true);
    getCheckpoints(page)
      .then((data) => {
        setCheckpoints(data.checkpoints || []);
        setTotalPages(data.total_pages);
        setTotal(data.total);
        setLoading(false);
      })
      .catch(() => setLoading(false));
  }, [page, state.isReady]);

  if (!state.isReady) {
    return (
      <div className="panel">
        <div className="panel__header"><h1>Time Checkpoints</h1></div>
        <div className="panel__content"><div className="empty-state"><p>Process data first to see checkpoints.</p></div></div>
      </div>
    );
  }

  return (
    <div className="panel">
      <div className="panel__header">
        <h1>Time Checkpoints</h1>
        <p className="panel__subtitle">{total} checkpoints (every 100 messages)</p>
      </div>
      <div className="panel__content">
        {loading && <div className="empty-state"><div className="spinner" /></div>}

        {!loading && checkpoints.map((c) => (
          <div key={c.id} className="data-card">
            <div className="data-card__header">
              <span className="data-card__title">Checkpoint #{c.id}</span>
              <span className="data-card__badge">msgs {c.start_global_idx}–{c.end_global_idx} ({c.message_count})</span>
            </div>
            <div className="data-card__body">{c.summary}</div>
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
