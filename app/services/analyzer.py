from app.models.request import AnalyzeRequest
from app.models.response import AnalyzeResponse
from app.services import zscore_detector, ml_detector, rag_service, llm_service


def analyze(req: AnalyzeRequest) -> AnalyzeResponse:
    """전체 분석 파이프라인을 오케스트레이션한다."""

    # [2] 시계열 feature 추출
    cpu_values = [p.value for p in req.cpuHistory]
    memory_values = [p.value for p in req.memoryHistory]
    error_rate_values = [p.value for p in req.errorRateHistory]

    # [3] z-score 기반 이상탐지
    zscore_result = zscore_detector.detect(cpu_values, memory_values, error_rate_values)

    # [4] ML 모델 기반 이상탐지
    ml_result = ml_detector.detect(
        cpu=req.cpu,
        memory=req.memory,
        error_rate=req.errorRate,
        restarts=req.restarts,
        cpu_history=cpu_values,
        memory_history=memory_values,
        error_rate_history=error_rate_values,
        log_count=len(req.errorLogs),
        event_count=len(req.k8sEvents),
    )

    # [5] 로그·이벤트 기반 쿼리 생성
    query = f"{req.anomalyType} {' '.join(req.k8sEvents)} {' '.join(req.errorLogs[:2])}"

    # [6] RAG 검색
    similar_cases = rag_service.search(query)

    # [7] LLM 리포트 생성
    llm_result = llm_service.generate_report(
        anomaly_type=req.anomalyType,
        pod_name=req.podName,
        namespace=req.namespace,
        zscore_result=zscore_result,
        ml_result=ml_result,
        error_logs=req.errorLogs,
        k8s_events=req.k8sEvents,
        similar_cases=similar_cases,
    )

    return AnalyzeResponse(
        severity=llm_result["severity"],
        aiAnalysis=llm_result["aiAnalysis"],
        recommendation=llm_result["recommendation"],
        similarCases=similar_cases,
    )
