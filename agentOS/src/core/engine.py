import os
import json
from typing import List, Union
from pydantic_ai import Agent, RunContext
from pydantic_ai.models.openai import OpenAIChatModel

from src.core.dependencies import AgentDeps
from src.core.schemas import Note, HistoryItem, ActionResponse, CacheItem, DiskUsage, FileScanResult

def get_agent() -> Agent:
    """
    Factory function to create the Agent with the latest configuration.
    This allows changing the model at runtime without restarting the script.
    """
    # 1. LOAD CONFIG (Fresh read)
    config_path = os.path.join(os.path.dirname(__file__), "../../data/config.json")
    config = {}
    if os.path.exists(config_path):
        try:
            with open(config_path) as f: config = json.load(f)
        except: pass

    base_url = config.get("base_url") or os.getenv("AGENT_BASE_URL", "http://localhost:11434/v1")

    # Ensure Ollama URL has /v1 for OpenAI client compatibility
    if "localhost" in base_url:
        base_url = base_url.rstrip("/")
        if not base_url.endswith("/v1"):
            base_url = f"{base_url}/v1"

    model_name = config.get("model") or os.getenv("AGENT_MODEL", "granite4:latest")
    api_key = os.getenv("AGENT_API_KEY", "ollama")

    # 2. SETUP MODEL
    # We set environment variables to ensure compatibility if kwargs fail
    os.environ["OPENAI_BASE_URL"] = base_url
    os.environ["OPENAI_API_KEY"] = api_key

    try:
        # Try passing kwargs directly (Standard Pydantic AI)
        model = OpenAIChatModel(model_name, base_url=base_url, api_key=api_key)
    except TypeError:
        # Fallback: Older/Different versions rely on Env Vars
        model = OpenAIChatModel(model_name)

    # 3. DEFINE AGENT
    agent = Agent(
        model,
        deps_type=AgentDeps,
        system_prompt=(
            "You are AgentOS, a system administration assistant. "
            "You have access to tools to manage the Disk, Memory (Notes/History), and System. "
            "Use these tools to answer user requests. "
            "When a tool returns data, summarize it concisely in natural language."
        )
    )

    # 4. REGISTER TOOLS

    # --- DISK TOOLS ---
    @agent.tool
    def list_caches(ctx: RunContext[AgentDeps]) -> List[CacheItem]:
        """Scan and list all development caches (Pip, NPM, Conda, etc.) and their sizes."""
        return ctx.deps.disk.get_caches()

    @agent.tool
    def clean_cache(ctx: RunContext[AgentDeps], cache_id: str) -> ActionResponse:
        """Clean a specific cache by its ID (e.g., 'pip', 'npm', 'docker')."""
        return ctx.deps.disk.clean_cache(cache_id)

    @agent.tool
    def explore_folder(ctx: RunContext[AgentDeps], path: str = "~") -> List[DiskUsage]:
        """List the sizes of subfolders in a specific directory."""
        return ctx.deps.disk.explore_folder(path)

    @agent.tool
    def scan_large_files(ctx: RunContext[AgentDeps], threshold: str = "500M") -> FileScanResult:
        """Find files larger than the threshold (e.g. '500M', '1G')."""
        return ctx.deps.disk.list_large_files(threshold)

    # --- MEMORY TOOLS ---
    @agent.tool
    def add_note(ctx: RunContext[AgentDeps], content: str, tags: List[str]) -> ActionResponse:
        """Save a note to the user's second brain."""
        return ctx.deps.memory.add_note(content, tags)

    @agent.tool
    def search_notes(ctx: RunContext[AgentDeps], tag: str) -> List[Note]:
        """Get notes, optionally filtering by a tag."""
        return ctx.deps.memory.get_notes(tag)

    @agent.tool
    def sync_history(ctx: RunContext[AgentDeps]) -> ActionResponse:
        """Import and sanitize shell history from .bash_history/.zsh_history."""
        return ctx.deps.memory.ingest_shell_history()

    @agent.tool
    def search_history(ctx: RunContext[AgentDeps], query: str) -> List[HistoryItem]:
        """Search for past commands executed by the user."""
        return ctx.deps.memory.search_history(query)

    @agent.tool
    def scrub_history(ctx: RunContext[AgentDeps], pattern: str) -> ActionResponse:
        """Permanently delete history items matching a regex pattern."""
        return ctx.deps.memory.scrub_history(pattern)

    # --- SYSTEM TOOLS ---
    @agent.tool
    def system_status(ctx: RunContext[AgentDeps]) -> dict:
        """Get status/sizes of Trash, Logs, and Apt cache."""
        return ctx.deps.system.get_status()

    @agent.tool
    def docker_prune(ctx: RunContext[AgentDeps]) -> ActionResponse:
        """Remove stopped containers and dangling images."""
        return ctx.deps.system.docker_prune()

    @agent.tool
    def vacuum_logs(ctx: RunContext[AgentDeps]) -> ActionResponse:
        """Vacuum systemd journals to free space."""
        return ctx.deps.system.vacuum_logs()

    @agent.tool
    def empty_trash(ctx: RunContext[AgentDeps]) -> ActionResponse:
        """Permanently empty the user's Trash."""
        return ctx.deps.system.empty_trash()
        
    return agent
