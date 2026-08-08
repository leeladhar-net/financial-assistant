import pytest
from app.services.user_service import UserService
from app.services.memory_service import MemoryService

def test_memory_service_crud(db_session):
    user = UserService.get_or_create_user(db_session, telegram_user_id=7001)
    
    # Save memory
    mem1 = MemoryService.save_memory(db_session, user.id, "preferred_market", "US", memory_type="preference")
    assert mem1.memory_value == "US"

    # Get memory
    fetched = MemoryService.get_memory(db_session, user.id, "preferred_market")
    assert fetched is not None
    assert fetched.memory_value == "US"

    # Update memory
    updated = MemoryService.save_memory(db_session, user.id, "preferred_market", "India")
    assert updated.memory_value == "India"

    # Get all user memories
    memories = MemoryService.get_all_user_memories(db_session, user.id)
    assert len(memories) == 1

    # Delete memory
    deleted = MemoryService.delete_memory(db_session, user.id, "preferred_market")
    assert deleted is True

    # Verify deletion
    assert MemoryService.get_memory(db_session, user.id, "preferred_market") is None
