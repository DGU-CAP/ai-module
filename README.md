# ai-module — FastAPI AI 분석 서버

## 프로젝트 소개

Kubernetes 클러스터 메트릭 기반 이상 탐지 및 RAG 기반 LLM 분석 기능을 제공하는 FastAPI 서버입니다.
Spring Boot 백엔드가 rule 기반으로 선별한 이상 후보 Pod 데이터를 받아,
z-score · ML · RAG · LLM으로 정밀 분석한 뒤 결과를 반환합니다.

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

## 기술 스택

- Python 3.12
- FastAPI / uvicorn
- scikit-learn (Isolation Forest)
- ChromaDB (Vector DB)
- OpenAI GPT-4o-mini (LLM)
- OpenAI text-embedding-3-small (임베딩)

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
│   │   ├── request.py         # AnalyzeRequest 스키마
│   │   └── response.py        # AnalyzeResponse 스키마
│   ├── core/
│   │   └── config.py          # 환경변수 설정
│   └── main.py                # FastAPI 앱 진입점
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
└── .github/workflows/
    └── ecr-push.yml           # CI/CD (ECR 자동 push)
```

---

## API 명세

### POST /analyze

Spring Boot로부터 이상 후보 Pod 데이터를 수신하고 AI 분석 결과를 반환합니다.

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

- `anomalyType` 가능한 값: `CPU_HIGH` / `MEMORY_HIGH` / `POD_RESTART` / `ERROR_RATE_HIGH` / `OOM_KILLED` / `CRASH_LOOP`
- `metrics` 배열 순서: 오래된 것 → 최신 순, 1분 간격 고정
- `errorLogs` 최대 20개

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

- `severity` 가능한 값: `CRITICAL` / `HIGH` / `MEDIUM` / `LOW`
- `similarCases` 없으면 빈 배열 `[]` 반환
- 타임아웃: connect 3초 / read 10초

### GET /health

Kubernetes livenessProbe용 헬스체크 엔드포인트입니다.

---

## 환경변수

프로젝트 루트에 `.env` 파일을 생성하세요. (`.gitignore`에 포함되어 있어 Git에 올라가지 않습니다)

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

## 로컬 실행

```bash
# 패키지 설치
pip install -r requirements.txt

# 서버 실행
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

정상 실행 시 터미널 출력:
```
[Startup] ChromaDB 초기화 및 문서 임베딩 시작...
[Embedder] 6개 문서 임베딩 완료
[Startup] 완료
INFO:     Uvicorn running on http://0.0.0.0:8000
```

실행 후 Swagger UI: http://localhost:8000/docs

---

## Docker 빌드 및 실행

```bash
# 빌드
docker build -t dgu-cap-ai .

# 실행
docker run -p 8000:8000 --env-file .env dgu-cap-ai
```

---

## 배포 흐름 (ECR 푸시)

코드 수정 후 main 브랜치에 푸시하면 GitHub Actions가 자동으로 ECR에 이미지를 빌드·푸시합니다.

```
git push origin main
  → GitHub Actions (ecr-push.yml)
  → Docker 이미지 빌드
  → ECR에 dgu-cap-ai:latest push
  → infra 레포에서 pull-and-load.sh ai 실행
  → kind 클러스터에 최신 이미지 load
  → kubectl rollout restart deployment/ai
```

---

## 클러스터 확인 명령어

```bash
# Pod 상태 확인
kubectl get pods

# FastAPI 로그 확인
kubectl logs deployment/ai

# 로컬에서 Swagger UI 접속
kubectl port-forward svc/ai 8000:8000
# → http://localhost:8000/docs
```
