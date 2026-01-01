from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, List, Optional

import yaml

from tcurl.models import RequestSet, Variable

CONFIG_DIR = Path.home() / ".config" / "nattoujam" / "tcurl"
REQUESTS_DIR = CONFIG_DIR / "requests"
CONFIG_PATH = CONFIG_DIR / "config.yaml"


def ensure_storage() -> None:
    REQUESTS_DIR.mkdir(parents=True, exist_ok=True)

    if not CONFIG_PATH.exists():
        default_config = {
            "http": {"timeout": 10},
            "editor": "vim",
            "ui": {"theme": "default"},
        }
        CONFIG_PATH.write_text(
            yaml.safe_dump(default_config, sort_keys=False),
            encoding="utf-8",
        )

    if not any(REQUESTS_DIR.glob("*.y*ml")):
        sample_request = {
            "name": "Example Request",
            "description": "Sample request created on first run",
            "method": "POST",
            "url": "https://api.example.com/users",
            "headers": {"Content-Type": "application/json"},
            "body": '{\n  "name": "$1",\n  "email": "$2"\n}\n',
            "variables": [
                {"name": "Name", "placeholder": "e.g. Jane Doe"},
                {"name": "Email", "placeholder": "e.g. jane@example.com"},
            ],
        }
        (REQUESTS_DIR / "example.yaml").write_text(
            yaml.safe_dump(sample_request, sort_keys=False),
            encoding="utf-8",
        )


def load_request_sets() -> List[RequestSet]:
    ensure_storage()
    request_sets: List[RequestSet] = []

    for path in sorted(REQUESTS_DIR.glob("*.y*ml")):
        data = _read_yaml(path)
        if not isinstance(data, dict):
            continue
        request_sets.append(_parse_request_set(data, path))

    return request_sets


def create_request_set(name: Optional[str] = None) -> RequestSet:
    ensure_storage()
    file_path = _next_request_path()
    request_name = name or "New Request"
    template = {
        "name": request_name,
        "description": "",
        "method": "GET",
        "url": "https://api.example.com",
        "headers": {"Content-Type": "application/json"},
        "body": "",
        "variables": [],
    }
    file_path.write_text(
        yaml.safe_dump(template, sort_keys=False),
        encoding="utf-8",
    )
    return _parse_request_set(template, file_path)


def _read_yaml(path: Path) -> Dict[str, Any]:
    with path.open("r", encoding="utf-8") as handle:
        data = yaml.safe_load(handle)
    return data or {}


def _parse_request_set(data: Dict[str, Any], path: Path) -> RequestSet:
    name = str(data.get("name") or path.stem)
    method = str(data.get("method") or "GET").upper()
    url = str(data.get("url") or "")
    headers = data.get("headers") if isinstance(data.get("headers"), dict) else {}
    body = data.get("body")
    if body is not None and not isinstance(body, str):
        body = str(body)

    variables = _parse_variables(data.get("variables"))

    return RequestSet(
        name=name,
        method=method,
        url=url,
        headers=headers,
        body=body,
        description=str(data.get("description") or ""),
        variables=variables,
        file_path=path,
    )


def _next_request_path() -> Path:
    base = REQUESTS_DIR / "new_request.yaml"
    if not base.exists():
        return base
    counter = 1
    while True:
        candidate = REQUESTS_DIR / f"new_request_{counter}.yaml"
        if not candidate.exists():
            return candidate
        counter += 1


def _parse_variables(raw_vars: Any) -> List[Variable]:
    if not isinstance(raw_vars, list):
        return []

    variables: List[Variable] = []
    for item in raw_vars:
        if not isinstance(item, dict):
            continue
        name = str(item.get("name") or "")
        placeholder = str(item.get("placeholder") or "")
        if not (name or placeholder):
            continue
        variables.append(Variable(name=name, placeholder=placeholder))
    return variables
