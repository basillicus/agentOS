from pydantic import BaseModel, Field
from typing import List, Optional, Literal
from datetime import datetime

# --- DISK MODELS ---
class DiskUsage(BaseModel):
    """Represents a file or directory size."""
    path: str = Field(..., description="Absolute path to the item")
    size_bytes: int = Field(..., description="Size in bytes")
    size_human: str = Field(..., description="Human readable size (e.g., '1.5GB')")
    name: str = Field(..., description="Name of the file or folder")

class CacheItem(DiskUsage):
    """Represents a system or application cache."""
    id: str = Field(..., description="Unique ID for the cache (e.g., 'pip', 'npm')")
    description: str = Field(..., description="What this cache contains")

class CondaEnvironment(DiskUsage):
    """Represents a Conda/Python environment."""
    is_base: bool = Field(False, description="True if this is the base installation (dangerous to delete)")

class FileScanResult(BaseModel):
    """Result of a large file scan."""
    files: List[DiskUsage] = Field(default_factory=list)
    threshold_used: str = Field(..., description="The size threshold used for the scan (e.g., '500MB')")

class ActionResponse(BaseModel):
    """Standard response for any modification action."""
    success: bool
    message: str
    error: Optional[str] = None
    affected_path: Optional[str] = None

# --- MEMORY MODELS ---

class Note(BaseModel):
    """A user-created note or memory."""
    id: Optional[int] = Field(None, description="Database ID")
    content: str = Field(..., description="The text content of the note")
    tags: List[str] = Field(default_factory=list, description="List of tags for organization")
    created_at: str = Field(..., description="ISO formatted creation time")

class HistoryItem(BaseModel):
    """A record of a previously executed command."""
    id: Optional[int] = Field(None, description="Database ID")
    command: str = Field(..., description="The shell command executed")
    context: str = Field("~", description="The directory where it was run")
    timestamp: str = Field(..., description="ISO formatted time")
    notes: Optional[str] = Field(None, description="Optional user annotation for this command")