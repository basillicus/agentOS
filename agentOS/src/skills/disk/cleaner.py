import os
import subprocess
import shutil
import json
import argparse
import sys
from typing import List, Dict, Union

# Add project root to path for imports
# Assumes structure: agentOS/src/skills/disk/cleaner.py
# We want to import form agentOS/src/core/schemas.py
current_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.abspath(os.path.join(current_dir, "../../../"))
if project_root not in sys.path:
    sys.path.append(project_root)

from src.core.schemas import CacheItem, CondaEnvironment, ActionResponse, DiskUsage, FileScanResult

class DiskSkill:
    """
    A skill for managing disk space, caches, and analyzing directory usage.
    
    Capabilities:
    1. Analyze and clean development caches (pip, npm, conda, uv).
    2. Manage Conda environments.
    3. Scan for large files.
    4. Explore folder structures by size.
    """

    def __init__(self):
        # Configuration only - NO HEAVY IO HERE
        self.known_caches = [
            {"id": "pip", "name": "Pip Cache", "path": "~/.cache/pip", "cmd": "pip cache purge", "desc": "Python wheel downloads"},
            {"id": "uv", "name": "UV Cache", "path": "~/.cache/uv", "cmd": "uv cache clean", "desc": "UV package downloads"},
            {"id": "rattler", "name": "Rattler/Pixi", "path": "~/.cache/rattler", "cmd": "pixi clean cache", "desc": "Pixi package cache"},
            {"id": "npm", "name": "NPM Cache", "path": "~/.npm", "cmd": "npm cache clean --force", "desc": "Node modules cache"},
            {"id": "conda_pkgs", "name": "Conda Pkgs", "path": "~/miniconda3/pkgs", "cmd": "conda clean --all -y", "desc": "Unused Conda packages"},
            {"id": "docker", "name": "Docker System", "path": "/var/lib/docker", "cmd": "docker system prune -f", "desc": "Dangling images & stopped containers"},
            {"id": "trash", "name": "Trash Can", "path": "~/.local/share/Trash", "cmd": "rm -rf ~/.local/share/Trash/*", "desc": "Deleted files"}
        ]

    # --- HELPERS ---

    def _run(self, cmd: str) -> tuple[str, str, int]:
        try:
            res = subprocess.run(cmd, shell=True, text=True, capture_output=True, check=False)
            return res.stdout.strip(), res.stderr.strip(), res.returncode
        except Exception as e:
            return "", str(e), 1

    def _size(self, path: str) -> int:
        path = os.path.expanduser(path)
        if not os.path.exists(path): return 0
        try:
            # -s for summary, -k for kb. * 1024 to get bytes.
            out, _, _ = self._run(f"du -sk '{path}' | cut -f1")
            return int(out) * 1024
        except: return 0

    def _fmt_size(self, size_bytes: int) -> str:
        if size_bytes == 0: return "0B"
        for unit in ['B', 'KB', 'MB', 'GB', 'TB']:
            if size_bytes < 1024.0: return f"{size_bytes:.1f}{unit}"
            size_bytes /= 1024.0
        return f"{size_bytes:.1f}TB"

    # --- ACTIONS (AGENTS CALL THESE) ---

    def get_caches(self) -> List[CacheItem]:
        """
        Scans known system and development caches to calculate their current size.
        """
        results = []
        for c in self.known_caches:
            size = self._size(c['path'])
            results.append(CacheItem(
                id=c['id'],
                name=c['name'],
                path=os.path.expanduser(c['path']),
                size_bytes=size,
                size_human=self._fmt_size(size),
                description=c['desc']
            ))
        return results

    def clean_cache(self, cache_id: str) -> ActionResponse:
        """
        Performs the cleaning command for a specific cache ID.
        
        Args:
            cache_id: The ID of the cache to clean (e.g., 'pip', 'docker').
        """
        target = next((c for c in self.known_caches if c['id'] == cache_id), None)
        if not target:
            return ActionResponse(success=False, message="Cache ID not found", error="Invalid ID")
        
        out, err, code = self._run(target['cmd'])
        if code == 0:
            return ActionResponse(success=True, message=f"Cleaned {target['name']}", affected_path=target['path'])
        return ActionResponse(success=False, message="Command failed", error=err or out)

    def list_large_files(self, threshold: str = "500M") -> FileScanResult:
        """
        Finds files in the home directory larger than the specified threshold.
        
        Args:
            threshold: Size string like '100M', '1G'.
        """
        # Exclude hidden files/directories generally to avoid noise
        cmd = f"find ~ -type f -size +{threshold} -not -path '*/.*' -exec du -h {{}} + | sort -rh | head -n 20"
        out, err, _ = self._run(cmd)
        
        files = []
        for line in out.split('\n'):
            if not line: continue
            parts = line.split('\t')
            if len(parts) == 2:
                path = parts[1]
                size_str = parts[0]
                files.append(DiskUsage(
                    path=path,
                    name=os.path.basename(path),
                    size_human=size_str,
                    size_bytes=0 # Placeholder
                ))
        return FileScanResult(files=files, threshold_used=threshold)

    def explore_folder(self, path: str = "~") -> List[DiskUsage]:
        """
        Lists immediate subdirectories of a path, sorted by size (smallest to largest).
        """
        start_path = os.path.expanduser(path)
        if not os.path.exists(start_path):
            return []
            
        items = []
        try:
            with os.scandir(start_path) as it:
                for entry in it:
                    if entry.is_dir(follow_symlinks=False):
                        size = self._size(entry.path)
                        items.append(DiskUsage(
                            name=entry.name,
                            path=entry.path,
                            size_bytes=size,
                            size_human=self._fmt_size(size)
                        ))
        except PermissionError:
            pass
            
        # Sort Smallest -> Largest
        return sorted(items, key=lambda x: x.size_bytes)

    # --- TUI IMPLEMENTATION (HUMAN INTERFACE) ---

    def run_tui(self):
        """Interactive Text User Interface."""
        while True:
            os.system('clear')
            print("==========================================")
            print("       AGENT OS - DISK MANAGER")
            print("==========================================")
            print("1. Scan & Clean Caches")
            print("2. Explore Folder Sizes")
            print("3. Find Large Files")
            print("q. Quit")
            
            choice = input("\nChoice: ").strip()
            
            if choice == 'q': break
            elif choice == '1': self._tui_caches()
            elif choice == '2': self._tui_explorer("~")
            elif choice == '3': self._tui_large_files()

    def _tui_caches(self):
        print("\nScanning caches... (this takes a second)")
        caches = self.get_caches()
        while True:
            os.system('clear')
            print("[ CACHE CLEANER ]")
            for i, c in enumerate(caches):
                print(f" {i+1}. {c.name:<20} {c.size_human:<8} ({c.description})")
            
            print("\nCommands: <number> to clean, 'b' back")
            choice = input("Choice: ").strip()
            if choice == 'b': return
            if choice.isdigit() and 0 < int(choice) <= len(caches):
                target = caches[int(choice)-1]
                print(f"Cleaning {target.name}...")
                res = self.clean_cache(target.id)
                if res.success: print("Success!")
                else: print(f"Error: {res.error}")
                input("Press Enter...")
                # Update size
                target.size_bytes = self._size(target.path)
                target.size_human = self._fmt_size(target.size_bytes)

    def _tui_explorer(self, path):
        current_path = path
        while True:
            os.system('clear')
            print(f"[ EXPLORING: {current_path} ]")
            print("Scanning...")
            items = self.explore_folder(current_path)
            
            # Print Smallest -> Largest
            print(f"{ '#':<4} {'Size':<10} {'Name'}")
            print("-" * 40)
            for i, item in enumerate(items):
                print(f"{i+1:<4} {item.size_human:<10} {item.name}/")
                
            print("\nCommands: <number> open, 'u' up, 'b' back")
            choice = input("Choice: ").strip()
            
            if choice == 'b': return
            if choice == 'u': 
                current_path = os.path.dirname(os.path.expanduser(current_path))
            elif choice.isdigit() and 0 < int(choice) <= len(items):
                current_path = items[int(choice)-1].path

    def _tui_large_files(self):
        thresh = input("Enter size (e.g. 500M): ").strip() or "500M"
        print("Scanning...")
        res = self.list_large_files(thresh)
        print("\n[ LARGE FILES ]")
        for f in res.files:
            print(f"{f.size_human:<10} {f.path}")
        input("\nPress Enter...")

# --- CLI ENTRY ---

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="AgentOS Disk Skill")
    parser.add_argument("--json", action="store_true", help="Output JSON for LLM")
    parser.add_argument("--action", help="LLM Action: get_caches, clean_cache, explore_folder")
    parser.add_argument("--arg", help="Argument for action (id, path, etc)")
    
    args = parser.parse_args()
    skill = DiskSkill()
    
    if args.json:
        # PURE AGENT MODE
        try:
            if args.action == "get_caches":
                print(json.dumps([c.dict() for c in skill.get_caches()]))
            elif args.action == "clean_cache":
                print(json.dumps(skill.clean_cache(args.arg).dict()))
            elif args.action == "explore_folder":
                path = args.arg or "~"
                print(json.dumps([i.dict() for i in skill.explore_folder(path)]))
            else:
                print(json.dumps({"error": "Unknown action"}))
        except Exception as e:
            print(json.dumps({"error": str(e)}))
    else:
        # HUMAN MODE
        skill.run_tui()
