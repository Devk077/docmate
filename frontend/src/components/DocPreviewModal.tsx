import { useEffect, useRef, useState } from 'react';
import { getPersonaColor } from '../utils/colors';
import type { Participant } from '../api/client';
import '../styles/chat.css';

const API_BASE = import.meta.env.VITE_API_URL || 'http://localhost:8000';

// File types we can render inline
const TEXT_EXTS = new Set(['.txt', '.md', '.csv', '.rst']);
const PDF_EXT = '.pdf';

function getExt(filename: string): string {
  const idx = filename.lastIndexOf('.');
  return idx === -1 ? '' : filename.slice(idx).toLowerCase();
}

interface DocPreviewProps {
  participant: Participant & { filename?: string };
  roomId: string;
  onClose: () => void;
}

export function DocPreviewModal({ participant, roomId, onClose }: DocPreviewProps) {
  const color = getPersonaColor(participant.persona_name);
  const backdropRef = useRef<HTMLDivElement>(null);

  const filename = participant.filename ?? participant.persona_name;
  const ext = getExt(filename);
  const previewUrl = `${API_BASE}/api/rooms/${roomId}/documents/${participant.document_id}/preview`;

  const [textContent, setTextContent] = useState<string | null>(null);
  const [fetchError, setFetchError] = useState(false);

  // Fetch text content for non-PDF renderable types
  useEffect(() => {
    if (!TEXT_EXTS.has(ext)) return;
    let cancelled = false;
    fetch(previewUrl)
      .then((r) => {
        if (!r.ok) throw new Error(`HTTP ${r.status}`);
        return r.text();
      })
      .then((t) => { if (!cancelled) setTextContent(t); })
      .catch(() => { if (!cancelled) setFetchError(true); });
    return () => { cancelled = true; };
  }, [previewUrl, ext]);

  // Close on Escape
  useEffect(() => {
    const handler = (e: KeyboardEvent) => { if (e.key === 'Escape') onClose(); };
    document.addEventListener('keydown', handler);
    return () => document.removeEventListener('keydown', handler);
  }, [onClose]);

  const renderBody = () => {
    if (ext === PDF_EXT) {
      return (
        <object
          data={previewUrl}
          type="application/pdf"
          className="doc-preview-iframe"
          aria-label={filename}
        >
          {/* Fallback for browsers that cannot render PDFs inline */}
          <div className="doc-preview-fallback">
            <p>Your browser cannot display this PDF inline.</p>
            <a href={previewUrl} target="_blank" rel="noopener noreferrer" className="btn btn-primary">
              Open PDF
            </a>
          </div>
        </object>
      );
    }

    if (TEXT_EXTS.has(ext)) {
      if (fetchError) {
        return (
          <div className="doc-preview-fallback">
            <p>Could not load file content.</p>
            <a href={previewUrl} target="_blank" rel="noopener noreferrer" className="btn btn-primary">
              Open in new tab
            </a>
          </div>
        );
      }
      if (textContent === null) {
        return (
          <div className="doc-preview-fallback">
            <div className="spinner" style={{ width: 28, height: 28 }} />
            <p>Loading…</p>
          </div>
        );
      }
      return <pre className="doc-preview-text">{textContent}</pre>;
    }

    // Unsupported type
    return (
      <div className="doc-preview-fallback">
        <p>Preview not available for <strong>{ext || 'this file type'}</strong>.</p>
        <a href={previewUrl} target="_blank" rel="noopener noreferrer" className="btn btn-primary">
          Download / Open
        </a>
      </div>
    );
  };

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
              style={{
                background: color, width: 28, height: 28,
                fontSize: '0.75rem', borderRadius: 7, flexShrink: 0,
                display: 'flex', alignItems: 'center', justifyContent: 'center',
                color: '#fff', fontWeight: 700,
              }}
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
          {renderBody()}
        </div>
      </div>
    </div>
  );
}
