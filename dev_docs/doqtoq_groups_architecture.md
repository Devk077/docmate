# DoqToq Groups Architecture Analysis

*Created to document the planning phase of the DoqToq Groups feature.*

## 1. Goal
To transform DoqToq from a single-document conversation interface into a multi-document collaboration platform ("DoqToq Groups"), where multiple documents can be loaded simultaneously, interact with the user, and even interact with each other.

## 2. Current Architecture Profile
Currently, the system is designed heavily around a 1:1 relationship between a user and a single document.
- **`app/chat.py`**: Handles UI but assumes a single RAG chain (`st.session_state.qa_chain`). Standard Streamlit widgets update chat history linearly.
- **`app/uploader.py`**: Accepts files and initializes a single `DocumentRAG` object. (Only one active document at a time).
- **`backend/rag_engine.py`**: The `DocumentRAG` class encapsulates the vector store, retriever, LLM, and prompt chain for exactly one document.

## 3. Structural Needs for DoqToq Groups
To support groups, we need to introduce a "Multi-Agent" orchestrator.

### A. The Group Orchestrator (Backend)
We need a new `DoqToqGroupRAG` or `GroupOrchestrator` class that:
1. Manages a list of `DocumentRAG` instances.
2. When a user asks a question, the orchestrator must decide:
   - Does this question target ALL documents?
   - Does it target specific documents?
   - Do the documents need to debate or synthesize an answer?
3. It must formulate a synthesis prompt, passing the retrieved chunks from *all relevant documents* to the LLM to generate a unified multi-document answer, or trigger responses from each document sequentially.

### B. Group Context & Personality (Prompts)
- We need new system prompts. Instead of typical RAG ("You are this document..."), the prompt needs to be: "You are the orchestrator of a group discussion between Document A and Document B. Provide insights from both." 
- Alternatively, we generate separate responses from each document and display them in the UI as different speakers.

### C. Multi-File Upload & UI (Frontend)
- `app/uploader.py` must allow multiple files.
- `app/chat.py` must handle avatars for *multiple different documents*. Instead of just "User" and "Document", we might have "User", "Doc A", "Doc B", "System Synthesizer".

## 4. Remaining Questions & Decisions
To implement this smoothly, several UX and behavioral decisions must be clarified (see `implementation_plan.md` for the questions directed at the user).
