"""
Endpoints para consultas (Query)
"""
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
import logging
import json

from app.database.database import get_db
from app.schemas.query import QueryRequest, QueryResponse, QueryHistoryResponse
from app.models.query_log import QueryLog
from app.models.user import User
from app.core.dependencies import get_current_user
from app.services.rag_service import rag_service

logger = logging.getLogger(__name__)

router = APIRouter()


@router.post("/", response_model=QueryResponse)
def make_query(
    query_data: QueryRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Realizar consulta en lenguaje natural sobre los documentos indexados

    El sistema utiliza arquitectura RAG:
    1. Vectoriza la pregunta
    2. Busca fragmentos relevantes en ChromaDB
    3. Construye prompt con contexto
    4. Genera respuesta con LLM local (Ollama)
    5. Retorna respuesta con referencias a fuentes
    """
    try:
        # Realizar consulta RAG
        logger.info(f"👤 Usuario {current_user.email} realizó consulta")

        result = rag_service.query(
            question=query_data.question,
            category_filter=query_data.category_filter,
            top_k=query_data.top_k
        )

        # Guardar en log de auditoría
        docs_referenciados = json.dumps([s["document_id"] for s in result["sources"]])

        query_log = QueryLog(
            usuario_id=current_user.id,
            pregunta=query_data.question,
            respuesta=result["answer"],
            docs_referenciados=docs_referenciados,
            tiempo_respuesta_ms=result["response_time_ms"]
        )

        db.add(query_log)
        db.commit()

        logger.info(f"Consulta procesada - Tiempo: {result['response_time_ms']}ms")

        return QueryResponse(
            answer=result["answer"],
            sources=result["sources"],
            chunks_used=result["chunks_used"],
            response_time_ms=result["response_time_ms"],
            category_filter=result.get("category_filter")
        )

    except Exception as e:
        logger.error(f"Error al procesar consulta: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error al procesar consulta: {str(e)}"
        )


@router.get("/history", response_model=QueryHistoryResponse)
def get_query_history(
    skip: int = 0,
    limit: int = 50,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Obtener historial de consultas del usuario actual

    Parámetros:
    - skip: Número de consultas a saltar (paginación)
    - limit: Número máximo de consultas a retornar
    """
    # Obtener consultas del usuario ordenadas por fecha (más recientes primero)
    query = db.query(QueryLog).filter(
        QueryLog.usuario_id == current_user.id
    ).order_by(QueryLog.fecha.desc())

    total = query.count()
    queries = query.offset(skip).limit(limit).all()

    return QueryHistoryResponse(
        total=total,
        queries=queries
    )


@router.get("/stats")
def get_query_stats(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Obtener estadísticas de consultas del usuario
    """
    total_queries = db.query(QueryLog).filter(
        QueryLog.usuario_id == current_user.id
    ).count()

    # Promedio de tiempo de respuesta
    avg_response_time = db.query(QueryLog).filter(
        QueryLog.usuario_id == current_user.id
    ).with_entities(QueryLog.tiempo_respuesta_ms).all()

    if avg_response_time:
        times = [t[0] for t in avg_response_time if t[0] is not None]
        avg_time = sum(times) / len(times) if times else 0
    else:
        avg_time = 0

    return {
        "total_queries": total_queries,
        "average_response_time_ms": int(avg_time),
        "user_id": current_user.id,
        "user_email": current_user.email
    }
