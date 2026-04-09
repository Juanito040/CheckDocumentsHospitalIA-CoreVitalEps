"""
Configuración de la aplicación usando Pydantic Settings
"""
from pydantic_settings import BaseSettings
from typing import List


class Settings(BaseSettings):
    """Configuración de la aplicación"""

    # Servidor
    HOST: str = "0.0.0.0"
    PORT: int = 8000
    DEBUG: bool = False  # Siempre False por defecto; activar solo en desarrollo vía .env

    # Base de datos
    DATABASE_URL: str = "sqlite:///./data/hospital_ia.db"

    # ChromaDB
    CHROMA_PATH: str = "./data/chromadb"
    CHROMA_COLLECTION: str = "hospital_docs"

    # Ollama
    OLLAMA_BASE_URL: str = "http://localhost:11434"
    OLLAMA_MODEL: str = "qwen2.5:32b"
    OLLAMA_EMBEDDING_MODEL: str = "nomic-embed-text"
    OLLAMA_FALLBACK_MODEL: str = "phi3:mini"

    # JWT — OBLIGATORIO cambiar SECRET_KEY en producción (mínimo 32 caracteres aleatorios)
    SECRET_KEY: str = "CHANGE-THIS-IN-PRODUCTION-USE-A-RANDOM-32-CHAR-STRING"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 1440  # 24 horas

    # CORS — orígenes permitidos separados por coma (ej: http://mifrontend.com,https://otro.com)
    ALLOWED_ORIGINS: str = "http://localhost:4200,http://localhost:3000"

    # RAG
    CHUNK_SIZE: int = 500
    CHUNK_OVERLAP: int = 100
    TOP_K_RESULTS: int = 8

    # Archivos
    MAX_FILE_SIZE_MB: int = 50
    ALLOWED_EXTENSIONS: List[str] = ["pdf", "docx"]

    # Logs
    LOG_LEVEL: str = "INFO"
    LOG_FILE: str = "./logs/app.log"

    class Config:
        env_file = ".env"
        case_sensitive = True


# Instancia global de configuración
settings = Settings()
