from typing import Optional, List, Dict, Any
from pydantic import BaseModel, ConfigDict

class SheetAnalysisResult(BaseModel):
    title: str
    row_count: int
    columns: List[str]
    summary_findings: List[str]
    declined_over_5pct: List[Dict[str, Any]] = []

class DocumentQAResult(BaseModel):
    document_name: str
    query: str
    answer: str
    key_metrics: Dict[str, Any] = {}
    sources: List[str] = []

class VoiceTranscriptionResult(BaseModel):
    transcription_text: str
    detected_intent: str
    assistant_response: str

class ImageAnalysisResult(BaseModel):
    detected_type: str # chart, table, screenshot
    key_insights: List[str]
    commentary: str
