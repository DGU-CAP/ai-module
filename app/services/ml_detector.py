import logging
import os
import numpy as np
import joblib
from app.models.request import AnalyzeRequest

logger = logging.getLogger(__name__)

MODEL_PATH = os.path.join(os.path.dirname(__file__), "..", "..", "models", "isolation_forest.pkl")


class MLResult:
    def __init__(self):
        self.is_anomaly: bool = False
        self.anomaly_score: float = 0.0  # 낮을수록 이상 (Isolation Forest 특성)
        self.features: dict = {}


class MLDetector:
    _model = None  # 클래스 변수로 모델 공유 (모든 인스턴스가 같은 모델 사용)

    def __init__(self):
        if MLDetector._model is None:
            MLDetector._load_model()

    @classmethod
    def _load_model(cls):
        """모델 파일을 로드해서 클래스 변수에 저장한다."""
        if not os.path.exists(MODEL_PATH):
            logger.info(
                f"[MLDetector] 모델 없음 — "
                f"POST /metrics로 정상 데이터 {200}개 쌓이면 자동 학습됩니다."
            )
            return
        try:
            cls._model = joblib.load(MODEL_PATH)
            logger.info(f"[MLDetector] 모델 로드 완료: {MODEL_PATH}")
        except Exception as e:
            logger.error(f"[MLDetector] 모델 로드 실패: {e}")

    @classmethod
    def reload(cls):
        """
        TrainingStore가 재학습 완료 후 호출하는 핫리로드 메서드.
        서버 재시작 없이 새 모델을 반영한다.
        """
        logger.info("[MLDetector] 모델 핫리로드 시작")
        cls._model = None
        cls._load_model()
        logger.info("[MLDetector] 모델 핫리로드 완료")

    def detect(self, request: AnalyzeRequest) -> MLResult:
        result = MLResult()
        features = self._extract_features(request)
        result.features = features

        # 모델 미학습 상태면 탐지 스킵 (is_anomaly=False 반환)
        if MLDetector._model is None:
            logger.info("[MLDetector] 모델 미학습 상태 — ML 탐지 스킵")
            return result

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

        # 사전 학습된 모델로 예측만 수행 (fit 없음)
        score = MLDetector._model.score_samples(feature_vector)[0]
        raw_pred = MLDetector._model.predict(feature_vector)[0]

        result.anomaly_score = float(score)
        result.is_anomaly = raw_pred == -1  # Isolation Forest: -1이면 이상

        logger.debug(
            f"[MLDetector] pod={request.podName} "
            f"score={score:.4f} is_anomaly={result.is_anomaly}"
        )
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
        """첫 값 대비 마지막 값의 증가율 (%). 첫 값이 0이면 마지막 값 그대로 반환."""
        if len(values) < 2:
            return 0.0
        first = values[0]
        last = values[-1]
        if first == 0:
            return float(last)
        return float((last - first) / first * 100)