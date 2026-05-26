"""Application configuration via pydantic-settings.

All settings can be overridden by environment variables or a .env file
(loaded relative to the current working directory).

Testing note: always instantiate ``Settings()`` directly in tests rather than
importing the module-level ``settings`` singleton. The singleton is created at
import time and will not reflect ``monkeypatch.setenv`` changes.
"""
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    loki_url: str = "http://localhost:3100"
    embed_url: str = "http://localhost:8080"
    embed_model: str = "nomic-embed-text"
    qdrant_url: str = "http://localhost:6333"
    ollama_url: str = "http://localhost:11434"
    ollama_model: str = "llama3"
    ingest_interval_minutes: int = 15
    collection_name: str = "logseerr"

    model_config = {"env_file": ".env", "extra": "ignore"}


settings = Settings()
