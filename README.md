# AI Module - 이상 탐지 및 챗봇 모듈

## 프로젝트 소개
Kubernetes 클러스터 메트릭 기반 이상 탐지 및 AI 챗봇 기능을 제공하는 FastAPI 서버입니다.

## 기술 스택
- Python 3.11
- FastAPI
- uvicorn

## 로컬 실행

```bash
pip install -r requirements.txt
uvicorn main:app --reload
```

## Docker 빌드 및 실행

```bash
# 빌드
docker build -t dgu-cap-ai .

# 실행
docker run -p 8000:8000 dgu-cap-ai
```

## 주의사항
- `requirements.txt` 파일이 반드시 있어야 Docker 빌드가 됩니다
- FastAPI 앱 진입점은 `main.py`의 `app` 객체 기준입니다. 다를 경우 Dockerfile의 CMD 수정 필요

## ECR 푸시 (인프라 팀 담당)

코드 작성 후 main 브랜치에 머지하면 GitHub Actions가 자동으로 ECR에 푸시합니다.
(워크플로는 추후 추가 예정)
