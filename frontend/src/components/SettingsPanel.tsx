import { useEffect } from 'react';
import { toast } from '../utils/toast';
import '../styles/chat.css';
import type { Room } from '../api/client';

interface SettingsPanelProps {
  room: Room;
  onClose: () => void;
}

const MODEL_OPTIONS = [
  { value: 'google',  label: 'Google Gemini' },
  { value: 'mistral', label: 'Mistral' },
  { value: 'ollama',  label: 'Ollama (local)' },
];




/**
 * Settings panel shown inline under the room header.
 * Currently shows read-only room settings.
 * Future: allow changing temperature, top-k, model per-session.
 */
export function SettingsPanel({ room, onClose }: SettingsPanelProps) {
  useEffect(() => {
    const handleEsc = (e: KeyboardEvent) => e.key === 'Escape' && onClose();
    window.addEventListener('keydown', handleEsc);
    return () => window.removeEventListener('keydown', handleEsc);
  }, [onClose]);

  const copyRoomId = async () => {
    try {
      await navigator.clipboard.writeText(room.id);
      toast.success('Room ID copied to clipboard');
    } catch {
      toast.error('Failed to copy Room ID');
    }
  };

  return (
    <div className="settings-panel">
      <div className="settings-panel-header">
        <span>Room Settings</span>
        <button className="settings-panel-close" onClick={onClose}>×</button>
      </div>

      <div className="settings-grid">
        <div className="settings-group">
          <label className="settings-label">AI Model</label>
          <div className="settings-value">{MODEL_OPTIONS.find(m => m.value === room.ai_model)?.label ?? room.ai_model}</div>
          <div className="settings-note">Set at room creation. Create a new room to change models.</div>
        </div>

        <div className="settings-group">
          <label className="settings-label">Embeddings</label>
          <div className="settings-value">HuggingFace · all-MiniLM-L6-v2</div>
          <div className="settings-note">Sentence transformer used for vector retrieval.</div>
        </div>

        <div className="settings-group">
          <label className="settings-label">Temperature</label>
          <div className="settings-value">0.7</div>
          <div className="settings-note">Controls response creativity. Lower = more factual.</div>
        </div>

        <div className="settings-group">
          <label className="settings-label">Top-K Retrieval</label>
          <div className="settings-value">4 chunks</div>
          <div className="settings-note">Number of document chunks retrieved per question.</div>
        </div>

        <div className="settings-group">
          <label className="settings-label">Similarity Threshold</label>
          <div className="settings-value">0.75</div>
          <div className="settings-note">Documents below this score are skipped for a given question.</div>
        </div>

        <div className="settings-group">
          <label className="settings-label">Room ID</label>
          <div className="settings-value mono" style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
            {room.id}
            <button
              onClick={copyRoomId}
              style={{ background: 'none', border: 'none', color: 'var(--text-muted)', cursor: 'pointer', display: 'flex', alignItems: 'center', padding: 4 }}
              title="Copy Room ID"
            >
              <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                <rect x="9" y="9" width="13" height="13" rx="2" ry="2"/>
                <path d="M5 15H4a2 2 0 0 1-2-2V4a2 2 0 0 1 2-2h9a2 2 0 0 1 2 2v1"/>
              </svg>
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}
