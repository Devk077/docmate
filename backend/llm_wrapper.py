__module_name__ = "llm_wrapper"

import os
from typing import Any, Dict, Iterator, List, Optional

import ollama
from dotenv import load_dotenv
from langchain_core.callbacks.manager import CallbackManagerForLLMRun
from langchain_core.language_models.chat_models import BaseChatModel
from langchain_core.messages import AIMessage, BaseMessage, HumanMessage, SystemMessage
from langchain_core.outputs import ChatGeneration, ChatResult
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_mistralai.chat_models import ChatMistralAI
from langchain_ollama import ChatOllama

load_dotenv()

GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY")
MISTRAL_API_KEY = os.getenv("MISTRAL_API_KEY")


def get_google_chat_model(
    model_name: str = "gemini-2.5-flash",
    temperature: float = 0.7,
    streaming: bool = False,
) -> ChatGoogleGenerativeAI:
    """
    Returns a Gemini chat model using the Google Generative AI API.
    """
    if not GOOGLE_API_KEY:
        raise ValueError("GOOGLE_API_KEY not found. Check your .env file.")
    try:
        return ChatGoogleGenerativeAI(
            model=model_name,
            google_api_key=GOOGLE_API_KEY,
            temperature=temperature,
            top_p=1.0,
            disable_streaming=not streaming,  # Use disable_streaming instead of streaming
        )
    except Exception as e:
        raise ValueError(f"Failed to initialize Google chat model: {str(e)}")


def get_mistral_chat_model(
    model_name: str = "mistral-medium",
    temperature: float = 0.7,
    streaming: bool = False,
) -> ChatMistralAI:
    """
    Returns a Mistral chat model using the Mistral API.
    Valid model names: mistral-tiny, mistral-small, mistral-medium
    """
    if not MISTRAL_API_KEY:
        raise ValueError("MISTRAL_API_KEY not found. Check your .env file.")
    try:
        return ChatMistralAI(
            model=model_name,
            api_key=MISTRAL_API_KEY,
            temperature=temperature,
            top_p=1.0,
            streaming=streaming,
        )
    except Exception as e:
        raise ValueError(f"Failed to initialize Mistral chat model: {str(e)}")


def get_ollama_chat_model(
    model_name: str = "mistral:latest", temperature: float = 0.7, streaming: bool = True
) -> ChatOllama:
    """
    Returns an Ollama chat model using the Ollama API.

    Args:
        model_name: The Ollama model to use. Common options:
                   - mistral:latest (default, 7B parameters)
                   - gemma3:1b (faster, 1B parameters)
                   - deepseek-r1:1.5b (alternative, 1.5B parameters)
                   - llama3:8b (if available)
        temperature: Sampling temperature (0.0 to 1.0)
        streaming: Whether to enable streaming responses

    Returns:
        ChatOllama instance ready for use

    Raises:
        ValueError: If model initialization fails
    """
    print(f"Using Ollama model: {model_name}")
    try:
        return ChatOllama(
            model=model_name,
            temperature=temperature,
            streaming=streaming,
        )
    except Exception as e:
        raise ValueError(f"Failed to initialize Ollama chat model: {str(e)}")
