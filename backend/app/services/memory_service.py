from typing import Optional, List
from sqlalchemy.orm import Session

from app.models.memory import UserMemory
from app.core.logging import logger

class MemoryService:
    @staticmethod
    def save_memory(
        db: Session,
        user_id: int,
        memory_key: str,
        memory_value: str,
        memory_type: str = "preference",
        importance: int = 1
    ) -> UserMemory:
        existing = (
            db.query(UserMemory)
            .filter(UserMemory.user_id == user_id, UserMemory.memory_key == memory_key)
            .first()
        )
        if existing:
            existing.memory_value = memory_value
            existing.memory_type = memory_type
            existing.importance = importance
            db.commit()
            db.refresh(existing)
            logger.info(f"Updated memory [{memory_key}] for user_id={user_id}")
            return existing
        else:
            mem = UserMemory(
                user_id=user_id,
                memory_key=memory_key,
                memory_value=memory_value,
                memory_type=memory_type,
                importance=importance
            )
            db.add(mem)
            db.commit()
            db.refresh(mem)
            logger.info(f"Saved memory [{memory_key}] for user_id={user_id}")
            return mem

    @staticmethod
    def get_memory(db: Session, user_id: int, memory_key: str) -> Optional[UserMemory]:
        return (
            db.query(UserMemory)
            .filter(UserMemory.user_id == user_id, UserMemory.memory_key == memory_key)
            .first()
        )

    @staticmethod
    def get_all_user_memories(db: Session, user_id: int) -> List[UserMemory]:
        return db.query(UserMemory).filter(UserMemory.user_id == user_id).all()

    @staticmethod
    def update_memory(db: Session, user_id: int, memory_key: str, memory_value: str) -> Optional[UserMemory]:
        mem = MemoryService.get_memory(db, user_id, memory_key)
        if mem:
            mem.memory_value = memory_value
            db.commit()
            db.refresh(mem)
        return mem

    @staticmethod
    def delete_memory(db: Session, user_id: int, memory_key: str) -> bool:
        mem = MemoryService.get_memory(db, user_id, memory_key)
        if mem:
            db.delete(mem)
            db.commit()
            return True
        return False
