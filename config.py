"""Configuration module for SlothMate AI."""
from pathlib import Path
from dataclasses import dataclass, field
from typing import Set
import os

PROJECT_ROOT = Path(__file__).resolve().parent

@dataclass
class AppConfig:
    app_name: str = "SlothMate AI"
    tagline: str = "Work less. Let your local AI handle the boring stuff."
    version: str = "1.0.0"
    
    # Ollama settings
    ollama_base_url: str = field(default_factory=lambda: os.getenv("OLLAMA_BASE_URL", "http://localhost:11434"))
    default_model: str = field(default_factory=lambda: os.getenv("SLOTHMATE_MODEL", "qwen2.5:3b"))
    request_timeout_seconds: int = 60
    temperature: float = 0.2
    
    # Storage settings
    data_dir: Path = field(default_factory=lambda: PROJECT_ROOT / "data")
    db_path: Path = field(default_factory=lambda: PROJECT_ROOT / "data" / "slothmate.db")
    inbox_dir: Path = field(default_factory=lambda: PROJECT_ROOT / "data" / "inbox")
    
    # File processing constraints
    max_file_size_bytes: int = 20 * 1024 * 1024  # 20 MB
    supported_extensions: Set[str] = field(default_factory=lambda: {".txt", ".md", ".pdf"})
    
    # Text chunking settings
    chunk_size_chars: int = 3500
    chunk_overlap_chars: int = 350
    
    def ensure_directories(self) -> None:
        self.data_dir.mkdir(parents=True, exist_ok=True)
        self.inbox_dir.mkdir(parents=True, exist_ok=True)

config = AppConfig()
config.ensure_directories()
