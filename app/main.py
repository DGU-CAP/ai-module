from contextlib import asynccontextmanager
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from app.api import analyze, health, metrics
from app.services.embedder import init_embedder
from app.services.ml_detector import MLDetector


@asynccontextmanager
async def lifespan(app: FastAPI):
    # [1] ChromaDB 초기화 + 문서 임베딩
    print("[Startup] ChromaDB 초기화 및 문서 임베딩 시작...")
    try:
        init_embedder()
        print("[Startup] 완료")
    except Exception as e:
        print(f"[Startup] 임베딩 초기화 실패 (RAG 비활성화): {e}")

    # [2] ML 모델 로드 시도
    # 모델 파일 없으면 스킵 — POST /metrics로 데이터 쌓이면 자동 학습됨
    MLDetector._load_model()

    yield

    print("[Shutdown] 앱 종료")


app = FastAPI(
    title="AI Analysis Server",
    description="Kubernetes 이상 탐지 및 원인 분석 AI 서버",
    version="0.2.0",
    lifespan=lifespan,
)

app.include_router(health.router)
app.include_router(analyze.router)
app.include_router(metrics.router)


@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    return JSONResponse(
        status_code=500,
        content={
            "detail": "내부 서버 오류",
            "error": str(exc),
        },
    )