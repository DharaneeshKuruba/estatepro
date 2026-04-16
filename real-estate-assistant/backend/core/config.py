from pydantic_settings import BaseSettings
from functools import lru_cache


class Settings(BaseSettings):
    database_url: str = "postgresql://admin:admin123@172.25.81.56/estatepro"
    secret_key: str = "super-secret-jwt-key-change-in-production"
    algorithm: str = "HS256"
    access_token_expire_minutes: int = 60
    chroma_path: str = "./chroma_store"
    chroma_collection_name: str = "real_estate_docs"
    groq_api_key: str = ""
    groq_model: str = "llama-3.3-70b-versatile"
    backend_url: str = "http://localhost:8080"
    langsmith_api_key: str = ""
    langsmith_project: str = "estate-nexa-ai"
    langsmith_endpoint: str = "https://api.smith.langchain.com"
    langsmith_tracing_v2: bool = False

    class Config:
        env_file = ".env"
        extra = "allow"


@lru_cache()
def get_settings():
    return Settings()
