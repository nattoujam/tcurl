from __future__ import annotations

import os
import shlex
import subprocess
from pathlib import Path

from tcurl.storage import get_editor_command


def open_in_editor(path: Path) -> bool:
    editor = get_editor_command()
    command = shlex.split(editor) + [str(path)]
    try:
        subprocess.run(command, check=False)
    except FileNotFoundError:
        return False
    return True
