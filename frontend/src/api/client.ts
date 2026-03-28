// DoqToq API Client — typed wrappers around all FastAPI endpoints

import { createLogger } from '../utils/logger';

const log = createLogger('api');
const API_BASE = import.meta.env.VITE_API_URL || 'http://localhost:8000';

log.info(`Base URL: ${API_BASE}`);

// ── Helpers ───────────────────────────────────────────────────

async function apiFetch<T>(
  input: RequestInfo,
  init?: RequestInit,
  label = String(input),
): Promise<T> {
  log.debug(`→ ${init?.method ?? 'GET'} ${label}`);
  const t0 = performance.now();
  try {
    const res = await fetch(input as string, init);
    const ms  = (performance.now() - t0).toFixed(0);

    if (!res.ok) {
      const body = await res.json().catch(() => ({})) as Record<string, unknown>;
      const detail = (body.detail as string) ?? `HTTP ${res.status}`;
      log.error(`✗ ${init?.method ?? 'GET'} ${label} — ${res.status} (${ms}ms)`, body);
      throw new Error(detail);
    }

    log.debug(`✓ ${init?.method ?? 'GET'} ${label} — ${res.status} (${ms}ms)`);

    // 204 No Content — nothing to parse
    if (res.status === 204) return undefined as unknown as T;

    return res.json() as Promise<T>;
  } catch (err) {
    if (err instanceof TypeError && (err as TypeError).message === 'Failed to fetch') {
      log.error(
        `Network error — cannot reach API at ${API_BASE}. ` +
        `Make sure uvicorn is running on port 8000.`,
        err
      );
    }
    throw err;
  }
}

// ── Types ─────────────────────────────────────────────────────

export interface Room {
  id: string;
  name: string;
  ai_model: string;
  document_count: number;
  created_at: string | null;
  updated_at: string | null;
}

export interface Document {
  id: string;
  room_id: string;
  filename: string;
  persona_name: string;
  qdrant_collection: string;
  file_path: string | null;
  added_at: string | null;
}

export interface Participant {
  document_id: string;
  persona_name: string;
  collection_name: string;
  spent: boolean;
}

export interface Session {
  id: string;
  room_id: string;
  ai_model: string;
  started_at: string | null;
}

export interface ChatMessage {
  id: string;
  session_id: string;
  role: 'user' | 'document' | 'orchestrator' | 'system';
  sender_name: string | null;
  document_id: string | null;
  content: string;
  turn_number: number;
  created_at: string | null;
}

// ── Rooms ─────────────────────────────────────────────────────

export async function listRooms(): Promise<Room[]> {
  return apiFetch<Room[]>(`${API_BASE}/api/rooms`, undefined, 'listRooms');
}

export async function createRoom(name: string, ai_model = 'google'): Promise<Room> {
  return apiFetch<Room>(
    `${API_BASE}/api/rooms`,
    {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ name, ai_model }),
    },
    `createRoom("${name}")`
  );
}

export async function getRoom(roomId: string): Promise<Room> {
  return apiFetch<Room>(`${API_BASE}/api/rooms/${roomId}`, undefined, `getRoom(${roomId})`);
}

export async function deleteRoom(roomId: string): Promise<void> {
  await apiFetch<void>(
    `${API_BASE}/api/rooms/${roomId}`,
    { method: 'DELETE' },
    `deleteRoom(${roomId})`
  );
}

export async function getParticipants(roomId: string): Promise<Participant[]> {
  return apiFetch<Participant[]>(
    `${API_BASE}/api/rooms/${roomId}/participants`,
    undefined,
    `getParticipants(${roomId})`
  );
}

// ── Documents ─────────────────────────────────────────────────

export async function uploadDocument(
  roomId: string,
  file: File,
  aiModel = 'google',
): Promise<Document> {
  log.info(`uploadDocument: "${file.name}" (${(file.size / 1024).toFixed(1)} KB) → room ${roomId}`);
  const form = new FormData();
  form.append('file', file);
  form.append('ai_model', aiModel);

  const t0 = performance.now();
  const res = await fetch(`${API_BASE}/api/rooms/${roomId}/documents`, {
    method: 'POST',
    body: form,
  });
  const ms = (performance.now() - t0).toFixed(0);

  if (!res.ok) {
    const detail = await res.json().catch(() => ({})) as Record<string, unknown>;
    log.error(`uploadDocument failed — ${res.status} (${ms}ms)`, detail);
    throw new Error((detail.detail as string) || `uploadDocument: ${res.status}`);
  }

  const doc = await res.json() as Document;
  log.info(`uploadDocument: persona="${doc.persona_name}" (${ms}ms)`);
  return doc;
}

export async function deleteDocument(roomId: string, documentId: string): Promise<void> {
  await apiFetch<void>(
    `${API_BASE}/api/rooms/${roomId}/documents/${documentId}`,
    { method: 'DELETE' },
    `deleteDocument(${documentId})`
  );
}

// ── Sessions & Chat ───────────────────────────────────────────

export async function getOrCreateSession(roomId: string): Promise<Session> {
  return apiFetch<Session>(
    `${API_BASE}/api/rooms/${roomId}/sessions`,
    { method: 'POST' },
    `getOrCreateSession(${roomId})`
  );
}

export async function getChatHistory(
  roomId: string,
  sessionId?: string,
): Promise<ChatMessage[]> {
  const url = sessionId
    ? `${API_BASE}/api/rooms/${roomId}/history?session_id=${sessionId}`
    : `${API_BASE}/api/rooms/${roomId}/history`;
  const msgs = await apiFetch<ChatMessage[]>(url, undefined, `getChatHistory(${roomId})`);
  log.debug(`getChatHistory: ${msgs.length} message(s)`);
  return msgs;
}

/**
 * Send a question and get a ReadableStream of SSE chunks.
 * Returns the raw Response so the caller can read the stream.
 */
export async function startChatStream(
  roomId: string,
  question: string,
  sessionId?: string,
): Promise<Response> {
  log.info(`startChatStream: room=${roomId} q="${question.slice(0, 60)}..."`);
  const res = await fetch(`${API_BASE}/api/rooms/${roomId}/chat`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ question, session_id: sessionId }),
  });
  if (!res.ok) {
    const detail = await res.json().catch(() => ({})) as Record<string, unknown>;
    log.error(`startChatStream failed — ${res.status}`, detail);
    throw new Error((detail.detail as string) || `startChatStream: ${res.status}`);
  }
  log.debug(`startChatStream: SSE stream opened`);
  return res;
}
