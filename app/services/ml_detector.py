import numpy as np
from sklearn.ensemble import IsolationForest
from app.models.request import AnalyzeRequest


class MLResult:
    def __init__(self):
        self.is_anomaly: bool = False
        self.anomaly_score: float = 0.0  # 낮을수록 이상 (음수)
        self.features: dict = {}


class MLDetector:

    def detect(self, request: AnalyzeRequest) -> MLResult:
        result = MLResult()

        features = self._extract_features(request)
        result.features = features

        feature_vector = np.array([[
            features["cpu_current"],
            features["cpu_mean"],
            features["cpu_max"],
            features["cpu_increase_rate"],
            features["memory_current"],
            features["memory_mean"],
            features["memory_increase_rate"],
            features["error_rate_current"],
            features["error_rate_increase_rate"],
            features["restarts"],
            features["error_log_count"],
            features["k8s_event_count"],
        ]])

        # 단일 샘플 Isolation Forest
        # 실제 운영에서는 사전 학습된 모델을 load해서 사용해야 함
        # 현재는 단일 샘플 기준으로 anomaly_score만 산출
        model = IsolationForest(contamination=0.1, random_state=42)
        model.fit(feature_vector)  # TODO: 학습 데이터 확보 후 사전 학습 모델로 교체
        score = model.score_samples(feature_vector)[0]

        result.anomaly_score = float(score)
        # Isolation Forest: score < -0.1 이면 이상으로 판단
        result.is_anomaly = score < -0.1

        return result

    def _extract_features(self, request: AnalyzeRequest) -> dict:
        cpu = request.metrics.cpu
        memory = request.metrics.memory
        error_rate = request.metrics.errorRate

        return {
            "cpu_current": cpu[-1],
            "cpu_mean": float(np.mean(cpu)),
            "cpu_max": float(np.max(cpu)),
            "cpu_increase_rate": self._increase_rate(cpu),

            "memory_current": memory[-1],
            "memory_mean": float(np.mean(memory)),
            "memory_increase_rate": self._increase_rate(memory),

            "error_rate_current": error_rate[-1],
            "error_rate_increase_rate": self._increase_rate(error_rate),

            "restarts": request.restarts,
            "error_log_count": len(request.errorLogs),
            "k8s_event_count": len(request.k8sEvents),
        }

    def _increase_rate(self, values: list[float]) -> float:
        """
        첫 값 대비 마지막 값의 증가율 (%).
        첫 값이 0이면 마지막 값 그대로 반환.
        """
        if len(values) < 2:
            return 0.0
        first = values[0]
        last = values[-1]
        if first == 0:
            return float(last)
        return float((last - first) / first * 100)