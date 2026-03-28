import { useState } from 'react';
import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom';
import { Sidebar } from './components/Sidebar';
import { NewRoomModal } from './components/NewRoomModal';
import { HomePage } from './pages/Home';
import { RoomPage } from './pages/Room';
import { useRooms } from './hooks/useRooms';
import type { Room } from './api/client';
import { useNavigate } from 'react-router-dom';
import { ToastContainer } from './components/ToastContainer';
import './styles/globals.css';
import './styles/sidebar.css';

function AppInner() {
  const { rooms, loading, removeRoom, refresh } = useRooms();
  const [showModal, setShowModal] = useState(false);
  const [sidebarOpen, setSidebarOpen] = useState(false);
  const navigate = useNavigate();

  const handleCreated = (room: Room) => {
    setShowModal(false);
    refresh();
    navigate(`/rooms/${room.id}`);
  };

  return (
    <div className="app-layout">
      <Sidebar
        rooms={rooms}
        loading={loading}
        onNewRoom={() => setShowModal(true)}
        onDeleteRoom={removeRoom}
        isOpen={sidebarOpen}
        onClose={() => setSidebarOpen(false)}
      />

      <main className="main-content">
        <Routes>
          <Route path="/" element={<HomePage onToggleSidebar={() => setSidebarOpen((o) => !o)} />} />
          <Route path="/rooms/:roomId" element={<RoomPage onToggleSidebar={() => setSidebarOpen((o) => !o)} />} />
          <Route path="*" element={<Navigate to="/" replace />} />
        </Routes>
      </main>

      {showModal && (
        <NewRoomModal
          onClose={() => setShowModal(false)}
          onCreated={handleCreated}
        />
      )}

      <ToastContainer />
    </div>
  );
}

function App() {
  return (
    <BrowserRouter>
      <AppInner />
    </BrowserRouter>
  );
}

export default App;
