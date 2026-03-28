"""
Abstract base class for vector database implementations.
This module defines the interface that all vector database implementations must follow.
"""

from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional

from langchain.embeddings.base import Embeddings
from langchain_core.documents import Document


class VectorDatabaseInterface(ABC):
    """
    Abstract interface for vector database implementations.

    This interface ensures consistency across different vector database providers
    and makes it easy to switch between them or add new ones.
    """

    def __init__(self, embedding_model: Embeddings, config: Dict[str, Any]):
        """
        Initialize the vector database with an embedding model and configuration.

        Args:
            embedding_model: The embedding model to use for vectorization
            config: Database-specific configuration parameters
        """
        self.embedding_model = embedding_model
        self.config = config
        self._vectorstore = None

    @abstractmethod
    def initialize(self, clear_existing: bool = False) -> None:
        """
        Initialize the vector database.

        Args:
            clear_existing: If True, clear any existing data
        """
        pass

    @abstractmethod
    def add_documents(self, documents: List[Document]) -> None:
        """
        Add documents to the vector database.

        Args:
            documents: List of documents to add
        """
        pass

    @abstractmethod
    def similarity_search(self, query: str, k: int = 4) -> List[Document]:
        """
        Perform similarity search on the vector database.

        Args:
            query: Query string to search for
            k: Number of similar documents to return

        Returns:
            List of similar documents
        """
        pass

    @abstractmethod
    def similarity_search_with_score(self, query: str, k: int = 4) -> List[tuple]:
        """
        Perform similarity search with relevance scores.

        Args:
            query: Query string to search for
            k: Number of similar documents to return

        Returns:
            List of tuples (document, score)
        """
        pass

    @abstractmethod
    def clear(self) -> None:
        """Clear all data from the vector database."""
        pass

    @abstractmethod
    def persist(self) -> None:
        """Persist the vector database to storage."""
        pass

    @abstractmethod
    def get_retriever(self, k: int = 4, **kwargs) -> Any:
        """
        Get a retriever object for the vector database.

        Args:
            k: Number of documents to retrieve
            **kwargs: Additional retriever-specific parameters

        Returns:
            Retriever object compatible with LangChain
        """
        pass

    @property
    def vectorstore(self) -> Any:
        """Get the underlying vectorstore object."""
        return self._vectorstore

    @abstractmethod
    def get_collection_info(self) -> Dict[str, Any]:
        """
        Get information about the current collection/database.

        Returns:
            Dictionary containing collection information
        """
        pass
