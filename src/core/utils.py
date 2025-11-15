import os
import sys
from pathlib import Path


def cls():
    os.system('cls')


def get_folder_path(folder_name: str) -> Path:
    """
    Return absolute Path to a given folder.
    - If running from exe (PyInstaller), use exe directory as base.
    - If running from source, assume cwd is 'src' and go one level up.
    """
    if getattr(sys, 'frozen', False):
        # Running from compiled exe
        base_path = Path(sys.executable).parent
    else:
        # Running from source
        cwd = Path(__file__).resolve()
        base_path = cwd.parent.parent.parent

    return base_path / folder_name
