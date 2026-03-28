__module_name__ = "embedder"

import logging
import os
from typing import Any, Dict, List, Literal

from dotenv import load_dotenv
from langchain.embeddings.base import Embeddings
from langchain_huggingface import HuggingFaceEmbeddings

load_dotenv()

logger = logging.getLogger(__name__)

EmbeddingProvider = Literal["huggingface", "mistral"]

# Module-level cache: (provider, model_name) → embedding model instance
# Prevents reloading HuggingFace models on every room open or document index.
_EMBEDDING_CACHE: Dict[str, Any] = {}

# Predefined model configurations for different providers
# Model Providers and Organizations:
# - sentence-transformers: all-MiniLM-L6-v2, all-mpnet-base-v2
# - BAAI (Beijing Academy of Artificial Intelligence): bge-small-en-v1.5, bge-base-en-v1.5, bge-large-en-v1.5
# - mistralai: mistral-embed
EMBEDDING_MODELS = {
    "huggingface": {
        # Sentence Transformers models
        "all-MiniLM-L6-v2": "sentence-transformers/all-MiniLM-L6-v2",
        "all-mpnet-base-v2": "sentence-transformers/all-mpnet-base-v2",
        # BAAI (Beijing Academy of Artificial Intelligence) models
        "bge-small-en-v1.5": "BAAI/bge-small-en-v1.5",
        "bge-base-en-v1.5": "BAAI/bge-base-en-v1.5",
        "bge-large-en-v1.5": "BAAI/bge-large-en-v1.5",
    },
    "mistral": {
        # Mistral AI models
        "mistral-embed": "mistral-embed"
    },
}


class MistralEmbeddings(Embeddings):
    """Custom Mistral embeddings wrapper for LangChain compatibility."""

    def __init__(self, model: str = "mistral-embed", api_key: str = None, **kwargs):
        """
        Initialize Mistral embeddings.

        Args:
            model: The Mistral model to use
            api_key: Mistral API key (if not provided, will use MISTRAL_API_KEY env var)
            **kwargs: Additional parameters
        """
        try:
            from mistralai import Mistral
        except ImportError:
            raise ImportError(
                "mistralai package not found. Please install it with: pip install mistralai"
            )

        self.model = model
        self.api_key = api_key or os.getenv("MISTRAL_API_KEY")

        if not self.api_key:
            raise ValueError(
                "MISTRAL_API_KEY not found. Please set it in your .env file or pass it as api_key parameter."
            )

        self.client = Mistral(api_key=self.api_key)

    def embed_documents(self, texts: List[str]) -> List[List[float]]:
        """Embed a list of documents."""
        try:
            response = self.client.embeddings.create(model=self.model, inputs=texts)
            return [data.embedding for data in response.data]
        except Exception as e:
            raise RuntimeError(f"Failed to embed documents with Mistral: {str(e)}")

    def embed_query(self, text: str) -> List[float]:
        """Embed a single query text."""
        try:
            response = self.client.embeddings.create(model=self.model, inputs=[text])
            return response.data[0].embedding
        except Exception as e:
            raise RuntimeError(f"Failed to embed query with Mistral: {str(e)}")


def get_embedding_model(
    provider: EmbeddingProvider = "huggingface",
    model_name: str = "all-MiniLM-L6-v2",
    **kwargs,
):
    """
    Get an embedding model from various providers.
    Results are cached in memory so the heavy HuggingFace model
    is only loaded ONCE per Python process.

    Args:
        provider: The embedding provider to use
        model_name: The model name (short name from EMBEDDING_MODELS)
        **kwargs: Additional parameters for the embedding model

    Returns:
        Configured embedding model instance
    """
    cache_key = f"{provider}::{model_name}"
    if cache_key in _EMBEDDING_CACHE:
        logger.debug(f"embedder - Cache hit for embedding model: {cache_key}")
        return _EMBEDDING_CACHE[cache_key]

    logger.info(f"embedder - Loading embedding model: provider={provider}, model={model_name}")
    if provider == "huggingface":
        model = _get_huggingface_embeddings(model_name, **kwargs)
    elif provider == "mistral":
        model = _get_mistral_embeddings(model_name, **kwargs)
    else:
        raise ValueError(f"Unsupported embedding provider: {provider}")

    _EMBEDDING_CACHE[cache_key] = model
    logger.info(f"embedder - Embedding model loaded and cached: {cache_key}")
    return model


def _get_huggingface_embeddings(model_name: str, **kwargs):
    """Get HuggingFace BGE embeddings."""
    full_model_name = EMBEDDING_MODELS["huggingface"].get(model_name, model_name)

    default_kwargs = {
        "model_name": full_model_name,
        "model_kwargs": {"device": "cpu"},  # Can be overridden
        "encode_kwargs": {"normalize_embeddings": True},
    }
    default_kwargs.update(kwargs)

    return HuggingFaceEmbeddings(**default_kwargs)


def _get_mistral_embeddings(model_name: str, **kwargs):
    """Get Mistral embeddings."""
    full_model_name = EMBEDDING_MODELS["mistral"].get(model_name, model_name)

    default_kwargs = {"model": full_model_name}
    default_kwargs.update(kwargs)

    return MistralEmbeddings(**default_kwargs)


def list_available_models(
    provider: EmbeddingProvider = None,
) -> Dict[str, Dict[str, str]]:
    """
    List all available embedding models.

    Args:
        provider: Optional provider to filter by

    Returns:
        Dictionary of available models by provider
    """
    if provider:
        return {provider: EMBEDDING_MODELS.get(provider, {})}
    return EMBEDDING_MODELS


def get_model_info(provider: EmbeddingProvider, model_name: str) -> Dict[str, Any]:
    """
    Get information about a specific embedding model.

    Args:
        provider: The embedding provider
        model_name: The model name

    Returns:
        Dictionary with model information
    """
    models = EMBEDDING_MODELS.get(provider, {})
    if model_name not in models:
        return {"error": f"Model {model_name} not found for provider {provider}"}

    info = {
        "provider": provider,
        "model_name": model_name,
        "full_model_path": models[model_name],
        "requires_api_key": provider == "mistral",
    }

    # Add provider-specific information
    if provider == "huggingface":
        # Determine the actual model creator/organization
        if model_name.startswith("bge-"):
            info.update(
                {
                    "type": "BGE (Beijing Academy of Artificial Intelligence - BAAI)",
                    "organization": "BAAI",
                    "local": True,
                    "gpu_recommended": "bge-large" in model_name,
                    "description": "BGE (Beijing Academy of Artificial Intelligence) embedding model",
                }
            )
        elif model_name in ["all-MiniLM-L6-v2", "all-mpnet-base-v2"]:
            info.update(
                {
                    "type": "Sentence Transformers",
                    "organization": "sentence-transformers",
                    "local": True,
                    "gpu_recommended": "mpnet" in model_name,
                    "description": "Sentence Transformers embedding model",
                }
            )
        else:
            info.update(
                {
                    "type": "HuggingFace",
                    "organization": "huggingface",
                    "local": True,
                    "gpu_recommended": False,
                }
            )
    elif provider == "mistral":
        info.update(
            {
                "type": "Mistral AI",
                "organization": "mistralai",
                "local": False,
                "api_based": True,
                "description": "Mistral AI embedding model",
            }
        )

    return info


def get_models_by_organization() -> Dict[str, Dict[str, List[str]]]:
    """
    Get embedding models organized by their actual organizations/providers.

    Returns:
        Dictionary organized by provider -> organization -> list of models
    """
    models_by_org = {
        "huggingface": {
            "sentence-transformers": ["all-MiniLM-L6-v2", "all-mpnet-base-v2"],
            "BAAI": ["bge-small-en-v1.5", "bge-base-en-v1.5", "bge-large-en-v1.5"],
        },
        "mistral": {"mistralai": ["mistral-embed"]},
    }
    return models_by_org


def list_models_with_providers() -> Dict[str, Any]:
    """
    List all available models with detailed provider information.

    Returns:
        Dictionary with detailed model and provider information
    """
    result = {
        "summary": {
            "total_models": 0,
            "providers": list(EMBEDDING_MODELS.keys()),
            "organizations": [],
        },
        "models_by_provider": {},
        "models_by_organization": get_models_by_organization(),
    }

    # Count total models and get organizations
    organizations = set()
    for provider, models in EMBEDDING_MODELS.items():
        result["models_by_provider"][provider] = {}
        result["summary"]["total_models"] += len(models)

        for model_name in models.keys():
            model_info = get_model_info(provider, model_name)
            result["models_by_provider"][provider][model_name] = model_info
            if "organization" in model_info:
                organizations.add(model_info["organization"])

    result["summary"]["organizations"] = list(organizations)
    return result


# Backward compatibility
def get_embedding_model_legacy(
    model_name: str = "sentence-transformers/all-MiniLM-L6-v2",
):
    """Legacy function for backward compatibility."""
    return HuggingFaceEmbeddings(model_name=model_name)
