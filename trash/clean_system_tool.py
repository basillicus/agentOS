import os
import subprocess
import sys
import shutil

# --- UTILITY FUNCTIONS ---

def run_command(command, shell=True, verbose=False):
    """Runs a shell command. Returns (stdout, stderr, returncode)."""
    try:
        if verbose:
            subprocess.run(command, shell=shell, check=False)
            return "", "", 0
        else:
            result = subprocess.run(
                command, 
                shell=shell, 
                text=True, 
                capture_output=True, 
                check=False
            )
            return result.stdout.strip(), result.stderr.strip(), result.returncode
    except Exception as e:
        return "", str(e), 1

def human_readable(size_bytes):
    if size_bytes == 0: return "0B"
    for unit in ['B', 'KB', 'MB', 'GB', 'TB']:
        if size_bytes < 1024.0:
            return f"{size_bytes:.1f}{unit}"
        size_bytes /= 1024.0
    return f"{size_bytes:.1f}TB"

def get_dir_size(path):
    """Returns size of a directory in bytes using du."""
    if not os.path.exists(path): return 0
    # -s for summary, -b for bytes (linux) or -k (posix)
    out, _, _ = run_command(f"du -sk '{path}' | cut -f1")
    try:
        return int(out) * 1024
    except:
        return 0

def clear_screen():
    os.system('clear')

def print_header(title):
    print("=" * 60)
    print(f"{title.center(60)}")
    print("=" * 60)

# --- SYSTEM TASKS ---

def system_tasks_menu():
    last_output = "" # State to keep output visible

    while True:
        clear_screen()
        # Check Sizes (Dynamic)
        trash_size = human_readable(get_dir_size(os.path.expanduser("~/.local/share/Trash")))
        journal_size_raw, _, _ = run_command("journalctl --disk-usage") 
        journal_size = journal_size_raw.split(': ')[-1] if 'Archived' in journal_size_raw else "Unknown"
        
        apt_size = "0B"
        if os.path.exists("/var/cache/apt/archives"):
            apt_size = human_readable(get_dir_size("/var/cache/apt/archives"))

        if last_output:
            print(last_output)
            print("-" * 60)

        print_header("SYSTEM CLEANUP TOOLS")
        print("\nWARNING: These actions affect system configuration or deleted files.\n")
        
        print(f"1. [ Docker Prune ]")
        print("   - Removes: Stopped containers, dangling images, build cache.")
        
        print(f"\n2. [ Vacuum Logs ] (Current: {journal_size})")
        print("   - Action: Keeps only last 2 weeks of logs.")

        print(f"\n3. [ Apt Clean ] (Current: {apt_size})")
        print("   - Action: Removes downloaded .deb files.")

        print(f"\n4. [ Empty Trash ] (Current: {trash_size})")
        print("   - Action: Permanently deletes files in Trash.")
        
        print("\n5. [ Large File Scan ]")
        print("   - Find individual large files.")

        print("\nb. Back to Main Menu")
        
        choice = input("\nEnter choice: ").strip().lower()
        
        if choice == 'b': return
        
        last_output = "" # Reset output unless we set it

        if choice == '1':
            print("\nRunning 'docker system prune'...")
            run_command("docker system prune", verbose=True)
            input("\nDone. Press Enter...")
            
        elif choice == '2':
            print("\nVacuuming journals...")
            out, err, _ = run_command("sudo journalctl --vacuum-time=2weeks")
            last_output = f"\n[Journal Vacuum Log]\n{out}\n{err}"

        elif choice == '3':
            print("\nCleaning Apt cache...")
            out, err, _ = run_command("sudo apt-get clean")
            last_output = "\nApt Cache Cleaned."

        elif choice == '4':
            print("\nEmptying Trash...")
            path = os.path.expanduser("~/.local/share/Trash/files")
            if os.path.exists(path):
                shutil.rmtree(path)
                os.makedirs(path)
            path_info = os.path.expanduser("~/.local/share/Trash/info")
            if os.path.exists(path_info):
                shutil.rmtree(path_info)
                os.makedirs(path_info)
            last_output = "\nTrash Emptied."

        elif choice == '5':
            size_str = input("\nEnter minimum file size (e.g. 500M, 1G) [default: 500M]: ").strip()
            if not size_str: size_str = "500M"
            
            print(f"\nScanning for files > {size_str}...")
            cmd = f"find ~ -type f -size +{size_str} -not -path '*/.*' -exec du -h {{}} + | sort -rh | head -n 20"
            out, err, _ = run_command(cmd)
            last_output = f"\n[ Large Files (> {size_str}) ]\n{out}"

# --- FOLDER EXPLORER ---

def get_subfolders_info(path):
    """Returns list of (name, size_bytes, path) for immediate subfolders."""
    items = []
    try:
        with os.scandir(path) as it:
            for entry in it:
                if entry.is_dir(follow_symlinks=False):
                    size = get_dir_size(entry.path)
                    items.append((entry.name, size, entry.path))
    except PermissionError:
        pass
    
    # Sort by size ASCENDING (Smallest -> Largest) so largest are at bottom
    return sorted(items, key=lambda x: x[1])

def folder_explorer(start_path):
    current_path = os.path.expanduser(start_path)
    if not os.path.exists(current_path):
        print(f"Error: Path {current_path} does not exist.")
        input("Press Enter...")
        return

    while True:
        clear_screen()
        print_header(f"EXPLORING: {current_path}")
        print("Calculating sizes... (Ctrl+C to cancel scan)")
        
        try:
            folders = get_subfolders_info(current_path)
        except KeyboardInterrupt:
            folders = []
            print("\nScan cancelled.")

        if not folders:
            print("\n(No subfolders found or Permission Denied)")
        
        print(f"\n{'#':<4} {'Size':<10} {'Folder Name'}")
        print("-" * 60)
        
        # Print folders (Smallest -> Largest)
        for i, (name, size, path) in enumerate(folders):
            print(f"{i+1:<4} {human_readable(size):<10} {name}/")
            
        print("\nOptions:")
        print("  #num.  Open Folder")
        print("  u.     Go Up One Level")
        print("  c.     Change Directory (Manual Input)")
        print("  b.     Back to Main Menu")
        
        choice = input("\nEnter choice: ").strip().lower()
        
        if choice == 'b':
            return
        elif choice == 'u':
            current_path = os.path.dirname(current_path)
        elif choice == 'c':
            new_path = input("Enter full path: ").strip()
            if os.path.exists(os.path.expanduser(new_path)):
                current_path = os.path.expanduser(new_path)
            else:
                input("Invalid path. Press Enter...")
        elif choice.isdigit():
            idx = int(choice) - 1
            if 0 <= idx < len(folders):
                current_path = folders[idx][2]

# --- MAIN ---

def main():
    while True:
        clear_screen()
        print_header("SYSTEM CLEAN & ANALYZE TOOL V2")
        print("1. System Cleanup Tasks (Docker, Logs, Large Files)")
        print("2. Explore Folder Sizes (Interactive Tree)")
        print("q. Quit")
        
        choice = input("\nEnter choice: ").strip().lower()
        
        if choice == 'q':
            sys.exit(0)
        elif choice == '1':
            system_tasks_menu()
        elif choice == '2':
            default_path = input("Enter start path [default: ~]: ").strip()
            if not default_path: default_path = "~"
            folder_explorer(default_path)

if __name__ == "__main__":
    main()