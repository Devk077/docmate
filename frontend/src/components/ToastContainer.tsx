import { useState, useEffect } from 'react';
import { toast, type ToastMessage } from '../utils/toast';
import '../styles/globals.css';

export function ToastContainer() {
  const [toasts, setToasts] = useState<ToastMessage[]>([]);

  useEffect(() => {
    const unsub = toast.subscribe((newToast) => {
      setToasts((prev) => [...prev, newToast]);
      setTimeout(() => {
        setToasts((prev) => prev.filter((t) => t.id !== newToast.id));
      }, 3500); // auto-hide
    });
    return unsub;
  }, []);

  if (toasts.length === 0) return null;

  return (
    <div className="toast-container">
      {toasts.map((t) => (
        <div key={t.id} className={`toast toast-${t.type}`}>
          {t.type === 'success' && '✓ '}
          {t.type === 'error' && '⚠ '}
          {t.type === 'info' && 'ⓘ '}
          {t.message}
        </div>
      ))}
    </div>
  );
}
