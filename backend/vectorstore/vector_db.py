__module_name__ = "vector_db"

"""
Backward compatibility layer for the new modular vector database system.

This module maintains the original API while using the new factory pattern internally.
All functions in this module are marked as LEGACY and will show deprecation warnings.

For new code, please use:
- get_vector_database() from the factory module
- VectorDatabaseInterface methods directly
"""

import os
import shutil
import warnings
from typing import Any, List, Union

from langchain.embeddings.base import Embeddings
from langchain_core.documents import Document

from .base import VectorDatabaseInterface
from .config import get_vector_db_config
from .factory import get_vector_database

# Global constant for vector database directory (legacy)
VECTOR_DB_DIR = "backend/vectorstore/index"


def _show_deprecation_warning(function_name: str, new_api: str) -> None:
    """Show deprecation warning for legacy functions."""
    warnings.warn(
        f"{function_name} is deprecated and will be removed in a future version. "
        f"Please use {new_api} instead.",
        DeprecationWarning,
        stacklevel=3,
    )


def get_vectorstore(embedding_model: Embeddings, clear_existing: bool = False) -> Any:
    """
    Get a vectorstore instance with proper error handling.

    LEGACY FUNCTION - For backward compatibility only.

    Args:
        embedding_model: The embedding model to use
        clear_existing: If True, clears any existing vector database

    Returns:
        The underlying vectorstore object (Chroma by default)

    Deprecated:
        Use get_vector_database() from the factory module instead.
    """
    _show_deprecation_warning(
        "get_vectorstore()", "get_vector_database() from backend.vectorstore.factory"
    )

    try:
        # Get vector database using new factory
        db = get_vector_database(embedding_model, clear_existing=clear_existing)

        # Return the underlying vectorstore for backward compatibility
        return db.vectorstore
    except Exception as e:
        print(f"Error in legacy get_vectorstore(): {e}")
        raise


def clear_vectorstore() -> None:
    """
    Clear the entire vector database with error handling.

    LEGACY FUNCTION - For backward compatibility only.

    Deprecated:
        Use VectorDatabaseInterface.clear() method instead.
    """
    _show_deprecation_warning(
        "clear_vectorstore()", "VectorDatabaseInterface.clear() method"
    )

    try:
        # For legacy compatibility, clear the default Chroma directory
        if os.path.exists(VECTOR_DB_DIR):
            shutil.rmtree(VECTOR_DB_DIR)
            print(f"Cleared legacy vectorstore at: {VECTOR_DB_DIR}")

        # Also try to get current config and clear properly
        config = get_vector_db_config()
        if config.provider == "chroma" and os.path.exists(
            config.chroma.persist_directory
        ):
            if config.chroma.persist_directory != VECTOR_DB_DIR:
                shutil.rmtree(config.chroma.persist_directory)
                print(
                    f"Cleared configured vectorstore at: {config.chroma.persist_directory}"
                )

    except (PermissionError, OSError) as e:
        print(f"Warning: Could not clear vectorstore: {e}")
    except Exception as e:
        print(f"Error in clear_vectorstore(): {e}")


def store_embeddings(vectorstore: Any, chunks: List[Document]) -> None:
    """
    Store embeddings with error handling.

    LEGACY FUNCTION - For backward compatibility only.

    Args:
        vectorstore: The vectorstore object (Chroma or VectorDatabaseInterface)
        chunks: List of document chunks to store

    Deprecated:
        Use VectorDatabaseInterface.add_documents() method instead.
    """
    _show_deprecation_warning(
        "store_embeddings()", "VectorDatabaseInterface.add_documents() method"
    )

    if not chunks:
        print("Warning: No chunks to store")
        return

    try:
        # Check if it's the new VectorDatabaseInterface
        if isinstance(vectorstore, VectorDatabaseInterface):
            vectorstore.add_documents(chunks)
            vectorstore.persist()
        # Check if it's a legacy Chroma object or similar
        elif hasattr(vectorstore, "add_documents"):
            vectorstore.add_documents(chunks)

            # Try to persist if the method exists
            if hasattr(vectorstore, "persist"):
                try:
                    vectorstore.persist()
                except Exception as persist_error:
                    print(f"Warning: Could not persist vectorstore: {persist_error}")
        else:
            raise ValueError(f"Unsupported vectorstore type: {type(vectorstore)}")

        print(f"Successfully stored {len(chunks)} chunks")

    except Exception as e:
        print(f"Error storing embeddings: {e}")
        raise RuntimeError(f"Failed to store embeddings: {e}")


# Additional legacy compatibility functions


def get_vectorstore_info() -> dict:
    """
    Get information about the current vectorstore configuration.

    LEGACY FUNCTION - For backward compatibility only.

    Returns:
        Dictionary with vectorstore information

    Deprecated:
        Use VectorDatabaseInterface.get_collection_info() method instead.
    """
    _show_deprecation_warning(
        "get_vectorstore_info()", "VectorDatabaseInterface.get_collection_info() method"
    )

    try:
        config = get_vector_db_config()
        return {
            "provider": config.provider,
            "config": (
                config.model_dump() if hasattr(config, "model_dump") else str(config)
            ),
            "legacy_dir": VECTOR_DB_DIR,
        }
    except Exception as e:
        return {"error": str(e)}


def is_vectorstore_initialized() -> bool:
    """
    Check if vectorstore is initialized (legacy compatibility).

    LEGACY FUNCTION - For backward compatibility only.

    Returns:
        True if vectorstore appears to be initialized

    Deprecated:
        Use VectorDatabaseInterface methods directly instead.
    """
    _show_deprecation_warning(
        "is_vectorstore_initialized()", "VectorDatabaseInterface methods directly"
    )

    try:
        config = get_vector_db_config()

        if config.provider == "chroma":
            # Check if Chroma directory exists and has content
            persist_dir = config.chroma.persist_directory
            return os.path.exists(persist_dir) and bool(os.listdir(persist_dir))
        elif config.provider == "qdrant":
            # For Qdrant, check if data directory exists
            data_path = config.qdrant.path
            return os.path.exists(data_path) and bool(os.listdir(data_path))

        return False
    except Exception:
        return False
