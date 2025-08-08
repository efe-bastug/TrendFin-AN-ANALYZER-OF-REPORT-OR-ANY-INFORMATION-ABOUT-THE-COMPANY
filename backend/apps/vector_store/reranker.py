"""
Reranker service for improving citation accuracy
Uses cross-encoder models to re-rank retrieved chunks based on relevance
"""

import openai
from typing import List, Dict, Optional
from django.conf import settings
import logging
import numpy as np
from sklearn.metrics.pairwise import cosine_similarity

logger = logging.getLogger(__name__)


class RerankerService:
    """Service for re-ranking retrieved chunks to improve citation accuracy"""
    
    def __init__(self):
        self.openai_client = openai.OpenAI(api_key=settings.OPENAI_API_KEY)
        self.model = "gpt-4o-mini"  # Can be changed to a cross-encoder model
        self.max_chunks_to_rerank = 10
        self.min_relevance_score = 0.7
        
    def rerank_chunks(
        self, 
        question: str, 
        chunks: List[Dict], 
        top_k: int = 4
    ) -> List[Dict]:
        """
        Re-rank chunks based on relevance to the question
        
        Args:
            question: User's question
            chunks: List of retrieved chunks
            top_k: Number of top chunks to return
            
        Returns:
            Re-ranked list of chunks
        """
        if not chunks:
            return []
            
        if len(chunks) <= top_k:
            return chunks
            
        try:
            scored_chunks = self._score_chunks_with_openai(question, chunks)
            
            scored_chunks.sort(key=lambda x: x['relevance_score'], reverse=True)
            
            filtered_chunks = [
                chunk for chunk in scored_chunks 
                if chunk['relevance_score'] >= self.min_relevance_score
            ]
            
            return filtered_chunks[:top_k]
            
        except Exception as e:
            logger.error(f"Error in reranking: {str(e)}")
            return chunks[:top_k]
    
    def _score_chunks_with_openai(self, question: str, chunks: List[Dict]) -> List[Dict]:
        """Score chunks using OpenAI API"""
        scored_chunks = []
        
        for chunk in chunks:
            try:
                prompt = self._create_scoring_prompt(question, chunk['content'])
                
                response = self.openai_client.chat.completions.create(
                    model=self.model,
                    messages=[
                        {
                            "role": "system",
                            "content": "You are a relevance scorer. Rate how well a document chunk answers a question on a scale of 0.0 to 1.0. Respond with only the number."
                        },
                        {
                            "role": "user",
                            "content": prompt
                        }
                    ],
                    max_tokens=10,
                    temperature=0.1
                )
                
                score_text = response.choices[0].message.content.strip()
                try:
                    score = float(score_text)
                    score = max(0.0, min(1.0, score))
                except ValueError:
                    score = 0.5
                
                chunk['relevance_score'] = score
                scored_chunks.append(chunk)
                
            except Exception as e:
                logger.error(f"Error scoring chunk: {str(e)}")
                chunk['relevance_score'] = 0.5
                scored_chunks.append(chunk)
        
        return scored_chunks
    
    def _create_scoring_prompt(self, question: str, chunk_content: str) -> str:
        """Create prompt for scoring chunk relevance"""
        return f"""Question: {question}

Document chunk: {chunk_content[:1000]}...

Rate how well this document chunk answers the question on a scale of 0.0 to 1.0, where:
- 0.0: Completely irrelevant
- 0.5: Somewhat relevant
- 1.0: Highly relevant and directly answers the question

Score:"""
    
    def boost_citation_accuracy(
        self, 
        question: str, 
        chunks: List[Dict], 
        answer: str
    ) -> List[Dict]:
        """
        Boost citation accuracy by checking if chunks are actually used in the answer
        
        Args:
            question: Original question
            chunks: Retrieved chunks
            answer: Generated answer
            
        Returns:
            Chunks with boosted scores for those actually cited
        """
        try:
            cited_chunks = self._identify_cited_chunks(answer, chunks)
            
            for chunk in chunks:
                if chunk['id'] in cited_chunks:
                    chunk['relevance_score'] = min(1.0, chunk['relevance_score'] * 1.2)
                    chunk['cited_in_answer'] = True
                else:
                    chunk['cited_in_answer'] = False
            
            return chunks
            
        except Exception as e:
            logger.error(f"Error boosting citation accuracy: {str(e)}")
            return chunks
    
    def _identify_cited_chunks(self, answer: str, chunks: List[Dict]) -> List[str]:
        """Identify which chunks are actually cited in the answer"""
        cited_chunk_ids = []
        
        for i, chunk in enumerate(chunks, 1):
            if f"[{i}]" in answer:
                cited_chunk_ids.append(chunk['id'])
            
            if chunk.get('document_name') and chunk['document_name'] in answer:
                cited_chunk_ids.append(chunk['id'])
            
            if f"page {chunk['page_start']}" in answer.lower() or f"page {chunk['page_end']}" in answer.lower():
                cited_chunk_ids.append(chunk['id'])
        
        return cited_chunk_ids
    
    def filter_low_quality_chunks(self, chunks: List[Dict]) -> List[Dict]:
        """Filter out low-quality chunks"""
        filtered_chunks = []
        
        for chunk in chunks:
            if len(chunk.get('content', '')) < 50:
                continue
                
            if chunk.get('relevance_score', 0) < 0.3:
                continue
                
            content = chunk.get('content', '')
            if content.strip() == '' or len(content.strip()) < 20:
                continue
                
            filtered_chunks.append(chunk)
        
        return filtered_chunks


reranker_service = RerankerService() 