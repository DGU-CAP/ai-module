from typing import List
from sklearn.ensemble import IsolationForest
import numpy as np


def detect(
    cpu: float,
    memory: float,
    error_rate: float,
    restarts: int,
    cpu_history: List[float],
    memory_history: List[float],
    error_rate_history: List[float],
    log_count: int,
    event_count: int,
) -> dict:
    """Isolation Forest로 이상 여부를 판단한다."""
    cpu_increase_rate = (cpu_history[-1] - cpu_history[0]) / (cpu_history[0] + 1e-9) if cpu_history else 0.0
    mem_increase_rate = (memory_history[-1] - memory_history[0]) / (memory_history[0] + 1e-9) if memory_history else 0.0

    feature_vector = np.array([[
        cpu,
        memory,
        error_rate,
        restarts,
        cpu_increase_rate,
        mem_increase_rate,
        log_count,
        event_count,
    ]])

    model = IsolationForest(n_estimators=100, contamination=0.1, random_state=42)
    # 단일 샘플이므로 학습 데이터 없이 score만 반환 (실제 서비스에서는 사전 학습 모델 로드)
    model.fit(feature_vector)
    score = model.decision_function(feature_vector)[0]
    is_anomaly = model.predict(feature_vector)[0] == -1

    return {
        "is_anomaly": bool(is_anomaly),
        "anomaly_score": round(float(score), 4),
    }
