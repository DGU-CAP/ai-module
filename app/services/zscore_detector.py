from typing import List
import statistics


ZSCORE_THRESHOLD = 3.0


def compute_zscore(values: List[float]) -> float:
    """시계열 마지막 값의 z-score를 반환한다."""
    if len(values) < 2:
        return 0.0
    mean = statistics.mean(values)
    stdev = statistics.stdev(values)
    if stdev == 0:
        return 0.0
    return (values[-1] - mean) / stdev


def detect(cpu_history: List[float], memory_history: List[float], error_rate_history: List[float]) -> dict:
    """각 지표의 z-score를 계산하고 이상 여부를 반환한다."""
    cpu_z = compute_zscore(cpu_history)
    mem_z = compute_zscore(memory_history)
    err_z = compute_zscore(error_rate_history)

    return {
        "cpu_zscore": round(cpu_z, 3),
        "memory_zscore": round(mem_z, 3),
        "error_rate_zscore": round(err_z, 3),
        "cpu_anomaly": abs(cpu_z) >= ZSCORE_THRESHOLD,
        "memory_anomaly": abs(mem_z) >= ZSCORE_THRESHOLD,
        "error_rate_anomaly": abs(err_z) >= ZSCORE_THRESHOLD,
    }
