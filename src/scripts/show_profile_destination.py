import os
import winreg

PROFILELIST_KEY = r"SOFTWARE\Microsoft\Windows NT\CurrentVersion\ProfileList"


def print_profiles_directory():
    with winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, PROFILELIST_KEY, 0, winreg.KEY_READ) as key:
        value, _ = winreg.QueryValueEx(key, "ProfilesDirectory")
        path = os.path.expandvars(value)
        print(f"ProfilesDirectory : {path}")


if __name__ == "__main__":
    print_profiles_directory()
