"""
DoqToq Groups — Web Search Tool

Silent background tool that documents can invoke mid-stream by emitting a
special token in their response. The Orchestrator intercepts this token,
runs the search, injects the result, and continues streaming.

Token format (the document emits this in its streamed response):
    [WEB_SEARCH_REQUEST: <query text here>]

The Orchestrator scans each incoming chunk for this token.
If found: it strips the token from the visible response, runs the search,
and appends the result as a system injection for the next LLM turn.
"""

__module_name__ = "web_search_tool"

import logging
import os
import re
from typing import Optional, Tuple

logger = logging.getLogger(__name__)

# Token pattern the document LLM emits to request a search
_SEARCH_REQUEST_PATTERN = re.compile(
    r"\[WEB_SEARCH_REQUEST:\s*(.+?)\]",
    re.IGNORECASE | re.DOTALL,
)


# ──────────────────────────────────────────────────────────────
# Search
# ──────────────────────────────────────────────────────────────

def run_search(query: str, max_results: int = 3) -> str:
    """
    Run a DuckDuckGo web search and return a formatted result string.

    Args:
        query: The search query string.
        max_results: Number of results to include in the response.

    Returns:
        Formatted string of search results, or an error message if search fails.
    """
    try:
        from langchain_community.tools import DuckDuckGoSearchRun
        search = DuckDuckGoSearchRun()
        results = search.run(query)
        logger.info(f"{__module_name__} - Web search completed for: '{query}'")
        return results

    except ImportError:
        logger.error(
            f"{__module_name__} - langchain_community not installed. "
            "Run: pip install langchain-community duckduckgo-search"
        )
        return "[Search unavailable: langchain-community not installed]"

    except Exception as e:
        logger.error(f"{__module_name__} - Search failed for '{query}': {e}")
        return f"[Search failed: {str(e)}]"


# ──────────────────────────────────────────────────────────────
# Token Interception
# ──────────────────────────────────────────────────────────────

def intercept_search_request(accumulated_text: str) -> Tuple[bool, str, Optional[str]]:
    """
    Check accumulated streamed text for a [WEB_SEARCH_REQUEST: ...] token.

    Call this after each streamed chunk on the running accumulated_text.
    When a match is found, strip the token from the text (so the user
    never sees it) and return the extracted query.

    Args:
        accumulated_text: The full text accumulated so far in the stream.

    Returns:
        Tuple of (found: bool, cleaned_text: str, query: Optional[str])
        - found: True if a search token was detected
        - cleaned_text: Text with the token removed (ready for display)
        - query: The extracted search query, or None if not found
    """
    match = _SEARCH_REQUEST_PATTERN.search(accumulated_text)
    if not match:
        return False, accumulated_text, None

    query = match.group(1).strip()
    cleaned_text = _SEARCH_REQUEST_PATTERN.sub("", accumulated_text).strip()
    logger.info(f"{__module_name__} - Intercepted search request: '{query}'")
    return True, cleaned_text, query


def format_search_result_for_injection(query: str, result: str) -> str:
    """
    Format a search result as a system message to inject into the document's
    next prompt turn so it can incorporate the fresh information.

    Args:
        query: The original search query.
        result: The raw result text from the search.

    Returns:
        A formatted string ready to be appended to the document's context.
    """
    return (
        f"\n\n[BACKGROUND WEB SEARCH RESULT]\n"
        f"Query: {query}\n"
        f"Result: {result}\n"
        f"Use this information to supplement your answer where relevant. "
        f"Do not reveal that you performed a web search — present it naturally as knowledge.\n"
        f"[END WEB SEARCH RESULT]\n"
    )
