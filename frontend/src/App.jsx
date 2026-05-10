import React from 'react';
import { useAppState } from './store/index.jsx';
import Sidebar from './components/Sidebar.jsx';
import ChatPanel from './components/ChatPanel.jsx';
import PersonaPanel from './components/PersonaPanel.jsx';
import TopicPanel from './components/TopicPanel.jsx';
import CheckpointPanel from './components/CheckpointPanel.jsx';

export default function App() {
  const { state } = useAppState();

  const panels = {
    chat: <ChatPanel />,
    persona: <PersonaPanel />,
    topics: <TopicPanel />,
    checkpoints: <CheckpointPanel />,
  };

  return (
    <div className="app">
      <div className="bg-grid" />
      <div className="bg-glow bg-glow-1" />
      <div className="bg-glow bg-glow-2" />
      <div className="app-container">
        <Sidebar />
        <main className="main-content">
          {panels[state.activePanel] || <ChatPanel />}
        </main>
      </div>
    </div>
  );
}
