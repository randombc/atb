"""
LGPO (Local Group Policy) manager.

This module provides functions to:
- locate LGPO.exe
- export local GPO to a named profile directory under 'Policies'
- apply a profile from 'Policies' back to the local machine
- list available profiles

Usage:
    from scripts.lgpo_manager import (
        export_profile, apply_profile, list_profiles, get_policies_storage
    )
"""

import os
import shutil
import subprocess
from pathlib import Path
from typing import List
import subprocess
import sys

from core.utils import get_folder_path


class LgpoError(RuntimeError):
    pass


def get_policies_storage() -> Path:
    """Return absolute path to 'Policies' storage folder."""
    return get_folder_path("Policies")


def _run_lgpo(args: List[str], timeout: int = 120) -> subprocess.CompletedProcess:
    """
    Run LGPO.exe with given arguments.

    - When running from frozen exe (PyInstaller): use directory of the executable.
    - When running in development (plain Python): use Policies folder in project root.
    """
    if getattr(sys, "frozen", False):
        # Running from PyInstaller-built exe: LGPO.exe is next to main.exe
        exe_dir = Path(sys.executable).resolve().parent
        exe = exe_dir / "LGPO.exe"
    else:
        # Development mode: LGPO.exe is in the Policies folder at the project root
        exe = get_policies_storage() / "LGPO.exe"

    if not exe.exists():
        raise LgpoError(f"LGPO.exe not found at: {exe}")

    cmd = [str(exe), *args]
    try:
        proc = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)
    except subprocess.TimeoutExpired as e:
        raise LgpoError(f"LGPO command timed out: {' '.join(cmd)}") from e

    if proc.returncode != 0:
        stdout = (proc.stdout or "").strip()
        stderr = (proc.stderr or "").strip()
        raise LgpoError(f"LGPO failed (rc={proc.returncode}). stdout: {stdout} stderr: {stderr}")

    return proc


def list_profiles() -> List[str]:
    """
    List profile names (directories) under 'Policies'.
    Returns directory names only (not full paths).
    """
    storage = get_policies_storage()
    if not storage.exists():
        return []
    profiles = []
    for item in storage.iterdir():
        if item.is_dir():
            profiles.append(item.name)
    return sorted(profiles, key=str.lower)


def export_profile(profile_name: str, overwrite: bool = False) -> Path:
    """
    Export current local GPO to 'Policies/<profile_name>' using LGPO /b.

    - profile_name: target directory name under Policies
    - overwrite: if False and directory exists and not empty -> error

    Returns: Path to created profile directory.
    """
    profile_name = profile_name.strip()
    if not profile_name:
        raise LgpoError("Empty profile name.")

    storage = get_policies_storage()
    target_dir = storage / profile_name

    if target_dir.exists():
        # If exists and contains files, guard unless overwrite is True
        if any(target_dir.iterdir()) and not overwrite:
            raise LgpoError(f"Profile '{profile_name}' already exists. Use a different name or enable overwrite.")
    else:
        target_dir.mkdir(parents=True, exist_ok=True)

    # LGPO backup (creates content inside target_dir)
    _run_lgpo(["/b", str(target_dir)])

    return target_dir


def apply_profile(profile_name_or_path: str) -> None:
    """
    Apply a profile to local machine using LGPO /g.

    - profile_name_or_path: either a name under 'Policies' or absolute/relative path to a backup dir
    """
    p = Path(profile_name_or_path)
    if not p.exists():
        # treat as profile name under storage
        p = get_policies_storage() / profile_name_or_path

    if not p.exists() or not p.is_dir():
        raise LgpoError(f"Profile directory not found: {p}")

    # LGPO apply
    _run_lgpo(["/g", str(p)])


def delete_profile(profile_name: str) -> None:
    """
    Delete profile directory from 'Policies' storage.
    """
    storage = get_policies_storage()
    target = storage / profile_name
    if not target.exists():
        return
    if target.is_dir():
        shutil.rmtree(target)
    else:
        target.unlink()


def profile_exists(profile_name: str) -> bool:
    """Check if a profile directory exists under 'Policies'."""
    return (get_policies_storage() / profile_name).exists()
