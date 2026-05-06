import logging
import os
import threading
import numpy as np
import joblib
from collections import deque
from sklearn.ensemble import IsolationForest
from app.models.metrics_request import MetricsRequest

logger = logging.getLogger(__name__)

MODEL_PATH = os.path.join(os.path.dirname(__file__), "..", "..", "models", "isolation_forest.pkl")

FIRST_TRAIN_THRESHOLD = 200   # 첫 학습 트리거 개수
RETRAIN_INTERVAL = 100        # 재학습 트리거 간격 (새로 쌓인 개수 기준)
MAX_STORE_SIZE = 2000         # 최대 보관 샘플 수 (오래된 것부터 제거)


def _extract_features(request: MetricsRequest) -> list[float]:
    cpu = request.metrics.cpu
    memory = request.metrics.memory
    error_rate = request.metrics.errorRate

    def increase_rate(values):
        if len(values) < 2:
            return 0.0
        first, last = values[0], values[-1]
        if first == 0:
            return float(last)
        return float((last - first) / first * 100)

    return [
        cpu[-1],
        float(np.mean(cpu)),
        float(np.max(cpu)),
        increase_rate(cpu),
        memory[-1],
        float(np.mean(memory)),
        increase_rate(memory),
        error_rate[-1],
        increase_rate(error_rate),
        request.restarts,
        len(request.errorLogs),
        len(request.k8sEvents),
    ]


class TrainingStore:
    """
    정상 데이터를 메모리에 저장하고,
    임계값 도달 시 Isolation Forest를 재학습하는 서비스.

    스레드 안전성을 위해 threading.Lock 사용.
    재학습은 별도 스레드에서 비동기로 수행 (API 응답 블로킹 방지).
    """

    def __init__(self):
        self._store: deque = deque(maxlen=MAX_STORE_SIZE)
        self._since_last_train: int = 0
        self._is_trained: bool = False
        self._lock = threading.Lock()
        self._training_in_progress = False

        if os.path.exists(MODEL_PATH):
            self._is_trained = True
            logger.info("[TrainingStore] 기존 모델 감지 — 학습 완료 상태로 시작")
        else:
            logger.info(
                f"[TrainingStore] 모델 없음 — "
                f"정상 데이터 {FIRST_TRAIN_THRESHOLD}개 쌓이면 첫 학습 시작"
            )

    def add(self, request: MetricsRequest) -> None:
        features = _extract_features(request)

        with self._lock:
            self._store.append(features)
            self._since_last_train += 1
            current_size = len(self._store)
            since = self._since_last_train
            should_train = self._should_trigger_train(current_size, since)

        if should_train and not self._training_in_progress:
            logger.info(
                f"[TrainingStore] 재학습 트리거 — "
                f"총 {current_size}개 / 마지막 학습 후 {since}개 추가"
            )
            thread = threading.Thread(target=self._train, daemon=True)
            thread.start()

    def _should_trigger_train(self, total: int, since_last: int) -> bool:
        if not self._is_trained:
            return total >= FIRST_TRAIN_THRESHOLD
        return since_last >= RETRAIN_INTERVAL

    def _train(self) -> None:
        self._training_in_progress = True
        try:
            with self._lock:
                X = np.array(list(self._store))
                self._since_last_train = 0

            logger.info(f"[TrainingStore] 학습 시작 — {len(X)}개 샘플")

            model = IsolationForest(
                n_estimators=200,
                contamination=0.05,  # 정상 데이터만 들어오므로 낮게 설정
                max_samples="auto",
                random_state=42,
            )
            model.fit(X)

            os.makedirs(os.path.dirname(MODEL_PATH), exist_ok=True)
            joblib.dump(model, MODEL_PATH)
            self._is_trained = True

            logger.info(f"[TrainingStore] 학습 완료 — 모델 저장: {MODEL_PATH}")

            # MLDetector 핫리로드
            from app.services.ml_detector import MLDetector
            MLDetector.reload()

        except Exception as e:
            logger.error(f"[TrainingStore] 학습 실패: {e}")
        finally:
            self._training_in_progress = False

    @property
    def sample_count(self) -> int:
        return len(self._store)

    @property
    def is_trained(self) -> bool:
        return self._is_trained


# 싱글톤 인스턴스
training_store = TrainingStore()