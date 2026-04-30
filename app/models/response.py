from typing import List
from pydantic import BaseModel


class AnalyzeResponse(BaseModel):
    severity: str  # CRITICAL | HIGH | MEDIUM | LOW
    aiAnalysis: str
    recommendation: str
    similarCases: List[str]
