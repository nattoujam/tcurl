from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Optional


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
    body: Optional[str]
    description: Optional[str] = ""
    variables: List[Variable] = None
    file_path: Optional[Path] = None

    def __post_init__(self) -> None:
        if self.variables is None:
            self.variables = []
