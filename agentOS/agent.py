#!/usr/bin/env python3
import sys
import os
import argparse
import json
import asyncio

# Ensure we can import from src
current_dir = os.path.dirname(os.path.abspath(__file__))
if current_dir not in sys.path:
    sys.path.append(current_dir)

from src.skills.disk.cleaner import DiskSkill
from src.skills.memory.manager import MemorySkill
from src.skills.system.tools import SystemSkill
from src.core.style import TUI, Colors
from src.core.dependencies import AgentDeps
from src.core.llm import LLMClient
import logfire

# Configure observability
# This will auto-detect PYDANTIC_LOGFIRE_TOKEN env var or use local fallback if configured.
try:
    logfire.configure()
except Exception:
    # Logfire might fail if not authenticated and strict mode is on, 
    # but usually it's safe to call.
    pass

# --- CONDITIONAL IMPORT FOR PYDANTIC AI ---
PYDANTIC_ERROR = None
try:
    from src.core.engine import get_agent  # Changed from 'agent' to 'get_agent'
    HAS_PYDANTIC_AI = True
except Exception as e:
    HAS_PYDANTIC_AI = False
    PYDANTIC_ERROR = str(e)

class AgentOS:
    def __init__(self):
        self.disk = DiskSkill()
        self.memory = MemorySkill()
        self.system = SystemSkill()
        self.llm = LLMClient() 
        
        self.deps = AgentDeps(self.disk, self.memory, self.system)

    def run_main_menu(self):
        """The Master TUI."""
        while True:
            current_model = self.llm.model
            
            TUI.header("AGENT OS", "System Intelligence & Memory")
            print(f"1. {Colors.BLUE}[ Disk Manager ]{Colors.RESET}   Clean caches, analyze storage")
            print(f"2. {Colors.MAGENTA}[ Second Brain ]{Colors.RESET}   Notes, History, Recall")
            print(f"3. {Colors.YELLOW}[ System Tools ]{Colors.RESET}   Docker, Logs, Trash")
            print(f"4. {Colors.GREEN}[ Agent Chat ]{Colors.RESET}     Talk to AgentOS (Pydantic AI)")
            print(f"5. [ Settings ]       Model: {Colors.CYAN}{current_model}{Colors.RESET}")
            print("q. Quit")
            
            choice = TUI.prompt("Select Module")
            
            if choice == 'q':
                sys.exit(0)
            elif choice == '1':
                self.disk.run_tui()
            elif choice == '2':
                self.memory.run_tui()
            elif choice == '3':
                self.system.run_tui()
            elif choice == '4':
                self.run_chat_mode_sync()
            elif choice == '5':
                self.run_settings_mode()

    def run_settings_mode(self):
        while True:
            TUI.header("SETTINGS", f"Current Provider: {self.llm.provider}")
            print(f"Current Model: {Colors.GREEN}{self.llm.model}{Colors.RESET}")
            print(f"Base URL:      {self.llm.base_url}")
            print("-" * 40)
            print("1. List & Select Available Models")
            print("b. Back")
            
            choice = TUI.prompt("Choice")
            
            if choice == 'b': return
            elif choice == '1':
                print("\nFetching models from server...")
                models = self.llm.list_models()
                print("\nAvailable Models:")
                for i, m in enumerate(models):
                    print(f"  {i+1}. {m}")
                
                sel = input("\nEnter number to select (or Enter to cancel): ")
                if sel.isdigit() and 0 < int(sel) <= len(models):
                    new_model = models[int(sel)-1]
                    self.llm.save_config(model=new_model)
                    print(f"Model switched to {self.llm.model} (Saved)")
                    input("Press Enter...")
                    return

    def run_chat_mode_sync(self):
        """Wrapper to run async chat loop."""
        if not HAS_PYDANTIC_AI:
            print(f"\n{Colors.RED}Error: Pydantic AI could not be loaded.{Colors.RESET}")
            print(f"{Colors.YELLOW}Reason: {PYDANTIC_ERROR}{Colors.RESET}")
            print("\nCommon fixes:")
            print("1. pip install pydantic-ai logfire")
            print("2. Check if your API key is set (if using OpenAI)")
            input("\nPress Enter to return...")
            return

        try:
            asyncio.run(self.run_chat_mode())
        except KeyboardInterrupt:
            pass

    async def run_chat_mode(self):
        """Interactive Chat Loop using Pydantic AI."""
        history = []
        
        # 1. LOAD AGENT WITH LATEST CONFIG
        # This fixes the issue where changing settings didn't apply until restart
        try:
            pydantic_agent = get_agent()
        except Exception as e:
            print(f"{Colors.RED}Failed to initialize Agent Engine: {e}{Colors.RESET}")
            input("Press Enter...")
            return

        TUI.header("AGENT CHAT", f"Model: {pydantic_agent.model.model_name}")
        print(f"{Colors.DIM}Type 'q' to exit.{Colors.RESET}")

        while True:
            user_in = TUI.prompt("You")
            if user_in.lower() in ['q', 'exit', 'quit', 'back']: return
            
            print(f"{Colors.DIM}Thinking...{Colors.RESET}")
            
            try:
                result = await pydantic_agent.run(user_in, deps=self.deps, message_history=history)
                print(f"\n{Colors.GREEN}AgentOS:{Colors.RESET} {result.output}")
                history = result.new_messages()
                
            except Exception as e:
                print(f"{Colors.RED}Agent Error: {e}{Colors.RESET}")
                if "404" in str(e):
                    print(f"\n{Colors.YELLOW}Tip: Go to 'Settings' and select a valid model installed in Ollama.{Colors.RESET}")

def main():
    parser = argparse.ArgumentParser(description="AgentOS: Your Personal System Agent")
    parser.add_argument("--json", action="store_true", help="Output JSON for LLM integration")
    parser.add_argument("module", nargs="?", help="Module (disk, memory, system, chat)")
    parser.add_argument("--action", help="Action to perform")
    parser.add_argument("--target", help="Target arg")
    parser.add_argument("--content", help="Content arg")
    parser.add_argument("--tags", help="Tags arg")

    args = parser.parse_args()
    agent = AgentOS()

    if not args.module:
        agent.run_main_menu()
        return
        
    if args.module == "chat":
        agent.run_chat_mode_sync()
        return

    # CLI / HEADLESS Handlers (Unchanged)
    result = {}
    try:
        # Disk Routing
        if args.module == "disk" and args.action:
            if args.action == "scan":
                result = [c.model_dump() for c in agent.disk.get_caches()]
            elif args.action == "clean":
                result = agent.disk.clean_cache(args.target).model_dump()
            elif args.action == "explore":
                path = args.target or "~"
                result = [i.model_dump() for i in agent.disk.explore_folder(path)]
            elif args.action == "large_files":
                threshold = args.target or "500M"
                result = agent.disk.list_large_files(threshold).model_dump()

        # Memory Routing
        elif args.module == "memory" and args.action:
            if args.action == "sync":
                result = agent.memory.ingest_shell_history().model_dump()
            elif args.action == "add_note":
                tags = args.tags.split(",") if args.tags else []
                result = agent.memory.add_note(args.content or "", tags).model_dump()
            elif args.action == "get_notes":
                result = [n.model_dump() for n in agent.memory.get_notes(args.tags)]
            elif args.action == "search":
                result = [h.model_dump() for h in agent.memory.search_history(args.content or "")]
            elif args.action == "scrub":
                result = agent.memory.scrub_history(args.content).model_dump()

        # System Routing
        elif args.module == "system" and args.action:
            if args.action == "status":
                result = agent.system.get_status()
            elif args.action == "docker_prune":
                result = agent.system.docker_prune().model_dump()
            elif args.action == "vacuum_logs":
                result = agent.system.vacuum_logs().model_dump()
            elif args.action == "empty_trash":
                result = agent.system.empty_trash().model_dump()
            elif args.action == "apt_clean":
                result = agent.system.apt_clean().model_dump()

    except Exception as e:
        result = {"error": str(e)}

    # Output
    if args.json:
        print(json.dumps(result, indent=2))
    else:
        # Simple text fallback
        if isinstance(result, list):
            for item in result: print(item)
        else:
            print(result)

if __name__ == "__main__":
    main()