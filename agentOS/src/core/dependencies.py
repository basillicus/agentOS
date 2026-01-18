from dataclasses import dataclass
import sys
import os

# Import Skills
current_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.abspath(os.path.join(current_dir, "../../../"))
if project_root not in sys.path:
    sys.path.append(project_root)

from src.skills.disk.cleaner import DiskSkill
from src.skills.memory.manager import MemorySkill
from src.skills.system.tools import SystemSkill

@dataclass
class AgentDeps:
    """Dependencies available to the Agent during execution."""
    disk: DiskSkill
    memory: MemorySkill
    system: SystemSkill
