/**
 * API Service — ALL fetch() calls live here. Components NEVER call fetch directly.
 */
const BASE = import.meta.env.VITE_API_URL || '';

async function request(url, options = {}) {
  const res = await fetch(`${BASE}${url}`, {
    headers: { 'Content-Type': 'application/json', ...options.headers },
    ...options,
  });
  const data = await res.json();
  if (!res.ok) throw new Error(data.error || `HTTP ${res.status}`);
  return data;
}

export const getHealth = () => request('/api/health');

export const uploadCSV = async (file) => {
  const formData = new FormData();
  formData.append('file', file);
  const res = await fetch(`${BASE}/api/upload`, { method: 'POST', body: formData });
  const data = await res.json();
  if (!res.ok) throw new Error(data.error || 'Upload failed');
  return data;
};

export const startProcessing = () => request('/api/process', { method: 'POST' });

export const getStatus = (taskId) => request(`/api/status/${taskId}`);

export const sendQuery = (query, conversationId = null) =>
  request('/api/query', {
    method: 'POST',
    body: JSON.stringify({ query, conversation_id: conversationId }),
  });

export const getConversations = (page = 1) =>
  request(`/api/conversations?page=${page}&per_page=20`);

export const getPersona = (conversationId) =>
  request(`/api/conversations/${conversationId}/persona`);

export const getTopics = (page = 1, conversationId = null) => {
  let url = `/api/topics?page=${page}&per_page=15`;
  if (conversationId !== null) url += `&conversation_id=${conversationId}`;
  return request(url);
};

export const getCheckpoints = (page = 1) =>
  request(`/api/checkpoints?page=${page}&per_page=15`);
