import os
import subprocess
import shutil
import sys
import glob

def run_command(command, shell=True):
    """Runs a shell command and returns the output."""
    try:
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

def get_size(path):
    """Returns the size of a path in bytes."""
    path = os.path.expanduser(path)
    if not os.path.exists(path):
        return 0
    try:
        # Fast recursive size using du
        out, _, _ = run_command(f"du -s '{path}' | cut -f1")
        return int(out) * 1024  # du returns kbytes by default
    except:
        return 0

def human_readable(size_bytes):
    if size_bytes == 0: return "0B"
    for unit in ['B', 'KB', 'MB', 'GB', 'TB']:
        if size_bytes < 1024.0:
            return f"{size_bytes:.1f}{unit}"
        size_bytes /= 1024.0
    return f"{size_bytes:.1f}TB"

def get_conda_envs():
    """Returns a list of conda environments with their sizes."""
    print("   Scanning Conda environments...")
    out, _, _ = run_command("conda env list")
    envs = []
    for line in out.split('\n'):
        if line.startswith("#") or not line.strip():
            continue
        parts = line.split()
        if len(parts) >= 1:
            path = parts[-1]
            name = parts[0] if len(parts) > 1 and parts[1] != '*' else os.path.basename(path)
            is_base = "miniconda3" == name or "anaconda3" == name or path.endswith("/miniconda3") or path.endswith("/anaconda3")
            envs.append({
                "name": name,
                "path": path,
                "size_bytes": get_size(path),
                "is_base": is_base
            })
    return sorted(envs, key=lambda x: x['size_bytes'], reverse=True)

def find_projects(filename, context_check=None):
    """
    Uses locate to find project files.
    context_check: optional directory name to check for existence (e.g. 'node_modules')
    """
    print(f"   Searching for {filename}...")
    out, _, _ = run_command(f"locate -b '\\{filename}'")
    paths = [p for p in out.split('\n') if p]
    
    clean_paths = []
    for p in paths:
        # Basic filter for hidden junk
        if "/." in p and ".config" not in p:
            continue
            
        dir_path = os.path.dirname(p)
        
        # If we need to check for a sibling folder (like node_modules)
        if context_check:
            if not os.path.exists(os.path.join(dir_path, context_check)):
                continue
                
        clean_paths.append(dir_path) # Return directory, not file
        
    return sorted(list(set(clean_paths))) # Unique dirs

def print_header():
    os.system('clear')
    print("==========================================")
    print("       DISK SPACE CLEANER TOOL V4")
    print("==========================================")

def show_projects(project_lists):
    print_header()
    print("\n[ PROJECT LISTING ]")
    
    for title, projects in project_lists.items():
        print(f"\n--- {title} ({len(projects)} found) ---")
        if not projects:
            print("  (None found)")
        else:
            # Show only top 15 to avoid scrolling madness
            for p in projects[:15]: 
                print(f"  {p}")
            if len(projects) > 15:
                print(f"  ... and {len(projects)-15} more.")

    input("\nPress Enter to return...")

def manage_caches(caches, project_lists):
    selected = [False] * len(caches)
    while True:
        print_header()
        print("\n[ MAIN MENU: CLEAN CACHES ]")
        
        for i, c in enumerate(caches):
            mark = "[x]" if selected[i] else "[ ]"
            size_str = human_readable(c['size_bytes'])
            print(f"  {i+1}. {mark} {c['name']:<20} Size: {size_str:<8} ({c['desc']})")

        print("\nOptions:")
        print("  1-5. Toggle selection")
        print("  r.   RUN Clean (for selected)")
        print("  e.   Manage Conda Environments")
        print("  p.   Show Project Lists (Pixi, UV, NPM, Bun)")
        print("  q.   Quit")

        choice = input("\nEnter choice: ").strip().lower()

        if choice == 'q':
            sys.exit(0)
        elif choice == 'e':
            return "manage_envs"
        elif choice == 'p':
            show_projects(project_lists)
        elif choice.isdigit():
            idx = int(choice) - 1
            if 0 <= idx < len(caches):
                selected[idx] = not selected[idx]
        elif choice == 'r':
            to_run = [c for i, c in enumerate(caches) if selected[i]]
            if not to_run:
                print("No tasks selected!")
                input("Press Enter...")
                continue
            
            print("\nRunning cleanup tasks...")
            for task in to_run:
                print(f"\n--> Running: {task['name']}...")
                run_command(task['cmd'])
                print("    Done.")
            
            print("\nAll Done.")
            input("Press Enter to continue...")
            for c in caches: c['size_bytes'] = get_size(c['path'])

def manage_envs(envs):
    display_envs = envs
    selected = [False] * len(display_envs)
    
    while True:
        print_header()
        print("\n[ MANAGE CONDA ENVIRONMENTS ]")
        
        total_selected = 0
        for i, env in enumerate(display_envs):
            mark = "[DELETE]" if selected[i] else "[ KEEP ]"
            size_str = human_readable(env['size_bytes'])
            base_warn = " (BASE)" if env['is_base'] else ""
            print(f"  {i+1}. {mark} {env['name']:<15} {size_str:<8} {env['path']} {base_warn}")
            if selected[i]: total_selected += env['size_bytes']

        print(f"\nPotential Space Reclaimed: {human_readable(total_selected)}")
        print("\nOptions:")
        print("  #num. Toggle selection")
        print("  d.    DELETE Selected Environments (Irreversible!)")
        print("  b.    Back to Main Menu")

        choice = input("\nEnter choice: ").strip().lower()

        if choice == 'b':
            return
        elif choice.isdigit():
            idx = int(choice) - 1
            if 0 <= idx < len(display_envs):
                selected[idx] = not selected[idx]
        elif choice == 'd':
            to_delete = [e for i, e in enumerate(display_envs) if selected[i]]
            if not to_delete:
                continue
            
            print(f"\nWARNING: You are about to DELETE {len(to_delete)} environments.")
            confirm = input("Type 'yes' to confirm: ")
            if confirm.lower() == 'yes':
                for env in to_delete:
                    print(f"Removing {env['name']}...")
                    run_command(f"conda env remove -n {env['name']} -y")
                    if os.path.exists(env['path']):
                         shutil.rmtree(env['path'], ignore_errors=True)
                
                print("Deletion complete. Re-scanning...")
                return "rescan"

def main():
    print_header()
    print("Initializing...")

    # Define Caches
    caches = [
        {"name": "Pip Cache", "path": "~/.cache/pip", "cmd": "pip cache purge", "desc": "Downloads only"},
        {"name": "UV Cache", "path": "~/.cache/uv", "cmd": "uv cache clean", "desc": "Downloads only"},
        {"name": "Rattler/Pixi", "path": "~/.cache/rattler", "cmd": "pixi clean cache", "desc": "Package Cache"},
        {"name": "NPM Cache", "path": "~/.npm", "cmd": "npm cache clean --force", "desc": "Package Cache"},
        {"name": "Conda Pkgs", "path": "~/miniconda3/pkgs", "cmd": "conda clean --all -y", "desc": "Shared Storage (Unused)"},
    ]

    for c in caches:
        c['size_bytes'] = get_size(c['path'])
    
    # Load Data
    # For NPM, we look for package-lock.json AND require node_modules to exist
    npm_projects = find_projects("package-lock.json", context_check="node_modules")
    bun_projects = find_projects("bun.lockb")
    pixi_projects = find_projects("pixi.toml")
    uv_projects = find_projects("uv.lock")

    project_lists = {
        "Pixi Projects": pixi_projects,
        "UV Projects": uv_projects,
        "NPM Projects (w/ node_modules)": npm_projects,
        "Bun Projects": bun_projects
    }

    envs = get_conda_envs()

    current_mode = "caches"
    while True:
        if current_mode == "caches":
            res = manage_caches(caches, project_lists)
            if res == "manage_envs": current_mode = "envs"
        elif current_mode == "envs":
            res = manage_envs(envs)
            if res == "rescan":
                envs = get_conda_envs()
                for c in caches: 
                    if "Conda" in c['name']: c['size_bytes'] = get_size(c['path'])
            else:
                current_mode = "caches"

if __name__ == "__main__":
    main()