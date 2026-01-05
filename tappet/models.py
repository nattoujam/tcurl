from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List, Optional


@dataclass
class Variable:
    name: str
    placeholder: str


@dataclass
class RequestSet:
    name: str
    method: str
    url: str
    headers: Dict[str, str]
    body: Optional[Dict[str, Any]]
    description: Optional[str] = ""
    variables: List[Variable] = None
    file_path: Optional[Path] = None

    def __post_init__(self) -> None:
        if self.variables is None:
            self.variables = []


@dataclass
class Response:
    status_code: Optional[int] = None
    reason: Optional[str] = None
    headers: Optional[Dict[str, str]] = None
    body: str = ""
    elapsed_ms: Optional[float] = None
    error: Optional[str] = None
    note: Optional[str] = None
