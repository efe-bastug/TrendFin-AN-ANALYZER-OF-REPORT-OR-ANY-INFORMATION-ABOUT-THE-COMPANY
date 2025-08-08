"""
Qdrant vector database client for storing and retrieving document embeddings
"""

from qdrant_client import QdrantClient
from qdrant_client.http import models
from qdrant_client.http.models import Distance, VectorParams, PointStruct
from typing import List, Dict, Optional, Tuple
import openai
from django.conf import settings
import logging
import uuid
import numpy as np

logger = logging.getLogger(__name__)


class VectorStoreClient:
    """Client for interacting with Qdrant vector database"""
    
    def __init__(self):
        self.client = QdrantClient(url=settings.QDRANT_SETTINGS['URL'])
        self.collection_name = settings.QDRANT_SETTINGS['COLLECTION_NAME']
        self.vector_size = settings.QDRANT_SETTINGS['VECTOR_SIZE']
        
        openai.api_key = settings.OPENAI_API_KEY
        self.embedding_model = settings.OPENAI_SETTINGS['EMBEDDING_MODEL']
        
        self._ensure_collection_exists()
    
    def _ensure_collection_exists(self):
        """Create collection if it doesn't exist"""
        try:
            collections = self.client.get_collections()
            collection_names = [col.name for col in collections.collections]
            
            if self.collection_name not in collection_names:
                logger.info(f"Creating Qdrant collection: {self.collection_name}")
                self.client.create_collection(
                    collection_name=self.collection_name,
                    vectors_config=VectorParams(
                        size=self.vector_size,
                        distance=Distance.COSINE
                    )
                )
                logger.info(f"Collection {self.collection_name} created successfully")
            else:
                logger.info(f"Collection {self.collection_name} already exists")
                
        except Exception as e:
            logger.error(f"Error ensuring collection exists: {str(e)}")
            raise
    
    def create_embeddings(self, texts: List[str]) -> List[List[float]]:
        """
        Create embeddings for a list of texts using OpenAI
        
        Args:
            texts: List of text strings to embed
            
        Returns:
            List of embedding vectors
        """
        try:
            logger.info(f"Creating embeddings for {len(texts)} texts")
            
            response = openai.embeddings.create(
                model=self.embedding_model,
                input=texts
            )
            
            embeddings = [item.embedding for item in response.data]
            logger.info(f"Successfully created {len(embeddings)} embeddings")
            
            return embeddings
            
        except Exception as e:
            logger.error(f"Error creating embeddings: {str(e)}")
            raise
    
    def store_chunk_embeddings(self, chunks_data: List[Dict]) -> List[str]:
        """
        Store document chunks with their embeddings in Qdrant
        
        Args:
            chunks_data: List of dictionaries containing chunk information
                Each dict should have: content, document_id, chunk_index, page_start, page_end
                
        Returns:
            List of vector IDs assigned by Qdrant
        """
        try:
            if not chunks_data:
                return []
            
            texts = [chunk['content'] for chunk in chunks_data]
            
            embeddings = self.create_embeddings(texts)
            
            points = []
            vector_ids = []
            
            for i, (chunk, embedding) in enumerate(zip(chunks_data, embeddings)):
                vector_id = str(uuid.uuid4())
                vector_ids.append(vector_id)
                
                point = PointStruct(
                    id=vector_id,
                    vector=embedding,
                    payload={
                        'document_id': str(chunk['document_id']),
                        'chunk_index': chunk['chunk_index'],
                        'page_start': chunk['page_start'],
                        'page_end': chunk['page_end'],
                        'content': chunk['content'],
                        'token_count': chunk.get('token_count', 0)
                    }
                )
                points.append(point)
            
            operation_info = self.client.upsert(
                collection_name=self.collection_name,
                wait=True,
                points=points
            )
            
            logger.info(f"Successfully stored {len(points)} embeddings in Qdrant")
            return vector_ids
            
        except Exception as e:
            logger.error(f"Error storing chunk embeddings: {str(e)}")
            raise
    
    def search_similar_chunks(
        self, 
        query: str, 
        limit: int = 4,
        document_ids: Optional[List[str]] = None
    ) -> List[Dict]:
        """
        Search for similar chunks using vector similarity
        
        Args:
            query: Search query text
            limit: Maximum number of results to return
            document_ids: Optional list of document IDs to filter by
            
        Returns:
            List of similar chunks with metadata and scores
        """
        try:
            query_embedding = self.create_embeddings([query])[0]
            
            search_filter = None
            if document_ids:
                document_id_strings = [str(doc_id) for doc_id in document_ids]
                search_filter = models.Filter(
                    must=[
                        models.FieldCondition(
                            key="document_id",
                            match=models.MatchAny(any=document_id_strings)
                        )
                    ]
                )
            
            search_result = self.client.search(
                collection_name=self.collection_name,
                query_vector=query_embedding,
                query_filter=search_filter,
                limit=limit,
                with_payload=True
            )
            
            results = []
            for scored_point in search_result:
                result = {
                    'vector_id': scored_point.id,
                    'score': scored_point.score,
                    'document_id': scored_point.payload['document_id'],
                    'chunk_index': scored_point.payload['chunk_index'],
                    'page_start': scored_point.payload['page_start'],
                    'page_end': scored_point.payload['page_end'],
                    'content': scored_point.payload['content'],
                    'token_count': scored_point.payload.get('token_count', 0)
                }
                results.append(result)
            
            logger.info(f"Found {len(results)} similar chunks for query")
            return results
            
        except Exception as e:
            logger.error(f"Error searching similar chunks: {str(e)}")
            raise
    
    def delete_document_embeddings(self, document_id: str) -> bool:
        """
        Delete all embeddings for a specific document
        
        Args:
            document_id: ID of the document to delete embeddings for
            
        Returns:
            True if successful, False otherwise
        """
        try:
            delete_filter = models.Filter(
                must=[
                    models.FieldCondition(
                        key="document_id",
                        match=models.MatchValue(value=document_id)
                    )
                ]
            )
            
            operation_info = self.client.delete(
                collection_name=self.collection_name,
                points_selector=models.FilterSelector(filter=delete_filter),
                wait=True
            )
            
            logger.info(f"Deleted embeddings for document {document_id}")
            return True
            
        except Exception as e:
            logger.error(f"Error deleting document embeddings: {str(e)}")
            return False
    
    def get_collection_info(self) -> Dict:
        """Get information about the collection"""
        try:
            collection_info = self.client.get_collection(self.collection_name)
            return {
                'name': collection_info.config.params.vectors.size,
                'vector_size': collection_info.config.params.vectors.size,
                'distance_metric': collection_info.config.params.vectors.distance,
                'points_count': collection_info.points_count,
                'status': collection_info.status
            }
        except Exception as e:
            logger.error(f"Error getting collection info: {str(e)}")
            return {}
    
    def health_check(self) -> bool:
        """Check if Qdrant is healthy and accessible"""
        try:
            collections = self.client.get_collections()
            return True
        except Exception as e:
            logger.error(f"Qdrant health check failed: {str(e)}")
            return False


def store_document_chunks(document_id: str) -> bool:
    """
    Bir belgenin tüm parçaları için gömmeleri depola
    
    Args:
        document_id: PDFDocument'ın UUID'si
        
    Returns:
        Başarılıysa True, aksi halde False
    """
    from apps.core.models import PDFDocument, DocumentChunk
    
    try:
        document = PDFDocument.objects.get(id=document_id)
        chunks = DocumentChunk.objects.filter(document=document).order_by('chunk_index')
        
        if not chunks.exists():
            logger.warning(f"No chunks found for document {document_id}")
            return False
        
        # Gömme için parça verilerini hazırla
        chunks_data = []
        for chunk in chunks:
            chunks_data.append({
                'content': chunk.content,
                'document_id': document_id,
                'chunk_index': chunk.chunk_index,
                'page_start': chunk.page_start,
                'page_end': chunk.page_end,
                'token_count': chunk.token_count
            })
        
        # Gömmeleri depola
        vector_client = VectorStoreClient()
        vector_ids = vector_client.store_chunk_embeddings(chunks_data)
        
        # Parçaları vektör ID'leriyle güncelle
        for chunk, vector_id in zip(chunks, vector_ids):
            chunk.vector_id = vector_id
            chunk.save()
        
        logger.info(f"Successfully stored embeddings for document {document_id}")
        return True
        
    except Exception as e:
        logger.error(f"Error storing document chunks: {str(e)}")
        return False


def search_relevant_chunks(query: str, document_ids: Optional[List[str]] = None, limit: int = 4) -> List[Dict]:
    """
    Belgeler arasında ilgili parçaları ara
    
    Args:
        query: Arama sorgusu
        document_ids: İsteğe bağlı, arama yapılacak belge ID'leri
        limit: Döndürülecek maksimum sonuç sayısı
        
    Returns:
        Meta verileriyle birlikte ilgili parça listesi
    """
    try:
        vector_client = VectorStoreClient()
        results = vector_client.search_similar_chunks(
            query=query,
            limit=limit,
            document_ids=document_ids
        )
        
        return results
        
    except Exception as e:
        logger.error(f"Error searching relevant chunks: {str(e)}")
        return []