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

class AgentOS:
    def __init__(self):
        self.disk = DiskSkill()
        self.memory = MemorySkill()
        self.system = SystemSkill()

    def run_main_menu(self):
        """The Master TUI."""
        while True:
            TUI.header("AGENT OS", "System Intelligence & Memory")
            print(f"1. {Colors.BLUE}[ Disk Manager ]{Colors.RESET}   Clean caches, analyze storage")
            print(f"2. {Colors.MAGENTA}[ Second Brain ]{Colors.RESET}   Notes, History, Recall")
            print(f"3. {Colors.YELLOW}[ System Tools ]{Colors.RESET}   Docker, Logs, Trash")
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

def main():
    parser = argparse.ArgumentParser(description="AgentOS: Your Personal System Agent")
    parser.add_argument("--json", action="store_true", help="Output JSON for LLM integration")
    
    subparsers = parser.add_subparsers(dest="module", help="Select capability module")
    
    # --- DISK SUBCOMMANDS ---
    disk_parser = subparsers.add_parser("disk", help="Disk cleaning and analysis")
    disk_parser.add_argument("--action", choices=["scan", "clean", "explore", "large_files"], required=True)
    disk_parser.add_argument("--target", help="Target ID for cleaning (pip, npm, etc) or path for explore")

    # --- MEMORY SUBCOMMANDS ---
    mem_parser = subparsers.add_parser("memory", help="Notes and History")
    mem_parser.add_argument("--action", choices=["add_note", "get_notes", "sync", "search", "scrub"], required=True)
    mem_parser.add_argument("--content", help="Note content or Search query")
    mem_parser.add_argument("--tags", help="Comma-separated tags")

    # --- SYSTEM SUBCOMMANDS ---
    sys_parser = subparsers.add_parser("system", help="System maintenance")
    sys_parser.add_argument("--action", choices=["docker_prune", "vacuum_logs", "empty_trash", "apt_clean", "status"], required=True)

    args = parser.parse_args()
    agent = AgentOS()

    # 1. INTERACTIVE MODE (No args)
    if not args.module:
        agent.run_main_menu()
        return

    # 2. HEADLESS / CLI MODE
    result = {}
    
    try:
        # Disk Routing
        if args.module == "disk":
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
        elif args.module == "memory":
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
        elif args.module == "system":
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
        # Simple text fallback
        if isinstance(result, list):
            for item in result: print(item)
        else:
            print(result)

if __name__ == "__main__":
    main()