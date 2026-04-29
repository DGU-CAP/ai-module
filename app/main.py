from fastapi import FastAPI
from app.api import analyze, health

app = FastAPI(title="AI 분석 서버", version="1.0.0")

app.include_router(health.router)
app.include_router(analyze.router)
