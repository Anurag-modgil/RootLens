import logging
import random
from typing import List, Dict, Any
from qdrant_client.models import Distance, VectorParams, PointStruct
from app.config import settings
from app.services.embeddings import LogEmbeddingService
from app.services.vector_store import VectorStoreService

logger = logging.getLogger("rootlens.rag")

class RAGService:
    def __init__(self):
        self.vector_store = VectorStoreService()
        self.client = self.vector_store._client
        self.embedding_service = LogEmbeddingService()
        self.collection_name = "knowledge_base"
        self._ensure_collection()

    def _ensure_collection(self):
        try:
            exists = self.client.collection_exists(self.collection_name)
            if not exists:
                logger.info(f"Creating Qdrant RAG KB collection '{self.collection_name}'...")
                self.client.create_collection(
                    collection_name=self.collection_name,
                    vectors_config=VectorParams(size=384, distance=Distance.COSINE)
                )
                logger.info(f"Collection '{self.collection_name}' created successfully.")
        except Exception as e:
            logger.error(f"Failed to ensure RAG collection: {str(e)}")
            raise

    def add_solution(self, title: str, description: str, solution: str):
        """
        Embed and index a historical incident title/description and its resolution.
        """
        try:
            text_to_embed = f"Title: {title}\nDescription: {description}"
            vector = self.embedding_service.get_embedding(text_to_embed)
            
            # Generate a random 64-bit integer ID for Qdrant
            point_id = random.randint(1, 10**8)
            
            payload = {
                "title": title,
                "description": description,
                "solution": solution
            }
            
            point = PointStruct(
                id=point_id,
                vector=vector,
                payload=payload
            )
            self.client.upsert(
                collection_name=self.collection_name,
                points=[point]
            )
            logger.info(f"Indexed solution for incident: '{title}' (ID: {point_id})")
        except Exception as e:
            logger.error(f"Failed to add solution to RAG: {str(e)}")
            raise RuntimeError(f"RAG upsert failed: {str(e)}")

    def search_solutions(self, query_text: str, limit: int = 3) -> List[Dict[str, Any]]:
        """
        Search for semantically similar historical incidents and return their solutions.
        """
        try:
            vector = self.embedding_service.get_embedding(query_text)
            results = self.client.query_points(
                collection_name=self.collection_name,
                query=vector,
                limit=limit
            )
            
            solutions = []
            for hit in results.points:
                solutions.append({
                    "score": hit.score,
                    "title": hit.payload["title"],
                    "description": hit.payload["description"],
                    "solution": hit.payload["solution"]
                })
            return solutions
        except Exception as e:
            logger.error(f"RAG search failed: {str(e)}")
            raise RuntimeError(f"RAG search failed: {str(e)}")
