import json
from openai import AsyncOpenAI
from app.models.request import AnalyzeRequest
from app.models.response import Severity
from app.services.zscore_detector import ZScoreResult
from app.services.ml_detector import MLResult
from app.core.config import settings


class LLMResult:
    def __init__(self):
        self.severity: Severity = Severity.LOW
        self.ai_analysis: str = ""
        self.recommendation: str = ""


class LLMService:
    """
    GPT-4o-mini를 이용해 장애 원인 분석 리포트를 생성하는 서비스.
    """

    def __init__(self):
        self.client = AsyncOpenAI(api_key=settings.openai_api_key)

    async def generate(
        self,
        request: AnalyzeRequest,
        zscore_result: ZScoreResult,
        ml_result: MLResult,
        similar_docs: list[str],
    ) -> LLMResult:
        """
        z-score, ML, RAG 결과를 모두 컨텍스트로 넣어 GPT-4o-mini로 분석 리포트 생성.
        LLM 호출 실패 시 rule 기반 fallback으로 응답.
        """
        # OpenAI API 키가 없으면 바로 fallback
        if not settings.openai_api_key:
            print("[LLMService] API 키 없음 → fallback 사용")
            return self._fallback(request, zscore_result)

        try:
            prompt = self._build_prompt(request, zscore_result, ml_result, similar_docs)

            response = await self.client.chat.completions.create(
                model=settings.openai_model,
                messages=[
                    {
                        "role": "system",
                        "content": (
                            "당신은 Kubernetes 인프라 장애 분석 전문가입니다. "
                            "주어진 데이터를 분석하여 반드시 JSON 형식으로만 응답하세요. "
                            "JSON 외의 텍스트는 절대 포함하지 마세요."
                        ),
                    },
                    {"role": "user", "content": prompt},
                ],
                temperature=0.2,      # 일관된 분석을 위해 낮게 설정
                max_tokens=1000,
                response_format={"type": "json_object"},  # JSON 모드 강제
            )

            raw = response.choices[0].message.content
            return self._parse_response(raw, request, zscore_result)

        except Exception as e:
            print(f"[LLMService] LLM 호출 실패: {e} → fallback 사용")
            return self._fallback(request, zscore_result)

    def _build_prompt(
        self,
        request: AnalyzeRequest,
        zscore_result: ZScoreResult,
        ml_result: MLResult,
        similar_docs: list[str],
    ) -> str:

        # RAG 문서 요약 (너무 길면 토큰 낭비)
        rag_context = ""
        if similar_docs:
            rag_context = "\n\n---\n".join(similar_docs[:3])
        else:
            rag_context = "유사 사례 없음"

        return f"""
다음 Kubernetes Pod 장애 데이터를 분석하여 JSON으로 응답하세요.

## Pod 정보
- Pod: {request.podName}
- Namespace: {request.namespace}
- Node: {request.nodeName}
- 이상 유형 (rule 탐지): {request.anomalyType.value}
- 감지 시각: {request.detectedAt}

## 현재 메트릭
- CPU: {request.metrics.cpu[-1]}% (최근 추이: {request.metrics.cpu})
- Memory: {request.metrics.memory[-1]}% (최근 추이: {request.metrics.memory})
- Error Rate: {request.metrics.errorRate[-1]}% (최근 추이: {request.metrics.errorRate})
- Restarts: {request.restarts}

## z-score 분석 결과
- CPU z-score: {zscore_result.cpu_zscore:.2f}
- Memory z-score: {zscore_result.memory_zscore:.2f}
- ErrorRate z-score: {zscore_result.error_rate_zscore:.2f}
- 통계적 이상 지표: {zscore_result.anomaly_fields if zscore_result.anomaly_fields else "없음"}

## ML 모델 분석 결과
- 이상 판정: {"이상" if ml_result.is_anomaly else "정상"}
- 이상 점수: {ml_result.anomaly_score:.4f} (낮을수록 이상)

## 에러 로그
{chr(10).join(request.errorLogs) if request.errorLogs else "없음"}

## Kubernetes 이벤트
{', '.join(request.k8sEvents) if request.k8sEvents else "없음"}

## 유사 장애 대응 문서 (RAG 검색 결과)
{rag_context}

## 응답 형식 (JSON만 반환)
{{
  "severity": "CRITICAL 또는 HIGH 또는 MEDIUM 또는 LOW",
  "aiAnalysis": "근본 원인을 2~3문장으로 설명 (한국어)",
  "recommendation": "구체적인 조치 방법을 2~3문장으로 설명 (한국어)"
}}
"""

    def _parse_response(
        self,
        raw: str,
        request: AnalyzeRequest,
        zscore_result: ZScoreResult,
    ) -> LLMResult:
        """GPT 응답 JSON을 파싱하여 LLMResult로 변환."""
        try:
            data = json.loads(raw)

            result = LLMResult()
            result.severity = Severity(data.get("severity", "LOW"))
            result.ai_analysis = data.get("aiAnalysis", "")
            result.recommendation = data.get("recommendation", "")
            return result

        except Exception as e:
            print(f"[LLMService] 응답 파싱 실패: {e} → fallback 사용")
            return self._fallback(request, zscore_result)

    def _fallback(
        self,
        request: AnalyzeRequest,
        zscore_result: ZScoreResult,
    ) -> LLMResult:
        """LLM 호출 실패 시 rule 기반으로 응답 생성."""
        result = LLMResult()
        result.severity = self._estimate_severity(request)
        result.ai_analysis = self._build_fallback_analysis(request, zscore_result)
        result.recommendation = self._build_fallback_recommendation(request)
        return result

    def _estimate_severity(self, request: AnalyzeRequest) -> Severity:
        anomaly_type = request.anomalyType.value

        if anomaly_type in ("OOM_KILLED", "CRASH_LOOP"):
            return Severity.CRITICAL
        if request.metrics.cpu[-1] > 90 or request.metrics.memory[-1] > 85:
            return Severity.HIGH
        if request.restarts >= 3:
            return Severity.MEDIUM
        return Severity.LOW

    def _build_fallback_analysis(
        self,
        request: AnalyzeRequest,
        zscore_result: ZScoreResult,
    ) -> str:
        parts = []

        if zscore_result.anomaly_fields:
            fields = ", ".join(zscore_result.anomaly_fields)
            parts.append(f"{fields} 지표가 통계적으로 이상 수준입니다.")

        if request.k8sEvents:
            parts.append(f"Kubernetes 이벤트: {', '.join(request.k8sEvents)}.")

        if request.errorLogs:
            parts.append(f"주요 에러: {request.errorLogs[0]}")

        if not parts:
            parts.append(f"{request.anomalyType.value} 이상이 감지되었습니다.")

        parts.append("(LLM 분석 미연결 — 수동 확인 필요)")
        return " ".join(parts)

    def _build_fallback_recommendation(self, request: AnalyzeRequest) -> str:
        recommendations = {
            "CPU_HIGH": "CPU 사용량이 높은 프로세스를 확인하고, HPA 설정 또는 리소스 limit 조정을 검토하세요.",
            "MEMORY_HIGH": "메모리 누수 여부를 확인하고, Pod memory limit 상향 또는 JVM heap 설정을 점검하세요.",
            "POD_RESTART": "Pod 재시작 원인을 로그에서 확인하고, livenessProbe 설정을 점검하세요.",
            "ERROR_RATE_HIGH": "HTTP 에러율이 높습니다. 의존 서비스 연결 상태와 최근 배포 이력을 확인하세요.",
            "OOM_KILLED": "컨테이너가 메모리 초과로 종료되었습니다. memory limit 상향 및 메모리 누수 구간 로그를 점검하세요.",
            "CRASH_LOOP": "CrashLoopBackOff 상태입니다. 애플리케이션 시작 로그와 설정 파일을 확인하세요.",
        }
        return recommendations.get(request.anomalyType.value, "수동으로 Pod 상태를 확인하세요.")