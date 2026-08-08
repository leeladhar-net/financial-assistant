import datetime
from typing import Optional, List
from pydantic import BaseModel, ConfigDict

class UserPreferenceBase(BaseModel):
    role: Optional[str] = None
    markets: Optional[List[str]] = []
    briefing_time: Optional[str] = None
    response_style: Optional[str] = None

class UserPreferenceCreate(UserPreferenceBase):
    pass

class UserPreferenceResponse(UserPreferenceBase):
    id: int
    user_id: int
    created_at: datetime.datetime
    updated_at: datetime.datetime

    model_config = ConfigDict(from_attributes=True)


class WatchlistBase(BaseModel):
    symbol: str
    company_name: Optional[str] = None
    market: Optional[str] = None
    priority: int = 1

class WatchlistResponse(WatchlistBase):
    id: int
    user_id: int
    created_at: datetime.datetime

    model_config = ConfigDict(from_attributes=True)


class UserInterestBase(BaseModel):
    topic: str
    priority: int = 1

class UserInterestResponse(UserInterestBase):
    id: int
    user_id: int
    created_at: datetime.datetime

    model_config = ConfigDict(from_attributes=True)


class UserBase(BaseModel):
    telegram_user_id: int
    username: Optional[str] = None
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    timezone: str = "UTC"

class UserCreate(UserBase):
    pass

class UserResponse(UserBase):
    id: int
    onboarding_completed: bool
    onboarding_state: str
    created_at: datetime.datetime
    updated_at: datetime.datetime

    model_config = ConfigDict(from_attributes=True)


class FullUserProfileResponse(UserResponse):
    preference: Optional[UserPreferenceResponse] = None
    watchlists: List[WatchlistResponse] = []
    interests: List[UserInterestResponse] = []
