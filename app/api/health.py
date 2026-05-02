from fastapi import APIRouter

router = APIRouter()


@router.get("/health")
async def health():
    """
    Kubernetes livenessProbe / readinessProbe용 헬스체크 엔드포인트.
    """
    return {"status": "ok"}