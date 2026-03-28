export type ToastType = 'success' | 'error' | 'info';

export interface ToastMessage {
  id: string;
  type: ToastType;
  message: string;
}

type ToastListener = (toast: ToastMessage) => void;

class ToastManager {
  private listeners: Set<ToastListener> = new Set();
  private nextId = 0;

  subscribe(listener: ToastListener): () => void {
    this.listeners.add(listener);
    return () => { this.listeners.delete(listener); };
  }

  show(message: string, type: ToastType) {
    const toast: ToastMessage = {
      id: `toast-${this.nextId++}`,
      type,
      message,
    };
    for (const listener of this.listeners) {
      listener(toast);
    }
  }

  success(message: string) { this.show(message, 'success'); }
  error(message: string) { this.show(message, 'error'); }
  info(message: string) { this.show(message, 'info'); }
}

export const toast = new ToastManager();
