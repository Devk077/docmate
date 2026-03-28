__module_name__ = "retriever"

from langchain_chroma import Chroma

try:
    from langchain_core.vectorstores.base import VectorStoreRetriever
except ImportError:  # Backward compatibility for older LangChain releases
    from langchain.vectorstores.base import VectorStoreRetriever


def get_basic_retriever(vectorstore: Chroma, k: int = 4) -> VectorStoreRetriever:
    """
    Returns a retriever using similarity search.
    """
    return vectorstore.as_retriever(search_type="similarity", search_kwargs={"k": k})


def get_metadata_filtered_retriever(
    vectorstore: Chroma, filter_key: str, filter_value: str, k: int = 4
):
    """
    Returns a retriever that filters chunks based on metadata (e.g., filename, section).
    """
    return vectorstore.as_retriever(
        search_type="similarity",
        search_kwargs={"k": k, "filter": {filter_key: filter_value}},
    )
