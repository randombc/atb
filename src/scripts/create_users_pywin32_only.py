"""
Create local users from all .list files in current directory using pywin32 + ADSI.

Each .list file describes a set of local users to create.
Lines starting with "#" are comments and will be ignored.

Format of user entry:
username;password;is_admin(yes/no);rdp(yes/no);chg_pwd(yes/no);never_expire_pwd(yes/no)
"""

import sys
import win32net
import win32netcon
import win32com.client
from pathlib import Path


# --- helpers ---------------------------------------------------------------

def user_exists(username: str) -> bool:
    try:
        win32net.NetUserGetInfo(None, username, 1)
        return True
    except win32net.error:
        return False


def set_never_expire_policy(username: str, never_expire_pwd: str) -> None:
    """yes -> password never expires, no -> password expires by policy"""
    info = win32net.NetUserGetInfo(None, username, 2)
    flags = info["flags"]

    if never_expire_pwd.lower() == "yes":
        flags |= win32netcon.UF_DONT_EXPIRE_PASSWD
    else:
        flags &= ~win32netcon.UF_DONT_EXPIRE_PASSWD

    info["flags"] = flags
    win32net.NetUserSetInfo(None, username, 2, info)


def set_chg_pwd_on_logon(username: str, chg_pwd: str) -> None:
    """Force password change at next logon using ADSI"""
    if chg_pwd.lower() == "yes":
        user = win32com.client.GetObject(f"WinNT://./{username},user")
        user.Put("PasswordExpired", 1)
        user.SetInfo()


def add_to_group_with_fallback(username: str, primary: str, fallback: str) -> None:
    try:
        win32net.NetLocalGroupAddMembers(None, primary, 3, [{"domainandname": username}])
    except win32net.error as e:
        # 1378: already in group; 1376/2220: no such group
        if e.winerror == 1378:
            return
        if e.winerror in (1376, 2220):
            try:
                win32net.NetLocalGroupAddMembers(None, fallback, 3, [{"domainandname": username}])
            except win32net.error as e2:
                if e2.winerror != 1378:
                    raise
        else:
            raise


def add_memberships(username: str, is_admin: str, rdp: str) -> None:
    if is_admin.lower() == "yes":
        add_to_group_with_fallback(username, "Administrators", "Адміністратори")
    else:
        add_to_group_with_fallback(username, "Users", "Користувачі")

    if rdp.lower() == "yes":
        add_to_group_with_fallback(username, "Remote Desktop Users", "Користувачі віддаленого робочого стола")


# --- main ops --------------------------------------------------------------

def create_user(username: str, password: str, is_admin: str, rdp: str,
                chg_pwd: str, never_expire_pwd: str) -> None:
    flags = win32netcon.UF_SCRIPT | win32netcon.UF_NORMAL_ACCOUNT
    if never_expire_pwd.lower() == "yes":
        flags |= win32netcon.UF_DONT_EXPIRE_PASSWD

    user_info = {
        "name": username,
        "password": password,
        "priv": win32netcon.USER_PRIV_USER,
        "home_dir": None,
        "comment": None,
        "flags": flags,
        "script_path": None,
    }

    win32net.NetUserAdd(None, 1, user_info)

    # Apply policies
    set_never_expire_policy(username, never_expire_pwd)
    set_chg_pwd_on_logon(username, chg_pwd)

    # Groups
    add_memberships(username, is_admin, rdp)


def process_user(line: str, source_file: Path) -> None:
    parts = [p.strip() for p in line.split(";")]
    if len(parts) != 6:
        print(f"[!] Invalid line format in {source_file.name}: {line}")
        return

    username, password, is_admin, rdp, chg_pwd, never_expire_pwd = parts

    if user_exists(username):
        print(f"[=] User {username} already exists, skipping...")
        return

    try:
        create_user(username, password, is_admin, rdp, chg_pwd, never_expire_pwd)
        print(f"[+] User {username} created from {source_file.name}")
        if is_admin.lower() == "yes":
            print(f"[+] {username} added to Administrators")
        else:
            print(f"[+] {username} added to Users")
        if rdp.lower() == "yes":
            print(f"[+] {username} added to Remote Desktop Users")
    except Exception as e:
        print(f"[!] Error creating {username} from {source_file.name}: {e}")


def process_list_file(path: Path) -> None:
    print(f"[*] Processing {path.name} ...")
    with path.open(encoding="utf-8") as f:
        for raw in f:
            line = raw.strip()
            if not line or line.startswith("#"):
                continue
            process_user(line, path)


def main():
    files = list(Path(".").glob("*.list"))
    if not files:
        print("[!] No .list files found in this directory.")
        sys.exit(1)

    for file in files:
        process_list_file(file)


if __name__ == "__main__":
    main()
