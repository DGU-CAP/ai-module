from pydantic import BaseModel, field_validator
from typing import List
from datetime import datetime
from app.models.request import MetricsData


class MetricsRequest(BaseModel):
    podName: str
    namespace: str
    nodeName: str
    metrics: MetricsData
    restarts: int
    errorLogs: List[str] = []
    k8sEvents: List[str] = []
    collectedAt: datetime

    @field_validator("collectedAt", mode="before")
    @classmethod
    def parse_collected_at(cls, v):
        # Spring Boot Jackson 기본값: LocalDateTime → 배열 [y, m, d, h, min, s, ns?]
        if isinstance(v, list):
            return datetime(*v[:6])
        return v

    @field_validator("errorLogs")
    @classmethod
    def limit_error_logs(cls, v):
        return v[:20]