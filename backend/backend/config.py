from typing import Literal, Optional
from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    DATABASE_URL: str = "postgresql+asyncpg://postgres:postgres@localhost:5432/lenny"
    OLLAMA_BASE_URL: str = "http://localhost:11434"
    OLLAMA_CHAT_MODEL: str = "llama3.2:3b"
    OLLAMA_EMBED_MODEL: str = "nomic-embed-text"
    ANTHROPIC_API_KEY: Optional[str] = None
    ANTHROPIC_CHAT_MODEL: str = "claude-3-5-haiku-20241022"
    ACTIVE_PROVIDER: Literal["ollama", "anthropic"] = "ollama"
    RETRIEVAL_TOP_K: int = 10
    RETRIEVAL_THRESHOLD: float = 0.35
    TRANSCRIPT_REPO_URL: str = "https://github.com/LennysNewsletter/lennys-newsletterpodcastdata.git"
    TRANSCRIPT_DIR: str = "/data/transcripts"
    MAX_TOKENS_GENERATE: int = 2000
    REQUEST_TIMEOUT_S: int = 60
    LOG_LEVEL: str = "INFO"

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")

settings = Settings()
