import os
import subprocess
import shutil
import sys
import json
import argparse

# Path setup
current_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.abspath(os.path.join(current_dir, "../../../"))
if project_root not in sys.path:
    sys.path.append(project_root)

from src.core.schemas import ActionResponse
from src.core.style import TUI, Colors

class SystemSkill:
    """
    Manages system-level maintenance: Docker, Journals, Trash, Apt.
    """
    
    def __init__(self):
        pass

    def _run(self, cmd: str) -> tuple[str, str, int]:
        try:
            res = subprocess.run(cmd, shell=True, text=True, capture_output=True, check=False)
            return res.stdout.strip(), res.stderr.strip(), res.returncode
        except Exception as e:
            return "", str(e), 1

    def _get_size(self, path: str) -> str:
        if not os.path.exists(path): return "0B"
        try:
            out, _, _ = self._run(f"du -sh '{path}' | cut -f1")
            return out
        except: return "0B"

    # --- ACTIONS ---

    def docker_prune(self) -> ActionResponse:
        """Removes stopped containers, dangling images, and build cache."""
        # Check if docker exists first
        if shutil.which("docker") is None:
            return ActionResponse(success=False, message="Docker not found on this system.")
            
        out, err, code = self._run("docker system prune -f")
        if code == 0:
            return ActionResponse(success=True, message="Docker system pruned.", affected_path="Docker")
        return ActionResponse(success=False, message="Docker prune failed.", error=err or out)

    def vacuum_logs(self, retention="2weeks") -> ActionResponse:
        """Vacuums systemd journals."""
        cmd = f"sudo journalctl --vacuum-time={retention}"
        out, err, code = self._run(cmd)
        # journalctl might return non-zero if no sudo, or if nothing to do.
        # We assume success if we see output or generic success code
        if "Vacuuming done" in err or code == 0:
            return ActionResponse(success=True, message=f"Logs vacuumed ({retention}).")
        return ActionResponse(success=False, message="Vacuum failed (needs sudo?)", error=err)

    def apt_clean(self) -> ActionResponse:
        """Cleans apt cache."""
        out, err, code = self._run("sudo apt-get clean")
        if code == 0:
            return ActionResponse(success=True, message="Apt cache cleaned.")
        return ActionResponse(success=False, message="Apt clean failed", error=err)

    def empty_trash(self) -> ActionResponse:
        """Empties the ~/.local/share/Trash folder."""
        trash_path = os.path.expanduser("~/.local/share/Trash")
        if not os.path.exists(trash_path):
            return ActionResponse(success=True, message="Trash is already empty.")
        
        try:
            # We delete the contents of 'files' and 'info' subdirs
            for sub in ["files", "info"]:
                p = os.path.join(trash_path, sub)
                if os.path.exists(p):
                    shutil.rmtree(p)
                    os.makedirs(p) # Recreate empty dir
            return ActionResponse(success=True, message="Trash emptied.", affected_path=trash_path)
        except Exception as e:
            return ActionResponse(success=False, message="Failed to empty trash", error=str(e))

    def get_status(self) -> dict:
        """Returns sizes of various cleanup targets."""
        trash_size = self._get_size(os.path.expanduser("~/.local/share/Trash"))
        apt_size = self._get_size("/var/cache/apt/archives")
        
        # Journal size
        j_out, _, _ = self._run("journalctl --disk-usage")
        j_size = j_out.split(': ')[-1].strip() if 'Archived' in j_out else "Unknown"
        
        return {
            "trash": trash_size,
            "apt": apt_size,
            "journal": j_size
        }

    # --- TUI ---

    def run_tui(self):
        while True:
            stats = self.get_status()
            TUI.header("SYSTEM MAINTENANCE", "Docker, Logs, & Trash")
            
            print(f"1. [ Docker ]      Prune System (Images/Containers)")
            print(f"2. [ Logs ]        Vacuum Journals (Size: {stats['journal']})")
            print(f"3. [ Apt ]         Clean Package Cache (Size: {stats['apt']})")
            print(f"4. [ Trash ]       Empty Trash (Size: {stats['trash']})")
            print("q. Back")
            
            choice = TUI.prompt("Choice")
            
            if choice == 'q': return
            
            elif choice == '1':
                print("Pruning Docker...")
                res = self.docker_prune()
                if res.success: TUI.success(res.message)
                else: TUI.error(res.message + f" {res.error or ''}")
                input("Press Enter...")
                
            elif choice == '2':
                print("Vacuuming Logs...")
                res = self.vacuum_logs()
                if res.success: TUI.success(res.message)
                else: TUI.error(res.message + f" {res.error or ''}")
                input("Press Enter...")

            elif choice == '3':
                print("Cleaning Apt...")
                res = self.apt_clean()
                if res.success: TUI.success(res.message)
                else: TUI.error(res.message + f" {res.error or ''}")
                input("Press Enter...")

            elif choice == '4':
                print("Emptying Trash...")
                res = self.empty_trash()
                if res.success: TUI.success(res.message)
                else: TUI.error(res.message + f" {res.error or ''}")
                input("Press Enter...")

if __name__ == "__main__":
    # Test run
    skill = SystemSkill()
    skill.run_tui()
