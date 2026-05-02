from app.models.request import AnalyzeRequest
from app.services.zscore_detector import ZScoreResult
from app.services.ml_detector import MLResult
from app.services.embedder import get_embedder
from app.core.config import settings


class RAGService:
    """
    Vector DB에서 유사 장애 사례/대응 문서를 검색하는 서비스.
    ChromaDB + OpenAI text-embedding-3-small 사용.
    """

    def search(
        self,
        request: AnalyzeRequest,
        zscore_result: ZScoreResult,
        ml_result: MLResult,
    ) -> list[str]:
        """
        현재 장애 상황과 유사한 문서를 검색.

        Returns:
            유사 문서 내용 목록. 없으면 빈 배열.
        """
        try:
            query = self._build_query(request, zscore_result)
            embedder = get_embedder()
            docs = embedder.search(query, top_k=settings.rag_top_k)
            return docs
        except Exception as e:
            print(f"[RAGService] 검색 실패: {e}")
            return []

    def _build_query(
        self,
        request: AnalyzeRequest,
        zscore_result: ZScoreResult,
    ) -> str:
        """
        anomalyType + 이상 지표 + k8sEvents + errorLogs 핵심 키워드 조합으로
        Vector DB 검색에 사용할 자연어 쿼리를 생성한다.
        """
        parts = []

        # anomalyType 기반 핵심 키워드
        anomaly_keywords = {
            "CPU_HIGH": "CPU 사용률 급증",
            "MEMORY_HIGH": "메모리 사용률 급증",
            "POD_RESTART": "Pod 반복 재시작",
            "ERROR_RATE_HIGH": "HTTP 에러율 급증",
            "OOM_KILLED": "OOMKilled 메모리 초과 종료",
            "CRASH_LOOP": "CrashLoopBackOff 반복 크래시",
        }
        parts.append(anomaly_keywords.get(request.anomalyType.value, request.anomalyType.value))

        # z-score로 감지된 이상 지표
        if zscore_result.anomaly_fields:
            parts.append(f"이상 지표: {', '.join(zscore_result.anomaly_fields)}")

        # k8s 이벤트
        if request.k8sEvents:
            parts.append(f"이벤트: {', '.join(request.k8sEvents)}")

        # 에러 로그 핵심 키워드 (앞 3개)
        if request.errorLogs:
            parts.append(f"에러: {', '.join(request.errorLogs[:3])}")

        return " | ".join(parts)