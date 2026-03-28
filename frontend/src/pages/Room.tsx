import React, { useState, useEffect, useRef, useCallback } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { getRoom, getOrCreateSession, getChatHistory } from '../api/client';
import { toast } from '../utils/toast';
import { useParticipants } from '../hooks/useParticipants';
import { useSSEStream } from '../hooks/useSSEStream';
import { ParticipantsPanel } from '../components/ParticipantsPanel';
import { ChatMessage, TypingIndicator, type Message } from '../components/ChatMessage';
import { ChatInput } from '../components/ChatInput';
import { SettingsPanel } from '../components/SettingsPanel';
import { createLogger } from '../utils/logger';
import type { Room } from '../api/client';
import '../styles/globals.css';
import '../styles/chat.css';

const log = createLogger('room');


export interface RoomPageProps {
  onToggleSidebar?: () => void;
}

export function RoomPage({ onToggleSidebar }: RoomPageProps = {}) {
  const { roomId } = useParams<{ roomId: string }>();
  const navigate = useNavigate();

  const [room, setRoom] = useState<Room | null>(null);
  const [sessionId, setSessionId] = useState<string | null>(null);
  const [messages, setMessages] = useState<Message[]>([]);
  const [streamingMsg, setStreamingMsg] = useState<Message | null>(null);
  const [thinkingSpeaker, setThinkingSpeaker] = useState<string | null>(null);
  const [isStreaming, setIsStreaming] = useState(false);
  const [loadError, setLoadError] = useState<string | null>(null);
  const [showSettings, setShowSettings] = useState(false);

  const messagesEndRef = useRef<HTMLDivElement>(null);
  const streamingMsgRef = useRef<Message | null>(null);
  const loadedRef = useRef(false);
  const initialHistoryLengthRef = useRef(0);

  const { participants, loading: participantsLoading, refresh: refreshParticipants } =
    useParticipants(roomId ?? null);

  // Keep ref in sync
  useEffect(() => { streamingMsgRef.current = streamingMsg; }, [streamingMsg]);

  // Scroll to bottom
  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages, streamingMsg]);

  // Reset when navigating between rooms
  useEffect(() => {
    loadedRef.current = false;
    setMessages([]);
    setStreamingMsg(null);
    streamingMsgRef.current = null;
    setThinkingSpeaker(null);
    setIsStreaming(false);
    setLoadError(null);
    setRoom(null);
    setSessionId(null);
    setShowSettings(false);
  }, [roomId]);

  // Load room + session + history — once per roomId
  useEffect(() => {
    if (!roomId || loadedRef.current) return;
    loadedRef.current = true;

    (async () => {
      log.info(`Loading room ${roomId}`);
      try {
        const [r, sess] = await Promise.all([
          getRoom(roomId),
          getOrCreateSession(roomId),
        ]);
        log.info(`Room: "${r.name}" | session: ${sess.id} | model: ${r.ai_model}`);
        setRoom(r);
        setSessionId(sess.id);

        const history = await getChatHistory(roomId, sess.id);
        log.info(`History: ${history.length} message(s)`);
        initialHistoryLengthRef.current = history.length;
        setMessages(
          history.map((m) => ({
            id: m.id,
            role: (m.role === 'user' ? 'user' : 'document') as Message['role'],
            sender_name: m.sender_name,
            content: m.content,
          }))
        );
      } catch (e) {
        log.error(`Failed to load room ${roomId}`, e);
        setLoadError((e as Error).message);
      }
    })();
  }, [roomId]);

  // SSE streaming
  const { stream } = useSSEStream({
    onSpeakerStart: (speaker) => {
      setThinkingSpeaker(speaker);
      const prev = streamingMsgRef.current;
      if (prev && prev.sender_name !== speaker) {
        setMessages((msgs) => [...msgs, { ...prev, streaming: false }]);
        setStreamingMsg(null);
        streamingMsgRef.current = null;
      }
    },
    onChunk: (data) => {
      if (!data.speaker || data.done) return;
      setStreamingMsg((prev) => {
        const next =
          prev && prev.sender_name === data.speaker
            ? { ...prev, content: prev.content + (data.chunk ?? '') }
            : {
                id: `stream-${Date.now()}`,
                role: 'document' as const,
                sender_name: data.speaker,
                content: data.chunk ?? '',
                streaming: true,
                web_search: data.web_search,
              };
        streamingMsgRef.current = next;
        return next;
      });
    },
    onRoundComplete: () => {
      const finalMsg = streamingMsgRef.current;
      streamingMsgRef.current = null;
      setStreamingMsg(null);
      if (finalMsg) {
        setMessages((msgs) => [...msgs, { ...finalMsg, streaming: false }]);
      }
      setThinkingSpeaker(null);
      setIsStreaming(false);
      refreshParticipants();
    },
    onError: (msg) => {
      setIsStreaming(false);
      setThinkingSpeaker(null);
      streamingMsgRef.current = null;
      setStreamingMsg(null);
      setMessages((msgs) => [
        ...msgs,
        {
          id: `err-${Date.now()}`,
          role: 'orchestrator' as const,
          content: `Error: ${msg}`,
          sender_name: 'System',
        },
      ]);
    },
  });

  const handleSend = useCallback(
    async (question: string) => {
      if (!roomId || isStreaming) return;
      
      let activeSessionId = sessionId;
      if (!activeSessionId) {
        try {
          const sess = await getOrCreateSession(roomId);
          setSessionId(sess.id);
          activeSessionId = sess.id;
        } catch (e) {
          toast.error('Failed to create session');
          return;
        }
      }

      log.debug(`Send: "${question.slice(0, 80)}"`);
      const userMsg: Message = {
        id: `user-${Date.now()}`,
        role: 'user',
        sender_name: 'You',
        content: question,
      };
      setMessages((prev) => [...prev, userMsg]);
      setIsStreaming(true);
      await stream(roomId, question, activeSessionId);
    },
    [roomId, sessionId, isStreaming, stream]
  );

  if (loadError) {
    return (
      <div className="empty-state" style={{ height: '100%' }}>
        <div className="icon" style={{ fontSize: '2rem', opacity: 0.5 }}>!</div>
        <h3>Failed to load room</h3>
        <p>{loadError}</p>
        <button className="btn btn-ghost" onClick={() => navigate('/')}>Back to Home</button>
      </div>
    );
  }

  if (!room) {
    return (
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'center', height: '100%' }}>
        <div className="spinner" style={{ width: 36, height: 36 }} />
      </div>
    );
  }

  return (
    <div className="room-layout">
      {/* ── Chat area ───────────────────────── */}
      <div className="chat-area">
        <div className="chat-header">
          <button className="chat-header-back mobile-only" onClick={onToggleSidebar} title="Menu">
            <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
              <line x1="3" y1="12" x2="21" y2="12"></line>
              <line x1="3" y1="6" x2="21" y2="6"></line>
              <line x1="3" y1="18" x2="21" y2="18"></line>
            </svg>
          </button>
          <div className="chat-header-title">
            <h2># {room.name}</h2>
            <div className="chat-header-subtitle">
              {participants.length} document{participants.length !== 1 ? 's' : ''} &middot; {room.ai_model}
            </div>
          </div>
          <button
            className="chat-header-settings"
            onClick={() => setShowSettings((v) => !v)}
            title="Settings"
          >
            <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
              <circle cx="12" cy="12" r="3"/>
              <path d="M19.4 15a1.65 1.65 0 0 0 .33 1.82l.06.06a2 2 0 1 1-2.83 2.83l-.06-.06a1.65 1.65 0 0 0-1.82-.33 1.65 1.65 0 0 0-1 1.51V21a2 2 0 0 1-4 0v-.09A1.65 1.65 0 0 0 9 19.4a1.65 1.65 0 0 0-1.82.33l-.06.06a2 2 0 1 1-2.83-2.83l.06-.06A1.65 1.65 0 0 0 4.68 15a1.65 1.65 0 0 0-1.51-1H3a2 2 0 0 1 0-4h.09A1.65 1.65 0 0 0 4.6 9a1.65 1.65 0 0 0-.33-1.82l-.06-.06a2 2 0 1 1 2.83-2.83l.06.06A1.65 1.65 0 0 0 9 4.68a1.65 1.65 0 0 0 1-1.51V3a2 2 0 0 1 4 0v.09a1.65 1.65 0 0 0 1 1.51 1.65 1.65 0 0 0 1.82-.33l.06-.06a2 2 0 1 1 2.83 2.83l-.06.06A1.65 1.65 0 0 0 19.4 9a1.65 1.65 0 0 0 1.51 1H21a2 2 0 0 1 0 4h-.09a1.65 1.65 0 0 0-1.51 1z"/>
            </svg>
          </button>
        </div>

        {/* Settings panel (inline, collapsible) */}
        {showSettings && (
          <SettingsPanel room={room} onClose={() => setShowSettings(false)} />
        )}

        <div className="chat-messages">
          {messages.length === 0 && !streamingMsg && !isStreaming && (
            <div className="empty-state" style={{ flex: 1 }}>
              <div className="icon" style={{ fontSize: '2rem', opacity: 0.4 }}>
                {participants.length === 0 ? '📄' : '[ ]'}
              </div>
              <h3>{participants.length === 0 ? 'Room is empty' : 'Start the discussion'}</h3>
              <p style={{ maxWidth: 400 }}>
                {participants.length === 0 ? (
                  'Upload at least one document using the + Add Document button in the panel to begin.'
                ) : (
                  <>
                    Ask a question and documents will respond from their own content.
                    <br />Type <code>@</code> to address a specific document.
                  </>
                )}
              </p>
            </div>
          )}

          {messages.map((msg, idx) => {
            const isDivider =
              initialHistoryLengthRef.current > 0 &&
              idx === initialHistoryLengthRef.current;
            return (
              <React.Fragment key={msg.id}>
                {isDivider && (
                  <div className="session-divider">
                    <span>Current Session</span>
                  </div>
                )}
                <ChatMessage message={msg} />
              </React.Fragment>
            );
          })}

          {isStreaming && !streamingMsg && thinkingSpeaker && (
            <TypingIndicator speaker={thinkingSpeaker} />
          )}
          {streamingMsg && <ChatMessage message={streamingMsg} />}

          <div ref={messagesEndRef} />
        </div>

        <ChatInput
          participants={participants}
          onSend={handleSend}
          disabled={isStreaming || participants.length === 0}
        />
      </div>

      {/* ── Participants panel ──────────────── */}
      <ParticipantsPanel
        roomId={roomId!}
        aiModel={room.ai_model}
        participants={participants}
        thinkingSpeaker={thinkingSpeaker}
        loading={participantsLoading}
        onDocumentAdded={refreshParticipants}
        onDocumentRemoved={refreshParticipants}
      />
    </div>
  );
}
