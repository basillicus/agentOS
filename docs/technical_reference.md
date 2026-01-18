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
