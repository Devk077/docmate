import { useState, useEffect, useCallback } from 'react';
import { listRooms, createRoom, deleteRoom, type Room } from '../api/client';
import { toast } from '../utils/toast';

export function useRooms() {
  const [rooms, setRooms] = useState<Room[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const fetchRooms = useCallback(async () => {
    try {
      setLoading(true);
      setError(null);
      const data = await listRooms();
      setRooms(data);
    } catch (e) {
      const msg = (e as Error).message;
      setError(msg);
      toast.error(`Failed to load rooms: ${msg}`);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => { fetchRooms(); }, [fetchRooms]);

  const addRoom = useCallback(async (name: string, aiModel = 'google') => {
    const room = await createRoom(name, aiModel);
    setRooms((prev) => [room, ...prev]);
    return room;
  }, []);

  const removeRoom = useCallback(async (roomId: string) => {
    try {
      await deleteRoom(roomId);
      setRooms((prev) => prev.filter((r) => r.id !== roomId));
      toast.success('Room deleted');
    } catch (e) {
      toast.error(`Failed to delete room: ${(e as Error).message}`);
    }
  }, []);

  return { rooms, loading, error, refresh: fetchRooms, addRoom, removeRoom };
}
