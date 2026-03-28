import { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { NewRoomModal } from '../components/NewRoomModal';
import { useRooms } from '../hooks/useRooms';
import type { Room } from '../api/client';
import '../styles/globals.css';
import '../styles/room.css';

interface HomePageProps {
  onToggleSidebar?: () => void;
}

export function HomePage({ onToggleSidebar }: HomePageProps = {}) {
  const { rooms, loading, removeRoom } = useRooms();
  const [showModal, setShowModal] = useState(false);
  const navigate = useNavigate();

  const handleCreated = (room: Room) => {
    setShowModal(false);
    navigate(`/rooms/${room.id}`);
  };

  const handleDelete = async (e: React.MouseEvent, roomId: string) => {
    e.stopPropagation();
    if (confirm('Delete this room and all its documents?')) {
      await removeRoom(roomId);
    }
  };

  const formatDate = (ds: string | null) => {
    if (!ds) return '';
    return new Date(ds).toLocaleDateString([], { month: 'short', day: 'numeric', year: 'numeric' });
  };

  return (
    <>
      <div className="home-header">
        <button className="mobile-only sidebar-toggle" onClick={onToggleSidebar}>
          <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
            <line x1="3" y1="12" x2="21" y2="12"></line>
            <line x1="3" y1="6" x2="21" y2="6"></line>
            <line x1="3" y1="18" x2="21" y2="18"></line>
          </svg>
        </button>
      </div>
      <div className="home-page">
        <div className="home-hero">
          <h1>Discussion Rooms</h1>
          <p>Multi-document AI discussions — each document speaks in its own voice</p>
        </div>

        <div className="home-actions">
          <button className="btn btn-primary" onClick={() => setShowModal(true)}>
            + New Discussion Room
          </button>
          {rooms.length > 0 && (
            <span style={{ color: 'var(--text-muted)', fontSize: '0.82rem' }}>
              {rooms.length} room{rooms.length !== 1 ? 's' : ''}
            </span>
          )}
        </div>

        {loading && (
          <div style={{ display: 'flex', justifyContent: 'center', padding: 60 }}>
            <div className="spinner" style={{ width: 32, height: 32 }} />
          </div>
        )}

        {!loading && rooms.length === 0 && (
          <div className="empty-state">
            <div className="icon">💬</div>
            <h3>No rooms yet</h3>
            <p>Create your first discussion room and upload up to 10 documents to start a multi-voice AI conversation.</p>
            <button className="btn btn-primary" onClick={() => setShowModal(true)}>
              Create First Room
            </button>
          </div>
        )}

        {!loading && rooms.length > 0 && (
          <div className="rooms-grid">
            {rooms.map((room, i) => (
              <div
                key={room.id}
                className="room-card"
                style={{ animationDelay: `${i * 40}ms` }}
                onClick={() => navigate(`/rooms/${room.id}`)}
              >
                <div className="room-card-header">
                  <div className="room-card-icon">
                    <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round" opacity="0.6">
                      <path d="M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z"/>
                    </svg>
                  </div>
                  <button
                    className="room-card-menu btn-danger"
                    style={{ padding: '4px 8px', fontSize: '0.78rem', borderRadius: 6 }}
                    onClick={(e) => handleDelete(e, room.id)}
                  >
                    Delete
                  </button>
                </div>
                <div className="room-card-title">{room.name}</div>
                <div className="room-card-meta">
                  <div className="meta-chip">{room.ai_model}</div>
                  <div className="meta-chip">{formatDate(room.created_at)}</div>
                </div>
              </div>
            ))}
          </div>
        )}

        {showModal && (
          <NewRoomModal
            onClose={() => setShowModal(false)}
            onCreated={handleCreated}
          />
        )}
      </div>
    </>
  );
}
