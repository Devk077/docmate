import { getPersonaColor } from '../utils/colors';
import '../styles/chat.css';

export interface Message {
  id: string;
  role: 'user' | 'document' | 'orchestrator';
  sender_name?: string | null;
  content: string;
  streaming?: boolean;
  web_search?: boolean;
}

interface ChatMessageProps {
  message: Message;
}



export function ChatMessage({ message }: ChatMessageProps) {
  const isUser = message.role === 'user';
  const color = !isUser && message.sender_name
    ? getPersonaColor(message.sender_name)
    : 'var(--text-muted)';

  return (
    <div className={`chat-message ${isUser ? 'user' : 'document'} fade-in`}>
      {!isUser && message.sender_name && (
        <div className="message-header">
          <div className="message-speaker-dot" style={{ background: color }} />
          <span className="message-speaker-name" style={{ color }}>
            {message.sender_name}
          </span>
        </div>
      )}

      <div className="message-bubble">
        <span style={{ whiteSpace: 'pre-wrap' }}>{message.content}</span>
        {message.streaming && <span className="streaming-cursor" />}
      </div>

      {message.web_search && (
        <div className="web-search-badge">Web search used</div>
      )}
    </div>
  );
}

export function TypingIndicator({ speaker }: { speaker: string }) {
  const color = getPersonaColor(speaker);
  return (
    <div className="chat-message document fade-in">
      <div className="message-header">
        <div className="message-speaker-dot" style={{ background: color }} />
        <span className="message-speaker-name" style={{ color }}>{speaker}</span>
      </div>
      <div className="typing-indicator">
        <div className="typing-dots">
          <span /><span /><span />
        </div>
        <span className="typing-speaker">thinking</span>
      </div>
    </div>
  );
}
