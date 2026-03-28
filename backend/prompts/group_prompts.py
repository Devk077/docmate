"""
DoqToq Groups — Group-Aware Prompt Functions

Provides prompt templates and utility functions specific to Discussion Rooms:
  - generate_persona_name()        → AI-generated friendly document name
  - load_group_system_prompt()     → per-doc system prompt with room awareness
  - load_group_chat_template()     → LangChain ChatPromptTemplate for group mode
  - load_contribution_check_prompt() → fast yes/no gate (alternative to vector gate)
  - load_compaction_prompt()       → prompt for compressing conversation history
"""

__module_name__ = "prompts.group_prompts"

import logging
import os
from pathlib import Path
from typing import List, Optional

from langchain_core.prompts import ChatPromptTemplate

logger = logging.getLogger(__name__)

# Path to the raw group system prompt markdown
_PROMPT_DIR = Path(__file__).parent
_GROUP_SYSTEM_PROMPT_PATH = _PROMPT_DIR / "group_system_prompt.md"


# ──────────────────────────────────────────────────────────────
# Persona Name Generation
# ──────────────────────────────────────────────────────────────

def generate_persona_name(
    file_path: str,
    model_provider: str = "google",
    model_name: Optional[str] = None,
) -> str:
    """
    Generate a short, friendly persona name for a document using the LLM.

    Reads the first 600 characters of the document text and asks the LLM
    to produce a concise name like "The Climate Report" or "Smith's ML Paper".

    Args:
        file_path: Absolute path to the uploaded document.
        model_provider: 'google', 'mistral', or 'ollama'.
        model_name: Specific model name override, or None for provider default.

    Returns:
        A short persona name string (3–6 words, title-cased).
        Falls back to the filename stem if LLM call fails.
    """
    # Extract document preview text
    preview = _extract_preview(file_path, max_chars=600)
    filename_stem = Path(file_path).stem.replace("_", " ").replace("-", " ").title()

    if not preview:
        logger.warning(f"{__module_name__} - Could not extract preview from '{file_path}', using filename")
        return filename_stem

    persona_prompt = (
        "You will be given the opening text of a document. "
        "Your task is to generate a short, friendly, memorable name for this document "
        "that will be used as its persona in a multi-document discussion room.\n\n"
        "Rules:\n"
        "- 2 to 5 words maximum\n"
        "- Title Case (e.g. 'The Climate Report', 'Smith's ML Paper', 'Q3 Earnings Brief')\n"
        "- Reflects the document's actual topic or nature\n"
        "- No quotes, no punctuation at the end\n"
        "- Be creative but accurate\n\n"
        f"Document opening text:\n{preview}\n\n"
        "Persona name (just the name, nothing else):"
    )

    try:
        llm = _get_llm(model_provider, model_name, temperature=0.3, streaming=False)
        from langchain_core.messages import HumanMessage
        response = llm.invoke([HumanMessage(content=persona_prompt)])
        raw = response.content if hasattr(response, "content") else str(response)
        name = raw.strip().strip('"').strip("'").strip()

        # Safety: if response is too long or empty, fall back to filename
        if not name or len(name) > 60:
            logger.warning(
                f"{__module_name__} - LLM returned invalid persona name: '{name}', "
                f"using filename fallback"
            )
            return filename_stem

        logger.info(f"{__module_name__} - Generated persona name: '{name}' for '{file_path}'")
        return name

    except Exception as e:
        logger.error(f"{__module_name__} - Persona name generation failed: {e}")
        return filename_stem


def _extract_preview(file_path: str, max_chars: int = 600) -> str:
    """
    Extract the first `max_chars` characters of readable text from a document.
    Supports PDF, TXT, and MD files.
    """
    ext = Path(file_path).suffix.lower()

    try:
        if ext == ".pdf":
            try:
                import pdfplumber
                with pdfplumber.open(file_path) as pdf:
                    text = ""
                    for page in pdf.pages:
                        text += page.extract_text() or ""
                        if len(text) >= max_chars:
                            break
                    return text[:max_chars].strip()
            except ImportError:
                # Fallback to pypdf
                from pypdf import PdfReader
                reader = PdfReader(file_path)
                text = ""
                for page in reader.pages:
                    text += page.extract_text() or ""
                    if len(text) >= max_chars:
                        break
                return text[:max_chars].strip()

        elif ext in (".txt", ".md", ".rst", ".csv"):
            with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
                return f.read(max_chars).strip()

        elif ext in (".docx",):
            from docx import Document as DocxDocument
            doc = DocxDocument(file_path)
            text = " ".join(p.text for p in doc.paragraphs)
            return text[:max_chars].strip()

        else:
            logger.warning(f"{__module_name__} - Unsupported file type for preview: {ext}")
            return ""

    except Exception as e:
        logger.error(f"{__module_name__} - Failed to extract preview from '{file_path}': {e}")
        return ""


# ──────────────────────────────────────────────────────────────
# Group System Prompt
# ──────────────────────────────────────────────────────────────

def load_group_system_prompt(
    persona_name: str,
    all_personas: List[str],
    conversation_context: str = "",
) -> str:
    """
    Load and fill the group system prompt template for a specific document.

    Args:
        persona_name: This document's persona name (e.g. "The Climate Report").
        all_personas: List of ALL persona names in the room (including this doc's own name).
        conversation_context: The output of GroupOrchestrator._build_group_context() —
                               a combined summary + recent messages string.

    Returns:
        Fully formatted system prompt string ready to pass to the LLM.
    """
    try:
        raw = _GROUP_SYSTEM_PROMPT_PATH.read_text(encoding="utf-8")
    except FileNotFoundError:
        logger.error(f"{__module_name__} - group_system_prompt.md not found at {_GROUP_SYSTEM_PROMPT_PATH}")
        raw = _fallback_system_prompt()

    # Build peer list (all docs except this one)
    peers = [p for p in all_personas if p.lower() != persona_name.lower()]
    peer_list = ", ".join(peers) if peers else "none yet"
    example_peer = peers[0] if peers else "another document"
    peer_count = len(peers)

    filled = (
        raw
        .replace("{persona_name}", persona_name)
        .replace("{peer_list}", peer_list)
        .replace("{example_peer}", example_peer)
        .replace("{peer_count}", str(peer_count))
        .replace("{conversation_context}", conversation_context or "No prior conversation yet.")
    )
    return filled


def load_group_chat_template(
    persona_name: str,
    all_personas: List[str],
    conversation_context: str = "",
) -> ChatPromptTemplate:
    """
    Build a LangChain ChatPromptTemplate for a document in group mode.

    This template uses the group system prompt and is structured to accept
    the same variables as the existing single-doc prompt_templates.py
    (similarity_score, context, question, etc.) for maximum compatibility.

    Args:
        persona_name: This document's persona name.
        all_personas: All persona names in the room.
        conversation_context: Shared conversation history string.

    Returns:
        ChatPromptTemplate ready for use in a LangChain LCEL chain.
    """
    system_prompt = load_group_system_prompt(
        persona_name=persona_name,
        all_personas=all_personas,
        conversation_context=conversation_context,
    )

    return ChatPromptTemplate.from_messages([
        ("system", system_prompt),
        (
            "human",
            """## My Document Context
- **Similarity Score**: {similarity_score} (0.0 = perfect match, 1.0+ = likely off-topic for me)
- **Average Similarity**: {avg_similarity}
- **Retrieved from My Content**: {context}

## Safety Assessment
{safety_context}

## Relevance Assessment
{relevance_context}

## What Other Documents Have Said This Round
{previous_answers}

## User Question
{question}

## Instructions
Respond as {persona_name}, drawing from your own content. If this question is more relevant to a peer document, you may acknowledge that briefly — but still contribute your perspective. Stay in character at all times.""".replace("{persona_name}", persona_name),
        ),
    ])


# ──────────────────────────────────────────────────────────────
# Contribution Check Prompt (optional fast gate)
# ──────────────────────────────────────────────────────────────

def load_contribution_check_prompt() -> ChatPromptTemplate:
    """
    A fast yes/no prompt to ask a document whether it should speak this round.

    This is an optional ALTERNATIVE to the vector similarity gate — it uses
    the LLM's language understanding instead of pure cosine distance.
    More accurate for nuanced questions, but adds latency (~200ms per doc).

    Recommended use: Replace vector gate only in rooms with ≤3 documents.

    Returns:
        ChatPromptTemplate expecting {context} and {question} variables.
    """
    return ChatPromptTemplate.from_messages([
        (
            "system",
            "You are determining whether a document's content is relevant to a user's question. "
            "Answer ONLY with 'YES' or 'NO'. No explanation needed."
        ),
        (
            "human",
            """Document content excerpt:
{context}

User question: {question}

Is this document's content relevant to answering this question?
Answer YES or NO:"""
        ),
    ])


# ──────────────────────────────────────────────────────────────
# Compaction Prompt
# ──────────────────────────────────────────────────────────────

def load_compaction_prompt() -> ChatPromptTemplate:
    """
    Prompt for compressing a batch of multi-document conversation messages
    into a concise summary milestone stored in PostgreSQL.

    The summary must preserve:
    - Key insights from each document
    - User questions that drove the conversation
    - Decisions or conclusions reached
    - Document names (so context doesn't lose attribution)

    Returns:
        ChatPromptTemplate expecting a {conversation} variable.
    """
    return ChatPromptTemplate.from_messages([
        (
            "system",
            "You are summarizing a multi-document AI discussion for memory compaction. "
            "Your summary will be used as context for future conversation turns. "
            "Be concise but complete — preserve all key points, attributed to each document."
        ),
        (
            "human",
            """Summarize the following conversation into a dense, structured paragraph.
Preserve:
- What each document contributed (use their names)
- Key facts, insights, or conclusions reached
- Open questions or threads the user left for later

Conversation to summarize:
{conversation}

Summary (1-3 paragraphs maximum):"""
        ),
    ])


# ──────────────────────────────────────────────────────────────
# Internal helpers
# ──────────────────────────────────────────────────────────────

def _get_llm(
    model_provider: str,
    model_name: Optional[str],
    temperature: float = 0.3,
    streaming: bool = False,
):
    """Get the LLM instance based on provider."""
    from backend.llm_wrapper import (
        get_google_chat_model,
        get_mistral_chat_model,
        get_ollama_chat_model,
    )

    if model_provider == "google":
        return get_google_chat_model(
            model_name=model_name or "gemini-2.5-flash",
            temperature=temperature,
            streaming=streaming,
        )
    elif model_provider == "mistral":
        return get_mistral_chat_model(
            model_name=model_name or "mistral-medium",
            temperature=temperature,
            streaming=streaming,
        )
    else:
        return get_ollama_chat_model(
            model_name=model_name or "mistral:latest",
            temperature=temperature,
            streaming=streaming,
        )


def _fallback_system_prompt() -> str:
    """Minimal fallback if the .md file is missing."""
    return (
        "You are {persona_name}, a document brought to life in a DoqToq Discussion Room. "
        "Your peers are: {peer_list}. "
        "Respond in first person, drawing from your own content. "
        "Shared conversation so far:\n{conversation_context}"
    )
