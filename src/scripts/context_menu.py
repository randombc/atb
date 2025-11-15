# context_menu.py
import winreg
import subprocess

_GUID = "{86ca1aa0-34aa-4e8b-a509-50c905bae2a2}"
_SUBKEY = rf"Software\Classes\CLSID\{_GUID}\InprocServer32"


def is_new_context_menu_enabled() -> bool:
    """
    Check whether Windows 11 uses the modern (new) context menu.

    Returns:
        True  -> modern Windows 11 context menu is active (default)
        False -> classic Windows 10-style context menu is forced
    """
    try:
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, _SUBKEY, 0, winreg.KEY_READ):
            return False
    except FileNotFoundError:
        return True


def set_new_context_menu(enabled: bool) -> bool:
    """
    Enable or disable the modern Windows 11 context menu.

    Args:
        enabled (bool): True to enable modern menu, False to enable classic one.

    Returns:
        bool: True if operation succeeded, False otherwise.
    """
    try:
        if enabled:
            # Remove the registry key -> restore new menu
            winreg.DeleteKey(winreg.HKEY_CURRENT_USER, _SUBKEY)
        else:
            # Create the key -> switch to classic menu
            key = winreg.CreateKey(winreg.HKEY_CURRENT_USER, _SUBKEY)
            winreg.SetValueEx(key, "", 0, winreg.REG_SZ, "")
            winreg.CloseKey(key)

        _restart_explorer()
        return True
    except FileNotFoundError:
        # If trying to delete key that doesn't exist -> already enabled
        return True
    except OSError:
        return False


def _restart_explorer():
    """Restart Windows Explorer to apply context menu changes immediately."""
    subprocess.run(
        ["taskkill", "/f", "/im", "explorer.exe"],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )
    subprocess.Popen(["explorer.exe"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
