from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    LLM_API_KEY: str = ""
    LLM_MODEL: str = "claude-sonnet-4-6"
    VECTOR_DB_PATH: str = "./data"

    class Config:
        env_file = ".env"


settings = Settings()
