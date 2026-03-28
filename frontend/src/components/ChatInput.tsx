import { useState, useRef, useEffect, useCallback } from 'react';
import { getPersonaColor } from '../utils/colors';
import type { Participant } from '../api/client';
import '../styles/chat.css';

interface ChatInputProps {
  participants: Participant[];
  onSend: (message: string) => void;
  disabled?: boolean;
}

export function ChatInput({ participants, onSend, disabled }: ChatInputProps) {
  const [value, setValue] = useState('');
  const [showMention, setShowMention] = useState(false);
  const [mentionQuery, setMentionQuery] = useState('');
  const [highlightIdx, setHighlightIdx] = useState(0);
  const textareaRef = useRef<HTMLTextAreaElement>(null);

  // List of matching persona names for @mention autocomplete
  const matches = participants.filter((p) =>
    mentionQuery === '' || p.persona_name.toLowerCase().includes(mentionQuery.toLowerCase())
  );

  // Auto-resize textarea
  useEffect(() => {
    const ta = textareaRef.current;
    if (ta) {
      ta.style.height = 'auto';
      ta.style.height = `${Math.min(ta.scrollHeight, 120)}px`;
    }
  }, [value]);

  const handleChange = (e: React.ChangeEvent<HTMLTextAreaElement>) => {
    const v = e.target.value;
    setValue(v);

    // Detect @mention: look for the last @ before cursor
    const cursor = e.target.selectionStart;
    const textBeforeCursor = v.slice(0, cursor);
    const atIdx = textBeforeCursor.lastIndexOf('@');

    if (atIdx !== -1) {
      const afterAt = textBeforeCursor.slice(atIdx + 1);
      if (!afterAt.includes(' ') && !afterAt.includes('\n')) {
        setMentionQuery(afterAt);
        setShowMention(true);
        setHighlightIdx(0);
        return;
      }
    }
    setShowMention(false);
  };

  const insertMention = useCallback(
    (personaName: string) => {
      const cursor = textareaRef.current?.selectionStart ?? value.length;
      const textBeforeCursor = value.slice(0, cursor);
      const atIdx = textBeforeCursor.lastIndexOf('@');
      const newValue =
        value.slice(0, atIdx) + `@${personaName} ` + value.slice(cursor);
      setValue(newValue);
      setShowMention(false);
      textareaRef.current?.focus();
    },
    [value]
  );

  const handleKeyDown = (e: React.KeyboardEvent<HTMLTextAreaElement>) => {
    if (showMention && matches.length > 0) {
      if (e.key === 'ArrowDown') {
        e.preventDefault();
        setHighlightIdx((i) => (i + 1) % matches.length);
        return;
      }
      if (e.key === 'ArrowUp') {
        e.preventDefault();
        setHighlightIdx((i) => (i - 1 + matches.length) % matches.length);
        return;
      }
      if (e.key === 'Tab' || e.key === 'Enter') {
        if (showMention) {
          e.preventDefault();
          insertMention(matches[highlightIdx].persona_name);
          return;
        }
      }
      if (e.key === 'Escape') {
        setShowMention(false);
        return;
      }
    }

    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSend();
    }
  };

  const handleSend = () => {
    const msg = value.trim();
    if (!msg || disabled) return;
    onSend(msg);
    setValue('');
    setShowMention(false);
  };

  return (
    <div className="chat-input-area">
      {/* @mention popover */}
      {showMention && matches.length > 0 && (
        <div className="mention-popover">
          <div className="mention-popover-label">@ Mention</div>
          {matches.map((p, i) => (
            <div
              key={p.document_id}
              className={`mention-item ${i === highlightIdx ? 'highlighted' : ''}`}
              onMouseDown={(e) => { e.preventDefault(); insertMention(p.persona_name); }}
            >
              <div className="mention-dot" style={{ background: getPersonaColor(p.persona_name) }} />
              <span className="mention-name">{p.persona_name}</span>
            </div>
          ))}
        </div>
      )}

      <div className="chat-input-wrapper">
        <textarea
          ref={textareaRef}
          value={value}
          onChange={handleChange}
          onKeyDown={handleKeyDown}
          placeholder={disabled ? 'Waiting for response...' : 'Ask a question... (type @ to mention a document)'}
          disabled={disabled}
          rows={1}
        />
        <button
          className="chat-send-btn"
          onClick={handleSend}
          disabled={!value.trim() || disabled}
          title="Send (Enter)"
        >
          ↑
        </button>
      </div>
      <div className="chat-hint">
        Press <kbd style={{ background: 'var(--bg-card)', padding: '1px 5px', borderRadius: 4, fontSize: '0.68rem' }}>Enter</kbd> to send ·
        <kbd style={{ background: 'var(--bg-card)', padding: '1px 5px', borderRadius: 4, fontSize: '0.68rem', marginLeft: 4 }}>Shift+Enter</kbd> for newline ·
        Type <span style={{ color: 'var(--accent)' }}>@</span> to mention a document
      </div>
    </div>
  );
}
