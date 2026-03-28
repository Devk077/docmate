import asyncio
from backend.db.postgres import get_room, get_all_rooms, get_latest_session
from api.orchestrator_store import get_or_load_orchestrator

async def test():
    rooms = get_all_rooms()
    if not rooms:
        print("No rooms")
        return
    room_id = str(rooms[0]['id'])
    session = get_latest_session(room_id)
    session_id = str(session['id'])
    print(f"Room: {room_id}, Session: {session_id}")
    orch = get_or_load_orchestrator(room_id)
    
    for doc in orch.run_round("hello", session_id=session_id):
        print(doc)

if __name__ == "__main__":
    asyncio.run(test())
