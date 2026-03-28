"""
DoqToq Groups — Vector DB Collection Naming Helpers

Every document in a Discussion Room gets its own isolated vector DB collection.
This module generates safe, deterministic collection names and provides
a helper to delete them when a document is removed from a room.

Naming convention:
    dtq_{room_id_short}_{filename_slug}
    e.g. dtq_a1b2c3d4_climate_report

Rules:
    - Lowercase only
    - Alphanumeric + underscores only (no hyphens — Qdrant dislikes them)
    - Max 64 chars total (Qdrant limit)
    - Always unique per (room_id, filename) pair
"""

__module_name__ = "vectorstore.naming"

import re
import logging
from typing import Optional

logger = logging.getLogger(__name__)


def make_collection_name(room_id: str, filename: str) -> str:
    """
    Generate a safe, deterministic vector DB collection name for a document.

    Args:
        room_id: UUID string of the room (e.g. "a1b2c3d4-e5f6-...")
        filename: Original uploaded filename (e.g. "Climate Report 2024.pdf")

    Returns:
        Safe collection name, e.g. "dtq_a1b2c3d4_climate_report_2024"

    Example:
        >>> make_collection_name("a1b2c3d4-e5f6-7890-abcd-ef1234567890", "Climate Report 2024.pdf")
        'dtq_a1b2c3d4_climate_report_2024'
    """
    # Take only the first 8 chars of the room UUID (enough to be unique per session)
    room_no_dash = room_id.replace("-", "").lower()
    room_short = room_no_dash[:8]

    # Strip file extension and slug-ify the filename
    name_without_ext = filename.rsplit(".", 1)[0] if "." in filename else filename
    slug = re.sub(r"[^a-z0-9]+", "_", name_without_ext.lower()).strip("_")

    # Build the collection name and trim to Qdrant's 64-char limit
    collection_name = f"dtq_{room_short}_{slug}"
    if len(collection_name) > 64:
        collection_name = collection_name[:64]

    # Ensure no trailing underscore after truncation
    collection_name = collection_name.rstrip("_")

    logger.info(
        f"{__module_name__} - Generated collection name '{collection_name}' "
        f"for room={room_id}, file={filename}"
    )
    return collection_name


def delete_collection(collection_name: str, provider: Optional[str] = None) -> bool:
    """
    Delete a vector DB collection by name. Called when a document is removed from a room.

    This function detects the active provider from the environment and deletes
    the collection from whichever DB is configured.

    Args:
        collection_name: The collection name to delete (e.g. "dtq_a1b2c3d4_climate_report")
        provider: Override the provider ("qdrant" or "chroma"). If None, reads from env.

    Returns:
        True if deleted successfully, False if collection didn't exist or error occurred.
    """
    import os
    active_provider = provider or os.getenv("VECTOR_DB_PROVIDER", "qdrant").lower()

    if active_provider == "qdrant":
        return _delete_qdrant_collection(collection_name)
    elif active_provider == "chroma":
        return _delete_chroma_collection(collection_name)
    else:
        logger.warning(f"{__module_name__} - Unknown provider '{active_provider}', cannot delete collection")
        return False


def _delete_qdrant_collection(collection_name: str) -> bool:
    """Delete a single Qdrant collection."""
    try:
        import os
        from qdrant_client import QdrantClient

        url = os.getenv("QDRANT_URL", "http://localhost:6333")
        api_key = os.getenv("QDRANT_API_KEY")

        client_kwargs = {"url": url}
        if api_key:
            client_kwargs["api_key"] = api_key

        client = QdrantClient(**client_kwargs)
        collections = client.get_collections()
        existing = [c.name for c in collections.collections]

        if collection_name not in existing:
            logger.info(f"{__module_name__} - Qdrant collection '{collection_name}' not found, nothing to delete")
            return False

        client.delete_collection(collection_name)
        logger.info(f"{__module_name__} - Deleted Qdrant collection: {collection_name}")
        return True

    except Exception as e:
        logger.error(f"{__module_name__} - Failed to delete Qdrant collection '{collection_name}': {e}")
        return False


def _delete_chroma_collection(collection_name: str) -> bool:
    """Delete a single ChromaDB collection."""
    try:
        import os
        import shutil

        persist_dir = os.getenv("CHROMA_PERSIST_DIR", "./data/vectorstore/chroma")
        collection_path = os.path.join(persist_dir, collection_name)

        if not os.path.exists(collection_path):
            logger.info(f"{__module_name__} - Chroma collection path '{collection_path}' not found, nothing to delete")
            return False

        shutil.rmtree(collection_path)
        logger.info(f"{__module_name__} - Deleted Chroma collection directory: {collection_path}")
        return True

    except Exception as e:
        logger.error(f"{__module_name__} - Failed to delete Chroma collection '{collection_name}': {e}")
        return False
