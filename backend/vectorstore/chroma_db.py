"""
Chroma vector database implementation.
This module implements the VectorDatabaseInterface for ChromaDB.
"""

import os
import shutil
import tempfile
from typing import Any, Dict, List, Optional

from langchain.embeddings.base import Embeddings
from langchain_chroma import Chroma
from langchain_core.documents import Document

from .base import VectorDatabaseInterface
from .config import ChromaConfig


class ChromaVectorDB(VectorDatabaseInterface):
    """ChromaDB implementation of the vector database interface."""

    def __init__(self, embedding_model: Embeddings, config: ChromaConfig):
        """
        Initialize ChromaDB vector database.

        Args:
            embedding_model: The embedding model to use
            config: ChromaDB-specific configuration
        """
        super().__init__(embedding_model, config)
        self.config: ChromaConfig = config
        self._vectorstore: Optional[Chroma] = None

    def initialize(self, clear_existing: bool = False) -> None:
        """
        Initialize the ChromaDB database.

        Args:
            clear_existing: If True, clear any existing data
        """
        working_dir = self.config.persist_directory

        # Clear existing database if requested
        if clear_existing and os.path.exists(working_dir):
            try:
                shutil.rmtree(working_dir)
                print(f"Cleared existing ChromaDB at: {working_dir}")
            except (PermissionError, OSError) as e:
                print(f"Warning: Could not remove existing ChromaDB: {e}")
                # Create a temporary directory as fallback
                working_dir = tempfile.mkdtemp(prefix="chroma_temp_")
                print(f"Using temporary directory: {working_dir}")

        # Create directory with proper permissions
        try:
            os.makedirs(working_dir, mode=0o755, exist_ok=True)
        except (PermissionError, OSError) as e:
            print(f"Warning: Could not create directory {working_dir}: {e}")
            # Use temporary directory as fallback
            working_dir = tempfile.mkdtemp(prefix="chroma_temp_")
            print(f"Using temporary directory: {working_dir}")

        # Initialize ChromaDB with error handling
        max_retries = 3
        for attempt in range(max_retries):
            try:
                self._vectorstore = Chroma(
                    persist_directory=working_dir,
                    embedding_function=self.embedding_model,
                    collection_metadata=self.config.collection_metadata,
                    collection_name=self.config.collection_name,
                )
                print(f"ChromaDB initialized successfully at: {working_dir}")
                return
            except Exception as e:
                print(f"ChromaDB initialization attempt {attempt + 1} failed: {e}")
                if attempt == max_retries - 1:
                    # Last attempt - try with a guaranteed writable temporary directory
                    temp_dir = tempfile.mkdtemp(prefix="chroma_fallback_")
                    print(f"Using fallback temporary directory: {temp_dir}")
                    self._vectorstore = Chroma(
                        persist_directory=temp_dir,
                        embedding_function=self.embedding_model,
                        collection_metadata=self.config.collection_metadata,
                        collection_name=self.config.collection_name,
                    )
                    return
                # Wait before retry
                import time

                time.sleep(1)

    def add_documents(self, documents: List[Document]) -> None:
        """
        Add documents to ChromaDB.

        Args:
            documents: List of documents to add
        """
        if not documents:
            print("Warning: No documents to store")
            return

        if self._vectorstore is None:
            raise RuntimeError(
                "Vector database not initialized. Call initialize() first."
            )

        try:
            self._vectorstore.add_documents(documents)
            print(f"Added {len(documents)} documents to ChromaDB")
        except Exception as e:
            print(f"Error storing documents in ChromaDB: {e}")
            raise

    def similarity_search(self, query: str, k: int = 4) -> List[Document]:
        """
        Perform similarity search in ChromaDB.

        Args:
            query: Query string to search for
            k: Number of similar documents to return

        Returns:
            List of similar documents
        """
        if self._vectorstore is None:
            raise RuntimeError(
                "Vector database not initialized. Call initialize() first."
            )

        return self._vectorstore.similarity_search(query, k=k)

    def similarity_search_with_score(self, query: str, k: int = 4) -> List[tuple]:
        """
        Perform similarity search with relevance scores.

        Args:
            query: Query string to search for
            k: Number of similar documents to return

        Returns:
            List of tuples (document, score)
        """
        if self._vectorstore is None:
            raise RuntimeError(
                "Vector database not initialized. Call initialize() first."
            )

        return self._vectorstore.similarity_search_with_score(query, k=k)

    def clear(self) -> None:
        """Clear all data from ChromaDB."""
        if os.path.exists(self.config.persist_directory):
            try:
                shutil.rmtree(self.config.persist_directory)
                print(f"Cleared ChromaDB data at: {self.config.persist_directory}")
            except (PermissionError, OSError) as e:
                print(f"Warning: Could not clear ChromaDB: {e}")

        # Reinitialize after clearing
        self._vectorstore = None

    def persist(self) -> None:
        """Persist ChromaDB to storage."""
        if self._vectorstore is None:
            print("Warning: No vectorstore to persist")
            return

        try:
            # Try to persist if the method exists
            if hasattr(self._vectorstore, "persist"):
                self._vectorstore.persist()
                print("ChromaDB persisted successfully")
            else:
                print(
                    "ChromaDB persistence not available (automatic persistence enabled)"
                )
        except Exception as e:
            print(f"Warning: Could not persist ChromaDB: {e}")

    def get_retriever(self, k: int = 4, **kwargs) -> Any:
        """
        Get a retriever object for ChromaDB.

        Args:
            k: Number of documents to retrieve
            **kwargs: Additional retriever-specific parameters

        Returns:
            ChromaDB retriever object
        """
        if self._vectorstore is None:
            raise RuntimeError(
                "Vector database not initialized. Call initialize() first."
            )

        return self._vectorstore.as_retriever(search_kwargs={"k": k, **kwargs})

    def get_collection_info(self) -> Dict[str, Any]:
        """
        Get information about the ChromaDB collection.

        Returns:
            Dictionary containing collection information
        """
        if self._vectorstore is None:
            return {"status": "not_initialized"}

        try:
            # Get collection info from ChromaDB
            collection = self._vectorstore._collection
            return {
                "provider": "chroma",
                "collection_name": self.config.collection_name,
                "persist_directory": self.config.persist_directory,
                "count": collection.count() if collection else 0,
                "metadata": self.config.collection_metadata,
            }
        except Exception as e:
            return {
                "provider": "chroma",
                "collection_name": self.config.collection_name,
                "persist_directory": self.config.persist_directory,
                "error": str(e),
            }
