import numpy as np
from datetime import timedelta
from app.models.request import AnalyzeRequest


class ZScoreResult:
    def __init__(self):
        self.cpu_zscore: float = 0.0
        self.memory_zscore: float = 0.0
        self.error_rate_zscore: float = 0.0
        self.is_anomaly: bool = False
        self.anomaly_fields: list[str] = []


class ZScoreDetector:

    # |z-score| >= 이 값이면 이상으로 판단
    THRESHOLD = 2.5

    def detect(self, request: AnalyzeRequest) -> ZScoreResult:
        result = ZScoreResult()

        result.cpu_zscore = self._calc_zscore(request.metrics.cpu)
        result.memory_zscore = self._calc_zscore(request.metrics.memory)
        result.error_rate_zscore = self._calc_zscore(request.metrics.errorRate)

        if abs(result.cpu_zscore) >= self.THRESHOLD:
            result.anomaly_fields.append("cpu")

        if abs(result.memory_zscore) >= self.THRESHOLD:
            result.anomaly_fields.append("memory")

        if abs(result.error_rate_zscore) >= self.THRESHOLD:
            result.anomaly_fields.append("errorRate")

        result.is_anomaly = len(result.anomaly_fields) > 0

        return result

    def _calc_zscore(self, values: list[float]) -> float:
        """
        배열의 마지막 값(현재값)이 나머지 값들 기준으로 얼마나 튀는지 계산.
        배열이 2개 미만이면 계산 불가 → 0 반환.
        """
        if len(values) < 2:
            return 0.0

        # 현재값을 제외한 이전 값들로 평균/표준편차 계산
        history = np.array(values[:-1], dtype=float)
        current = values[-1]

        mean = np.mean(history)
        std = np.std(history)

        # 표준편차가 0이면 (모든 값이 동일) 변화 없음
        if std == 0:
            return 0.0

        return float((current - mean) / std)

    def restore_timestamps(self, values: list[float], detected_at) -> list[dict]:
        """
        Spring Boot와 합의된 규칙:
        - 배열 순서: 오래된 것 → 최신 순
        - 간격: 1분 고정
        - detectedAt = 마지막 값의 시점
        """
        n = len(values)
        return [
            {
                "timestamp": detected_at - timedelta(minutes=(n - 1 - i)),
                "value": v
            }
            for i, v in enumerate(values)
        ]