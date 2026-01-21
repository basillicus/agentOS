# AgentOS Technical Reference

This document provides a deep dive into the architecture of AgentOS for developers wishing to extend its capabilities.

## 1. System Architecture

AgentOS is built on a **Modular Skill Architecture**. The core application (`agent.py`) acts as a router, dispatching user intent either to a TUI (Terminal User Interface) or to the AI Agent.

### Core Components

*   **`src/core/dependencies.py`**: Defines the `AgentDeps` dataclass. This is the "Context" object passed to every tool call. It contains instances of the Skill classes (`DiskSkill`, `MemorySkill`, `SystemSkill`), allowing tools to interact with the system statefully.
*   **`src/core/engine.py`**: The Pydantic AI integration point.
    *   **`get_agent()`**: A factory function that re-initializes the `Agent` object on demand. This is crucial for allowing runtime model switching (e.g., changing from `llama3` to `granite4`) without restarting the Python process.
    *   **Tool Registration**: Tools are decorated with `@agent.tool`. They receive `ctx: RunContext[AgentDeps]` as their first argument, giving them access to the Skills.

## 2. The Agent Engine (`src.core.engine`)

We use **Pydantic AI** to type-safe the interaction between the LLM and our Python code.

### Model Compatibility
The engine supports both OpenAI and Ollama (via OpenAI-compatibility).
*   **Critical Detail:** Ollama's OpenAI-compatible endpoint is at `/v1`. The engine automatically detects `localhost` URLs and appends `/v1` if missing to prevent `404 Not Found` errors.

### Dependency Injection
Instead of global variables, we use Dependency Injection.
```python
@dataclass
class AgentDeps:
    disk: DiskSkill
    memory: MemorySkill
    system: SystemSkill
```
When `agent.run(..., deps=deps)` is called, this object is accessible in every tool.

## 3. Creating a New Skill

To add a new skill (e.g., `NetworkSkill`):

1.  **Create the Module**:
    Create `src/skills/network/manager.py`.

2.  **Implement the Class**:
    ```python
    class NetworkSkill:
        def scan_ports(self, target: str) -> List[int]:
            # Implementation...
            return [80, 443]
            
        def run_tui(self):
            # Interactive menu logic...
    ```

3.  **Register in `AgentDeps`**:
    Update `src/core/dependencies.py` to include `network: NetworkSkill`.

4.  **Register Tools in `engine.py`**:
    ```python
    @agent.tool
    def scan_network(ctx: RunContext[AgentDeps], target: str) -> List[int]:
        """Scan open ports on a target."""
        return ctx.deps.network.scan_ports(target)
    ```

5.  **Add to Main Menu**:
    Update `agent.py` to include the new option in the TUI.

## 4. Configuration Persistence

Configuration is handled by `src/core/llm.py` (legacy/simple client) and read by `src/core/engine.py`.
*   Data is stored in `agentOS/data/config.json`.
*   Keys: `model`, `base_url`.

## 5. Apptainer & Containerization

AgentOS is designed to run as a **Self-Contained AI Appliance** using Apptainer (formerly Singularity). This allows it to run on high-performance computing (HPC) clusters or standardized environments without complex dependency management.

### 5.1 Container Architecture

The container (`agentOS.sif`) is built as a layered stack:

1.  **Base Layer:** `python:3.11-slim` (Debian Trixie).
2.  **Runtime Layer:**
    *   **Ollama:** Installed directly inside the container to provide the LLM inference engine.
    *   **Dependencies:** `git`, `curl`, `zstd` (for Ollama model extraction), and Python packages.
3.  **Application Layer:** The AgentOS source code (`/app/agentOS`).
4.  **Entrypoint Layer:** A smart `entrypoint.sh` script that orchestrates the startup.

### 5.2 The Smart Entrypoint (`entrypoint.sh`)

The entrypoint script is the brain of the container. It handles three critical tasks before the agent starts:

1.  **Ollama Management:**
    *   Checks if an external `OLLAMA_HOST` is provided.
    *   If not, it spawns an **internal** `ollama serve` process in the background.
    *   It waits for the API to become responsive before launching the Python agent.

2.  **Permission Fixes (Root vs. User):**
    *   Ollama defaults to storing models in `/root/.ollama/models`.
    *   In Apptainer, the container runs as the **host user**, not root.
    *   The script detects this and automatically redirects `OLLAMA_MODELS` to a writable location (checked in this order):
        1.  `/data/ollama/models` (if `/data` is mounted and writable).
        2.  `$HOME/.ollama/models` (fallback).

3.  **Model Provisioning:**
    *   Checks if the requested `AGENT_MODEL` (default: `granite4`) exists.
    *   If missing, it attempts to `ollama pull` it automatically (requires Internet).

### 5.3 Data Persistence & Binding

To make the container useful, you must persist two types of data: **User Data** (DB/Config) and **LLM Models**.

#### A. Persisting User Data
The application looks for the `AGENTOS_DATA_DIR` environment variable.
*   **Internal Path:** `/data` (Standard convention).
*   **Host Path:** Any directory (e.g., `~/agent-data`).

```bash
mkdir -p ~/agent-data
apptainer run --bind ~/agent-data:/data --env AGENTOS_DATA_DIR=/data agentOS.sif
```

#### B. Managing LLM Models
Downloading models (multi-GB files) every time is inefficient. You should bind a local model directory.

**Scenario 1: Using Host Models**
If you already have Ollama running on your host or models downloaded at `/usr/share/ollama/...`:

```bash
# Map host models to the container's writable model path
apptainer run \
  --bind ~/agent-data:/data \
  --bind /usr/share/ollama/.ollama/models:/data/ollama/models \
  --env AGENTOS_DATA_DIR=/data \
  agentOS.sif
```
*The entrypoint will detect the non-root user and use `/data/ollama/models` as the model path.*

**Scenario 2: Self-Contained Download**
If you bind an empty folder, the container will download the model into it once, and persist it for future runs.

```bash
mkdir -p ~/my-models
apptainer run \
  --bind ~/agent-data:/data \
  --bind ~/my-models:/data/ollama/models \
  --env AGENTOS_DATA_DIR=/data \
  agentOS.sif
```

### 5.4 Build Process

The build uses a definition file (`agentOS.def`) and a helper script (`build_apptainer.sh`).

*   **Requirement:** `apptainer` installed on the host.
*   **Command:** `./build_apptainer.sh`
*   **Flags:** Uses `--fakeroot` to allow package installation (apt/pip) during the build phase without requiring root privileges on the host system.

### 5.5 Development Mode (Hot Reload)

You can develop the agent *inside* the container context without rebuilding the `.sif` file by binding your local source code over the container's `/app` directory:

```bash
apptainer run \
  --bind ./agentOS:/app/agentOS \
  --bind ./entrypoint.sh:/app/entrypoint.sh \
  --bind ~/agent-data:/data \
  agentOS.sif
```

