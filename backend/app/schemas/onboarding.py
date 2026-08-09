from typing import Optional, List
from pydantic import BaseModel

class ExtractedProfileData(BaseModel):
    role: Optional[str] = None
    markets: Optional[List[str]] = None
    watchlist: Optional[List[str]] = None
    interests: Optional[List[str]] = None
    briefing_time: Optional[str] = None
    response_style: Optional[str] = None
    preferred_language: Optional[str] = None

class OnboardingStepResult(BaseModel):
    onboarding_completed: bool
    current_state: str
    next_question: Optional[str] = None
    extracted_data: ExtractedProfileData
