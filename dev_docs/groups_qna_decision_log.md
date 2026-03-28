# DoqToq Groups — Q&A Decision Log

*Every architectural decision made during the planning of the DoqToq Groups feature is recorded here. Written to be understandable by anyone who isn't already familiar with the project.*

---

## Q1: How should multiple documents respond to a user's question?

**Problem:** When there are multiple documents in a room, should they all answer at once, take turns, or only the most relevant ones speak?

**Decision:** The smartest document speaks first, then others can add to it if they have something meaningful. This is like a human discussion — not everyone talks at once, but whoever has the most relevant thing to say goes first. Each response is streamed live to the user. After one document finishes, its response is shared with all other documents so they can build on it, agree, or push back.

**Why:** This feels natural, keeps responses focused, and avoids information overload from all documents replying simultaneously.

---

## Q2: How is each document's knowledge stored and kept separate?

**Problem:** If we put all documents into one shared database, they might interfere with each other's knowledge. But if we open a completely separate database connection per document, it wastes resources.

**Decision:** Use **one Qdrant connection** (the database that stores document vectors), but create a **separate "collection" (like a folder) per document**. Collections are named as `dtq_{room_id}_{document_slug}` (e.g., `dtq_abc123_climate_report`). All documents share the same underlying connection but are stored in isolated spaces.

**Why:** Opening database connections is expensive. A single connection can serve many collections. This way, knowledge is perfectly isolated per document (no cross-contamination) while being resource-efficient. When a session ends, all collections for that room are deleted.

---

## Q3: Can documents talk to each other autonomously?

**Problem:** Should documents be able to respond to each other without the user prompting them?

**Decision:** Yes. Documents can autonomously reply to each other. However, **every single response is shown to the user** — there are no hidden or background conversations. The user always sees everything.

**Why:** Transparency is key. The value of the group discussion is learning how different sources relate, agree, or contradict each other.

---

## Q4: How do we prevent documents from debating forever?

**Problem:** If Doc A says something and Doc B disagrees, and they just keep going back and forth, the conversation has no natural end point.

**Decision:** The Orchestrator monitors each response and computes how similar it is to what was already said (using a similarity score). If a document starts repeating the same idea without adding anything new, it is marked "spent" and removed from the speaking queue for that round. When all documents in the queue are "spent", the round ends and the user is prompted.

**Why:** This is more natural than a hard turn limit (e.g., "only 3 replies max"). It mirrors how real discussions end — when nobody has anything new to say.

**Config:** `GROUP_DIMINISHING_RETURNS_SIM=0.92` — if a new response is 92%+ similar to the previous, the doc is marked spent.

---

## Q5: How does the Orchestrator decide which documents should speak?

**Problem:** With several documents in a room, how does the system decide which ones are relevant to a given user question without making expensive AI calls for every document on every turn?

**Decision:** Use a **vector similarity gate** — a fast pre-check before any LLM generation happens.

**How it works step by step:**
1. The user asks a question.
2. The question is checked against each document's Qdrant collection using a similarity search (this is a fast, cheap database lookup — not an LLM call).
3. Documents that score above a configured threshold (`GROUP_SIMILARITY_THRESHOLD=0.65`) are added to the speaking queue.
4. If the user's message contains an `@mention` (e.g., `@The Climate Report`), that specific document is added directly — bypassing the similarity check.
5. Each queued document is then asked (via a short prompt): *"Do you want to contribute or not?"* — only those that say yes generate a full response.
6. Full generation only happens for confirmed speakers. This saves significant cost.

**Fallback:** If no document clears the threshold, the one with the highest similarity score (even if below threshold) is used as a fallback answerer. If even that score is very low, the Orchestrator tells the user it couldn't find a good match and offers a web search.

---

## Q6: How do we manage the growing chat history without crashing the AI?

**Problem:** LLMs have a maximum input size. In a long group discussion, if we feed all 50+ messages into every AI call, we either hit the limit or pay very high token costs.

**Decision: Incremental Milestone Compaction**

**How it works:**
1. The last N messages (default: 10, configured via `GROUP_DOC_COMPACTION_N`) are always kept verbatim and fed to the AI.
2. Every time the message count hits a multiple of N (message 10, 20, 30...), a **compaction** happens: a cheap AI call summarizes *only the oldest batch* of messages (messages 1–5, for example) into a short paragraph.
3. This summary is appended to a running "summary log" — it is never rewritten from scratch, only appended to.
4. The AI receives: [running summary] + [last N messages verbatim] + [current question].
5. The full log is always stored in PostgreSQL and shown uncompressed to the user in the chat UI.

**Why not compact every message?** Because then every single message triggers a compaction call, and those compaction calls get *more expensive* over time as the full history grows. With milestones, cost stays flat.

**Config:** `GROUP_DOC_COMPACTION_N=10`

---

## Q7 & Q8: How does web search work, and who can access it?

**Problem:** Documents might need information that isn't in their uploaded content (e.g., recent news, live data). But we don't want users to directly trigger searches, and we don't want web searches to interrupt the conversation.

**Decision: Web search is an Orchestrator-owned tool, accessible only to documents.**

**How it works:**
1. While generating a response, if a document detects it lacks information on a topic, it emits a structured signal in its output: `[WEB_SEARCH_REQUEST: carbon tax rates 2024]`.
2. The Orchestrator intercepts this token mid-stream.
3. The document's turn is **halted** (paused, not cancelled). If other documents are in the speaking queue, they continue — the conversation does not freeze.
4. The Orchestrator runs the web search using a tool (e.g., DuckDuckGo via LangChain) and retrieves a result.
5. The search runs **silently** — no message is shown to the user about the fact that a search happened.
6. The document receives the result and **resumes its turn**, incorporating the information naturally into its response.
7. The query, result, and requesting document are written to the `web_search_logs` PostgreSQL table for auditing and debugging.

**Why silent?** Users don't need to see implementation details. They just see a well-informed, fluent document response. The logs give full visibility to developers.

---

## Q9: How does the user start and manage a Discussion Room?

**Decision:** There is **no separate "Groups" mode** — DoqToq is mode-agnostic. Whether the user uploads 1 document or 10, the interface is the same. A room with one document behaves like the current single-doc experience. A room with multiple documents activates group discussion automatically.

**User journey:**
- Main screen shows a list of rooms + "New Room" button.
- User creates a room, gives it a name, uploads documents.
- The Orchestrator auto-generates a persona name per document on upload (stored in PostgreSQL — never regenerated).
- User picks an AI model (can be changed mid-chat at any time).
- The room is persistent — user can leave and resume, and the chat history is restored from PostgreSQL.

---

## Q10: How are documents named/identified in the chat?

**Decision:** The Orchestrator generates a friendly persona name when a document is first uploaded (e.g., *"The Climate Report"*, *"The Policy Handbook"*). This is done once using a short AI prompt based on the document's title or first paragraph, and saved in the `documents` PostgreSQL table. On all future sessions, the stored name is used — no re-generation.

---

## Q11: What model does the Orchestrator use for routing?

**Deferred to a future phase.**

---

## Q12: What happens when no document is relevant to the user's question?

**Decision:** The Orchestrator uses the **best-scoring document** as a fallback even if it didn't clear the threshold. If the score is very low (suggesting complete irrelevance), the Orchestrator informs the user: *"None of the documents in this group seem to have relevant information on this topic. Would you like me to run a web search?"*

---

## Q13: Where is chat history stored, and why not Qdrant?

**Decision: PostgreSQL.**

**Why not Qdrant?** Qdrant is built for similarity search over vector embeddings. It is not designed for relational data like "what was said in message 34 of session X". Storing chat history in Qdrant would be like storing a spreadsheet in a search engine — technically possible but wrong tool.

**What PostgreSQL stores:**
- Room definitions and names
- Document metadata and persona names (stored once, reused forever)
- Session records
- All chat messages (ordered by turn number)
- Context summary milestones (for the compaction strategy)
- Web search logs (for audit trail)

**What Qdrant stores:**
- The vector embeddings of document chunks (for similarity search during retrieval)

---

## Environment Variables Reference

```env
GROUP_SIMILARITY_THRESHOLD=0.65       # Min similarity score for a doc to speak (0–1 scale)
GROUP_DOC_COMPACTION_N=10             # How many messages before triggering a compaction
GROUP_DIMINISHING_RETURNS_SIM=0.92    # Above this similarity, a doc is marked "spent"
GROUP_MAX_ROOM_DOCS=10                # Max docs allowed in one room
```
