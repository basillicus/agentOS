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
│   │   └── llm.py       # OpenAI-compatible API Client
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
- [x] **Chat Interface:** Interactive loop in `agent.py` to route natural language to tools.
