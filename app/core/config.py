from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    # OpenAI
    openai_api_key: str = ""
    openai_model: str = "gpt-4o-mini"
    openai_embedding_model: str = "text-embedding-3-small"

    # ChromaDB
    chroma_persist_dir: str = "./data/chroma"
    chroma_collection_name: str = "incident_docs"

    # RAG
    rag_top_k: int = 3                  # 유사 문서 몇 개 가져올지
    docs_dir: str = "./data/docs"       # 장애 대응 문서 폴더

    # Spring Boot와 합의된 메트릭 수집 간격 (분)
    metric_interval_minutes: int = 1

    class Config:
        env_file = ".env"


settings = Settings()