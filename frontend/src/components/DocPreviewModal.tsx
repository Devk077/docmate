import { useEffect, useRef } from 'react';
import { getPersonaColor } from '../utils/colors';
import type { Participant } from '../api/client';
import '../styles/chat.css';

const API_BASE = import.meta.env.VITE_API_URL || 'http://localhost:8000';

interface DocPreviewProps {
  participant: Participant;
  roomId: string;
  onClose: () => void;
}

/**
 * Modal that shows a PDF/text file preview for a document participant.
 * PDFs are rendered in an <iframe>, text files shown as pre-formatted text.
 */
export function DocPreviewModal({ participant, roomId, onClose }: DocPreviewProps) {
  const color = getPersonaColor(participant.persona_name);
  const backdropRef = useRef<HTMLDivElement>(null);

  // Keyboard close
  useEffect(() => {
    const handler = (e: KeyboardEvent) => {
      if (e.key === 'Escape') onClose();
    };
    document.addEventListener('keydown', handler);
    return () => document.removeEventListener('keydown', handler);
  }, [onClose]);

  const previewUrl = `${API_BASE}/api/rooms/${roomId}/documents/${participant.document_id}/preview`;

  return (
    <div
      className="doc-preview-backdrop"
      ref={backdropRef}
      onClick={(e) => { if (e.target === backdropRef.current) onClose(); }}
    >
      <div className="doc-preview-modal">
        <div className="doc-preview-header">
          <div className="doc-preview-title">
            <div
              className="participant-avatar"
              style={{ background: color, width: 28, height: 28, fontSize: '0.75rem', borderRadius: 7, flexShrink: 0, display: 'flex', alignItems: 'center', justifyContent: 'center', color: '#fff', fontWeight: 700 }}
            >
              {participant.persona_name.charAt(0).toUpperCase()}
            </div>
            <div>
              <div style={{ fontWeight: 600, fontSize: '0.9rem' }}>{participant.persona_name}</div>
              <div style={{ fontSize: '0.72rem', color: 'var(--text-muted)' }}>Document Preview</div>
            </div>
          </div>
          <div style={{ display: 'flex', gap: 8 }}>
            <a
              href={previewUrl}
              target="_blank"
              rel="noopener noreferrer"
              className="btn btn-ghost"
              style={{ fontSize: '0.8rem', padding: '5px 12px', textDecoration: 'none' }}
            >
              Open full
            </a>
            <button className="settings-panel-close" onClick={onClose} style={{ fontSize: '1.2rem' }}>×</button>
          </div>
        </div>

        <div className="doc-preview-body">
          <iframe
            src={previewUrl}
            title={participant.persona_name}
            className="doc-preview-iframe"
            sandbox="allow-same-origin allow-scripts"
          />
        </div>
      </div>
    </div>
  );
}
