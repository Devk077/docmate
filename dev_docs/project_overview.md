# DoqToq Project Overview

## 1. What is this project?
DoqToq (Documents that Talk) is an AI-powered document platform that turns static files (PDFs, Markdown, text, JSON) into interactive conversational partners. Instead of just searching a document for text, this project gives the document a "personality" and allows you, the user, to chat with it. It acts as if the document itself is answering your questions in the first person. 

Technically, it's a **Retrieval-Augmented Generation (RAG)** application built with a **Streamlit** frontend and a **LangChain** backend, utilizing Vector Databases (like **Qdrant** or **ChromaDB**) to retrieve relevant information and Large Language Models (like **Google Gemini**, **Mistral**, or **Ollama**) to generate natural responses.

## 2. Core Purpose & Use Cases (Simple Terms)

### Purpose
To make reading and extracting information from long or complex documents as easy as having a chat with an intelligent assistant who has memorized the entire text.

### Use Cases
- **Students & Researchers**: Quickly understand lengthy academic papers or textbooks without reading them cover-to-cover. You can simply ask, "What is your main conclusion?"
- **Professionals & Lawyers**: Scan through long legal contracts, financial reports, or technical manuals by asking specific questions like "What are the termination clauses mentioned in you?"
- **Content Creators**: Interact with their own notes or scripts to brainstorm or summarize ideas.
- **HR and Onboarding**: Allow new employees to ask questions directly to the company handbook or policy documents.

## 3. Core Feature List
- **Universal Document Support**: Accept various file formats including PDF, TXT, JSON, and Markdown.
- **Document Empathy/Personality**: AI responses are framed as if the document is speaking directly to the user (e.g., "Within my contents, I discuss...").
- **Multi-LLM Support**: Easily switch between different AI models like Google Gemini, Mistral AI, or local models via Ollama.
- **Flexible Vector Databases**: Supports both ChromaDB and Qdrant for storing document embeddings and performing similarities searches.
- **Real-Time Streaming**: Responses appear word-by-word giving an interactive, natural feel. Configurable to be instant, word-by-word, or character-by-character.
- **Smart Retrieval & Citations**: Identifies and points out exactly how relevant the retrieved chunk of text is (High/Medium/Low relevance).
- **Built-in Safety**: Includes safeguards against prompt injection and answers strictly based on the document's content (handles off-topic queries gracefully).
- **Session Memory**: Remembers past interactions in the same conversation to provide continuous context.

## 4. Codebase Structure
- **`app/`**: Contains the Streamlit frontend.
  - `main.py`: Entry point for the UI.
  - `chat.py`, `sidebar.py`, `uploader.py`, `streaming_queue.py`: UI components managing different interactive sections.
- **`backend/`**: Contains the core LLM logic, LangChain wrappers, and RAG systems.
  - `rag_engine.py`: Orchestrator of the RAG pipeline.
  - `embedder.py`, `chunker.py`, `llm_wrapper.py`, `retriever.py`: Modular components for AI processing.
  - `prompts/`: Contains engineered prompts that give the application its specific persona and safety features.
  - `vectorstore/`: Abstractions mapping standard API interfaces to Qdrant or ChromaDB databases.
- **`data/`**: Designated for document uploads, sample documents, and local vector database storage (if not using cloud DBs).
- **`docs/`**: A rich documentation directory including philosophy, API specs, and a deployment guide.
- **`alternatives/`**: Experimental features like multi-threaded streaming queues.
- **`utils/`**: Helper methods like suppressed warnings and loggers.

## 5. Adding New Features
The repository is highly modular. Adding new features typically involves:
1. **Frontend additions**: Modifying Streamlit scripts in `app/`.
2. **Backend additions**: Updating LLM handling in `backend/` or prompts in `backend/prompts/`.
3. **Database integrations**: Editing logic inside `backend/vectorstore/`.
