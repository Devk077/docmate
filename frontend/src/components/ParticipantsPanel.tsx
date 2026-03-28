import { useState, useRef, useCallback } from 'react';
import { uploadDocument, deleteDocument } from '../api/client';
import { DocCard, type DocSettings } from './DocCard';
import { DocPreviewModal } from './DocPreviewModal';
import type { Participant } from '../api/client';
import { toast } from '../utils/toast';
import '../styles/chat.css';

interface ParticipantsPanelProps {
  roomId: string;
  aiModel: string;
  participants: Participant[];
  thinkingSpeaker?: string | null;
  loading: boolean;
  onDocumentAdded: () => void;
  onDocumentRemoved: () => void;
}

export function ParticipantsPanel({
  roomId,
  aiModel,
  participants,
  thinkingSpeaker,
  loading,
  onDocumentAdded,
  onDocumentRemoved,
}: ParticipantsPanelProps) {
  const [uploading, setUploading] = useState(false);
  const [deletingId, setDeletingId] = useState<string | null>(null);
  const [previewParticipant, setPreviewParticipant] = useState<Participant | null>(null);
  const [docSettings, setDocSettings] = useState<Record<string, DocSettings>>({});
  const fileInputRef = useRef<HTMLInputElement>(null);

  const handleFileChange = useCallback(
    async (e: React.ChangeEvent<HTMLInputElement>) => {
      const files = Array.from(e.target.files || []);
      if (!files.length) return;
      setUploading(true);
      try {
        for (const file of files) {
          await uploadDocument(roomId, file, aiModel);
        }
        toast.success(`Successfully added ${files.length} document${files.length > 1 ? 's' : ''}`);
        onDocumentAdded();
      } catch (err) {
        toast.error(`Failed to add document: ${(err as Error).message}`);
      } finally {
        setUploading(false);
        if (fileInputRef.current) fileInputRef.current.value = '';
      }
    },
    [roomId, aiModel, onDocumentAdded]
  );

  const handleDelete = async (docId: string) => {
    if (!confirm('Remove this document from the room?')) return;
    setDeletingId(docId);
    try {
      await deleteDocument(roomId, docId);
      toast.success('Document removed');
      onDocumentRemoved();
    } catch (err) {
      toast.error(`Failed to remove document: ${(err as Error).message}`);
    } finally {
      setDeletingId(null);
    }
  };

  const handleSettingsChange = (docId: string, settings: DocSettings) => {
    setDocSettings((prev) => ({ ...prev, [docId]: settings }));
    // NOTE: Currently applied in-memory for this session. Backend update requires
    // a dedicated PATCH endpoint — tracked for Phase 8.
  };

  const defaultSettings = (docId: string): DocSettings =>
    docSettings[docId] ?? {
      temperature: 0.7,
      top_k: 4,
      model_provider: aiModel,
      embedding_provider: 'huggingface',
    };

  return (
    <aside className="participants-panel">
      <div className="panel-header">
        <h3>Participants</h3>
        <div className="panel-count">
          {participants.length} document{participants.length !== 1 ? 's' : ''}
        </div>
      </div>

      {/* Add document button */}
      <div className="panel-actions">
        <button
          className="add-doc-btn"
          onClick={() => fileInputRef.current?.click()}
          disabled={uploading}
          title="Add a document to this room"
        >
          {uploading ? (
            <><span className="spinner" style={{ width: 12, height: 12, borderWidth: 1.5 }} /> Indexing...</>
          ) : (
            <>+ Add Document</>
          )}
        </button>
        <input
          ref={fileInputRef}
          type="file"
          multiple
          accept=".pdf,.txt,.docx,.md,.csv"
          style={{ display: 'none' }}
          onChange={handleFileChange}
        />
      </div>

      <div className="panel-divider" />

      {/* Participant list */}
      <div className="panel-list">
        {loading && (
          <div style={{ display: 'flex', justifyContent: 'center', padding: 20 }}>
            <div className="spinner" />
          </div>
        )}

        {!loading && participants.length === 0 && (
          <div style={{ padding: '12px 16px', color: 'var(--text-muted)', fontSize: '0.8rem', lineHeight: 1.6 }}>
            No documents yet.<br />
            Click "Add Document" to start a discussion.
          </div>
        )}

        {participants.map((p) => (
          <DocCard
            key={p.document_id}
            participant={p}
            isThinking={thinkingSpeaker === p.persona_name}
            settings={defaultSettings(p.document_id)}
            onSettingsChange={handleSettingsChange}
            onDelete={handleDelete}
            onPreview={setPreviewParticipant}
            deleting={deletingId === p.document_id}
          />
        ))}
      </div>

      {/* PDF/Doc preview modal */}
      {previewParticipant && (
        <DocPreviewModal
          participant={previewParticipant}
          roomId={roomId}
          onClose={() => setPreviewParticipant(null)}
        />
      )}
    </aside>
  );
}
