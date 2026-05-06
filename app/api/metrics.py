import logging
from fastapi import APIRouter
from app.models.metrics_request import MetricsRequest
from app.services.training_store import training_store

logger = logging.getLogger(__name__)

router = APIRouter()


@router.post("/metrics")
async def receive_metrics(request: MetricsRequest):
    """
    Spring Boot가 1분마다 정상 Pod 데이터를 전송하는 엔드포인트.
    데이터를 저장하고 임계값 도달 시 ML 모델 재학습을 트리거한다.

    - 첫 학습: 200개 도달 시
    - 재학습: 이후 100개 쌓일 때마다
    - 최대 보관: 2000개 (오래된 것부터 제거)
    """
    training_store.add(request)

    logger.debug(
        f"[/metrics] pod={request.podName} 저장 완료 — "
        f"누적 {training_store.sample_count}개 / "
        f"모델 학습 완료: {training_store.is_trained}"
    )

    return {
        "status": "ok",
        "sample_count": training_store.sample_count,
        "is_trained": training_store.is_trained,
    }