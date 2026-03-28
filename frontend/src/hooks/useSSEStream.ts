import { useCallback, useRef } from 'react';
import { createLogger } from '../utils/logger';

const log = createLogger('sse');

const API_BASE = import.meta.env.VITE_API_URL || 'http://localhost:8000';

export interface SSEChunk {
  event?: string;
  speaker?: string;
  document_id?: string;
  chunk?: string;
  done?: boolean;
  web_search?: boolean;
  error?: string;
}

export interface UseSSEStreamOptions {
  onChunk: (data: SSEChunk) => void;
  onSpeakerStart?: (speaker: string, documentId?: string) => void;
  onRoundComplete?: () => void;
  onError?: (msg: string) => void;
}

/**
 * Hook that streams SSE from POST /api/rooms/{id}/chat.
 * Uses fetch + ReadableStream (compatible with POST, unlike EventSource).
 */
export function useSSEStream(opts: UseSSEStreamOptions) {
  const abortRef = useRef<AbortController | null>(null);

  const stream = useCallback(
    async (roomId: string, question: string, sessionId?: string) => {
      // Cancel any in-progress stream
      abortRef.current?.abort();
      const controller = new AbortController();
      abortRef.current = controller;

      log.info(`Starting stream — room=${roomId} q="${question.slice(0, 60)}"`);
      const t0 = performance.now();

      try {
        const res = await fetch(`${API_BASE}/api/rooms/${roomId}/chat`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ question, session_id: sessionId }),
          signal: controller.signal,
        });

        if (!res.ok) {
          const body = await res.json().catch(() => ({})) as Record<string, unknown>;
          log.error(`Stream request failed — HTTP ${res.status}`, body);
          throw new Error((body.detail as string) ?? `HTTP ${res.status}`);
        }

        if (!res.body) {
          log.error('Stream response has no body');
          throw new Error('No response body');
        }

        log.debug('SSE stream opened, reading chunks...');
        const reader = res.body.getReader();
        const decoder = new TextDecoder();
        let buffer = '';
        let chunkCount = 0;

        while (true) {
          const { done, value } = await reader.read();
          if (done) {
            log.debug(`Stream ended — ${chunkCount} event(s) in ${(performance.now() - t0).toFixed(0)}ms`);
            break;
          }

          buffer += decoder.decode(value, { stream: true });
          const lines = buffer.split('\n');
          buffer = lines.pop() ?? ''; // keep partial line

          for (const line of lines) {
            if (!line.startsWith('data: ')) continue;
            const raw = line.slice(6).trim();
            if (!raw) continue;

            try {
              const data: SSEChunk = JSON.parse(raw);
              chunkCount++;

              if (data.error) {
                log.error(`SSE error event: ${data.error}`);
                opts.onError?.(data.error);
                return;
              }

              if (data.event === 'speaker_start') {
                log.info(`Speaker start — "${data.speaker}" (doc=${data.document_id})`);
                opts.onSpeakerStart?.(data.speaker!, data.document_id);
              } else if (data.event === 'round_complete') {
                log.info(`Round complete — total ${chunkCount} events, ${(performance.now() - t0).toFixed(0)}ms`);
                opts.onRoundComplete?.();
              } else if (data.done) {
                log.debug('SSE done=true token received');
                opts.onChunk(data);
              } else {
                opts.onChunk(data);
              }
            } catch (parseErr) {
              log.warn(`Malformed SSE line (skipped): "${raw.slice(0, 80)}"`, parseErr);
            }
          }
        }
      } catch (e) {
        const err = e as Error;
        if (err.name === 'AbortError') {
          log.debug('Stream aborted by user');
          return;
        }
        if (err.message === 'Failed to fetch') {
          log.error(`Network error — cannot reach API at ${API_BASE}`);
        } else {
          log.error(`Stream error: ${err.message}`, err);
        }
        opts.onError?.(err.message);
      }
    },
    [opts],
  );

  const abort = useCallback(() => {
    log.debug('Aborting active stream');
    abortRef.current?.abort();
    abortRef.current = null;
  }, []);

  return { stream, abort };
}
