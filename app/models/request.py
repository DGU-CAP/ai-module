from datetime import datetime
from typing import List, Optional
from pydantic import BaseModel


class MetricPoint(BaseModel):
    timestamp: datetime
    value: float


class AnalyzeRequest(BaseModel):
    podName: str
    namespace: str
    nodeName: str
    anomalyType: str  # CPU_HIGH | MEMORY_HIGH | POD_RESTART | ERROR_RATE_HIGH | OOM_KILLED | CRASH_LOOP

    cpu: float
    memory: float
    restarts: int
    errorRate: float

    cpuHistory: List[MetricPoint]
    memoryHistory: List[MetricPoint]
    errorRateHistory: List[MetricPoint]

    errorLogs: Optional[List[str]] = []
    k8sEvents: Optional[List[str]] = []

    detectedAt: datetime
