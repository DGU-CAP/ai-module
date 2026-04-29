from fastapi import APIRouter
from app.models.request import AnalyzeRequest
from app.models.response import AnalyzeResponse
from app.services import analyzer

router = APIRouter()


@router.post("/analyze", response_model=AnalyzeResponse)
def analyze(req: AnalyzeRequest) -> AnalyzeResponse:
    return analyzer.analyze(req)
