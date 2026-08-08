from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field, ConfigDict

class TelegramUser(BaseModel):
    id: int
    is_bot: Optional[bool] = False
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    username: Optional[str] = None
    language_code: Optional[str] = None

class TelegramChat(BaseModel):
    id: int
    type: str
    title: Optional[str] = None
    username: Optional[str] = None
    first_name: Optional[str] = None
    last_name: Optional[str] = None

class TelegramMessage(BaseModel):
    message_id: int
    from_user: Optional[TelegramUser] = Field(None, alias="from")
    chat: TelegramChat
    date: int
    text: Optional[str] = None
    document: Optional[Dict[str, Any]] = None
    photo: Optional[List[Dict[str, Any]]] = None
    voice: Optional[Dict[str, Any]] = None

    model_config = ConfigDict(populate_by_name=True)

class TelegramUpdate(BaseModel):
    update_id: int
    message: Optional[TelegramMessage] = None
    callback_query: Optional[Dict[str, Any]] = None

    model_config = ConfigDict(populate_by_name=True)

