from fastapi import APIRouter
from app.services.training_store import training_store

router = APIRouter()


@router.get("/health")
async def health():
    """
    Kubernetes livenessProbe / readinessProbe용 헬스체크 엔드포인트.
    """
    return {
        "status": "ok",
        "ml_sample_count": training_store.sample_count,
        "ml_is_trained": training_store.is_trained,
    }