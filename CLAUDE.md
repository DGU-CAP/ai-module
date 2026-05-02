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
  → RAG 유사 사례 검색 (ChromaDB)
  → LLM 리포트 생성 (GPT-4o-mini)
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
│   │   ├── analyze.py         # POST /analyze 엔드포인트
│   │   └── health.py          # GET /health 헬스체크
│   ├── services/
│   │   ├── analyzer.py        # 전체 분석 흐름 조율
│   │   ├── zscore_detector.py # z-score 이상탐지
│   │   ├── ml_detector.py     # Isolation Forest 탐지
│   │   ├── rag_service.py     # Vector DB 검색
│   │   ├── llm_service.py     # LLM 리포트 생성
│   │   └── embedder.py        # 문서 임베딩 및 ChromaDB 초기화
│   ├── models/
│   │   ├── request.py         # AnalyzeRequest (Spring Boot 수신)
│   │   └── response.py        # AnalyzeResponse (결과 반환)
│   ├── core/
│   │   └── config.py          # 환경변수 · API 키 설정
│   └── main.py                # FastAPI 앱 초기화 · 라우터 등록
├── data/
│   └── docs/                  # RAG용 장애 대응 문서
│       ├── oom_killed.md
│       ├── crash_loop_backoff.md
│       ├── cpu_high.md
│       ├── memory_high.md
│       ├── error_rate_high.md
│       └── pod_restart.md
├── Dockerfile
├── requirements.txt
├── .env                       # 실제 비밀값 (깃 제외)
├── .gitignore
└── .github/workflows/
    └── ecr-push.yml           # Docker 빌드 → ECR push CI/CD
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
  "anomalyType": "OOM_KILLED",
  "metrics": {
    "cpu": [65, 70, 72, 90, 92],
    "memory": [60, 62, 65, 70, 78],
    "errorRate": [1, 2, 3, 10, 15]
  },
  "restarts": 3,
  "errorLogs": [
    "OutOfMemoryError at com.example...",
    "Connection refused at com.example..."
  ],
  "k8sEvents": ["OOMKilled", "BackOff"],
  "detectedAt": "2026-04-29T13:30:00"
}
```

**metrics 규칙:**
- 배열 순서: 오래된 것 → 최신 순
- 간격: 1분 고정
- detectedAt = 배열의 마지막 값 시점
- errorLogs 최대 20개

**anomalyType 가능한 값:**
- `CPU_HIGH` / `MEMORY_HIGH` / `POD_RESTART` / `ERROR_RATE_HIGH` / `OOM_KILLED` / `CRASH_LOOP`

**응답 예시:**
```json
{
  "severity": "CRITICAL",
  "aiAnalysis": "CPU 급증과 OOMKilled 이벤트가 함께 발생했으며...",
  "recommendation": "Pod memory limit과 JVM heap size 설정을 확인하고...",
  "similarCases": [
    "OOMKilled 장애 대응",
    "메모리 사용률 급증 장애 대응"
  ]
}
```

**severity 가능한 값:** `CRITICAL` / `HIGH` / `MEDIUM` / `LOW`

**유사 사례 없을 때:** `"similarCases": []`

---

## FastAPI 내부 처리 순서

```
[1] 요청 데이터 검증 (Pydantic)
[2] z-score 탐지 + ML 탐지 (병렬 실행)
      z-score: (현재값 - 이전 평균) / 표준편차, |z| >= 2.5 이면 이상
      ML: cpu, memory, errorRate, restarts, 증가율, 로그 개수 등 feature 조합
[3] RAG 검색
      anomalyType + 이상 지표 + k8sEvents + errorLogs 조합으로 쿼리 생성
      ChromaDB에서 유사 장애 대응 문서 top 3 검색
[4] LLM 리포트 생성 (GPT-4o-mini)
      입력: rule 탐지 결과 + z-score + ML + 로그 + RAG 문서
      출력: severity, aiAnalysis, recommendation
[5] 응답 반환
      similarCases: RAG 문서 제목만 추출해서 반환
```

---

## RAG 문서 (data/docs/)

FastAPI 시작 시 자동으로 임베딩되어 ChromaDB에 저장된다.
Pod가 재시작되면 자동으로 재임베딩된다.

- `oom_killed.md` — OOMKilled 장애 대응
- `crash_loop_backoff.md` — CrashLoopBackOff 장애 대응
- `cpu_high.md` — CPU 사용률 급증 장애 대응
- `memory_high.md` — 메모리 사용률 급증 장애 대응
- `error_rate_high.md` — HTTP 에러율 급증 장애 대응
- `pod_restart.md` — Pod 반복 재시작 장애 대응

---

## 인프라 연결 정보

- **Spring Boot → FastAPI 호출 주소 (Kubernetes 내부):** `http://ai:8000/analyze`
- **FastAPI Service 이름:** `ai`
- **포트:** `8000`
- **connect timeout:** 3초 / **read timeout:** 10초

---

## 환경변수

`.env` 파일을 프로젝트 루트에 생성한다. (`.gitignore`에 포함되어 Git에 올라가지 않음)

```
OPENAI_API_KEY=sk-...
```

| 변수명 | 설명 | 기본값 |
|--------|------|--------|
| `OPENAI_API_KEY` | OpenAI API 키 | 없음 (필수) |
| `OPENAI_MODEL` | LLM 모델명 | gpt-4o-mini |
| `OPENAI_EMBEDDING_MODEL` | 임베딩 모델명 | text-embedding-3-small |
| `CHROMA_PERSIST_DIR` | ChromaDB 저장 경로 | ./data/chroma |
| `RAG_TOP_K` | RAG 검색 문서 개수 | 3 |

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
