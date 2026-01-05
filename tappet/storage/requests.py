from __future__ import annotations

from pathlib import Path
import time
from typing import Any, Dict, List, Optional

import yaml

from tappet.models import RequestSet
from tappet.storage.config import ensure_config
from tappet.storage.paths import REQUESTS_DIR

SAMPLE_REQUEST = {
    "name": "New Request",
    "description": "",
    "method": "GET",
    "url": "http://localhost:8000",
    "headers": {"Content-Type": "application/json"},
    "body": {
        "name": "$1",
        "email": "$2",
    },
}


def ensure_requests_dir() -> None:
    ensure_config()
    REQUESTS_DIR.mkdir(parents=True, exist_ok=True)
    if not any(REQUESTS_DIR.glob("*.y*ml")):
        (REQUESTS_DIR / "example.yaml").write_text(
            yaml.safe_dump(SAMPLE_REQUEST, sort_keys=False),
            encoding="utf-8",
        )


def load_request_sets() -> List[RequestSet]:
    ensure_requests_dir()
    request_sets: List[RequestSet] = []

    for path in sorted(REQUESTS_DIR.glob("*.y*ml")):
        data = _read_yaml(path)
        if not isinstance(data, dict):
            continue
        request_sets.append(_parse_request_set(data, path))

    return request_sets


def create_request_set() -> Optional[RequestSet]:
    ensure_requests_dir()
    file_path = _next_path()
    if file_path is None:
        return None
    file_path.write_text(
        yaml.safe_dump(SAMPLE_REQUEST, sort_keys=False),
        encoding="utf-8",
    )
    return _parse_request_set(SAMPLE_REQUEST, file_path)


def duplicate_request_set(request_set: RequestSet) -> Optional[RequestSet]:
    ensure_requests_dir()
    if request_set.file_path is None or not request_set.file_path.exists():
        return None
    source = request_set.file_path
    file_path = _next_path()
    if file_path is None:
        return None
    file_path.write_text(source.read_text(encoding="utf-8"), encoding="utf-8")
    data = _read_yaml(file_path)
    if not isinstance(data, dict):
        data = {}
    return _parse_request_set(data, file_path)


def delete_request_set(request_set: RequestSet) -> bool:
    if request_set.file_path is None:
        return False
    if not request_set.file_path.exists():
        return False
    request_set.file_path.unlink()
    return True


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
    if isinstance(body, dict):
        pass
    elif isinstance(body, str):
        parsed = yaml.safe_load(body)
        body = parsed if isinstance(parsed, dict) else {}
    else:
        body = {}

    return RequestSet(
        name=name,
        method=method,
        url=url,
        headers=headers,
        body=body,
        description=str(data.get("description") or ""),
        file_path=path,
    )


def _next_path() -> Optional[Path]:
    stamp = time.time_ns() // 1_000_000
    next_path = REQUESTS_DIR / f"{stamp}.yaml"
    if next_path.exists():
        return None
    return next_path
