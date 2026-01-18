# Agent System Specification

## Vision
To build a modular, dual-interface (CLI + LLM) system administration toolkit. The system empowers both human users and AI agents to maintain, organize, and query the local development environment efficiently.

## Core Philosophy
1.  **Dual-Use Design:** Every tool must be usable as an interactive CLI (TUI) for humans and as a structured function (API/JSON) for LLMs.
2.  **Production-First Engineering:**
    *   **Strict Typing:** All inputs/outputs must use `Pydantic` models.
    *   **Lazy Loading:** Tools must not execute heavy operations (I/O) during initialization.
    *   **Documentation:** Comprehensive docstrings for all classes and methods to guide the Agent.
    *   **User Experience:** TUIs must be visually distinct (colored) and intuitive.
3.  **State Awareness:** The system remembers past actions, successful commands, and user preferences via a local SQLite database.
4.  **Security:** Secrets in command history are sanitized (redacted) before storage.

## Architecture

### 1. Directory Structure
```
/agentOS
├── bin/                 # Shell wrappers
├── src/
│   ├── core/            # Shared logic
│   │   ├── schemas.py   # Pydantic models (The Contract)
│   │   ├── style.py     # TUI Styling & Colors
│   │   ├── llm.py       # Basic LLM Client (Legacy/Simple)
│   │   └── engine.py    # Pydantic AI Agent Factory & Tool Registration
│   ├── skills/          # Distinct capability modules
│   │   ├── disk/        # Disk cleaner & Analyzer
│   │   ├── memory/      # History & Notes (Secure)
│   │   └── system/      # Docker, Logs, Trash
│   └── agent.py         # Main entry point & Chat Loop
├── data/                # Local SQLite DB (agent.db)
└── README.md
```

### 2. The "Skill" Interface
Each module (e.g., `DiskSkill`, `MemorySkill`) must implement:
*   **`run_tui()`**: Interactive, colored menu.
*   **Public Methods**: Typed methods returning Pydantic objects.

### 3. Agent Engine (Pydantic AI)
The system uses `pydantic-ai` to orchestrate tool usage.
*   **Dependencies:** `AgentDeps` class injects skills into the agent context.
*   **Dynamic Configuration:** The agent factory (`get_agent()`) allows runtime model switching without restart.
*   **Compatibility:** Handles differences between Ollama (requires `/v1` suffix) and standard OpenAI endpoints.

## Roadmap

### Phase 1: Foundation (Completed)
- [x] Define Architecture & Schemas.
- [x] Implement **Disk Skill** (Cache cleaning, Env management, File scanning).
- [x] Dual-mode support (JSON/TUI).

### Phase 2: The "Second Brain" (Completed)
- [x] **Core Styling:** `style.py` for consistent, colored UI.
- [x] **Database Setup:** SQLite initialization for history/notes.
- [x] **Memory Skill:**
    - [x] Command History Ingestion with **Security Sanitization**.
    - [x] Semantic/Text Search for commands.
    - [x] Notes management.

### Phase 3: The Agent (Completed)
- [x] **System Skill:** Docker pruning, Log vacuuming, Trash emptying.
- [x] **LLM Client:** `src/core/llm.py` supporting OpenAI-compatible APIs.
- [x] **Chat Interface:** Interactive loop in `agent.py` using **Pydantic AI**.
- [x] **Runtime Config:** Switch models via Settings menu.

### Phase 4: Refinement & Documentation (In Progress)
- [ ] **Documentation:** User README and Developer Technical Guide.
- [ ] **Robustness:** Better error handling for LLM timeouts/failures.
- [ ] **Testing:** Unit tests for core skills.

### Phase 5: Future Expansion
- [ ] **Git Skill:** Smart commit generation, branch cleanup.
- [ ] **Network Skill:** Port scanning, process killing by port.
- [ ] **Web Search:** Integration for fetching external docs.