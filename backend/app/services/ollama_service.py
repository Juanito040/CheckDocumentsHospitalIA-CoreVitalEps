"""
Servicio para integración con Ollama (LLM local)
"""
import logging
from typing import List, Optional
import ollama

from app.core.config import settings

logger = logging.getLogger(__name__)


class OllamaService:
    """Servicio para interactuar con Ollama (modelos LLM locales)"""

    def __init__(self):
        self.base_url = settings.OLLAMA_BASE_URL
        self.model = settings.OLLAMA_MODEL
        self.embedding_model = settings.OLLAMA_EMBEDDING_MODEL
        self.fallback_model = settings.OLLAMA_FALLBACK_MODEL
        logger.info(f"OllamaService inicializado - Modelo: {self.model}")

    def generate_embedding(self, text: str) -> List[float]:
        """
        Generar embedding (vector) de un texto usando nomic-embed-text

        Args:
            text: Texto para vectorizar

        Returns:
            Lista de floats representando el vector embedding
        """
        try:
            response = ollama.embeddings(
                model=self.embedding_model,
                prompt=text
            )
            embedding = response['embedding']
            logger.debug(f"Embedding generado - dimensiones: {len(embedding)}")
            return embedding

        except Exception as e:
            logger.error(f"Error al generar embedding: {e}")
            raise Exception(f"Error al generar embedding: {str(e)}")

    def generate_response(
        self,
        prompt: str,
        context: Optional[str] = None,
        use_fallback: bool = False
    ) -> str:
        """
        Generar respuesta usando el modelo LLM (qwen2.5:32b o phi3:mini como fallback)

        Args:
            prompt: Pregunta o prompt del usuario
            context: Contexto opcional (fragmentos de documentos recuperados)
            use_fallback: Si True, usar el modelo fallback (phi3:mini)

        Returns:
            Respuesta generada por el modelo
        """
        model_to_use = self.fallback_model if use_fallback else self.model

        try:
            # Construir el prompt completo con contexto si existe
            full_prompt = self._build_prompt_with_context(prompt, context)

            logger.info(f"Generando respuesta con modelo: {model_to_use}")

            response = ollama.generate(
                model=model_to_use,
                prompt=full_prompt,
                options={
                    "temperature": 0.15,
                    "top_p": 0.9,
                    "top_k": 40,
                    "repeat_penalty": 1.1,
                    "num_ctx": 4096,  # Ventana de contexto ampliada
                }
            )

            answer = response['response']
            logger.info(f"Respuesta generada - longitud: {len(answer)} caracteres")

            return answer

        except Exception as e:
            logger.error(f"Error al generar respuesta con {model_to_use}: {e}")

            # Si falló el modelo principal y no estábamos usando fallback, intentar con fallback
            if not use_fallback:
                logger.warning(f"Intentando con modelo fallback: {self.fallback_model}")
                return self.generate_response(prompt, context, use_fallback=True)

            raise Exception(f"Error al generar respuesta: {str(e)}")

    def rewrite_query(self, question: str) -> str:
        """
        Reformular la pregunta del usuario en términos técnicos/documentales
        para mejorar la búsqueda semántica en ChromaDB.

        Args:
            question: Pregunta original del usuario

        Returns:
            Pregunta reformulada con terminología documental/hospitalaria
        """
        prompt = f"""Reformula la siguiente pregunta usando términos técnicos, médicos o administrativos que probablemente aparezcan en documentos hospitalarios. Devuelve ÚNICAMENTE la pregunta reformulada, sin explicaciones ni prefijos.

Pregunta original: {question}

Pregunta reformulada:"""

        try:
            response = ollama.generate(
                model=self.model,
                prompt=prompt,
                options={"temperature": 0.1, "top_p": 0.9, "num_ctx": 1024}
            )
            rewritten = response['response'].strip()
            logger.info(f"Query reescrita: '{question[:60]}' → '{rewritten[:60]}'")
            return rewritten if rewritten else question
        except Exception as e:
            logger.warning(f"Error al reescribir query, usando original: {e}")
            return question

    def _build_prompt_with_context(self, question: str, context: Optional[str] = None) -> str:
        """
        Construir prompt estructurado con contexto para el LLM

        Args:
            question: Pregunta del usuario
            context: Contexto recuperado de documentos

        Returns:
            Prompt formateado para el modelo
        """
        if not context:
            return f"""Eres CoreVital, un asistente especializado en documentación hospitalaria del Hospital San Rafael.

No tienes documentos disponibles para responder esta consulta. Indica al usuario que debe cargar documentos relevantes antes de realizar consultas.

Pregunta: {question}

Responde en español, de forma breve y profesional."""

        return f"""Eres CoreVital, un asistente especializado en documentación hospitalaria del Hospital San Rafael. Respondes preguntas basándote EXCLUSIVAMENTE en los fragmentos de documentos proporcionados.

DOCUMENTOS DE REFERENCIA:
{context}

PREGUNTA: {question}

INSTRUCCIONES:
1. Responde ÚNICAMENTE con información presente en los documentos de referencia.
2. Si la respuesta está parcialmente en los documentos, responde lo que puedas e indica qué parte no encontraste.
3. Si la respuesta NO está en los documentos, di exactamente: "No encontré información sobre esto en los documentos disponibles."
4. Cuando uses información de un fragmento específico, cítalo: "Según [nombre del archivo]..."
5. No agregues conocimiento externo ni suposiciones.
6. Responde en español, de forma clara y estructurada.
7. Usa listas o pasos numerados cuando corresponda.
8. Si la información recuperada es ambigua o incompleta, indícalo explícitamente.

RESPUESTA:"""

    def test_connection(self) -> dict:
        """
        Probar conexión con Ollama y verificar modelos disponibles

        Returns:
            Dict con status y lista de modelos
        """
        try:
            # Listar modelos disponibles
            models = ollama.list()

            model_names = [model['name'] for model in models['models']]

            # Verificar si nuestros modelos están disponibles
            main_model_available = any(self.model in name for name in model_names)
            embedding_model_available = any(self.embedding_model in name for name in model_names)
            fallback_model_available = any(self.fallback_model in name for name in model_names)

            logger.info(f"Modelos disponibles en Ollama: {model_names}")

            return {
                "status": "connected",
                "models_available": model_names,
                "main_model_ready": main_model_available,
                "embedding_model_ready": embedding_model_available,
                "fallback_model_ready": fallback_model_available,
                "warnings": self._generate_warnings(
                    main_model_available,
                    embedding_model_available,
                    fallback_model_available
                )
            }

        except Exception as e:
            logger.error(f"Error al conectar con Ollama: {e}")
            return {
                "status": "error",
                "error": str(e),
                "message": "No se pudo conectar con Ollama. Verifica que esté ejecutándose en " + self.base_url
            }

    def _generate_warnings(
        self,
        main_available: bool,
        embedding_available: bool,
        fallback_available: bool
    ) -> List[str]:
        """Generar advertencias sobre modelos faltantes"""
        warnings = []

        if not main_available:
            warnings.append(f"Modelo principal '{self.model}' no encontrado. Ejecuta: ollama pull {self.model}")

        if not embedding_available:
            warnings.append(
                f"Modelo de embeddings '{self.embedding_model}' no encontrado. "
                f"Ejecuta: ollama pull {self.embedding_model}"
            )

        if not fallback_available:
            warnings.append(
                f"Modelo fallback '{self.fallback_model}' no encontrado. "
                f"Ejecuta: ollama pull {self.fallback_model}"
            )

        return warnings


# Instancia global del servicio
ollama_service = OllamaService()
