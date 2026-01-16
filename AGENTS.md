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

## Architecture

### 1. Directory Structure
```
/agentOS
├── bin/                 # Shell wrappers
├── src/
│   ├── core/            # Shared logic
│   │   ├── schemas.py   # Pydantic models (The Contract)
│   │   ├── style.py     # TUI Styling & Colors
│   │   └── db.py        # Database connection/ORM
│   ├── skills/          # Distinct capability modules
│   │   ├── disk/        # Disk cleaner & Analyzer (Done)
│   │   ├── memory/      # History & Notes (In Progress)
│   │   └── system/      # System info & Process management
│   └── agent.py         # Main entry point
├── data/                # Local SQLite DB (agent.db)
└── README.md
```

### 2. The "Skill" Interface
Each module (e.g., `DiskSkill`, `MemorySkill`) must implement:
*   **`run_tui()`**: Interactive, colored menu.
*   **Public Methods**: Typed methods returning Pydantic objects (e.g., `get_notes() -> List[Note]`).

## Roadmap

### Phase 1: Foundation (Completed)
- [x] Define Architecture & Schemas.
- [x] Implement **Disk Skill** (Cache cleaning, Env management, File scanning).
- [x] Dual-mode support (JSON/TUI).

### Phase 2: The "Second Brain" (Current)
- [ ] **Core Styling:** create `style.py` for consistent, colored UI.
- [ ] **Database Setup:** SQLite initialization for history/notes.
- [ ] **Memory Skill:**
    - [ ] Command History Ingestion.
    - [ ] Semantic/Text Search for commands.
    - [ ] Notes management (Tags, Content).

### Phase 3: The Agent (Future)
- [ ] Master CLI wrapper (`agentOS <command>`).
- [ ] LLM Integration loop.