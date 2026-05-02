from pydantic import BaseModel, field_validator
from typing import List
from datetime import datetime
from enum import Enum


class AnomalyType(str, Enum):
    CPU_HIGH = "CPU_HIGH"
    MEMORY_HIGH = "MEMORY_HIGH"
    POD_RESTART = "POD_RESTART"
    ERROR_RATE_HIGH = "ERROR_RATE_HIGH"
    OOM_KILLED = "OOM_KILLED"
    CRASH_LOOP = "CRASH_LOOP"


class MetricsData(BaseModel):
    cpu: List[float]
    memory: List[float]
    errorRate: List[float]

    @field_validator("cpu", "memory", "errorRate")
    @classmethod
    def must_not_be_empty(cls, v):
        if len(v) == 0:
            raise ValueError("metrics 배열은 비어있을 수 없습니다")
        return v


class AnalyzeRequest(BaseModel):
    podName: str
    namespace: str
    nodeName: str
    anomalyType: AnomalyType

    metrics: MetricsData

    restarts: int

    errorLogs: List[str] = []
    k8sEvents: List[str] = []

    detectedAt: datetime

    @field_validator("errorLogs")
    @classmethod
    def limit_error_logs(cls, v):
        # 최대 20개로 제한
        return v[:20]