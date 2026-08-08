from typing import List, Optional
from sqlalchemy.orm import Session
from sqlalchemy import desc

from app.models.conversation import Conversation, Message
from app.core.logging import logger

class ConversationService:
    @staticmethod
    def get_or_create_active_conversation(db: Session, user_id: int) -> Conversation:
        conversation = (
            db.query(Conversation)
            .filter(Conversation.user_id == user_id)
            .order_by(desc(Conversation.updated_at))
            .first()
        )
        if not conversation:
            logger.info(f"Creating new active conversation for user_id={user_id}")
            conversation = Conversation(user_id=user_id)
            db.add(conversation)
            db.commit()
            db.refresh(conversation)
        return conversation

    @staticmethod
    def save_message(
        db: Session,
        conversation_id: int,
        user_id: int,
        role: str,
        content: str,
        message_type: str = "text"
    ) -> Message:
        msg = Message(
            conversation_id=conversation_id,
            user_id=user_id,
            role=role,
            content=content,
            message_type=message_type
        )
        db.add(msg)
        
        # Touch conversation updated_at
        conversation = db.query(Conversation).filter(Conversation.id == conversation_id).first()
        if conversation:
            db.add(conversation)
            
        db.commit()
        db.refresh(msg)
        return msg

    @staticmethod
    def get_recent_messages(db: Session, conversation_id: int, limit: int = 20) -> List[Message]:
        """
        Retrieves recent messages in chronological order.
        Limits retrieval to prevent loading entire history into context window.
        """
        msgs = (
            db.query(Message)
            .filter(Message.conversation_id == conversation_id)
            .order_by(desc(Message.created_at))
            .limit(limit)
            .all()
        )
        return sorted(msgs, key=lambda m: m.created_at)

    @staticmethod
    def get_conversation_history(db: Session, user_id: int, limit: int = 50) -> List[Message]:
        msgs = (
            db.query(Message)
            .filter(Message.user_id == user_id)
            .order_by(desc(Message.created_at))
            .limit(limit)
            .all()
        )
        return sorted(msgs, key=lambda m: m.created_at)
