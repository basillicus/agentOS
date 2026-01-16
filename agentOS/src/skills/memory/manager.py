import sqlite3
import os
import sys
import json
import argparse
import re
from datetime import datetime
from typing import List, Optional

# Path setup
current_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.abspath(os.path.join(current_dir, "../../../"))
if project_root not in sys.path:
    sys.path.append(project_root)

from src.core.schemas import Note, HistoryItem, ActionResponse
from src.core.style import TUI, Colors

class MemorySkill:
    """
    Manages the 'Second Brain' of the Agent: Notes and Command History.
    Uses a local SQLite database.
    """
    
    def __init__(self, db_path=None):
        if not db_path:
            self.db_path = os.path.join(project_root, "data", "agent.db")
        else:
            self.db_path = db_path
            
        self._init_db()

    def _init_db(self):
        """Creates tables and sets strict file permissions."""
        db_dir = os.path.dirname(self.db_path)
        os.makedirs(db_dir, exist_ok=True)
        
        conn = sqlite3.connect(self.db_path)
        c = conn.cursor()
        
        c.execute('''CREATE TABLE IF NOT EXISTS notes 
                     (id INTEGER PRIMARY KEY, content TEXT, tags TEXT, created_at TEXT)''')
        
        c.execute('''CREATE TABLE IF NOT EXISTS history 
                     (id INTEGER PRIMARY KEY, command TEXT UNIQUE, context TEXT, timestamp TEXT, notes TEXT)''')
        
        conn.commit()
        conn.close()

        # SECURITY: Lock down file permissions (Read/Write for Owner only)
        try:
            os.chmod(self.db_path, 0o600)
        except Exception:
            pass

    def _get_conn(self):
        return sqlite3.connect(self.db_path)

    # --- SECURITY & SANITIZATION ---

    def sanitize_command(self, cmd: str) -> str:
        """
        Instead of blocking commands, we mask the values of sensitive keys.
        Ex: 'export API_KEY=12345' -> 'export API_KEY=[REDACTED]'
        """
        # Patterns to identify sensitive assignments
        patterns = [
            # Shell assignments: export KEY=value OR KEY="value"
            # Using raw strings r'' to simplify regex
            r"(?i)\b((?:[A-Z_]*)(?:PASS|SECRET|KEY|TOKEN|AUTH|SIG)[A-Z_0-9]*)([\s]*=[\s]*)(['\"]?)([^'\"\s;&|]+)(['\"]?)",
            # AWS/Cloud CLI flags: --secret-key value
            r"(--[a-z0-9-]*?(?:secret|key|token|password)[a-z0-9-]*)([\s]+)([^ \n]+)"
        ]
        
        sanitized = cmd
        for pattern in patterns:
            # We use a callback to keep the structure but replace the value
            def replace_val(match):
                groups = match.groups()
                # Determine which group is the value based on length of groups
                if len(groups) == 5: # Shell assignment
                    key, sep, q1, val, q2 = groups
                    return f"{key}{sep}{q1}***REDACTED***{q2}"
                elif len(groups) == 3: # CLI Flag
                    flag, sep, val = groups
                    return f"{flag}{sep}***REDACTED***"
                return match.group(0)

            sanitized = re.sub(pattern, replace_val, sanitized)
            
        return sanitized

    def scrub_history(self, pattern: str) -> ActionResponse:
        """
        Permanently deletes history items matching a regex pattern.
        """
        conn = self._get_conn()
        c = conn.cursor()
        
        try:
            c.execute("SELECT count(*) FROM history WHERE command LIKE ?", (f"%{pattern}%",))
            count = c.fetchone()[0]
            
            if count == 0:
                return ActionResponse(success=True, message="No matches found.")
            
            c.execute("DELETE FROM history WHERE command LIKE ?", (f"%{pattern}%",))
            conn.commit()
            return ActionResponse(success=True, message=f"Scrubbed {count} records matching '{pattern}'")
        except Exception as e:
            return ActionResponse(success=False, message=str(e))
        finally:
            conn.close()

    def delete_history_item(self, item_id: int) -> ActionResponse:
        conn = self._get_conn()
        c = conn.cursor()
        c.execute("DELETE FROM history WHERE id=?", (item_id,))
        conn.commit()
        conn.close()
        return ActionResponse(success=True, message="Deleted.")

    # --- HISTORY SYNC ---

    def ingest_shell_history(self) -> ActionResponse:
        """Reads shell history, sanitizes secrets, and imports."""
        shells = [".bash_history", ".zsh_history"]
        count = 0
        conn = self._get_conn()
        c = conn.cursor()
        
        for shell_file in shells:
            path = os.path.expanduser(f"~/{shell_file}")
            if os.path.exists(path):
                try:
                    with open(path, "r", errors="ignore") as f:
                        for line in f:
                            cmd = line.strip()
                            if shell_file == ".zsh_history" and ";" in cmd:
                                cmd = cmd.split(";", 1)[1]
                            
                            if cmd and len(cmd) > 2:
                                # SANITIZE instead of SKIP
                                safe_cmd = self.sanitize_command(cmd)

                                try:
                                    c.execute("INSERT OR IGNORE INTO history (command, context, timestamp) VALUES (?, ?, ?)", 
                                              (safe_cmd, "shell_import", datetime.now().isoformat()))
                                    if c.rowcount > 0: count += 1
                                except: pass
                except Exception as e:
                    return ActionResponse(success=False, message=f"Error reading {shell_file}: {e}")
        
        conn.commit()
        conn.close()
        return ActionResponse(success=True, message=f"Imported {count} commands.")

    # --- NOTES API ---
    def add_note(self, content: str, tags: List[str] = []) -> ActionResponse:
        conn = self._get_conn()
        c = conn.cursor()
        try:
            c.execute("INSERT INTO notes (content, tags, created_at) VALUES (?, ?, ?)", 
                      (content, ",".join(tags), datetime.now().isoformat()))
            conn.commit()
            return ActionResponse(success=True, message="Note added")
        except Exception as e:
            return ActionResponse(success=False, message=str(e))
        finally:
            conn.close()

    def get_notes(self, tag_filter: str = None) -> List[Note]:
        conn = self._get_conn()
        c = conn.cursor()
        query = "SELECT id, content, tags, created_at FROM notes"
        params = ()
        if tag_filter:
            query += " WHERE tags LIKE ?"
            params = (f"%{tag_filter}%",)
        query += " ORDER BY id DESC"
        c.execute(query, params)
        rows = c.fetchall()
        conn.close()
        return [Note(id=r[0], content=r[1], tags=r[2].split(",") if r[2] else [], created_at=r[3]) for r in rows]

    def delete_note(self, note_id: int) -> ActionResponse:
        conn = self._get_conn()
        c = conn.cursor()
        c.execute("DELETE FROM notes WHERE id=?", (note_id,))
        conn.commit()
        return ActionResponse(success=True, message="Note deleted")

    # --- HISTORY API ---
    def add_history(self, command: str, context: str = "~") -> ActionResponse:
        safe_cmd = self.sanitize_command(command)
            
        conn = self._get_conn()
        c = conn.cursor()
        try:
            c.execute("INSERT INTO history (command, context, timestamp) VALUES (?, ?, ?)", 
                      (safe_cmd, context, datetime.now().isoformat()))
            conn.commit()
            return ActionResponse(success=True, message="Command saved")
        except sqlite3.IntegrityError:
             return ActionResponse(success=True, message="Command already exists")
        finally:
            conn.close()

    def search_history(self, term: str) -> List[HistoryItem]:
        conn = self._get_conn()
        c = conn.cursor()
        c.execute("SELECT id, command, context, timestamp, notes FROM history WHERE command LIKE ? ORDER BY id DESC LIMIT 50", 
                  (f"%{term}%",))
        rows = c.fetchall()
        conn.close()
        return [HistoryItem(id=r[0], command=r[1], context=r[2], timestamp=r[3], notes=r[4]) for r in rows]

    # --- TUI ---

    def run_tui(self):
        while True:
            TUI.header("MEMORY MANAGER", "Second Brain: Notes & Command History")
            print("1. [ Notes ]    Manage your thoughts")
            print("2. [ History ]  Search past commands")
            print("3. [ Sync ]     Import Shell History")
            print(f"4. {Colors.RED}[ Scrub ]    Delete Records{Colors.RESET}")
            print("q. Quit")
            
            choice = TUI.prompt("Choice")
            
            if choice == 'q': break
            elif choice == '1': self._tui_notes()
            elif choice == '2': self._tui_history()
            elif choice == '3':
                print("\nImporting history...")
                res = self.ingest_shell_history()
                if res.success: TUI.success(res.message)
                else: TUI.error(res.message)
                input("Press Enter...")
            elif choice == '4': self._tui_scrub()

    def _tui_notes(self):
        while True:
            notes = self.get_notes()
            TUI.header("MY NOTES", f"Total: {len(notes)}")
            if not notes: print("  (No notes found)")
            for note in notes[:10]:
                tags = f"[{', '.join(note.tags)}]" if note.tags else ""
                print(f"{Colors.YELLOW}{note.id}.{Colors.RESET} {note.content[:50]:<40} {Colors.DIM}{tags}{Colors.RESET}")
            print("\na. Add Note  |  d <id>. Delete  |  b. Back")
            choice = TUI.prompt("Action")
            if choice == 'b': return
            elif choice == 'a':
                c = TUI.prompt("Content")
                t = TUI.prompt("Tags").split(',')
                self.add_note(c, [x.strip() for x in t if x.strip()])
            elif choice.startswith('d '):
                try: self.delete_note(int(choice.split()[1]))
                except: pass

    def _tui_history(self):
        while True:
            TUI.header("COMMAND HISTORY", "Search your past actions")
            term = TUI.prompt("Search Term (Enter for all)")
            items = self.search_history(term)
            
            if not items:
                print(f"\n{Colors.YELLOW}(No history found){Colors.RESET}")
            else:
                print(f"\nFound {len(items)} items:")
                for item in items:
                    print(f"{Colors.YELLOW}{item.id:<4}{Colors.RESET} {Colors.GREEN}{item.command:<60}{Colors.RESET}")
            
            print(f"\n{Colors.RED}d <id>. Delete Item{Colors.RESET}  |  b. Back")
            choice = TUI.prompt("Action")
            
            if choice == 'b': return
            elif choice.startswith('d '):
                try:
                    self.delete_history_item(int(choice.split()[1]))
                    print("Deleted.")
                except: pass

    def _tui_scrub(self):
        while True:
            TUI.header(f"{Colors.RED}DANGER ZONE: SCRUB HISTORY{Colors.RESET}")
            print("Remove commands matching a specific word or pattern.")
            pattern = TUI.prompt("Enter pattern to WIPE (or 'b' to back)")
            if pattern == 'b': return
            if not pattern: continue
            
            confirm = TUI.prompt(f"Are you sure you want to delete matches for '{pattern}'? (yes/no)")
            if confirm == 'yes':
                res = self.scrub_history(pattern)
                if res.success: TUI.success(res.message)
                else: TUI.error(res.message)
                input("Press Enter...")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="AgentOS Memory Skill")
    parser.add_argument("--json", action="store_true", help="Output JSON for LLM")
    parser.add_argument("--action", help="Actions: get_notes, add_note, search_history, sync_history, scrub")
    parser.add_argument("--arg", help="Arg for scrub or search")
    parser.add_argument("--content", help="Content for notes")
    parser.add_argument("--tags", help="Tags for notes")
    
    args = parser.parse_args()
    skill = MemorySkill()
    
    if args.json:
        try:
            if args.action == "sync_history":
                print(json.dumps(skill.ingest_shell_history().dict(), indent=2))
            elif args.action == "scrub" and args.arg:
                print(json.dumps(skill.scrub_history(args.arg).dict(), indent=2))
            elif args.action == "get_notes":
                 print(json.dumps([n.dict() for n in skill.get_notes()], indent=2))
            elif args.action == "add_note":
                 tags = args.tags.split(",") if args.tags else []
                 print(json.dumps(skill.add_note(args.content or "", tags).dict(), indent=2))
            elif args.action == "search_history":
                 print(json.dumps([h.dict() for h in skill.search_history(args.query or "")], indent=2))
            else:
                print(json.dumps({"error": "Invalid action"}))
        except Exception as e:
            print(json.dumps({"error": str(e)}))
    else:
        skill.run_tui()
