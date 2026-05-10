/**
 * Global state — useReducer + Context. No Redux needed.
 */
import { createContext, useContext, useReducer } from 'react';

const initialState = {
  isReady: false,
  isProcessing: false,
  progress: 0,
  stage: '',
  taskId: null,
  activePanel: 'chat',
  selectedConversationId: null,
  chatMessages: [],
  persona: null,
  topics: [],
  checkpoints: [],
  sidebarOpen: false,
};

function reducer(state, action) {
  switch (action.type) {
    case 'SET_READY':
      return { ...state, isReady: true, isProcessing: false, progress: 100 };
    case 'SET_PROCESSING':
      return { ...state, isProcessing: true, taskId: action.taskId };
    case 'SET_PROGRESS':
      return { ...state, progress: action.progress, stage: action.stage || state.stage };
    case 'SET_PANEL':
      return { ...state, activePanel: action.panel };
    case 'SET_CONVERSATION':
      return { ...state, selectedConversationId: action.id, persona: null };
    case 'ADD_CHAT_MESSAGE':
      return { ...state, chatMessages: [...state.chatMessages, action.message] };
    case 'SET_PERSONA':
      return { ...state, persona: action.persona };
    case 'SET_TOPICS':
      return { ...state, topics: action.topics };
    case 'SET_CHECKPOINTS':
      return { ...state, checkpoints: action.checkpoints };
    case 'TOGGLE_SIDEBAR':
      return { ...state, sidebarOpen: !state.sidebarOpen };
    case 'CLOSE_SIDEBAR':
      return { ...state, sidebarOpen: false };
    default:
      return state;
  }
}

const AppContext = createContext();

export function AppProvider({ children }) {
  const [state, dispatch] = useReducer(reducer, initialState);
  return (
    <AppContext.Provider value={{ state, dispatch }}>
      {children}
    </AppContext.Provider>
  );
}

export function useAppState() {
  const ctx = useContext(AppContext);
  if (!ctx) throw new Error('useAppState must be used within AppProvider');
  return ctx;
}
