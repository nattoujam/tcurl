from __future__ import annotations

from typing import Any, Dict

import yaml

from tappet.storage.paths import CONFIG_DIR, CONFIG_PATH

DEFAULT_CONFIG = {
    "http": {"timeout": 10},
    "editor": "vim",
    "ui": {"theme": "default"},
}


def ensure_config() -> None:
    CONFIG_DIR.mkdir(parents=True, exist_ok=True)
    if not CONFIG_PATH.exists():
        CONFIG_PATH.write_text(
            yaml.safe_dump(DEFAULT_CONFIG, sort_keys=False),
            encoding="utf-8",
        )


def load_config() -> Dict[str, Any]:
    ensure_config()
    with CONFIG_PATH.open("r", encoding="utf-8") as handle:
        data = yaml.safe_load(handle)
    return data if isinstance(data, dict) else {}


def get_editor_command() -> str:
    config = load_config()
    editor = config.get("editor")
    if isinstance(editor, str) and editor.strip():
        return editor.strip()
    return "vim"
