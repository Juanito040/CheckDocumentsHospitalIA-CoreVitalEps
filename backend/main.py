"""
Sistema de Consulta Inteligente - CoreVital
Punto de entrada principal de la aplicación FastAPI
"""
import logging
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
import uvicorn

from app.core.config import settings
from app.core.logging_config import setup_logging

# Configurar logging
setup_logging()
logger = logging.getLogger(__name__)

# Crear aplicación FastAPI — docs solo disponibles en modo DEBUG
app = FastAPI(
    title="Sistema de Consulta IA - CoreVital",
    description="API REST para consultas inteligentes sobre documentación hospitalaria usando RAG",
    version="1.0.0",
    docs_url="/docs" if settings.DEBUG else None,
    redoc_url="/redoc" if settings.DEBUG else None,
    openapi_url="/openapi.json" if settings.DEBUG else None,
)

# Configurar CORS — orígenes leídos desde variable de entorno ALLOWED_ORIGINS
_allowed_origins = [o.strip() for o in settings.ALLOWED_ORIGINS.split(",") if o.strip()]
app.add_middleware(
    CORSMiddleware,
    allow_origins=_allowed_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.on_event("startup")
async def startup_event():
    """Evento ejecutado al iniciar la aplicación"""
    logger.info("Iniciando Sistema de Consulta IA - CoreVital")
    logger.info(f"Base de datos: {settings.DATABASE_URL}")
    logger.info(f"Modelo LLM: {settings.OLLAMA_MODEL}")
    logger.info(f"Modelo Embeddings: {settings.OLLAMA_EMBEDDING_MODEL}")


@app.on_event("shutdown")
async def shutdown_event():
    """Evento ejecutado al detener la aplicación"""
    logger.info("Deteniendo Sistema de Consulta IA")


@app.get("/")
async def root():
    """Endpoint raíz"""
    return {
        "message": "Sistema de Consulta IA - CoreVital",
        "status": "online",
        "version": "1.0.0",
        "docs": "/docs"
    }


@app.get("/api/health")
async def health_check():
    """Health check del sistema"""
    from app.services.ollama_service import ollama_service

    # Test de conexión con Ollama
    ollama_status = ollama_service.test_connection()

    return {
        "status": "ok",
        "model": settings.OLLAMA_MODEL,
        "embedding_model": settings.OLLAMA_EMBEDDING_MODEL,
        "database": "connected",
        "ollama": ollama_status
    }


# Importar middleware
from app.core.middleware import log_requests_middleware
app.middleware("http")(log_requests_middleware)

# Importar y registrar routers
from app.routes import auth, documents, query, users, stats
app.include_router(auth.router, prefix="/api/auth", tags=["Autenticación"])
app.include_router(documents.router, prefix="/api/documents", tags=["Documentos"])
app.include_router(query.router, prefix="/api/query", tags=["Consultas"])
app.include_router(users.router, prefix="/api/users", tags=["Usuarios"])
app.include_router(stats.router, prefix="/api/stats", tags=["Estadísticas"])


if __name__ == "__main__":
    uvicorn.run(
        "main:app",
        host=settings.HOST,
        port=settings.PORT,
        reload=settings.DEBUG,
        log_level=settings.LOG_LEVEL.lower()
    )
