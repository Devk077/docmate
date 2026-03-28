# DoqToq Groups — User Journey & UI Design

*A Discord-inspired experience for multi-document group discussions.*

---

## Concept: The "Discussion Room"
Think of each group session as a **Discussion Room** — similar in spirit to a Discord server with channels, but the "members" of the room are AI-powered documents instead of people. The user is the moderator who can steer, intervene, or just observe.

---

## User Journey (Step by Step)

### 1. Landing / Home Screen
- User opens DoqToq.
- The app has one unified mode — it works whether the user uploads one document or ten. There is no separate "Groups" tab or "Single Doc" tab.
- The main screen shows a list of the user's **Discussion Rooms** and a **"+ New Room"** button.
- A Discussion Room with one document behaves like the current single-doc chat. A room with multiple docs activates group discussion automatically.

### 2. Create a Discussion Room
- User clicks **"+ New Room"**.
- They give the room a name (e.g., *"Climate Policy Research"*).
- They upload **one or more documents** into the room (PDF, TXT, JSON, MD).
- For each document uploaded, the Orchestrator auto-generates a **friendly persona name** (e.g., *"The Climate Report"*, *"The Policy Handbook"*).
- User selects the **AI model** for document responses from a dropdown (Gemini, Mistral, Ollama). This model is used only for the doc generation step, not for the Orchestrator's internal routing calls.
- User clicks **"Start Discussion"**.
- The AI model can also be **changed at any point mid-chat** from the participants panel. The change takes effect on the next document turn — no need to restart the room.

### 3. Entering the Discussion Room
- The room UI loads. The layout has:
  - **Main chat panel** — the group conversation, center stage.
  - **Participants panel** (right sidebar or collapsible) — shows all documents in the room as "members", each with their persona name, a brief AI-generated bio, and an online indicator (green = active, grey = not speaking).
  - **Orchestrator indicator** — a subtle floating indicator showing what the Orchestrator is currently doing (e.g., *"Routing..."*, *"Doc A is thinking..."*, *"Web searching..."*).

### 4. Talking in the Room
**Case A — Ask the whole group:**
- User types a message not addressed to anyone specifically.
- e.g., *"What are the main challenges in renewable energy adoption?"*
- Orchestrator routes to all relevant docs via vector gating.
- Each qualified doc's response appears sequentially in the chat, tagged with their persona name and avatar.

**Case B — Address a specific document:**
- User types using `@DocName` syntax.
- e.g., *"@The Climate Report, what's your view on carbon taxes?"*
- Orchestrator routes exclusively to that document, bypasses vector gating for others.
- Other docs may choose to reply if the Orchestrator decides they have a meaningful rebuttal.

**Case C — Doc-to-Doc reply:**
- A document can address another document directly in its response.
- e.g., *"@The Policy Handbook, your regulatory timeline overlooks something I cover in my second chapter..."*
- The mentioned document enters the queue for a rebuttal turn.

### 5. Web Search (Document-Triggered, Silent)
- A document reaches a knowledge gap mid-discussion and signals the Orchestrator to perform a web search.
- The web search runs **silently** — nothing is shown in the chat. The user will not see a "Web searching..." bubble or any intermediate web result.
- The requesting document's turn is **halted** (not cancelled) until the search returns. Other documents in the queue continue speaking during this time — the conversation is not paused.
- Once the result is back, the document resumes its turn using the new information naturally in its response (as if it had known it all along).
- **Everything is logged** — the query, the search result, the requesting document, and the timestamp are written to the database for audit and debugging purposes.

### 6. Leaving / Ending a Room
- User can pause the discussion at any time.
- Rooms can be saved and resumed (Qdrant collections persist under the session ID).
- User can add or remove documents from a room at any time (triggers a new collection for the added doc, deletes collection for the removed one).

---

## UI Component Map

```
┌──────────────────────────────────────────────────────┐
│  Sidebar                                             │
│  [Single Doc] [Groups ←]                            │
│  ─────────────────────────────                       │
│  My Rooms:                                           │
│    📁 Climate Policy Research                        │
│    📁 Legal Review Q1                                │
│  [+ New Room]                                        │
└──────────┬───────────────────────────────────────────┘
           │
┌──────────▼────────────────────┬──────────────────────┐
│  Main Chat Panel              │  Participants         │
│                               │  ─────────────────── │
│  [🌐 Web] Found this: ...     │  👤 You               │
│                               │  📄 The Climate Report│
│  [📄 Climate Report]          │    ● active           │
│   "Based on my section 3..."  │                       │
│                               │  📄 Policy Handbook   │
│  [📄 Policy Handbook]         │    ○ idle             │
│   "I'd add that..."           │                       │
│                               │  🧠 Orchestrator      │
│  [You] @Climate Report, ...   │    Routing...         │
│                               │                       │
│  [ Type a message... ] [Send] │  [AI Model: Gemini ▼] │
└───────────────────────────────┴──────────────────────┘
```

---

## Key UX Decisions
- **No walls of text:** Each document response is rendered in its own chat bubble, labeled with the persona name.
- **Orchestrator is visible but unobtrusive** — shows activity status, not verbose logs.
- **Web search is non-blocking** — shown as a small indicator, doesn't freeze the conversation.
- **@mention routing** — users and documents can direct messages at specific participants.
- **AI model selector** is per-room, not global, and applies to document generation only.
