# Orchestrator Evolution & Living Document Analysis

This document captures the findings and architectural shifts discovered during the refinement of the DoqToq Multi-Document Orchestrator.

## 1. Key Findings & Discoveries

### A. The "Amnesia" Bug (Context Loss)
*   **Finding**: Documents were frequently losing track of previous messages in a room.
*   **Cause**: The `{conversation_context}` variable was missing from the `group_system_prompt.md` and wasn't being correctly injected by the `GroupOrchestrator` into the RAG chain.
*   **Fix**: Re-introduced `{conversation_context}` into the system prompt and ensured `run_round()` builds a fresh window of the last 10 messages for every document turn.

### B. Hidden vs. Visible Communication
*   **Finding**: Initial attempts used a hidden token protocol `[ASK_DOCUMENT: ...]` to fetch info between documents.
*   **User Feedback**: The user expressed a preference for *visible* interaction—seeing the documents actually talk to each other in the chat.
*   **Evolution**: Shifted to **Conversational Routing**. Documents now use standard `@PersonaName` mentions in their text to hand off the floor. 

### C. Identity Shift: Assistant vs. Living Document
*   **Finding**: The AI was sounding too much like "I am an AI assistant reading your file."
*   **Requirement**: The personas should be strictly **Living Documents** ("I am Abhidnya's Resume," "I am the Climate Report").
*   **Fix**: System prompt was rewritten to enforce first-person identity ("I contain...", "In my section...") and professional, document-oriented tones.

## 2. Latest Architectural Implementation

### Conversational Turn Management
The orchestrator has evolved from a static sequential list to a **Dynamic Turn Queue**.

```python
# Modern run_round logic
while speaking_queue and current_turn < max_agent_turns:
    doc = speaking_queue.pop(0)
    # ... stream response ...
    if mentions_peer(accumulated_text):
        speaking_queue.insert(0, mentioned_peer) # Peer answers next!
```

### Safety Features
*   **Loop Cap**: A hard limit of `max_agent_turns = 3` per round prevents documents from debating each other indefinitely.
*   **Strict Bypass**: Users can still force a round to end or target a specific doc using the `@mention` prefix in their query.

## 3. Current Project State

| Component | Status | Note |
|---|---|---|
| **Prompts** | 🟢 Optimized | Document-centric, supports visible @mentions. |
| **Logic** | 🟢 Stable | Turn-based queue with dynamic hand-offs. |
| **Routing** | 🟢 Enhanced | Handles both User->Doc and Doc->Doc mentions. |
| **Web Search** | 🟡 Integrated | Works but is currently passive (needs manual trigger check). |
| **UI** | 🟡 Syncing | React frontend needs to handle the multiple response bubbles in a single round. |

## 4. Next Steps
1.  **Frontend Message Grouping**: Ensure the React UI correctly handles a single SSE stream producing multiple speakers sequentially.
2.  **Persona Tuning**: Review generated persona names to ensure they are human-readable and easy to `@mention`.
3.  **Testing**: Implement `pytest` for the `GroupOrchestrator` queue logic to ensure no infinite loops occur.
