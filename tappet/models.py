from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, Optional


@dataclass
class RequestSet:
    name: str
    method: str
    url: str
    headers: Dict[str, str]
    body: Optional[Dict[str, Any]]
    description: Optional[str] = ""
    file_path: Optional[Path] = None


@dataclass
class Response:
    status_code: Optional[int] = None
    reason: Optional[str] = None
    headers: Optional[Dict[str, str]] = None
    body: str = ""
    elapsed_ms: Optional[float] = None
    error: Optional[str] = None
    note: Optional[str] = None
