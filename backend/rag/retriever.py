import os
import sys
import pickle
import numpy as np
import logging
from typing import List, Dict, Any

logger = logging.getLogger("retriever")

# Lazy imports to keep server startup instantaneous
faiss = None
SentenceTransformer = None

class NutritionRetriever:
    _instance = None
    
    def __new__(cls, *args, **kwargs):
        if not cls._instance:
            cls._instance = super(NutritionRetriever, cls).__new__(cls, *args, **kwargs)
            cls._instance._initialized = False
        return cls._instance
        
    def __init__(self):
        if self._initialized:
            return
        
        self.backend_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        self.index_dir = os.path.join(self.backend_dir, "rag", "faiss_index")
        self.index_path = os.path.join(self.index_dir, "index.faiss")
        self.metadata_path = os.path.join(self.index_dir, "metadata.pkl")
        
        self.index = None
        self.documents = None
        self.model = None
        self._initialized = True
        
    def _lazy_load(self) -> bool:
        """Lazy load heavy models and index when the first query comes in."""
        global faiss, SentenceTransformer
        
        if self.index is not None and self.model is not None:
            return True
            
        try:
            if faiss is None:
                import faiss as _faiss
                faiss = _faiss
            if SentenceTransformer is None:
                from sentence_transformers import SentenceTransformer as _ST
                SentenceTransformer = _ST
        except ImportError as e:
            logger.error(f"❌ Failed to import FAISS or SentenceTransformer: {e}. Ensure packages are installed.")
            return False
            
        if not os.path.exists(self.index_path) or not os.path.exists(self.metadata_path):
            logger.warning("⚠️ RAG database index or metadata not found. Please run: python backend/ingest.py")
            return False
            
        try:
            logger.info("🔋 Loading FAISS index for retriever...")
            self.index = faiss.read_index(self.index_path)
            
            logger.info("🔋 Loading document metadata...")
            with open(self.metadata_path, "rb") as f:
                self.documents = pickle.load(f)
                
            logger.info("🧠 Loading Sentence-Transformer model ('all-MiniLM-L6-v2')...")
            self.model = SentenceTransformer("all-MiniLM-L6-v2")
            logger.info("✅ RAG retriever components loaded successfully.")
            return True
        except Exception as e:
            logger.error(f"❌ Error loading RAG index/model: {e}")
            self.index = None
            self.model = None
            return False
            
    async def retrieve(self, question: str, k: int = 5) -> List[str]:
        """Retrieve top k relevant nutrition contexts for a given question, checking Redis cache first."""
        if not question or not question.strip():
            return []
            
        # Try checking Redis cache first
        try:
            from utils.cache import get_cached, set_cached, make_cache_key
            cache_key = make_cache_key("rag", question)
            cached_results = await get_cached(cache_key)
            if cached_results is not None:
                logger.info(f"⚡ RAG Cache Hit for query: '{question}'")
                return cached_results
        except Exception as e:
            logger.warning(f"⚠️ Error reading RAG cache: {e}. Continuing with standard retrieval.")
            cache_key = None
            
        # Cache miss, retrieve from FAISS
        if not self._lazy_load():
            return []
            
        try:
            # Encode query and normalize for Cosine Similarity (Inner Product)
            query_vector = self.model.encode([question], convert_to_numpy=True)
            norm = np.linalg.norm(query_vector, axis=1, keepdims=True)
            normalized_query = query_vector / (norm + 1e-10)
            
            # Search FAISS index
            scores, indices = self.index.search(normalized_query, k)
            
            results = []
            for score, idx in zip(scores[0], indices[0]):
                if idx == -1 or idx >= len(self.documents):
                    continue
                results.append(self.documents[idx]["text"])
                
            # Cache the results in Redis
            if results and cache_key:
                try:
                    await set_cached(cache_key, results, ttl=86400) # Cache for 1 day
                    logger.info(f"💾 Cached RAG results in Redis for query: '{question}'")
                except Exception as cache_err:
                    logger.warning(f"Failed to cache RAG results: {cache_err}")
                    
            return results
        except Exception as err:
            logger.error(f"❌ Retrieval search failed: {err}")
            return []

_retriever = None

def get_retriever() -> NutritionRetriever:
    global _retriever
    if _retriever is None:
        _retriever = NutritionRetriever()
    return _retriever
