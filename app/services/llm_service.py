from typing import List
import anthropic
from app.core.config import settings


def generate_report(
    anomaly_type: str,
    pod_name: str,
    namespace: str,
    zscore_result: dict,
    ml_result: dict,
    error_logs: List[str],
    k8s_events: List[str],
    similar_cases: List[str],
) -> dict:
    """LLM을 호출해 분석 리포트를 생성한다."""
    similar_cases_text = "\n".join(f"- {c}" for c in similar_cases) if similar_cases else "없음"
    error_logs_text = "\n".join(error_logs) if error_logs else "없음"
    k8s_events_text = ", ".join(k8s_events) if k8s_events else "없음"

    prompt = f"""당신은 Kubernetes 이상탐지 전문가입니다. 아래 데이터를 분석해 JSON으로 결과를 반환하세요.

## 이상 정보
- Pod: {pod_name} (namespace: {namespace})
- 이상 유형: {anomaly_type}

## Z-Score 분석
- CPU z-score: {zscore_result['cpu_zscore']} (이상: {zscore_result['cpu_anomaly']})
- Memory z-score: {zscore_result['memory_zscore']} (이상: {zscore_result['memory_anomaly']})
- Error Rate z-score: {zscore_result['error_rate_zscore']} (이상: {zscore_result['error_rate_anomaly']})

## ML 분석
- 이상 탐지: {ml_result['is_anomaly']} (score: {ml_result['anomaly_score']})

## 에러 로그
{error_logs_text}

## Kubernetes 이벤트
{k8s_events_text}

## 유사 장애 사례
{similar_cases_text}

다음 JSON 형식으로만 응답하세요:
{{
  "severity": "CRITICAL|HIGH|MEDIUM|LOW",
  "aiAnalysis": "분석 내용",
  "recommendation": "조치 권고사항"
}}"""

    client = anthropic.Anthropic(api_key=settings.LLM_API_KEY)
    message = client.messages.create(
        model=settings.LLM_MODEL,
        max_tokens=1024,
        messages=[{"role": "user", "content": prompt}],
    )

    import json
    text = message.content[0].text.strip()
    result = json.loads(text)

    return {
        "severity": result.get("severity", "MEDIUM"),
        "aiAnalysis": result.get("aiAnalysis", ""),
        "recommendation": result.get("recommendation", ""),
    }
