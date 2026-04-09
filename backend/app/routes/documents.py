"""
Endpoints para gestión de documentos
"""
from fastapi import APIRouter, Depends, HTTPException, status, UploadFile, File, Form
from sqlalchemy.orm import Session
from pathlib import Path
import shutil
import uuid
import logging

from app.database.database import get_db
from app.schemas.document import DocumentResponse, DocumentList, DocumentUploadResponse
from app.models.document import Document
from app.models.user import User
from app.core.dependencies import get_current_user, get_current_admin_user
from app.services.document_processor import document_processor
from app.services.ollama_service import ollama_service
from app.services.vector_store_service import vector_store_service

logger = logging.getLogger(__name__)

router = APIRouter()

# Directorio para almacenar archivos temporalmente
UPLOAD_DIR = Path("data/documents")
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)


@router.post("/upload", response_model=DocumentUploadResponse)
async def upload_document(
    file: UploadFile = File(...),
    categoria: str = Form(...),
    current_user: User = Depends(get_current_admin_user),  # Solo admin puede subir
    db: Session = Depends(get_db)
):
    """
    Subir documento (PDF o DOCX) y procesarlo para indexación semántica

    Solo usuarios con rol 'admin' pueden subir documentos
    """
    # 1. Validaciones
    if not document_processor.validate_file_extension(file.filename):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Extensión no permitida. Solo se aceptan: {', '.join(document_processor.ALLOWED_EXTENSIONS)}"
        )

    # Leer tamaño del archivo
    file.file.seek(0, 2)  # Ir al final
    file_size = file.file.tell()
    file.file.seek(0)  # Volver al inicio

    if not document_processor.validate_file_size(file_size):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Archivo demasiado grande. Máximo: {document_processor.MAX_FILE_SIZE_MB} MB"
        )

    # Validar categoría
    valid_categories = ["protocolo", "normativa", "historia_clinica"]
    if categoria not in valid_categories:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Categoría inválida. Opciones: {', '.join(valid_categories)}"
        )

    try:
        # 2. Guardar archivo temporalmente
        document_id = str(uuid.uuid4())
        file_extension = Path(file.filename).suffix.lstrip('.')
        temp_file_path = UPLOAD_DIR / f"{document_id}.{file_extension}"

        with temp_file_path.open("wb") as buffer:
            shutil.copyfileobj(file.file, buffer)

        logger.info(f"📄 Archivo guardado temporalmente: {temp_file_path}")

        # 3. Procesar documento (extraer texto y fragmentar)
        chunks, metadatas, chunk_ids = document_processor.process_document(
            file_path=str(temp_file_path),
            filename=file.filename,
            file_extension=file_extension,
            document_id=document_id,
            category=categoria
        )

        # 4. Generar embeddings para cada chunk
        logger.info(f"🔄 Generando embeddings para {len(chunks)} chunks...")
        embeddings = []

        for i, chunk in enumerate(chunks):
            embedding = ollama_service.generate_embedding(chunk)
            embeddings.append(embedding)

            if (i + 1) % 10 == 0:
                logger.info(f"   Progreso: {i + 1}/{len(chunks)} embeddings generados")

        # 5. Almacenar en ChromaDB
        vector_store_service.add_documents(
            embeddings=embeddings,
            documents=chunks,
            metadatas=metadatas,
            ids=chunk_ids
        )

        # 6. Guardar metadatos en BD SQLite
        document = Document(
            id=document_id,
            nombre_archivo=file.filename,
            categoria=categoria,
            usuario_id=current_user.id,
            num_chunks=len(chunks),
            estado="activo"
        )

        db.add(document)
        db.commit()
        db.refresh(document)

        logger.info(f"Documento indexado exitosamente: {file.filename}")

        return DocumentUploadResponse(
            message="Documento procesado e indexado exitosamente",
            document_id=document_id,
            filename=file.filename,
            chunks_created=len(chunks),
            category=categoria
        )

    except Exception as e:
        logger.error(f"Error al procesar documento: {e}")

        # Limpiar archivo temporal si existe
        if temp_file_path.exists():
            temp_file_path.unlink()

        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error al procesar documento: {str(e)}"
        )


@router.get("/", response_model=DocumentList)
def list_documents(
    skip: int = 0,
    limit: int = 100,
    categoria: str = None,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Listar documentos indexados

    Parámetros:
    - skip: Número de documentos a saltar (paginación)
    - limit: Número máximo de documentos a retornar
    - categoria: Filtrar por categoría (opcional)
    """
    query = db.query(Document).filter(Document.estado == "activo")

    if categoria:
        query = query.filter(Document.categoria == categoria)

    total = query.count()
    documents = query.offset(skip).limit(limit).all()

    return DocumentList(
        total=total,
        documents=documents
    )


@router.delete("/{document_id}")
def delete_document(
    document_id: str,
    current_user: User = Depends(get_current_admin_user),  # Solo admin puede eliminar
    db: Session = Depends(get_db)
):
    """
    Eliminar documento (marca como eliminado y borra vectores de ChromaDB)

    Solo usuarios con rol 'admin' pueden eliminar documentos
    """
    # Buscar documento
    document = db.query(Document).filter(Document.id == document_id).first()

    if not document:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Documento no encontrado"
        )

    if document.estado == "eliminado":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="El documento ya está eliminado"
        )

    try:
        # Eliminar de ChromaDB
        vector_store_service.delete_document(document_id)

        # Marcar como eliminado en BD
        document.estado = "eliminado"
        db.commit()

        logger.info(f"Documento eliminado: {document.nombre_archivo}")

        return {
            "message": "Documento eliminado exitosamente",
            "document_id": document_id
        }

    except Exception as e:
        logger.error(f"Error al eliminar documento: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error al eliminar documento: {str(e)}"
        )


@router.get("/{document_id}", response_model=DocumentResponse)
def get_document(
    document_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Obtener detalles de un documento específico
    """
    document = db.query(Document).filter(Document.id == document_id).first()

    if not document:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Documento no encontrado"
        )

    return document
