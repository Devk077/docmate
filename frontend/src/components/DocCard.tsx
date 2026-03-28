import { useState, useRef, useEffect } from 'react';
import { getPersonaColor, getInitial } from '../utils/colors';
import type { Participant } from '../api/client';
import '../styles/chat.css';

export interface DocSettings {
  temperature: number;
  top_k: number;
  model_provider: string;
  embedding_provider: string;
}

interface DocCardProps {
  participant: Participant;
  isThinking: boolean;
  settings: DocSettings;
  onSettingsChange: (docId: string, settings: DocSettings) => void;
  onDelete: (docId: string) => void;
  onPreview: (participant: Participant) => void;
  deleting: boolean;
}

const MODEL_OPTIONS = ['google', 'mistral', 'ollama'];
const EMBEDDING_OPTIONS = ['huggingface', 'openai'];

export function DocCard({
  participant,
  isThinking,
  settings,
  onSettingsChange,
  onDelete,
  onPreview,
  deleting,
}: DocCardProps) {
  const [menuOpen, setMenuOpen] = useState(false);
  const [settingsOpen, setSettingsOpen] = useState(false);
  const [draft, setDraft] = useState<DocSettings>(settings);
  const menuRef = useRef<HTMLDivElement>(null);

  const color = getPersonaColor(participant.persona_name);

  // Close menu on outside click
  useEffect(() => {
    if (!menuOpen && !settingsOpen) return;
    const handler = (e: MouseEvent) => {
      if (menuRef.current && !menuRef.current.contains(e.target as Node)) {
        setMenuOpen(false);
      }
    };
    document.addEventListener('mousedown', handler);
    return () => document.removeEventListener('mousedown', handler);
  }, [menuOpen, settingsOpen]);

  const applySettings = () => {
    onSettingsChange(participant.document_id, draft);
    setSettingsOpen(false);
    setMenuOpen(false);
  };

  return (
    <div className={`participant-card ${isThinking ? 'thinking' : ''}`}>
      {/* Avatar — click to preview doc */}
      <button
        className="participant-avatar"
        style={{ background: color, cursor: 'pointer' }}
        onClick={() => onPreview(participant)}
        title="Preview document"
      >
        {getInitial(participant.persona_name)}
      </button>

      <div className="participant-info">
        <div className="participant-name" title={participant.persona_name}>
          {participant.persona_name}
        </div>
        <div className="participant-status">
          {isThinking ? 'Responding...' : 'Ready'}
        </div>
      </div>

      <div className="participant-right" ref={menuRef}>
        <div
          className="status-dot"
          style={{ background: isThinking ? 'var(--accent)' : 'var(--text-muted)' }}
        />

        {/* 3-dot menu button */}
        <button
          className="doc-menu-btn"
          onClick={() => setMenuOpen((v) => !v)}
          title="Document options"
        >
          ···
        </button>

        {/* Dropdown menu */}
        {menuOpen && (
          <div className="doc-menu-dropdown">
            <button
              className="doc-menu-item"
              onClick={() => { onPreview(participant); setMenuOpen(false); }}
            >
              <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"><path d="M1 12s4-8 11-8 11 8 11 8-4 8-11 8-11-8-11-8z"/><circle cx="12" cy="12" r="3"/></svg>
              Preview
            </button>
            <button
              className="doc-menu-item"
              onClick={() => { setSettingsOpen(true); setMenuOpen(false); }}
            >
              <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"><circle cx="12" cy="12" r="3"/><path d="M19.4 15a1.65 1.65 0 0 0 .33 1.82l.06.06a2 2 0 0 1-2.83 2.83l-.06-.06a1.65 1.65 0 0 0-1.82-.33 1.65 1.65 0 0 0-1 1.51V21a2 2 0 0 1-4 0v-.09A1.65 1.65 0 0 0 9 19.4a1.65 1.65 0 0 0-1.82.33l-.06.06a2 2 0 0 1-2.83-2.83l.06-.06A1.65 1.65 0 0 0 4.68 15a1.65 1.65 0 0 0-1.51-1H3a2 2 0 0 1 0-4h.09A1.65 1.65 0 0 0 4.6 9a1.65 1.65 0 0 0-.33-1.82l-.06-.06a2 2 0 0 1 2.83-2.83l.06.06A1.65 1.65 0 0 0 9 4.68a1.65 1.65 0 0 0 1-1.51V3a2 2 0 0 1 4 0v.09a1.65 1.65 0 0 0 1 1.51 1.65 1.65 0 0 0 1.82-.33l.06-.06a2 2 0 0 1 2.83 2.83l-.06.06A1.65 1.65 0 0 0 19.4 9a1.65 1.65 0 0 0 1.51 1H21a2 2 0 0 1 0 4h-.09a1.65 1.65 0 0 0-1.51 1z"/></svg>
              Settings
            </button>
            <div className="doc-menu-divider" />
            <button
              className="doc-menu-item danger"
              onClick={() => { setMenuOpen(false); onDelete(participant.document_id); }}
              disabled={deleting}
            >
              <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"><polyline points="3 6 5 6 21 6"/><path d="M19 6l-1 14a2 2 0 0 1-2 2H8a2 2 0 0 1-2-2L5 6m3 0V4a1 1 0 0 1 1-1h4a1 1 0 0 1 1 1v2"/></svg>
              {deleting ? 'Removing...' : 'Remove'}
            </button>
          </div>
        )}
      </div>

      {/* Settings modal */}
      {settingsOpen && (
        <div className="doc-settings-backdrop" onClick={() => setSettingsOpen(false)}>
          <div className="doc-settings-modal" onClick={(e) => e.stopPropagation()}>
            <div className="doc-settings-header">
              <div className="doc-settings-title">
                <div className="participant-avatar" style={{ background: color, width: 24, height: 24, fontSize: '0.7rem', flexShrink: 0 }}>
                  {getInitial(participant.persona_name)}
                </div>
                <span>{participant.persona_name}</span>
              </div>
              <button className="settings-panel-close" onClick={() => setSettingsOpen(false)}>×</button>
            </div>

            <div className="doc-settings-body">
              <div className="doc-setting-row">
                <label className="settings-label">Temperature</label>
                <div className="doc-setting-slider-group">
                  <input
                    type="range" min="0" max="1" step="0.05"
                    value={draft.temperature}
                    onChange={(e) => setDraft((d) => ({ ...d, temperature: parseFloat(e.target.value) }))}
                    className="doc-setting-slider"
                  />
                  <span className="doc-setting-value">{draft.temperature.toFixed(2)}</span>
                </div>
                <div className="settings-note">0 = deterministic · 1 = creative</div>
              </div>

              <div className="doc-setting-row">
                <label className="settings-label">Top-K Retrieval</label>
                <div className="doc-setting-slider-group">
                  <input
                    type="range" min="1" max="10" step="1"
                    value={draft.top_k}
                    onChange={(e) => setDraft((d) => ({ ...d, top_k: parseInt(e.target.value) }))}
                    className="doc-setting-slider"
                  />
                  <span className="doc-setting-value">{draft.top_k} chunks</span>
                </div>
                <div className="settings-note">Number of document chunks retrieved per question</div>
              </div>

              <div className="doc-setting-row">
                <label className="settings-label">AI Model</label>
                <select
                  value={draft.model_provider}
                  onChange={(e) => setDraft((d) => ({ ...d, model_provider: e.target.value }))}
                  className="doc-setting-select"
                >
                  {MODEL_OPTIONS.map((m) => (
                    <option key={m} value={m}>{m === 'google' ? 'Google Gemini' : m === 'mistral' ? 'Mistral' : 'Ollama (local)'}</option>
                  ))}
                </select>
              </div>

              <div className="doc-setting-row">
                <label className="settings-label">Embeddings</label>
                <select
                  value={draft.embedding_provider}
                  onChange={(e) => setDraft((d) => ({ ...d, embedding_provider: e.target.value }))}
                  className="doc-setting-select"
                >
                  {EMBEDDING_OPTIONS.map((e) => (
                    <option key={e} value={e}>{e === 'huggingface' ? 'HuggingFace (all-MiniLM-L6-v2)' : 'OpenAI (ada-002)'}</option>
                  ))}
                </select>
                <div className="settings-note">Applied on next room load</div>
              </div>
            </div>

            <div className="doc-settings-footer">
              <button className="btn btn-ghost" onClick={() => setSettingsOpen(false)}>Cancel</button>
              <button className="btn btn-primary" onClick={applySettings}>Apply</button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
