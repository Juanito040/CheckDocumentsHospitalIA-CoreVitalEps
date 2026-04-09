"""
Servicio para manejo de ChromaDB (base de datos vectorial)
"""
import logging
from typing import List, Dict, Optional
from pathlib import Path
import chromadb
from chromadb.config import Settings

from app.core.config import settings

logger = logging.getLogger(__name__)


class VectorStoreService:
    """Servicio para gestionar embeddings en ChromaDB"""

    def __init__(self):
        self.chroma_path = Path(settings.CHROMA_PATH)
        self.collection_name = settings.CHROMA_COLLECTION

        # Crear directorio si no existe
        self.chroma_path.mkdir(parents=True, exist_ok=True)

        # Inicializar cliente de ChromaDB
        self.client = chromadb.PersistentClient(
            path=str(self.chroma_path),
            settings=Settings(
                anonymized_telemetry=False,
                allow_reset=True
            )
        )

        # Obtener o crear colección
        self.collection = self._get_or_create_collection()

        logger.info(f"ChromaDB inicializado - Colección: {self.collection_name}")

    def _get_or_create_collection(self):
        """Obtener colección existente o crear una nueva"""
        try:
            collection = self.client.get_or_create_collection(
                name=self.collection_name,
                metadata={"description": "Documentos del CoreVital"}
            )
            logger.info(f"Colección '{self.collection_name}' lista")
            return collection
        except Exception as e:
            logger.error(f"Error al obtener/crear colección: {e}")
            raise

    def add_documents(
        self,
        embeddings: List[List[float]],
        documents: List[str],
        metadatas: List[Dict],
        ids: List[str]
    ) -> bool:
        """
        Agregar documentos con sus embeddings a ChromaDB

        Args:
            embeddings: Lista de vectores (embeddings)
            documents: Lista de textos originales (chunks)
            metadatas: Lista de metadatos para cada documento
            ids: Lista de IDs únicos para cada documento

        Returns:
            True si se agregaron exitosamente
        """
        try:
            self.collection.add(
                embeddings=embeddings,
                documents=documents,
                metadatas=metadatas,
                ids=ids
            )

            logger.info(f"{len(documents)} documentos agregados a ChromaDB")
            return True

        except Exception as e:
            logger.error(f"Error al agregar documentos a ChromaDB: {e}")
            raise Exception(f"Error al almacenar en ChromaDB: {str(e)}")

    def similarity_search(
        self,
        query_embedding: List[float],
        top_k: int = None,
        filter_metadata: Optional[Dict] = None
    ) -> Dict:
        """
        Búsqueda por similitud semántica

        Args:
            query_embedding: Vector embedding de la consulta
            top_k: Número de resultados a retornar (por defecto settings.TOP_K_RESULTS)
            filter_metadata: Filtros opcionales por metadatos (ej: {"categoria": "protocolo"})

        Returns:
            Dict con resultados: {
                "ids": List[str],
                "documents": List[str],
                "metadatas": List[Dict],
                "distances": List[float]
            }
        """
        if top_k is None:
            top_k = settings.TOP_K_RESULTS

        try:
            results = self.collection.query(
                query_embeddings=[query_embedding],
                n_results=top_k,
                where=filter_metadata  # Filtro opcional
            )

            # ChromaDB retorna listas anidadas, aplanar los resultados
            return {
                "ids": results["ids"][0] if results["ids"] else [],
                "documents": results["documents"][0] if results["documents"] else [],
                "metadatas": results["metadatas"][0] if results["metadatas"] else [],
                "distances": results["distances"][0] if results["distances"] else []
            }

        except Exception as e:
            logger.error(f"Error en búsqueda semántica: {e}")
            raise Exception(f"Error en búsqueda: {str(e)}")

    def delete_document(self, document_id: str) -> bool:
        """
        Eliminar todos los chunks de un documento por su ID

        Args:
            document_id: ID del documento a eliminar

        Returns:
            True si se eliminó exitosamente
        """
        try:
            # Buscar todos los chunks del documento
            results = self.collection.get(
                where={"doc_id": document_id}
            )

            if not results["ids"]:
                logger.warning(f"No se encontraron chunks para documento {document_id}")
                return False

            # Eliminar todos los chunks encontrados
            self.collection.delete(
                ids=results["ids"]
            )

            logger.info(f"Documento {document_id} eliminado ({len(results['ids'])} chunks)")
            return True

        except Exception as e:
            logger.error(f"Error al eliminar documento {document_id}: {e}")
            raise Exception(f"Error al eliminar: {str(e)}")

    def get_collection_stats(self) -> Dict:
        """
        Obtener estadísticas de la colección

        Returns:
            Dict con estadísticas
        """
        try:
            count = self.collection.count()

            return {
                "collection_name": self.collection_name,
                "total_chunks": count,
                "path": str(self.chroma_path)
            }

        except Exception as e:
            logger.error(f"Error al obtener estadísticas: {e}")
            return {
                "collection_name": self.collection_name,
                "error": str(e)
            }

    def reset_collection(self) -> bool:
        """
        PRECAUCIÓN: Eliminar toda la colección (solo para desarrollo/testing)

        Returns:
            True si se eliminó exitosamente
        """
        try:
            self.client.delete_collection(name=self.collection_name)
            self.collection = self._get_or_create_collection()
            logger.warning("Colección ChromaDB eliminada y recreada")
            return True

        except Exception as e:
            logger.error(f"Error al resetear colección: {e}")
            return False

    def search_by_metadata(self, metadata_filter: Dict) -> Dict:
        """
        Buscar documentos por metadatos específicos

        Args:
            metadata_filter: Filtro de metadatos (ej: {"categoria": "protocolo", "estado": "activo"})

        Returns:
            Dict con documentos que coinciden con el filtro
        """
        try:
            results = self.collection.get(
                where=metadata_filter
            )

            return {
                "ids": results["ids"],
                "documents": results["documents"],
                "metadatas": results["metadatas"]
            }

        except Exception as e:
            logger.error(f"Error en búsqueda por metadatos: {e}")
            raise Exception(f"Error en búsqueda: {str(e)}")


# Instancia global del servicio
vector_store_service = VectorStoreService()
