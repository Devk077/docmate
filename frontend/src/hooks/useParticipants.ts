import { useState, useEffect, useCallback } from 'react';
import { getParticipants, type Participant } from '../api/client';
import { createLogger } from '../utils/logger';

const log = createLogger('participants');

export function useParticipants(roomId: string | null) {
  const [participants, setParticipants] = useState<Participant[]>([]);
  const [loading, setLoading] = useState(false);

  const fetch = useCallback(async () => {
    if (!roomId) return;
    log.debug(`Fetching participants for room ${roomId}`);
    setLoading(true);
    try {
      const data = await getParticipants(roomId);
      log.info(`Loaded ${data.length} participant(s):`, data.map(p => p.persona_name));
      setParticipants(data);
    } catch (err) {
      log.error(`Failed to load participants`, err);
      setParticipants([]);
    } finally {
      setLoading(false);
    }
  }, [roomId]);

  useEffect(() => { fetch(); }, [fetch]);

  const markThinking = useCallback((personaName: string) => {
    setParticipants((prev) =>
      prev.map((p) => ({ ...p, spent: p.persona_name !== personaName }))
    );
  }, []);

  const clearThinking = useCallback(() => {
    setParticipants((prev) => prev.map((p) => ({ ...p, spent: false })));
  }, []);

  return { participants, loading, refresh: fetch, markThinking, clearThinking };
}
