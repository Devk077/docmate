"""
Configuration management for vector databases using Pydantic V2.
"""

import os
from pathlib import Path
from typing import Any, Dict, Literal, Optional

from pydantic import BaseModel, Field, field_validator, model_validator

VectorDBProvider = Literal["qdrant", "chroma"]


class QdrantConfig(BaseModel):
    """Configuration for Qdrant vector database."""

    mode: Literal["local", "server"] = Field(
        default="local", description="Qdrant deployment mode"
    )
    path: str = Field(
        default="./data/vectorstore/qdrant", description="Local storage path"
    )
    url: str = Field(default="http://localhost:6333", description="Qdrant server URL")
    collection_name: str = Field(
        default="doqtoq_documents", description="Collection name"
    )
    vector_size: int = Field(
        default=384, description="Vector dimensions (must match embedding model)"
    )
    distance: Literal["Cosine", "Euclid", "Dot"] = Field(
        default="Cosine", description="Distance metric"
    )
    prefer_grpc: bool = Field(default=False, description="Use gRPC instead of HTTP")
    api_key: Optional[str] = Field(default=None, description="API key for Qdrant Cloud")
    timeout: int = Field(default=60, description="Connection timeout in seconds")

    @field_validator("vector_size")
    @classmethod
    def validate_vector_size(cls, v):
        if v <= 0:
            raise ValueError("Vector size must be positive")
        return v

    @field_validator("timeout")
    @classmethod
    def validate_timeout(cls, v):
        if v <= 0:
            raise ValueError("Timeout must be positive")
        return v

    @field_validator("path")
    @classmethod
    def validate_path(cls, v):
        # Preserve relative path formatting
        return v


class ChromaConfig(BaseModel):
    """Configuration for Chroma vector database."""

    persist_directory: str = Field(
        default="./data/vectorstore/chroma", description="Persistence directory"
    )
    collection_name: str = Field(
        default="doqtoq_documents", description="Collection name"
    )
    collection_metadata: Dict[str, str] = Field(
        default_factory=lambda: {"hnsw:space": "cosine"},
        description="Collection metadata settings",
    )

    @field_validator("persist_directory")
    @classmethod
    def validate_persist_directory(cls, v):
        # Preserve relative path formatting
        return v


class VectorDBConfig(BaseModel):
    """Main configuration for vector database system."""

    provider: VectorDBProvider = Field(
        default="qdrant", description="Vector database provider"
    )  # Changed default to qdrant
    qdrant: QdrantConfig = Field(
        default_factory=QdrantConfig, description="Qdrant configuration"
    )
    chroma: ChromaConfig = Field(
        default_factory=ChromaConfig, description="Chroma configuration"
    )

    @model_validator(mode="before")
    @classmethod
    def validate_config(cls, values):
        """Validate the overall configuration."""
        # No longer need to warn about Qdrant - it's now available!
        return values

    model_config = {
        "validate_assignment": True,
        "extra": "forbid",  # Prevent unknown fields
        "use_enum_values": True,
    }


def get_vector_db_config() -> VectorDBConfig:
    """
    Get vector database configuration from environment variables or defaults.

    Environment Variables:
        VECTOR_DB_PROVIDER: "qdrant" or "chroma"
        QDRANT_MODE: "local" or "server"
        QDRANT_PATH: Path for local Qdrant storage
        QDRANT_URL: URL for Qdrant server
        QDRANT_COLLECTION: Collection name for Qdrant
        QDRANT_VECTOR_SIZE: Vector dimensions
        QDRANT_DISTANCE: Distance metric
        QDRANT_PREFER_GRPC: Use gRPC instead of HTTP
        QDRANT_API_KEY: API key for Qdrant Cloud
        QDRANT_TIMEOUT: Connection timeout
        CHROMA_PERSIST_DIR: Persist directory for Chroma
        CHROMA_COLLECTION: Collection name for Chroma

    Returns:
        VectorDBConfig object with loaded configuration
    """
    # Get provider with validation
    provider = os.getenv("VECTOR_DB_PROVIDER", "qdrant").lower()  # Default to qdrant
    if provider not in ["qdrant", "chroma"]:
        print(
            f"Warning: Invalid VECTOR_DB_PROVIDER '{provider}'. Defaulting to 'qdrant'"
        )
        provider = "qdrant"

    # Build configuration dictionary
    config_data = {
        "provider": provider,
        "qdrant": {
            "mode": os.getenv("QDRANT_MODE", "local"),
            "path": os.getenv("QDRANT_PATH", "./data/vectorstore/qdrant"),
            "url": os.getenv("QDRANT_URL", "http://localhost:6333"),
            "collection_name": os.getenv("QDRANT_COLLECTION", "doqtoq_documents"),
            "vector_size": int(os.getenv("QDRANT_VECTOR_SIZE", "384")),
            "distance": os.getenv("QDRANT_DISTANCE", "Cosine"),
            "prefer_grpc": os.getenv("QDRANT_PREFER_GRPC", "false").lower() == "true",
            "api_key": os.getenv("QDRANT_API_KEY"),
            "timeout": int(os.getenv("QDRANT_TIMEOUT", "60")),
        },
        "chroma": {
            "persist_directory": os.getenv(
                "CHROMA_PERSIST_DIR", "./data/vectorstore/chroma"
            ),
            "collection_name": os.getenv("CHROMA_COLLECTION", "doqtoq_documents"),
        },
    }

    try:
        return VectorDBConfig(**config_data)
    except Exception as e:
        print(f"Error parsing vector database configuration: {e}")
        print("Using default configuration...")
        return VectorDBConfig()


def create_data_directory(path: str) -> None:
    """
    Create data directory with proper permissions.

    Args:
        path: Directory path to create

    Raises:
        OSError: If directory cannot be created
    """
    try:
        Path(path).mkdir(parents=True, exist_ok=True, mode=0o755)
        print(f"Created/verified data directory: {path}")
    except (PermissionError, OSError) as e:
        print(f"Error: Could not create directory {path}: {e}")
        raise


def validate_embedding_model_compatibility(
    config: VectorDBConfig, embedding_dimension: int
) -> bool:
    """
    Validate that the vector database configuration is compatible with the embedding model.

    Args:
        config: Vector database configuration
        embedding_dimension: Dimension of the embedding model

    Returns:
        True if compatible, False otherwise
    """
    if config.provider == "qdrant":
        if config.qdrant.vector_size != embedding_dimension:
            print(
                f"Warning: Qdrant vector_size ({config.qdrant.vector_size}) "
                f"doesn't match embedding dimension ({embedding_dimension})"
            )
            return False

    # Chroma automatically handles vector dimensions
    return True
