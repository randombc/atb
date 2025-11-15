import winreg
import sys
import ctypes
from ctypes import wintypes


REG_PATH = r"SOFTWARE\Policies\Microsoft\Windows\DeviceInstall\Restrictions"

# Registry value names used by device installation restriction policies
VAL_ALLOW_DEVICE_IDS_FLAG = "AllowDeviceIDs"       # REG_DWORD: policy enabled/disabled
VAL_DENY_UNSPECIFIED = "DenyUnspecified"           # REG_DWORD: "Prevent installation of devices not described by other policy settings"
VAL_DENY_REMOVABLE = "DenyRemovableDevices"        # REG_DWORD: optional flag


# --- WinAPI: RefreshPolicyEx (to refresh group policy without gpupdate) ---

# Load userenv.dll
_userenv = ctypes.WinDLL("userenv.dll", use_last_error=True)

# BOOL RefreshPolicyEx(BOOL bMachine, DWORD dwOptions);
_RefreshPolicyEx = _userenv.RefreshPolicyEx
_RefreshPolicyEx.argtypes = [wintypes.BOOL, wintypes.DWORD]
_RefreshPolicyEx.restype = wintypes.BOOL

# Options for RefreshPolicyEx
RP_FORCE = 0x00000001  # Force re-application of all policy settings


def refresh_machine_policy():
    """
    Trigger a machine policy refresh using RefreshPolicyEx WinAPI instead of 'gpupdate /force'.

    This does NOT show any UI, it just tells the system to re-apply GPO for the machine.
    """
    print("[i] Triggering machine group policy refresh via RefreshPolicyEx...")
    result = _RefreshPolicyEx(True, RP_FORCE)  # True = machine policies
    if not result:
        err = ctypes.get_last_error()
        print(f"[!] RefreshPolicyEx failed, GetLastError = {err}")
    else:
        print("[+] Machine group policy refresh requested successfully.")


# --- Registry helper functions ---


def open_policy_key(write=False):
    """
    Open or create the DeviceInstall\\Restrictions registry key.
    """
    access = winreg.KEY_READ
    if write:
        access = winreg.KEY_READ | winreg.KEY_WRITE

    try:
        key = winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, REG_PATH, 0, access)
    except FileNotFoundError:
        if not write:
            raise
        key = winreg.CreateKeyEx(
            winreg.HKEY_LOCAL_MACHINE,
            REG_PATH,
            0,
            access
        )
    return key


def get_dword(name):
    """
    Read a REG_DWORD value from the policy key.

    :param name: Value name.
    :return: Integer value or None if not present.
    """
    try:
        key = winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, REG_PATH, 0, winreg.KEY_READ)
    except FileNotFoundError:
        return None

    try:
        value, vtype = winreg.QueryValueEx(key, name)
        if vtype != winreg.REG_DWORD:
            return None
        return int(value)
    except FileNotFoundError:
        return None
    finally:
        winreg.CloseKey(key)


def set_dword(name, value):
    """ Write a REG_DWORD value to the policy key. """
    key = open_policy_key(write=True)
    try:
        winreg.SetValueEx(key, name, 0, winreg.REG_DWORD, int(value))
    finally:
        winreg.CloseKey(key)


def delete_value(name):
    """ Delete a value from the policy key if it exists. """
    try:
        key = open_policy_key(write=True)
    except FileNotFoundError:
        return

    try:
        winreg.DeleteValue(key, name)
    except FileNotFoundError:
        pass
    finally:
        winreg.CloseKey(key)


# --- Whitelist control functions ---


def enable_whitelist_mode():
    """
    Enable whitelist mode:
      - Allow installation of devices matching IDs
      - Block all unspecified devices
      - Optionally block removable devices
    """
    try:
        set_dword(VAL_ALLOW_DEVICE_IDS_FLAG, 1)
        set_dword(VAL_DENY_UNSPECIFIED, 1)
        set_dword(VAL_DENY_REMOVABLE, 1)

        print("[+] Whitelist mode ENABLED.")
        refresh_machine_policy()

    except PermissionError:
        print("[-] Permission denied. Run this script as Administrator.")
        sys.exit(1)


def disable_whitelist_mode():
    """
    Disable whitelist enforcement by removing flags.
    """
    try:
        delete_value(VAL_ALLOW_DEVICE_IDS_FLAG)
        delete_value(VAL_DENY_UNSPECIFIED)
        delete_value(VAL_DENY_REMOVABLE)

        print("[+] Whitelist mode DISABLED.")
        refresh_machine_policy()

    except PermissionError:
        print("[-] Permission denied. Run this script as Administrator.")
        sys.exit(1)


def get_whitelist_status():
    """
    Return True if whitelist mode is enabled, False otherwise.

    Conditions:
      - AllowDeviceIDs == 1
      - DenyUnspecified == 1
    """
    allow_flag = get_dword(VAL_ALLOW_DEVICE_IDS_FLAG)
    deny_unspecified = get_dword(VAL_DENY_UNSPECIFIED)

    return allow_flag == 1 and deny_unspecified == 1


# --- CLI ---


def main():
    print("USB Whitelist Policy Control")
    print("============================")
    print("1) Enable whitelist mode")
    print("2) Disable whitelist mode")
    print("3) Check whitelist status")
    print("0) Exit")

    choice = input("Enter choice: ").strip()

    if choice == "1":
        enable_whitelist_mode()

    elif choice == "2":
        disable_whitelist_mode()

    elif choice == "3":
        status = get_whitelist_status()
        print("\nWhitelist mode:", "ENABLED" if status else "DISABLED")

    elif choice == "0":
        return

    else:
        print("[-] Invalid option.")


if __name__ == "__main__":
    main()
