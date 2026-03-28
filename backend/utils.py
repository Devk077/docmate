__module_name__ = "utils"

import os
import re


def is_query_off_topic(retrieved_docs: list, threshold: int = 0) -> bool:
    return len(retrieved_docs) <= threshold


def clean_text(text: str) -> str:
    return text.strip().replace("\n", " ")


def load_system_prompt(filepath=None):
    """Load from prompts/system_prompt.md"""
    if filepath is None:
        filepath = os.path.join(
            os.path.dirname(__file__), "prompts", "system_prompt.md"
        )

    try:
        with open(filepath, "r", encoding="utf-8") as file:
            return file.read().strip()
    except FileNotFoundError:
        return "You are a helpful AI assistant that represents a document. Respond in first person as if you are the document itself."


def load_off_topic_prompt(filepath=None):
    """Load from prompts/off_topic_prompt.md"""
    if filepath is None:
        filepath = os.path.join(
            os.path.dirname(__file__), "prompts", "off_topic_prompt.md"
        )

    try:
        with open(filepath, "r", encoding="utf-8") as file:
            return file.read().strip()
    except FileNotFoundError:
        return "I'm afraid I don't know much about that. I only contain information related to my specific content."


def load_prompt_injection_response(filepath=None):
    """Load from prompts/prompt_injection_response.md"""
    if filepath is None:
        filepath = os.path.join(
            os.path.dirname(__file__), "prompts", "prompt_injection_response.md"
        )

    try:
        with open(filepath, "r", encoding="utf-8") as file:
            return file.read().strip()
    except FileNotFoundError:
        return "I'm here to help you understand my content. Please ask me questions about what I contain."


def is_potential_prompt_injection(query: str) -> bool:
    """
    Detects common prompt injection patterns in user input.
    """
    injection_patterns = [
        r"(ignore|disregard)\s+(all\s+|the\s+)?(above|previous)\s+(instructions|prompt)",
        r"pretend\s+to\s+be",
        r"you\s+are\s+now\s+",
        r"act\s+as\s+",
        r"forget\s+(all\s+|everything\s+)?(previous\s+)?(instructions|and tell me)",
        r"repeat\s+after\s+me",
        r"shutdown|reset|override|bypass",
        r"i'm testing for prompt injection",
        r"as an ai language model",
        r"system:\s*change",
        r"(ignore|disregard)\s+previous",
        r"you\s+are\s+now\s+(a\s+)?different",
    ]

    for pattern in injection_patterns:
        if re.search(pattern, query, re.IGNORECASE):
            return True
    return False
