__module_name__ = "backend"
__version__ = "1.0.0"
__author__ = "Shreyas Bangera"
__description__ = "DoqToq - Documents that talk"

from .chunker import chunk_document
from .embedder import get_embedding_model

# Export main classes for easy importing
from .rag_engine import DocumentRAG

__all__ = ["DocumentRAG", "chunk_document", "get_embedding_model"]
