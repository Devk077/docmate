"""
DoqToq Groups — Group Orchestrator

Manages a pool of DocumentRAG instances for a single Discussion Room.
Responsible for:
  - Loading/restoring documents from PostgreSQL on room open
  - Vector similarity gating (decides which docs speak)
  - @mention parsing (routes to a single named doc)
  - Sequential streaming across multiple speaking docs
  - Incremental context compaction (rolling summary in PostgreSQL)
  - Silent web search interception mid-stream

Usage in single-doc rooms (1 doc):
    orchestrator.run_round(question, session_id)
    → behaves like the original DocumentRAG.query_stream()

Usage in multi-doc rooms:
    orchestrator.run_round(question, session_id)
    → yields chunks from each qualifying doc sequentially
"""

__module_name__ = "group_rag_engine"

import logging
import os
import re
from dataclasses import dataclass, field
from typing import Any, Dict, Iterator, List, Optional

from backend.db.postgres import (
    get_documents_in_room,
    get_latest_summary,
    get_session_messages,
    get_turn_count,
    log_web_search,
    save_context_summary,
    save_message,
)
from backend.prompts.group_prompts import (
    generate_persona_name,
    load_group_system_prompt,
)
from backend.rag_engine import DocumentRAG, ModelProvider
from backend.vectorstore.naming import make_collection_name
from backend.web_search_tool import (
    format_search_result_for_injection,
    intercept_search_request,
    run_search,
)

logger = logging.getLogger(__name__)

# ──────────────────────────────────────────────────────────────
# Configuration (from environment, with sensible defaults)
# ──────────────────────────────────────────────────────────────

GROUP_SIMILARITY_THRESHOLD = float(os.getenv("GROUP_SIMILARITY_THRESHOLD", "0.65"))
GROUP_DOC_COMPACTION_N = int(os.getenv("GROUP_DOC_COMPACTION_N", "10"))
GROUP_DIMINISHING_RETURNS_SIM = float(os.getenv("GROUP_DIMINISHING_RETURNS_SIM", "0.92"))
GROUP_MAX_ROOM_DOCS = int(os.getenv("GROUP_MAX_ROOM_DOCS", "10"))


# ──────────────────────────────────────────────────────────────
# Internal data class representing one document in the room
# ──────────────────────────────────────────────────────────────

@dataclass
class RoomDocument:
    """Wrapper holding a DocumentRAG instance alongside its room metadata."""
    document_id: str          # PostgreSQL UUID
    persona_name: str         # e.g. "The Climate Report"
    collection_name: str      # e.g. "dtq_a1b2c3d4_climate_report"
    file_path: str
    rag: DocumentRAG          # the live RAG instance
    spent: bool = False       # True if diminishing returns detected this round


# ──────────────────────────────────────────────────────────────
# GroupOrchestrator
# ──────────────────────────────────────────────────────────────

class GroupOrchestrator:
    """
    Orchestrates multi-document conversations inside a Discussion Room.

    One orchestrator instance is created per active room and stored in
    Streamlit session state for the duration of the session.
    """

    def __init__(
        self,
        room_id: str,
        model_provider: ModelProvider = "google",
        model_name: Optional[str] = None,
        temperature: float = 0.7,
        top_k: int = 4,
        embedding_provider: str = "huggingface",
        embedding_model: str = "all-MiniLM-L6-v2",
        streaming: bool = True,
    ):
        self.room_id = room_id
        self.model_provider = model_provider
        self.model_name = model_name
        self.temperature = temperature
        self.top_k = top_k
        self.embedding_provider = embedding_provider
        self.embedding_model = embedding_model
        self.streaming = streaming

        # {document_id: RoomDocument}
        self._docs: Dict[str, RoomDocument] = {}

        # Quick lookup: persona_name (lowercase) → document_id
        self._persona_index: Dict[str, str] = {}

        logger.info(f"{__module_name__} - Orchestrator created for room: {room_id}")

    # ──────────────────────────────────────────────────────────
    # Document Management
    # ──────────────────────────────────────────────────────────

    def load_room_documents(self) -> None:
        """
        Load all documents registered to this room from PostgreSQL and
        instantiate a DocumentRAG for each one (skip_indexing=True for speed).
        """
        logger.info(f"{__module_name__} - load_room_documents() START for room {self.room_id}")
        db_docs = get_documents_in_room(self.room_id)
        if not db_docs:
            logger.info(f"{__module_name__} - Room {self.room_id} has no documents yet")
            return

        logger.info(f"{__module_name__} - Found {len(db_docs)} document(s) in DB")
        for idx, doc_row in enumerate(db_docs):
            persona_name = doc_row.get('persona_name', 'unknown')
            file_path = doc_row.get("file_path", "")
            logger.info(
                f"{__module_name__} - load_room_documents() [{idx+1}/{len(db_docs)}] "
                f"persona='{persona_name}', file='{file_path}'"
            )
            if not file_path or not os.path.exists(file_path):
                logger.warning(
                    f"{__module_name__} - Skipping '{persona_name}': "
                    f"file not found at '{file_path}'"
                )
                continue

            self._create_rag_for_doc(
                document_id=str(doc_row["id"]),
                persona_name=persona_name,
                collection_name=doc_row["qdrant_collection"],
                file_path=file_path,
                clear_existing=False,
            )
            logger.info(f"{__module_name__} - [OK] Restored '{persona_name}'")

        logger.info(
            f"{__module_name__} - load_room_documents() DONE: "
            f"{len(self._docs)} doc(s) loaded for room {self.room_id}"
        )

    def add_document(
        self,
        document_id: str,
        persona_name: str,
        collection_name: str,
        file_path: str,
    ) -> RoomDocument:
        """
        Add a newly uploaded document to the orchestrator at runtime.
        This creates the vector collection and indexes the document content.

        Args:
            document_id: PostgreSQL UUID string for the document.
            persona_name: AI-generated friendly name (e.g. "The Climate Report").
            collection_name: Pre-computed collection name from make_collection_name().
            file_path: Absolute path to the uploaded file on disk.

        Returns:
            The created RoomDocument wrapper.

        Raises:
            ValueError: If room is at capacity.
        """
        if len(self._docs) >= GROUP_MAX_ROOM_DOCS:
            raise ValueError(
                f"Room is at capacity ({GROUP_MAX_ROOM_DOCS} documents max). "
                "Remove a document before adding a new one."
            )

        return self._create_rag_for_doc(
            document_id=document_id,
            persona_name=persona_name,
            collection_name=collection_name,
            file_path=file_path,
            clear_existing=True,  # Fresh document — build the collection
        )

    def remove_document(self, document_id: str) -> None:
        """
        Remove a document from the active orchestrator (in-memory only).
        The caller is responsible for deleting the DB row and vector collection.
        """
        if document_id in self._docs:
            doc = self._docs.pop(document_id)
            # Remove from persona index
            self._persona_index = {
                k: v for k, v in self._persona_index.items() if v != document_id
            }
            logger.info(
                f"{__module_name__} - Removed document '{doc.persona_name}' from orchestrator"
            )

    def _create_rag_for_doc(
        self,
        document_id: str,
        persona_name: str,
        collection_name: str,
        file_path: str,
        clear_existing: bool,
    ) -> RoomDocument:
        """Internal: Create a DocumentRAG and register it."""
        mode = "FULL INDEX" if clear_existing else "RESTORE (skip_indexing)"
        logger.info(
            f"{__module_name__} - _create_rag_for_doc() [{mode}] "
            f"persona='{persona_name}', collection={collection_name}"
        )

        if clear_existing:
            # New document — full indexing pipeline
            rag = DocumentRAG(
                file_path=file_path,
                model_provider=self.model_provider,
                model_name=self.model_name,
                temperature=self.temperature,
                top_k=self.top_k,
                embedding_provider=self.embedding_provider,
                embedding_model=self.embedding_model,
                streaming=self.streaming,
                collection_name=collection_name,
                skip_indexing=False,  # chunk + embed + build collection
            )
        else:
            # Restoring existing document — skip re-indexing, attach to existing collection
            from backend.embedder import get_embedding_model
            from backend.vectorstore import get_vector_database

            rag = DocumentRAG(
                file_path=file_path,
                model_provider=self.model_provider,
                model_name=self.model_name,
                temperature=self.temperature,
                top_k=self.top_k,
                embedding_provider=self.embedding_provider,
                embedding_model=self.embedding_model,
                streaming=self.streaming,
                collection_name=collection_name,
                skip_indexing=True,
            )

            logger.info(f"{__module_name__} - Restore: loading embedding model...")
            embedding_model_obj = get_embedding_model(
                provider=self.embedding_provider, model_name=self.embedding_model
            )
            logger.info(f"{__module_name__} - Restore: embedding model ready, connecting to Qdrant collection '{collection_name}'...")

            try:
                rag.vector_db = get_vector_database(
                    embedding_model_obj,
                    clear_existing=False,
                    collection_name=collection_name,
                )
                logger.info(f"{__module_name__} - Restore: Qdrant connected, setting up retriever...")
                rag.retriever = rag.vector_db.get_retriever(k=self.top_k)
            except Exception as e:
                logger.error(f"{__module_name__} - Restore: Qdrant connection FAILED for '{collection_name}': {e}")
                raise RuntimeError(
                    f"Could not reconnect to vector store for '{persona_name}'. "
                    f"The collection '{collection_name}' may be missing. "
                    f"Try deleting and re-creating this room. Error: {e}"
                )

            logger.info(f"{__module_name__} - Restore: setting up LLM...")
            rag._setup_llm()
            logger.info(f"{__module_name__} - Restore: setting up RAG chain...")
            rag._setup_rag_chain()
            logger.info(f"{__module_name__} - Restore: '{persona_name}' fully ready")

        room_doc = RoomDocument(
            document_id=document_id,
            persona_name=persona_name,
            collection_name=collection_name,
            file_path=file_path,
            rag=rag,
        )
        self._docs[document_id] = room_doc
        self._persona_index[persona_name.lower()] = document_id

        logger.info(
            f"{__module_name__} - Registered '{persona_name}' "
            f"(collection={collection_name}) in room {self.room_id}"
        )
        return room_doc

    # ──────────────────────────────────────────────────────────
    # Routing
    # ──────────────────────────────────────────────────────────

    def parse_mention(self, message: str) -> Optional[RoomDocument]:
        """
        Check if the user's message contains @PersonaName and, if so,
        return the corresponding RoomDocument — bypassing the vector gate.

        Handles multi-word persona names such as "Dev's Tech Resume" anywhere in the
        text, and normalizes smart quotes to prevent matching failures.
        Partial prefix matches are supported (e.g. "@Dev" matches "Dev's Tech Resume").
        """
        msg_norm = message.replace('’', "'").lower()

        ranked = sorted(self._persona_index.keys(), key=len, reverse=True)
        
        # 1. Try exact matches: @Full Persona Name anywhere in the message
        for persona_lower in ranked:
            p_norm = persona_lower.replace('’', "'").lower()
            if f"@{p_norm}" in msg_norm:
                doc_id = self._persona_index[persona_lower]
                doc = self._docs.get(doc_id)
                logger.info(
                    f"{__module_name__} - @mention resolved to: '{doc.persona_name if doc else '?'}'"
                )
                return doc

        # 2. Fallback: match first word after @ against any substring in persona names
        # Extract all @words from the message. Using \\w+ captures letters/numbers without punctuation.
        # This gracefully handles "@Aditya's" -> "aditya"
        matches = re.finditer(r"@([\w\-]+)", msg_norm)
        for match in matches:
            fw = match.group(1)
            # Ignore tiny matches
            if len(fw) < 3:
                continue
            for persona_lower, doc_id in self._persona_index.items():
                p_norm = persona_lower.replace('’', "'").lower()
                if fw in p_norm:
                    doc = self._docs.get(doc_id)
                    logger.info(
                        f"{__module_name__} - @mention partial match '{fw}' → '{doc.persona_name if doc else '?'}'"
                    )
                    return doc

        logger.warning(
            f"{__module_name__} - @mention in message could not be resolved. "
            f"Persona index: {list(self._persona_index.keys())}"
        )
        return None

    def get_autocomplete_names(self) -> List[str]:
        """
        Return all persona names in this room for @mention autocomplete.

        Returns:
            List of persona name strings (original casing).
        """
        return [doc.persona_name for doc in self._docs.values()]

    def route(self, question: str) -> List[RoomDocument]:
        """
        Run the vector similarity gate for each document and return an
        ordered list of documents that should speak this round.

        A document qualifies if its best similarity score for the question
        is below GROUP_SIMILARITY_THRESHOLD (lower distance = more relevant).

        Documents are ordered ascending by score (most relevant first).

        Args:
            question: The user's message text.

        Returns:
            Ordered list of qualifying RoomDocument instances.
            Empty list if no document clears the threshold.
        """
        if not self._docs:
            return []

        scored: List[tuple] = []  # (score, RoomDocument)

        for doc in self._docs.values():
            if doc.spent:
                continue
            try:
                results = doc.rag.vector_db.similarity_search_with_score(question, k=1)
                if results:
                    _, score = results[0]
                    logger.info(
                        f"{__module_name__} - Gate: '{doc.persona_name}' "
                        f"score={score:.3f} threshold={GROUP_SIMILARITY_THRESHOLD}"
                    )
                    if score <= GROUP_SIMILARITY_THRESHOLD:
                        scored.append((score, doc))
            except Exception as e:
                logger.warning(
                    f"{__module_name__} - Gate check failed for '{doc.persona_name}': {e}"
                )

        # Sort by score ascending (most relevant first)
        scored.sort(key=lambda x: x[0])
        qualifying = [doc for _, doc in scored]

        if not qualifying and self._docs:
            # Fallback: at least one doc responds (the closest one)
            logger.info(
                f"{__module_name__} - No doc cleared the gate — using closest doc as fallback"
            )
            all_scored = []
            for doc in self._docs.values():
                try:
                    results = doc.rag.vector_db.similarity_search_with_score(question, k=1)
                    if results:
                        _, score = results[0]
                        all_scored.append((score, doc))
                except Exception:
                    pass
            if all_scored:
                all_scored.sort(key=lambda x: x[0])
                qualifying = [all_scored[0][1]]

        logger.info(
            f"{__module_name__} - {len(qualifying)} doc(s) in speaking queue"
        )
        return qualifying

    # ──────────────────────────────────────────────────────────
    # Main Round Runner
    # ──────────────────────────────────────────────────────────

    def run_round(
        self,
        question: str,
        session_id: str,
    ) -> Iterator[Dict[str, Any]]:
        """
        Execute one full question-answer round across all qualifying documents.

        Yields dict chunks compatible with the existing chat.py rendering:
            {
                "speaker": str,            # persona_name of the current doc
                "document_id": str,        # UUID of the current doc
                "answer_chunk": str,       # partial streamed text token
                "answer": str,            # accumulated text so far for this doc
                "is_complete": bool,       # True = this doc finished speaking
                "round_complete": bool,    # True = ALL docs finished (last chunk only)
                "web_search_performed": bool,
            }

        Args:
            question: The raw user message (may contain @mention).
            session_id: Active PostgreSQL session UUID.
        """
        if not self._docs:
            yield {
                "speaker": "Orchestrator",
                "document_id": None,
                "answer": "No documents are loaded in this room yet. Please upload a document first.",
                "answer_chunk": "",
                "is_complete": True,
                "round_complete": True,
                "web_search_performed": False,
            }
            return

        # Reset spent flags for all docs at the start of each round
        for doc in self._docs.values():
            doc.spent = False

        # Determine speaking queue
        mentioned_doc = self.parse_mention(question)
        if mentioned_doc:
            # Strict @mention — only the addressed document speaks
            speaking_queue = [mentioned_doc]
            logger.info(
                f"{__module_name__} - @mention strict mode: only '{mentioned_doc.persona_name}' will answer"
            )
        else:
            speaking_queue = self.route(question)

        if not speaking_queue:
            yield {
                "speaker": "Orchestrator",
                "document_id": None,
                "answer": "None of the documents in this room seem to contain information relevant to your question.",
                "answer_chunk": "",
                "is_complete": True,
                "round_complete": True,
                "web_search_performed": False,
            }
            return

        # Save user turn to PostgreSQL
        turn_count = get_turn_count(session_id)
        turn_count += 1
        save_message(
            session_id=session_id,
            role="user",
            content=question,
            turn_number=turn_count,
            sender_name="You",
        )

        # Build shared context (summary + recent messages) for all docs this round
        group_context = self._build_group_context(session_id)

        # Trigger compaction if threshold reached
        if turn_count % GROUP_DOC_COMPACTION_N == 0:
            self._compact_history(session_id, turn_count, group_context)

        # Stream each doc in order
        max_agent_turns = 3
        current_turn = 0
        previous_answers = []

        while speaking_queue and current_turn < max_agent_turns:
            room_doc = speaking_queue.pop(0)
            accumulated = ""
            web_search_performed = False

            try:
                # Build context for this specific doc's turn
                answer_relay = "No other documents have spoken yet."
                if previous_answers:
                    answer_relay = "\n".join(
                        f"[{name} already answered this question/query]:\n{ans}"
                        for name, ans in previous_answers
                    )

                # Wire in the group-aware prompt with full current context
                room_doc.rag.set_group_context(
                    persona_name=room_doc.persona_name,
                    all_personas=[d.persona_name for d in self._docs.values()],
                    conversation_context=group_context,
                )

                for chunk_dict in room_doc.rag.query_stream(question, previous_answers=answer_relay):

                    chunk_text: str = chunk_dict.get("answer_chunk", "")
                    accumulated = chunk_dict.get("answer", accumulated)
                    is_complete: bool = chunk_dict.get("is_complete", False)

                    # Check for web search token in accumulated text
                    found, cleaned, query = intercept_search_request(accumulated)
                    if found and query:
                        web_search_performed = True
                        search_result = run_search(query)
                        log_web_search(
                            session_id=session_id,
                            query=query,
                            result=search_result,
                            requesting_document_id=room_doc.document_id,
                        )
                        # Replace token-polluted text with the cleaned version
                        accumulated = cleaned
                        chunk_text = ""  # swallow the token chunk

                    if is_complete:
                        # We have the full string, parse for hand-offs
                        mentioned_peer = self.parse_mention(accumulated)
                        will_handoff = False
                        if mentioned_peer and mentioned_peer.document_id != room_doc.document_id:
                            will_handoff = True
                        
                        round_is_truly_complete = (len(speaking_queue) == 0) and (not will_handoff)

                        yield {
                            "speaker": room_doc.persona_name,
                            "document_id": room_doc.document_id,
                            "answer_chunk": chunk_text,
                            "answer": accumulated,
                            "is_complete": True,
                            "round_complete": round_is_truly_complete,
                            "web_search_performed": web_search_performed,
                            "source_documents": chunk_dict.get("source_documents", []),
                            "similarity_metrics": chunk_dict.get("similarity_metrics", {}),
                        }

                        # Diminishing returns proxy check
                        room_doc.spent = len(accumulated.strip()) < 30

                        # Save this doc's final message to PostgreSQL
                        turn_count += 1
                        save_message(
                            session_id=session_id,
                            role="document",
                            content=accumulated,
                            turn_number=turn_count,
                            sender_name=room_doc.persona_name,
                            document_id=room_doc.document_id,
                        )
                        previous_answers.append((room_doc.persona_name, accumulated))

                        if will_handoff:
                            logger.info(f"{__module_name__} - {room_doc.persona_name} handballed to {mentioned_peer.persona_name}")
                            speaking_queue.insert(0, mentioned_peer)

                        break
                    else:
                        yield {
                            "speaker": room_doc.persona_name,
                            "document_id": room_doc.document_id,
                            "answer_chunk": chunk_text,
                            "answer": accumulated,
                            "is_complete": False,
                            "round_complete": False,
                            "web_search_performed": web_search_performed,
                            "source_documents": chunk_dict.get("source_documents", []),
                            "similarity_metrics": chunk_dict.get("similarity_metrics", {}),
                        }

            except Exception as e:
                logger.error(f"{__module_name__} - Error streaming from '{room_doc.persona_name}': {e}")
                yield {
                    "speaker": room_doc.persona_name,
                    "document_id": room_doc.document_id,
                    "answer": f"I encountered an error while preparing my response: {str(e)}",
                    "answer_chunk": "",
                    "is_complete": True,
                    "round_complete": len(speaking_queue) == 0,
                    "web_search_performed": False,
                    "error": str(e),
                }

            current_turn += 1

    # ──────────────────────────────────────────────────────────
    # Context & Compaction
    # ──────────────────────────────────────────────────────────

    def _build_group_context(self, session_id: str) -> str:
        """
        Build a context string for the LLM from the latest compaction summary
        + the last N raw messages.

        Returns:
            Multi-line string ready to embed in a prompt.
        """
        latest_summary = get_latest_summary(session_id)
        after_turn = latest_summary["covers_up_to_turn"] if latest_summary else 0
        recent_messages = get_session_messages(session_id, after_turn=after_turn)

        parts: List[str] = []

        if latest_summary:
            parts.append(
                f"[CONVERSATION SUMMARY (up to turn {latest_summary['covers_up_to_turn']})]\n"
                f"{latest_summary['summary']}"
            )

        if recent_messages:
            parts.append("[RECENT MESSAGES]")
            for msg in recent_messages:
                sender = msg.get("sender_name") or msg["role"]
                parts.append(f"{sender}: {msg['content']}")

        return "\n\n".join(parts)

    def _compact_history(
        self,
        session_id: str,
        current_turn: int,
        current_context: str,
    ) -> None:
        """
        Compress current context into a new summary row in PostgreSQL.
        Uses the room's LLM to summarize.

        This is a fire-and-forget operation — failures are logged but don't
        interrupt user conversation.
        """
        try:
            from backend.llm_wrapper import (
                get_google_chat_model,
                get_mistral_chat_model,
                get_ollama_chat_model,
            )
            from langchain_core.messages import HumanMessage

            if self.model_provider == "google":
                llm = get_google_chat_model(
                    model_name=self.model_name or "gemini-2.5-flash",
                    temperature=0.3,
                )
            elif self.model_provider == "mistral":
                llm = get_mistral_chat_model(
                    model_name=self.model_name or "mistral-medium",
                    temperature=0.3,
                )
            else:
                llm = get_ollama_chat_model(
                    model_name=self.model_name or "mistral:latest",
                    temperature=0.3,
                )

            prompt = (
                f"Summarize the following multi-document discussion conversation "
                f"into a concise paragraph that preserves all key insights, decisions, "
                f"and document contributions:\n\n{current_context}"
            )
            response = llm.invoke([HumanMessage(content=prompt)])
            summary_text = response.content if hasattr(response, "content") else str(response)

            save_context_summary(
                session_id=session_id,
                summary=summary_text,
                covers_up_to_turn=current_turn,
            )
            logger.info(
                f"{__module_name__} - Compacted history to turn {current_turn} "
                f"for session {session_id}"
            )

        except Exception as e:
            logger.error(f"{__module_name__} - Compaction failed: {e}")

    # ──────────────────────────────────────────────────────────
    # Settings Update
    # ──────────────────────────────────────────────────────────

    def update_model(self, model_provider: ModelProvider, model_name: Optional[str] = None) -> None:
        """
        Switch the AI model for all documents in the room.
        Changes take effect from the next round.

        Args:
            model_provider: 'google', 'mistral', or 'ollama'
            model_name: Specific model name override, or None for provider default.
        """
        self.model_provider = model_provider
        self.model_name = model_name

        for doc in self._docs.values():
            doc.rag.update_settings(
                model_provider=model_provider,
            )

        logger.info(
            f"{__module_name__} - Switched room {self.room_id} to "
            f"model_provider={model_provider}, model_name={model_name}"
        )

    # ──────────────────────────────────────────────────────────
    # Inspection
    # ──────────────────────────────────────────────────────────

    def get_participants(self) -> List[Dict[str, Any]]:
        """Return participant info dicts for the UI, including filename for preview type detection."""
        return [
            {
                "document_id": doc.document_id,
                "persona_name": doc.persona_name,
                "collection_name": doc.collection_name,
                "filename": os.path.basename(doc.file_path) if doc.file_path else "",
                "spent": doc.spent,
            }
            for doc in self._docs.values()
        ]

    def __len__(self) -> int:
        """Number of documents currently in this room."""
        return len(self._docs)

    def __repr__(self) -> str:
        return (
            f"GroupOrchestrator(room_id={self.room_id!r}, "
            f"docs={list(self._persona_index.keys())}, "
            f"model={self.model_provider})"
        )
