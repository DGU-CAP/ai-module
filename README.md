# ai-module — FastAPI AI 분석 서버

## 프로젝트 소개

Kubernetes 클러스터 메트릭 기반 이상 탐지 및 RAG 기반 LLM을 통한 분석 기능을 제공하는 FastAPI 서버입니다.
Spring Boot 백엔드가 rule 기반으로 선별한 이상 후보 Pod 데이터를 받아,
z-score · ML · RAG · LLM으로 정밀 분석한 뒤 결과를 반환합니다.

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

## 기술 스택

- Python 3.12
- FastAPI
- uvicorn
- scikit-learn (Isolation Forest)
- RAG (Vector DB 기반 유사 사례 검색)
- LLM API

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
└── .github/workflows/
    └── ecr-push.yml         # Docker 빌드 → ECR push CI/CD
```

## API 명세

### POST /analyze

Spring Boot로부터 이상 후보 Pod 데이터를 수신하고 AI 분석 결과를 반환합니다.

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
    {"timestamp": "2026-04-29T13:30:00", "value": 92.5}
  ],
  "memoryHistory": [...],
  "errorRateHistory": [...],
  "errorLogs": [
    "OutOfMemoryError at com.example...",
    "Connection refused at com.example..."
  ],
  "k8sEvents": ["OOMKilled", "BackOff"],
  "detectedAt": "2026-04-29T13:30:00"
}
```

`anomalyType` 가능한 값: `CPU_HIGH` / `MEMORY_HIGH` / `POD_RESTART` / `ERROR_RATE_HIGH` / `OOM_KILLED` / `CRASH_LOOP`

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

`severity` 가능한 값: `CRITICAL` / `HIGH` / `MEDIUM` / `LOW`

### GET /health

서버 상태 확인용 헬스체크 엔드포인트입니다.

## 환경변수

`.env` 파일을 생성하고 아래 변수를 설정하세요. (`.env`는 깃에 포함되지 않습니다)

| 변수명 | 설명 |
|---|---|
| `LLM_API_KEY` | LLM API 키 |
| `LLM_MODEL` | 사용할 LLM 모델명 |
| `VECTOR_DB_PATH` | RAG Vector DB 경로 |

## 로컬 실행

```bash
pip install -r requirements.txt
uvicorn app.main:app --reload
```

실행 후 Swagger UI: http://localhost:8000/docs

## Docker 빌드 및 실행

```bash
# 빌드
docker build -t dgu-cap-ai .

# 실행
docker run -p 8000:8000 --env-file .env dgu-cap-ai
```

## 주의사항

- `requirements.txt` 파일이 반드시 있어야 Docker 빌드가 됩니다
- FastAPI 앱 진입점은 `app/main.py`의 `app` 객체 기준입니다. 다를 경우 Dockerfile의 CMD 수정 필요
- `.env` 파일에 실제 API 키를 설정해야 LLM · RAG 기능이 동작합니다

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
