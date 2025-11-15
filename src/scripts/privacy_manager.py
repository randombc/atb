# privacy_manager.py
import os
import winreg
from enum import Enum
from typing import Tuple, Optional

# ============================
# --- Operation modes ---
# ============================
class OperationMode(Enum):
    APPLY = 1     # Apply hardened privacy rules
    DEFAULT = 2   # Restore default Windows rules
    PRINT = 3     # Just read and print current values

# ============================
# --- Rules configuration ---
# ============================
RULES = [
    ("HKLM\\SOFTWARE\\Policies\\Microsoft\\Windows\\OOBE", "DisablePrivacyExperience", "REG_DWORD", 1, 0),
    ("HKLM\\SOFTWARE\\Policies\\Microsoft\\Windows\\DataCollection", "AllowTelemetry", "REG_DWORD", 0, 3),
    ("HKLM\\SOFTWARE\\Policies\\Microsoft\\Windows\\DataCollection", "DoNotShowFeedbackNotifications", "REG_DWORD", 1, 0),
    ("HKLM\\SOFTWARE\\Policies\\Microsoft\\Windows\\AdvertisingInfo", "DisabledByGroupPolicy", "REG_DWORD", 1, 0),
    ("HKLM\\SOFTWARE\\Policies\\Microsoft\\Windows\\LocationAndSensors", "DisableLocation", "REG_DWORD", 1, 0),
    ("HKLM\\SOFTWARE\\Policies\\Microsoft\\Windows\\Windows Search", "AllowCortana", "REG_DWORD", 0, 1),
    ("HKLM\\SOFTWARE\\Policies\\Microsoft\\Windows\\System", "EnableActivityFeed", "REG_DWORD", 0, 1),
    ("HKLM\\SOFTWARE\\Policies\\Microsoft\\Windows\\System", "PublishUserActivities", "REG_DWORD", 0, 1),
    ("HKLM\\SOFTWARE\\Policies\\Microsoft\\Windows\\System", "UploadUserActivities", "REG_DWORD", 0, 1),
    ("HKLM\\SOFTWARE\\Policies\\Microsoft\\Windows\\Explorer", "ShowOrHideMostUsedApps", "REG_DWORD", 2, 0),
    ("HKLM\\SOFTWARE\\Policies\\Microsoft\\Windows\\WindowsCopilot", "TurnOffWindowsCopilot", "REG_DWORD", 1, 0),
    ("HKLM\\SOFTWARE\\Policies\\Microsoft\\Edge", "HideFirstRunExperience", "REG_DWORD", 1, 0),
    ("HKLM\\SOFTWARE\\Policies\\Microsoft\\Edge", "ShowFirstRunExperience", "REG_DWORD", 0, 1),
]

# ============================
# --- Helper functions ---
# ============================
HIVE_MAP = {
    "HKLM": winreg.HKEY_LOCAL_MACHINE,
    "HKEY_LOCAL_MACHINE": winreg.HKEY_LOCAL_MACHINE,
    "HKCU": winreg.HKEY_CURRENT_USER,
    "HKEY_CURRENT_USER": winreg.HKEY_CURRENT_USER,
    "HKCR": winreg.HKEY_CLASSES_ROOT,
    "HKEY_CLASSES_ROOT": winreg.HKEY_CLASSES_ROOT,
    "HKU": winreg.HKEY_USERS,
    "HKEY_USERS": winreg.HKEY_USERS,
    "HKCC": winreg.HKEY_CURRENT_CONFIG,
    "HKEY_CURRENT_CONFIG": winreg.HKEY_CURRENT_CONFIG,
}

def parse_full_path(full_path: str) -> Tuple[int, str]:
    parts = full_path.split("\\", 1)
    hive_key = parts[0].upper()
    if hive_key not in HIVE_MAP:
        raise ValueError(f"Unknown registry hive prefix: '{hive_key}'")
    subkey = parts[1] if len(parts) > 1 else ""
    return HIVE_MAP[hive_key], subkey

def reg_type_to_winreg(reg_type: str):
    rt = reg_type.upper()
    if rt == "REG_DWORD":
        return winreg.REG_DWORD
    if rt == "REG_SZ":
        return winreg.REG_SZ
    if rt == "REG_EXPAND_SZ":
        return winreg.REG_EXPAND_SZ
    if rt == "REG_BINARY":
        return winreg.REG_BINARY
    raise ValueError(f"Unsupported reg type: {reg_type}")

def set_value(hive, subkey, name, value, reg_type):
    with winreg.CreateKeyEx(hive, subkey, 0, winreg.KEY_WRITE) as key:
        winreg.SetValueEx(key, name, 0, reg_type_to_winreg(reg_type), value)

def get_value(hive, subkey, name) -> Optional[Tuple[object, int]]:
    try:
        with winreg.OpenKey(hive, subkey, 0, winreg.KEY_READ) as key:
            return winreg.QueryValueEx(key, name)
    except FileNotFoundError:
        return None

# ============================
# --- Public function ---
# ============================
def manage_privacy_rules(mode: OperationMode) -> None:
    """Execute selected mode and print results directly."""
    for full_path, name, reg_type, apply_value, default_value in RULES:
        hive, subkey = parse_full_path(full_path)

        if mode == OperationMode.PRINT:
            current = get_value(hive, subkey, name)
            if current is None:
                print(f"{full_path} -> {name}: Not set")
            else:
                val, val_type = current
                print(f"{full_path} -> {name}: Current={val} (type={val_type})")
        else:
            value = apply_value if mode == OperationMode.APPLY else default_value
            try:
                set_value(hive, subkey, name, value, reg_type)
                print(f"{full_path} -> {name}: Set to {value}")
            except Exception as e:
                print(f"{full_path} -> {name}: Error: {e}")

# ============================
# --- Menu loop ---
# ============================
def clear_screen():
    os.system("cls" if os.name == "nt" else "clear")

if __name__ == "__main__":
    mode = None
    while mode is None:
        clear_screen()
        print("=" * 50)
        print(" Privacy Manager - Select Mode")
        print("=" * 50)
        print("1 - Apply hardened privacy rules")
        print("2 - Restore default Windows rules")
        print("3 - Print current registry values")
        print("=" * 50)

        try:
            choice = int(input("Enter your choice (1, 2, or 3): ").strip())
            mode = OperationMode(choice)
        except (ValueError, KeyError):
            mode = None  # invalid input -> repeat

    clear_screen()
    print(f"Running in mode: {mode.name}\n")
    manage_privacy_rules(mode)
    print("\nDone. Press Enter to exit...")
    input()
