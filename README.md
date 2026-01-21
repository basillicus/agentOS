# AgentOS 🤖

**AgentOS** is an intelligent, dual-interface system administration toolkit. It bridges the gap between traditional CLI tools and modern LLM-based assistance, allowing you to manage your local development environment through both interactive menus (TUI) and natural language chat.

## ✨ Features

*   **🧠 Intelligent Chat:** Talk to your system using local LLMs (via Ollama) or OpenAI-compatible APIs to perform complex tasks.
*   **💾 Disk Manager:** Analyze disk usage, clean development caches (pip, npm, conda), and find large files.
*   **🧠 Second Brain:** Securely ingest shell history, search past commands, and manage personal notes.
*   **⚙️ System Tools:** Prune Docker containers, vacuum system logs, and manage the Trash.
*   **🔌 Dual Mode:** Every feature is available as a structured API (for the AI) and a colored TUI (for you).

![AgentOS Working Example](images/test_agentOS_example.png)

## 🚀 Getting Started

### Prerequisites

*   **Python 3.10+**
*   **Ollama** (Recommended for local privacy) or an OpenAI API Key.
*   **Linux/macOS** (Windows support is experimental).

### Installation

1.  Clone the repository:
    ```bash
    git clone https://github.com/basillicus/agentOS.git
    cd agentOS
    ```

2.  Install dependencies:
    ```bash
    pip install -r requirements.txt
    ```
    *(Note: Ensure `pydantic-ai` and `logfire` are installed for Chat capabilities)*

3.  **Optional:** Set up your environment variables if using a remote provider:
    ```bash
    export AGENT_BASE_URL="http://localhost:11434/v1"
    export AGENT_MODEL="granite4:latest"
    ```

### Running with Apptainer (Singularity)

You can package AgentOS as a portable Apptainer (Singularity) container. We support three build flavors:

1.  **Standard** (Default): Includes Ollama. Downloads models at runtime.
2.  **Lite**: Code only. Requires external Ollama server.
3.  **Full**: Includes Ollama and `granite4` model baked in (Large).

**Build the image:**
```bash
./build_apptainer.sh [standard|lite|full]
# Example:
./build_apptainer.sh standard
```

**Run the agent:**
```bash
./agentOS-standard.sif
```

### Persist Data & Models (Recommended)
    To save notes/history and use your host's existing Ollama models:
    ```bash
    mkdir -p ~/agent-data
    apptainer run \
      --bind ~/agent-data:/data \
      --bind /usr/share/ollama/.ollama/models:/root/.ollama/models \
      --env AGENTOS_DATA_DIR=/data \
      agentOS.sif
    ```

    Or execute specific modules directly:
    ```bash
    ./agentOS.sif --json disk --action scan
    ```

### Development Mode (No Rebuild Required)
If you modify the code (`entrypoint.sh` or `agentOS/`), you don't need to rebuild the image. Simply bind your local code over the container's code:

```bash
  --env AGENTOS_DATA_DIR=/data \
  agentOS.sif
```

### Running a Custom Model (e.g., Llama3, Mistral)
To use a specific model that you already have locally, bind your models folder and set the `AGENT_MODEL` variable:

```bash
# Example: Using 'llama3' from your local Ollama library
apptainer run \
  --bind ~/agent-data:/data \
  --bind /usr/share/ollama/.ollama/models:/data/ollama/models \
  --env AGENTOS_DATA_DIR=/data \
  --env AGENT_MODEL=llama3 \
  agentOS.sif
```

### Usage

Run the main agent entry point:

```bash
python3 agentOS/agent.py
```

You will be presented with the Main Menu:

1.  **Disk Manager** - Clean up space.
2.  **Second Brain** - Search history/notes.
3.  **System Tools** - Maintenance tasks.
4.  **Agent Chat** - **The Magic!** Ask questions like *"Clean my pip cache"* or *"Find files larger than 1GB"*.
5.  **Settings** - Switch models dynamically.

## 🛠 Configuration

Configuration is stored in `agentOS/data/config.json`. You can modify this file directly or use the **Settings** menu in the TUI to change the active model.

## 🧪 Testing

AgentOS includes a comprehensive testing framework with three levels:

*   **Unit Tests:** Test individual skills and components in isolation.
*   **Integration Tests:** Test how components work together.
*   **Evaluation Tests:** Test the agent's behavior with logging via Logfire.

### Running Tests

Run all tests:
```bash
python run_tests.py
```

Run specific test types:
```bash
python run_tests.py --type unit      # Unit tests only
python run_tests.py --type integration  # Integration tests only
python run_tests.py --type evals    # Evaluation tests only
```

Or using pytest:
```bash
pip install pytest pytest-cov
pytest tests/unit/ -v
pytest tests/integration/ -v
pytest tests/evals/ -v
pytest tests/ --cov=agentOS --cov-report=html  # With coverage
```

### Evaluation Framework

The evaluation framework uses Pydantic Logfire for observability:
```bash
# Install dev dependencies
pip install -e ".[dev]"
# Or install logfire separately
pip install logfire

# Run evaluation tests with logfire
python -m pytest tests/evals/ -v
```

## 🤝 Contributing

See [AGENTS.md](AGENTS.md) for the architectural specification and roadmap.
See [docs/](docs/) for technical developer documentation.

## 📄 License

MIT
