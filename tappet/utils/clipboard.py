import os
import subprocess


def copy_to_clipboard(text: str) -> bool:
    display = os.environ.get("DISPLAY")
    is_wsl = "WSL_DISTRO_NAME" in os.environ
    use_x11 = bool(display) and not is_wsl
    commands = [["pbcopy"], ["wl-copy"]]
    if use_x11:
        commands.extend([["xclip", "-selection", "clipboard"], ["xsel", "--clipboard", "--input"]])
    for command in commands:
        try:
            process = subprocess.Popen(command, stdin=subprocess.PIPE)
            process.communicate(input=text.encode())
            return process.returncode == 0
        except FileNotFoundError:
            continue
        except Exception:
            return False
    return False
