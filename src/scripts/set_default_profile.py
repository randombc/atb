import os
import winreg

PROFILELIST_KEY = r"SOFTWARE\Microsoft\Windows NT\CurrentVersion\ProfileList"


def set_profiles_directory(drive: str):
    """Change where new profiles are created (ProfilesDirectory only)."""
    if not os.path.exists(drive + "\\"):
        raise RuntimeError(f"Drive {drive}\\ does not exist.")

    profiles_dir = rf"{drive}\Users"
    os.makedirs(profiles_dir, exist_ok=True)

    with winreg.OpenKey(
            winreg.HKEY_LOCAL_MACHINE,
            PROFILELIST_KEY,
            0, winreg.KEY_SET_VALUE
    ) as key:
        winreg.SetValueEx(key, "ProfilesDirectory", 0, winreg.REG_EXPAND_SZ, profiles_dir)


def setup_profiles(drive: str):
    """Main function: configure ProfilesDirectory and fix Default hive."""
    set_profiles_directory(drive)


if __name__ == "__main__":
    setup_profiles("D:")
