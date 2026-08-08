import datetime
from typing import Optional, List
from pydantic import BaseModel, ConfigDict

class MessageCreate(BaseModel):
    conversation_id: int
    user_id: int
    role: str
    content: str
    message_type: str = "text"

class MessageResponse(BaseModel):
    id: int
    conversation_id: int
    user_id: int
    role: str
    content: str
    message_type: str
    created_at: datetime.datetime

    model_config = ConfigDict(from_attributes=True)


class ConversationResponse(BaseModel):
    id: int
    user_id: int
    created_at: datetime.datetime
    updated_at: datetime.datetime
    messages: List[MessageResponse] = []

    model_config = ConfigDict(from_attributes=True)
