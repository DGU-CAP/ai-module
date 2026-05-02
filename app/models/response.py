from pydantic import BaseModel
from typing import List
from enum import Enum


class Severity(str, Enum):
    CRITICAL = "CRITICAL"
    HIGH = "HIGH"
    MEDIUM = "MEDIUM"
    LOW = "LOW"


class AnalyzeResponse(BaseModel):
    severity: Severity
    aiAnalysis: str
    recommendation: str
    similarCases: List[str] = []