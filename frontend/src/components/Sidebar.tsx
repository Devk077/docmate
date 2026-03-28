import { useNavigate, useLocation } from 'react-router-dom';
import '../styles/sidebar.css';
import type { Room } from '../api/client';

interface SidebarProps {
  rooms: Room[];
  onNewRoom: () => void;
  onDeleteRoom: (roomId: string) => void;
  loading: boolean;
  isOpen?: boolean;
  onClose?: () => void;
}

export function Sidebar({ rooms, onNewRoom, onDeleteRoom, loading, isOpen, onClose }: SidebarProps) {
  const navigate = useNavigate();
  const { pathname } = useLocation();

  const activeRoomId = pathname.startsWith('/rooms/') ? pathname.split('/')[2] : null;

  const handleDelete = (e: React.MouseEvent, roomId: string) => {
    e.stopPropagation();
    if (confirm('Delete this room and all its documents?')) {
      onDeleteRoom(roomId);
      if (activeRoomId === roomId) navigate('/');
    }
  };

  return (
    <>
      {isOpen && <div className="sidebar-backdrop" onClick={onClose} />}
      <aside className={`sidebar ${isOpen ? 'open' : ''}`}>
        {/* Brand */}
      <div className="sidebar-brand">
        <div className="logo">D</div>
        <span className="brand-name">DoqToq</span>
      </div>

      {/* Rooms section */}
      <div className="sidebar-section-header">
        <span className="sidebar-section-label">Discussion Rooms</span>
        <button className="sidebar-add-btn" onClick={onNewRoom} title="New room">+</button>
      </div>

      <nav className="sidebar-rooms">
        {loading && (
          <div className="sidebar-empty">
            <div className="spinner" style={{ margin: '0 auto' }} />
          </div>
        )}

        {!loading && rooms.length === 0 && (
          <div className="sidebar-empty">
            No rooms yet.<br />
            Click <strong>+</strong> to start a discussion.
          </div>
        )}

        {rooms.map((room) => (
          <div
            key={room.id}
            className={`sidebar-room-item ${activeRoomId === room.id ? 'active' : ''}`}
            onClick={() => navigate(`/rooms/${room.id}`)}
          >
            <div className="room-icon">
              <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" opacity="0.7">
                <path d="M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z"/>
              </svg>
            </div>
            <div className="room-info">
              <div className="room-name">{room.name}</div>
              <div className="room-doc-count">{room.document_count} doc{room.document_count !== 1 ? 's' : ''} &middot; {room.ai_model}</div>
            </div>
            <button
              className="room-delete-btn"
              onClick={(e) => handleDelete(e, room.id)}
              title="Delete room"
            >
              ×
            </button>
          </div>
        ))}
      </nav>

      {/* Footer */}
      <div className="sidebar-footer">
        <div className="sidebar-footer-text">DoqToq v2.0 · Groups</div>
      </div>
    </aside>
    </>
  );
}
