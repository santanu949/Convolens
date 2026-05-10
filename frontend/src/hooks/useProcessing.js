/**
 * useProcessing hook — handles upload, processing, and status polling.
 */
import { useEffect, useRef, useCallback } from 'react';
import { useAppState } from '../store/index.jsx';
import { getHealth, getStatus, startProcessing, uploadCSV } from '../services/api.js';

export function useProcessing() {
  const { state, dispatch } = useAppState();
  const intervalRef = useRef(null);

  // Check health on mount
  useEffect(() => {
    getHealth()
      .then((data) => {
        if (data.system_ready) {
          dispatch({ type: 'SET_READY' });
        }
      })
      .catch(() => {});
    return () => clearInterval(intervalRef.current);
  }, [dispatch]);

  const handleUpload = useCallback(async (file) => {
    try {
      await uploadCSV(file);
      return true;
    } catch (err) {
      console.error('Upload failed:', err);
      return false;
    }
  }, []);

  const handleProcess = useCallback(async () => {
    try {
      const data = await startProcessing();
      dispatch({ type: 'SET_PROCESSING', taskId: data.task_id });

      // Start polling
      intervalRef.current = setInterval(async () => {
        try {
          const status = await getStatus(data.task_id);
          dispatch({
            type: 'SET_PROGRESS',
            progress: status.progress,
            stage: status.stage,
          });

          if (status.status === 'completed') {
            clearInterval(intervalRef.current);
            dispatch({ type: 'SET_READY' });
          } else if (status.status === 'error') {
            clearInterval(intervalRef.current);
            dispatch({ type: 'SET_PROGRESS', progress: 0, stage: `Error: ${status.error}` });
          }
        } catch {
          // Keep polling
        }
      }, 2000);
    } catch (err) {
      console.error('Process failed:', err);
    }
  }, [dispatch]);

  return {
    isReady: state.isReady,
    isProcessing: state.isProcessing,
    progress: state.progress,
    stage: state.stage,
    handleUpload,
    handleProcess,
  };
}
