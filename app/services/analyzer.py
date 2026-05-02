import asyncio
from app.models.request import AnalyzeRequest
from app.models.response import AnalyzeResponse
from app.services.zscore_detector import ZScoreDetector
from app.services.ml_detector import MLDetector
from app.services.rag_service import RAGService
from app.services.llm_service import LLMService


class AnalyzerService:
    """
    전체 분석 흐름을 조율하는 서비스.

    흐름:
    1. z-score 탐지 + ML 탐지 (병렬)
    2. RAG 유사 문서 검색
    3. LLM 리포트 생성
    """

    def __init__(self):
        self.zscore_detector = ZScoreDetector()
        self.ml_detector = MLDetector()
        self.rag_service = RAGService()
        self.llm_service = LLMService()

    async def analyze(self, request: AnalyzeRequest) -> AnalyzeResponse:

        # [1] z-score와 ML 탐지 — 서로 독립적이므로 병렬 실행
        zscore_result, ml_result = await asyncio.gather(
            asyncio.to_thread(self.zscore_detector.detect, request),
            asyncio.to_thread(self.ml_detector.detect, request),
        )

        # [2] RAG 검색 — z-score 결과 기반으로 쿼리 생성
        similar_docs = await asyncio.to_thread(
            self.rag_service.search, request, zscore_result, ml_result
        )

        # [3] LLM 리포트 생성 — 앞의 모든 결과를 컨텍스트로 전달
        llm_result = await self.llm_service.generate(
            request, zscore_result, ml_result, similar_docs
        )

        # similarCases: RAG가 찾은 문서의 첫 줄(제목)만 요약해서 반환
        similar_cases = self._summarize_docs(similar_docs)

        return AnalyzeResponse(
            severity=llm_result.severity,
            aiAnalysis=llm_result.ai_analysis,
            recommendation=llm_result.recommendation,
            similarCases=similar_cases,
        )

    def _summarize_docs(self, docs: list[str]) -> list[str]:
        """
        RAG가 찾은 전체 문서 내용 대신
        각 문서의 첫 줄(제목)만 추출해서 similarCases로 반환.
        Spring Boot가 받는 응답을 간결하게 유지하기 위해서다.
        """
        summaries = []
        for doc in docs:
            first_line = doc.strip().split("\n")[0]
            # 마크다운 헤더 기호 제거
            first_line = first_line.lstrip("#").strip()
            if first_line:
                summaries.append(first_line)
        return summaries