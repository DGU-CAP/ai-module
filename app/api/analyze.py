from fastapi import APIRouter, HTTPException
from app.models.request import AnalyzeRequest
from app.models.response import AnalyzeResponse
from app.services.analyzer import analyzer_service

router = APIRouter()


@router.post("/analyze", response_model=AnalyzeResponse)
async def analyze(request: AnalyzeRequest):
    """
    Spring Boot로부터 이상 후보 Pod 데이터를 받아 AI 분석 결과를 반환한다.

    처리 흐름:
    1. z-score 탐지 + ML 탐지 (병렬)
    2. RAG 유사 사례 검색
    3. LLM 리포트 생성
    """
    try:
        result = await analyzer_service.analyze(request)
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))