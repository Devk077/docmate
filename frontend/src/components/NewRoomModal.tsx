import { useState, useRef, useCallback } from 'react';
import { createRoom, uploadDocument, getOrCreateSession } from '../api/client';
import type { Room } from '../api/client';
import { toast } from '../utils/toast';
import '../styles/room.css';

interface NewRoomModalProps {
  onClose: () => void;
  onCreated: (room: Room) => void;
}

const AI_MODELS = [
  { value: 'google', label: '🔵 Google Gemini' },
  { value: 'mistral', label: '🟠 Mistral' },
  { value: 'ollama', label: '🟣 Ollama (local)' },
];

function formatBytes(b: number) {
  if (b < 1024) return `${b} B`;
  if (b < 1024 * 1024) return `${(b / 1024).toFixed(1)} KB`;
  return `${(b / (1024 * 1024)).toFixed(1)} MB`;
}

export function NewRoomModal({ onClose, onCreated }: NewRoomModalProps) {
  const [name, setName] = useState('');
  const [aiModel, setAiModel] = useState('google');
  const [files, setFiles] = useState<File[]>([]);
  const [dragOver, setDragOver] = useState(false);
  const [step, setStep] = useState<'form' | 'uploading' | 'done'>('form');
  const [progress, setProgress] = useState({ current: 0, total: 0, label: '' });
  const fileInputRef = useRef<HTMLInputElement>(null);

  const addFiles = useCallback((newFiles: File[]) => {
    setFiles((prev) => {
      const existing = new Set(prev.map((f) => f.name));
      return [...prev, ...newFiles.filter((f) => !existing.has(f.name))];
    });
  }, []);

  const onDrop = (e: React.DragEvent) => {
    e.preventDefault();
    setDragOver(false);
    addFiles(Array.from(e.dataTransfer.files));
  };

  const removeFile = (idx: number) => {
    setFiles((prev) => prev.filter((_, i) => i !== idx));
  };

  const handleCreate = async () => {
    if (!name.trim()) { toast.error('Room name is required'); return; }
    if (files.length === 0) { toast.error('Upload at least one document'); return; }
    setStep('uploading');

    try {
      // 1. Create room
      setProgress({ current: 0, total: files.length + 1, label: 'Creating room...' });
      const room = await createRoom(name.trim(), aiModel);

      // 2. Create initial session
      await getOrCreateSession(room.id);

      // 3. Upload each file
      for (let i = 0; i < files.length; i++) {
        setProgress({
          current: i + 1,
          total: files.length + 1,
          label: `Indexing "${files[i].name}" (${i + 1}/${files.length})...`,
        });
        await uploadDocument(room.id, files[i], aiModel);
      }

      setStep('done');
      toast.success('Room created successfully');
      setTimeout(() => onCreated(room), 400);
    } catch (e) {
      toast.error(`Failed to create room: ${(e as Error).message}`);
      setStep('form');
    }
  };

  const pct = progress.total > 0 ? Math.round((progress.current / progress.total) * 100) : 0;

  return (
    <div className="modal-backdrop" onClick={(e) => e.target === e.currentTarget && onClose()}>
      <div className="modal">
        <div className="modal-header">
          <h2>New Discussion Room</h2>
          <button className="modal-close" onClick={onClose}>×</button>
        </div>

        {step === 'form' && (
          <>
            {/* Room name */}
            <div className="form-group">
              <label className="form-label">Room Name</label>
              <input
                value={name}
                onChange={(e) => setName(e.target.value)}
                placeholder="e.g. Q3 Research Review"
                autoFocus
                onKeyDown={(e) => e.key === 'Enter' && handleCreate()}
              />
            </div>

            {/* AI Model */}
            <div className="form-group">
              <label className="form-label">AI Model</label>
              <select value={aiModel} onChange={(e) => setAiModel(e.target.value)}>
                {AI_MODELS.map((m) => (
                  <option key={m.value} value={m.value}>{m.label}</option>
                ))}
              </select>
            </div>

            {/* Drop zone */}
            <div className="form-group">
              <label className="form-label">Documents</label>
              <div
                className={`dropzone ${dragOver ? 'dragover' : ''}`}
                onDragOver={(e) => { e.preventDefault(); setDragOver(true); }}
                onDragLeave={() => setDragOver(false)}
                onDrop={onDrop}
                onClick={() => fileInputRef.current?.click()}
              >
                <div className="dropzone-icon">
                <svg width="32" height="32" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round" opacity="0.4">
                  <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"/>
                  <polyline points="14,2 14,8 20,8"/>
                </svg>
              </div>
                <div className="dropzone-title">Drop files here or click to browse</div>
                <div className="dropzone-sub">Each document becomes a discussion participant</div>
                <div className="dropzone-types">
                  {['PDF', 'TXT', 'DOCX', 'MD'].map((t) => (
                    <span key={t} className="file-type-chip">.{t.toLowerCase()}</span>
                  ))}
                </div>
              </div>
              <input
                ref={fileInputRef}
                type="file"
                multiple
                accept=".pdf,.txt,.docx,.md,.csv"
                style={{ display: 'none' }}
                onChange={(e) => addFiles(Array.from(e.target.files || []))}
              />

              {files.length > 0 && (
                <div className="file-list">
                  {files.map((f, i) => (
                    <div key={f.name} className="file-item">
                      <span className="file-item-icon">
                      <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" opacity="0.5">
                        <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"/>
                        <polyline points="14,2 14,8 20,8"/>
                      </svg>
                    </span>
                      <span className="file-item-name">{f.name}</span>
                      <span className="file-item-size">{formatBytes(f.size)}</span>
                      <button className="file-item-remove" onClick={() => removeFile(i)}>×</button>
                    </div>
                  ))}
                </div>
              )}
            </div>

            <div className="modal-actions">
              <button className="btn btn-ghost" onClick={onClose}>Cancel</button>
              <button className="btn btn-primary" onClick={handleCreate}>
              Start Discussion
            </button>
            </div>
          </>
        )}

        {step === 'uploading' && (
          <div style={{ padding: '20px 0' }}>
            <div className="upload-progress">
              <div className="progress-label">
                <span>{progress.label}</span>
                <span>{pct}%</span>
              </div>
              <div className="progress-bar-track">
                <div className="progress-bar-fill" style={{ width: `${pct}%` }} />
              </div>
            </div>
            <p style={{ fontSize: '0.8rem', marginTop: 16, textAlign: 'center' }}>
              Generating persona names and indexing documents...
            </p>
          </div>
        )}

        {step === 'done' && (
          <div className="empty-state">
            <h3>Room ready</h3>
            <p>Opening your discussion room...</p>
          </div>
        )}
      </div>
    </div>
  );
}
