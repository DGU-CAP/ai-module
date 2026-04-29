# ai-module — FastAPI AI 분석 서버

## 프로젝트 개요

이 레포는 Kubernetes 이상탐지 시스템의 **AI 분석 서버**다.
Spring Boot 백엔드가 rule 기반으로 선별한 이상 후보 Pod 데이터를 받아,
z-score · ML · RAG · LLM으로 정밀 분석한 뒤 결과를 반환한다.

---

## 전체 시스템 흐름

```
Spring Boot (30초마다 데이터 수집)
  → rule 기반 1차 이상탐지
  → 이상 후보 Pod만 POST /analyze 호출
      ↓
FastAPI (이 레포)
  → z-score 정밀탐지
  → ML 모델 탐지 (Isolation Forest)
  → RAG 유사 사례 검색
  → LLM 리포트 생성
  → 결과 반환
      ↓
Spring Boot
  → 티켓 생성 · DB 저장
      ↓
Frontend
  → 티켓 조회
```

---

## 디렉토리 구조

```
ai-module/
├── app/
│   ├── api/
│   │   ├── analyze.py       # POST /analyze 엔드포인트
│   │   └── health.py        # GET /health 헬스체크
│   ├── services/
│   │   ├── analyzer.py      # 전체 분석 흐름 오케스트레이션
│   │   ├── zscore_detector.py   # z-score 기반 정밀 이상탐지
│   │   ├── ml_detector.py       # Isolation Forest 모델 탐지
│   │   ├── rag_service.py       # Vector DB 검색 · 유사 사례 조회
│   │   └── llm_service.py       # LLM 분석 리포트 생성
│   ├── models/
│   │   ├── request.py       # AnalyzeRequest (Spring Boot 수신)
│   │   └── response.py      # AnalyzeResponse (결과 반환)
│   ├── core/
│   │   └── config.py        # 환경변수 · API 키 설정
│   └── main.py              # FastAPI 앱 초기화 · 라우터 등록
├── data/                    # RAG용 장애 문서 · Runbook
├── Dockerfile
├── requirements.txt
├── .env                     # 실제 비밀값 (깃 제외)
├── .gitignore
└── .github/workflows/
    └── ecr-push.yml         # Docker 빌드 → ECR push CI/CD
```

---

## API 명세

### POST /analyze

Spring Boot로부터 이상 후보 Pod 데이터를 수신한다.

**요청 예시:**
```json
{
  "podName": "payment-service-7d6f8",
  "namespace": "default",
  "nodeName": "worker-node-1",
  "anomalyType": "CPU_HIGH",

  "cpu": 92.5,
  "memory": 78.3,
  "restarts": 3,
  "errorRate": 15.0,

  "cpuHistory": [
    {"timestamp": "2026-04-29T13:21:00", "value": 31.2},
    {"timestamp": "2026-04-29T13:22:00", "value": 33.5},
    {"timestamp": "2026-04-29T13:23:00", "value": 35.1},
    {"timestamp": "2026-04-29T13:24:00", "value": 42.3},
    {"timestamp": "2026-04-29T13:25:00", "value": 51.0},
    {"timestamp": "2026-04-29T13:26:00", "value": 58.4},
    {"timestamp": "2026-04-29T13:27:00", "value": 68.4},
    {"timestamp": "2026-04-29T13:28:00", "value": 75.1},
    {"timestamp": "2026-04-29T13:29:00", "value": 81.2},
    {"timestamp": "2026-04-29T13:30:00", "value": 92.5}
  ],
  "memoryHistory": [...],   // 동일하게 1분 간격 10개
  "errorRateHistory": [...], // 동일하게 1분 간격 10개

  "errorLogs": [
    "OutOfMemoryError at com.example...",
    "Connection refused at com.example..."
  ],
  "k8sEvents": ["OOMKilled", "BackOff"],

  "detectedAt": "2026-04-29T13:30:00"
}
```

**anomalyType 가능한 값:**
- `CPU_HIGH`
- `MEMORY_HIGH`
- `POD_RESTART`
- `ERROR_RATE_HIGH`
- `OOM_KILLED`
- `CRASH_LOOP`

**응답 예시:**
```json
{
  "severity": "CRITICAL",
  "aiAnalysis": "CPU 급증과 OOMKilled 이벤트가 함께 발생했으며...",
  "recommendation": "Pod memory limit과 JVM heap size 설정을 확인하고...",
  "similarCases": [
    "2024-03-15 동일 패턴 → Java heap 부족으로 인한 OOMKilled 발생"
  ]
}
```

**severity 가능한 값:** `CRITICAL` / `HIGH` / `MEDIUM` / `LOW`

**유사 사례 없을 때:** `"similarCases": []`

---

## FastAPI 내부 처리 순서

```
[1] 요청 데이터 검증 (Pydantic)
[2] 시계열 데이터에서 feature 추출
      → 시계열 규격: 1분 간격 × 10개 = 최근 10분 데이터
      → Spring Boot가 30초마다 수집한 값을 1분 단위 평균으로 변환해서 전달
[3] z-score 기반 이상탐지
      → (현재값 - 평균) / 표준편차
      → |z| >= 3 이면 이상 가능성 높음
[4] ML 모델 기반 이상탐지 (Isolation Forest)
      → feature: cpu, memory, errorRate, restarts,
                 증가율, 로그 개수, 이벤트 개수 등
[5] 로그 · 이벤트 기반 원인 후보 생성
[6] RAG 검색 (data/ 디렉토리 기반 Vector DB)
      → 유사 장애 티켓, Runbook, 대응 문서 검색
[7] LLM 리포트 생성
      → 입력: rule 탐지 결과 + z-score + ML + 로그 + RAG 결과
      → 출력: severity, aiAnalysis, recommendation, similarCases
[8] 응답 반환
```

---

## RAG 검색 대상 (data/ 디렉토리)

- 과거 장애 티켓
- 장애 대응 매뉴얼 · Runbook
- Kubernetes 장애 대응 문서
- OOMKilled 대응 문서
- CrashLoopBackOff 대응 문서
- DB 연결 장애 사례
- Pod memory limit 조정 가이드

---

## 인프라 연결 정보

- **Spring Boot → FastAPI 호출 주소 (Kubernetes 내부):** `http://ai:8000/analyze`
- **FastAPI Service 이름:** `ai`
- **포트:** `8000`
- **connect timeout:** 3초 / **read timeout:** 10초

---

## 환경변수 (core/config.py에서 관리)

| 변수명 | 설명 |
|---|---|
| `LLM_API_KEY` | LLM API 키 |
| `LLM_MODEL` | 사용할 LLM 모델명 |
| `VECTOR_DB_PATH` | RAG Vector DB 경로 |

---

## 배포 흐름

```
코드 수정
  → git push origin main
  → GitHub Actions (ecr-push.yml)
  → Docker 이미지 빌드
  → ECR에 dgu-cap-ai:latest push
  → infra 레포에서 pull-and-load.sh ai 실행
  → kind 클러스터에 최신 이미지 load
  → kubectl rollout restart deployment/ai
```

---

## 로컬 확인 명령어

```bash
# Pod 상태 확인
kubectl get pods

# FastAPI 로그 확인
kubectl logs deployment/ai

# 로컬에서 Swagger UI 접속
kubectl port-forward svc/ai 8000:8000
# → http://localhost:8000/docs
```
