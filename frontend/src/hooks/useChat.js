/**
 * useChat hook — manages chat messages, sending queries, typing state.
 */
import { useState, useCallback } from 'react';
import { useAppState } from '../store/index.jsx';
import { sendQuery } from '../services/api.js';

export function useChat() {
  const { state, dispatch } = useAppState();
  const [isTyping, setIsTyping] = useState(false);

  const send = useCallback(async (text) => {
    if (!text.trim() || !state.isReady) return;

    // Add user message
    dispatch({
      type: 'ADD_CHAT_MESSAGE',
      message: { role: 'user', text: text.trim() },
    });

    setIsTyping(true);
    try {
      const result = await sendQuery(text.trim(), state.selectedConversationId);
      dispatch({
        type: 'ADD_CHAT_MESSAGE',
        message: {
          role: 'bot',
          text: result.answer,
          sources: result.sources,
          confidence: result.confidence,
          queryTime: result.query_time_ms,
          queryType: result.query_type,
        },
      });
    } catch (err) {
      dispatch({
        type: 'ADD_CHAT_MESSAGE',
        message: { role: 'bot', text: `Error: ${err.message}` },
      });
    } finally {
      setIsTyping(false);
    }
  }, [state.isReady, state.selectedConversationId, dispatch]);

  return {
    messages: state.chatMessages,
    isTyping,
    send,
  };
}
