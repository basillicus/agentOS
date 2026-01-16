import os

class Colors:
    """ANSI Color codes for TUI styling."""
    RESET = "\033[0m"
    BOLD = "\033[1m"
    DIM = "\033[2m"
    
    # Foreground
    RED = "\033[91m"
    GREEN = "\033[92m"
    YELLOW = "\033[93m"
    BLUE = "\033[94m"
    MAGENTA = "\033[95m"
    CYAN = "\033[96m"
    WHITE = "\033[97m"

class TUI:
    """Helper for consistent TUI rendering."""
    
    @staticmethod
    def clear():
        os.system('clear')

    @staticmethod
    def header(title: str, subtext: str = ""):
        TUI.clear()
        print(f"{Colors.BOLD}{Colors.BLUE}{'=' * 60}{Colors.RESET}")
        print(f"{Colors.BOLD}{Colors.WHITE}{title.center(60)}{Colors.RESET}")
        if subtext:
            print(f"{Colors.DIM}{subtext.center(60)}{Colors.RESET}")
        print(f"{Colors.BOLD}{Colors.BLUE}{'=' * 60}{Colors.RESET}")
        print("")

    @staticmethod
    def item(index: int, label: str, value: str = "", extra: str = ""):
        """Prints a list item: '1. Label  Value  (Extra)'"""
        idx_str = f"{Colors.YELLOW}{index}.{Colors.RESET}"
        val_str = f"{Colors.GREEN}{value}{Colors.RESET}" if value else ""
        ext_str = f"{Colors.DIM}({extra}){Colors.RESET}" if extra else ""
        print(f" {idx_str} {Colors.BOLD}{label:<20}{Colors.RESET} {val_str:<10} {ext_str}")

    @staticmethod
    def success(msg: str):
        print(f"\n{Colors.GREEN}✔ {msg}{Colors.RESET}")

    @staticmethod
    def error(msg: str):
        print(f"\n{Colors.RED}✖ {msg}{Colors.RESET}")

    @staticmethod
    def prompt(text: str) -> str:
        return input(f"\n{Colors.CYAN}➤ {text}{Colors.RESET} ").strip()
