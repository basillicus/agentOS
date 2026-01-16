#!/usr/bin/env python3
import sys
import os
import argparse
import json

# Ensure we can import from src
current_dir = os.path.dirname(os.path.abspath(__file__))
if current_dir not in sys.path:
    sys.path.append(current_dir)

from src.skills.disk.cleaner import DiskSkill
from src.skills.memory.manager import MemorySkill
from src.skills.system.tools import SystemSkill
from src.core.style import TUI, Colors
from src.core.llm import LLMClient

class AgentOS:
    def __init__(self):
        self.disk = DiskSkill()
        self.memory = MemorySkill()
        self.system = SystemSkill()
        self.llm = LLMClient()

    def run_main_menu(self):
        """The Master TUI."""
        while True:
            TUI.header("AGENT OS", "System Intelligence & Memory")
            print(f"1. {Colors.BLUE}[ Disk Manager ]{Colors.RESET}   Clean caches, analyze storage")
            print(f"2. {Colors.MAGENTA}[ Second Brain ]{Colors.RESET}   Notes, History, Recall")
            print(f"3. {Colors.YELLOW}[ System Tools ]{Colors.RESET}   Docker, Logs, Trash")
            print(f"4. {Colors.GREEN}[ Agent Chat ]{Colors.RESET}     Talk to AgentOS")
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
                self.run_chat_mode()

    def run_chat_mode(self):
        """Interactive Chat Loop with Tool Execution."""
        history = []
        TUI.header("AGENT CHAT", "Ask me to clean disk, find notes, etc.")
        if not self.llm.api_key:
            print(f"{Colors.YELLOW}Running in SIMULATION MODE (No API Key detected).{Colors.RESET}")
        
        while True:
            user_in = TUI.prompt("You")
            if user_in.lower() in ['q', 'exit', 'quit', 'back']: return
            
            # Get Response from LLM
            print(f"{Colors.DIM}Thinking...{Colors.RESET}")
            text, tool_call = self.llm.chat(user_in, history)
            
            if text:
                print(f"\n{Colors.GREEN}AgentOS:{Colors.RESET} {text}")
                history.append({"role": "assistant", "content": text})
            
            if tool_call:
                self._handle_tool_call(tool_call)

    def _handle_tool_call(self, tool_call):
        """Executes the tool requested by the LLM."""
        module = tool_call.get("tool")
        args = tool_call.get("args", {})
        
        print(f"\n{Colors.CYAN}>> Agent is requesting to run: {module.upper()} / {args.get('action')}{Colors.RESET}")
        print(f"   Args: {args}")
        
        confirm = input("Execute? (Y/n): ").strip().lower()
        if confirm == 'n':
            print("Action cancelled.")
            return

        result = {}
        try:
            if module == "disk":
                if args['action'] == "scan":
                    result = [c.dict() for c in self.disk.get_caches()]
                elif args['action'] == "clean":
                    result = self.disk.clean_cache(args['target']).dict()
                elif args['action'] == "explore":
                    result = [i.dict() for i in self.disk.explore_folder(args.get('target', "~"))]
                elif args['action'] == "large_files":
                    result = self.disk.list_large_files(args.get('target', "500M")).dict()

            elif module == "memory":
                if args['action'] == "add_note":
                    result = self.memory.add_note(args.get('content'), args.get('tags', '').split(',') ).dict()
                elif args['action'] == "search":
                    result = [h.dict() for h in self.memory.search_history(args.get('content'))]
                elif args['action'] == "sync":
                    result = self.memory.ingest_shell_history().dict()

            elif module == "system":
                if args['action'] == "docker_prune":
                    result = self.system.docker_prune().dict()
                elif args['action'] == "status":
                    result = self.system.get_status()

            # Show Result
            print(f"\n{Colors.GREEN}Result:{Colors.RESET}")
            if isinstance(result, list):
                # Summarize long lists
                for item in result[:5]: print(item)
                if len(result) > 5: print(f"... and {len(result)-5} more.")
            else:
                print(json.dumps(result, indent=2))
                
        except Exception as e:
            print(f"{Colors.RED}Error executing tool: {e}{Colors.RESET}")

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

    # 1. INTERACTIVE MODE (No args)
    if not args.module:
        agent.run_main_menu()
        return
        
    # 2. CHAT MODE
    if args.module == "chat":
        agent.run_chat_mode()
        return

    # 3. HEADLESS / CLI MODE
    # (Previous CLI logic logic maintained below...)
    result = {}
    try:
        # Disk Routing
        if args.module == "disk" and args.action:
            if args.action == "scan":
                result = [c.dict() for c in agent.disk.get_caches()]
            elif args.action == "clean":
                result = agent.disk.clean_cache(args.target).dict()
            elif args.action == "explore":
                path = args.target or "~"
                result = [i.dict() for i in agent.disk.explore_folder(path)]
            elif args.action == "large_files":
                threshold = args.target or "500M"
                result = agent.disk.list_large_files(threshold).dict()

        # Memory Routing
        elif args.module == "memory" and args.action:
            if args.action == "sync":
                result = agent.memory.ingest_shell_history().dict()
            elif args.action == "add_note":
                tags = args.tags.split(",") if args.tags else []
                result = agent.memory.add_note(args.content or "", tags).dict()
            elif args.action == "get_notes":
                result = [n.dict() for n in agent.memory.get_notes(args.tags)]
            elif args.action == "search":
                result = [h.dict() for h in agent.memory.search_history(args.content or "")]
            elif args.action == "scrub":
                result = agent.memory.scrub_history(args.content).dict()

        # System Routing
        elif args.module == "system" and args.action:
            if args.action == "status":
                result = agent.system.get_status()
            elif args.action == "docker_prune":
                result = agent.system.docker_prune().dict()
            elif args.action == "vacuum_logs":
                result = agent.system.vacuum_logs().dict()
            elif args.action == "empty_trash":
                result = agent.system.empty_trash().dict()
            elif args.action == "apt_clean":
                result = agent.system.apt_clean().dict()

    except Exception as e:
        result = {"error": str(e)}

    # Output
    if args.json:
        print(json.dumps(result, indent=2))
    else:
        if isinstance(result, list):
            for item in result: print(item)
        else:
            print(result)

if __name__ == "__main__":
    main()
