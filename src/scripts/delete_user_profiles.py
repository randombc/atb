#!/usr/bin/env python3
"""
Force-delete a local Windows user and their profile folder.

Requirements:
  pip install pywin32

Run as Administrator.
"""
import os
import sys
import subprocess
import shutil
import stat
import time
import ctypes

try:
    import win32net
    import win32security
except Exception:
    print("This script requires pywin32 (win32net, win32security). Install with: pip install pywin32")
    raise

import winreg

__all__ = ["remove_user_and_profile"]


def is_admin():
    """Return True if script is running with elevated privileges."""
    try:
        return ctypes.windll.shell32.IsUserAnAdmin() != 0
    except Exception:
        return False


def run_cmd(cmd):
    """Run subprocess command and return CompletedProcess."""
    return subprocess.run(cmd, capture_output=True, text=True)


def find_user_sessions(username):
    """Find session IDs for given user using 'query user'."""
    try:
        cp = run_cmd(["query", "user"])
    except FileNotFoundError:
        print("'query' command not found; cannot detect user sessions.")
        return []
    out = cp.stdout.splitlines()
    sessions = []
    for line in out:
        if not line.strip():
            continue
        parts = line.split()
        if parts[0].lower() == username.lower():
            try:
                sid = int(parts[2])
                sessions.append(sid)
            except Exception:
                for p in parts:
                    if p.isdigit():
                        sessions.append(int(p))
                        break
    return sessions


def logoff_session(session_id):
    """Logoff a session by id."""
    cp = run_cmd(["logoff", str(session_id)])
    if cp.returncode == 0:
        print(f"Logged off session {session_id}")
    else:
        print(f"Failed to log off session {session_id}: {cp.stderr.strip()}")


def delete_local_user(username):
    """Delete local user account using win32net.NetUserDel"""
    try:
        win32net.NetUserDel(None, username)
        print(f"User '{username}' deleted from SAM.")
        return True
    except Exception as e:
        print(f"Failed to delete user '{username}': {e}")
        return False


def get_sid_for_username(username):
    """Return SID string for a local username, or None if not found."""
    try:
        sid_obj, domain, acct_type = win32security.LookupAccountName(None, username)
        sid_str = win32security.ConvertSidToStringSid(sid_obj)
        return sid_str
    except Exception:
        return None


def get_profile_path_from_sid(sid_str):
    """Get ProfileImagePath from registry by SID."""
    try:
        key_path = rf"SOFTWARE\Microsoft\Windows NT\CurrentVersion\ProfileList\{sid_str}"
        with winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, key_path, 0, winreg.KEY_READ) as k:
            profile_path, _ = winreg.QueryValueEx(k, "ProfileImagePath")
            print(f"ProfileImagePath for {sid_str} => {profile_path}")
            return profile_path
    except FileNotFoundError:
        return None
    except Exception as e:
        print(f"Error reading ProfileList for {sid_str}: {e}")
        return None


def delete_profile_registry_entry(sid_str):
    """Delete the ProfileList key for given SID (HKLM)."""
    try:
        key_path = rf"SOFTWARE\Microsoft\Windows NT\CurrentVersion\ProfileList\{sid_str}"
        winreg.DeleteKey(winreg.HKEY_LOCAL_MACHINE, key_path)
        print(f"Deleted registry key: {key_path}")
        return True
    except FileNotFoundError:
        return False
    except Exception as e:
        print(f"Failed to delete registry key {sid_str}: {e}")
        return False


def take_ownership_and_grant_full(path):
    """Force ownership and grant Administrators full control."""
    if not os.path.exists(path):
        return False
    print(f"Taking ownership and granting Administrators full control for: {path}")
    run_cmd(["takeown", "/F", path, "/R", "/D", "Y"])
    run_cmd(["icacls", path, "/grant", "Administrators:F", "/T", "/C"])
    return True


def on_rm_error(func, path, exc_info):
    """Error handler for shutil.rmtree: change file attributes and retry."""
    try:
        os.chmod(path, stat.S_IWRITE)
        if os.path.isdir(path):
            os.rmdir(path)
        else:
            os.remove(path)
    except Exception:
        pass


def remove_profile_folder(path, max_retries=3):
    """Force delete profile folder."""
    if not path:
        return False
    path = os.path.expandvars(path)
    if not os.path.exists(path):
        print(f"Profile path does not exist: {path}")
        return True
    for attempt in range(1, max_retries + 1):
        print(f"Attempt {attempt} to remove folder: {path}")
        try:
            take_ownership_and_grant_full(path)
            for root, dirs, files in os.walk(path):
                for name in files:
                    fp = os.path.join(root, name)
                    try:
                        os.chmod(fp, stat.S_IWRITE)
                        run_cmd(["attrib", "-R", "-S", fp])
                    except Exception:
                        pass
                for name in dirs:
                    dp = os.path.join(root, name)
                    try:
                        os.chmod(dp, stat.S_IWRITE)
                        run_cmd(["attrib", "-R", "-S", dp])
                    except Exception:
                        pass
            shutil.rmtree(path, onerror=on_rm_error)
            if not os.path.exists(path):
                print(f"Successfully removed folder: {path}")
                return True
        except Exception as e:
            print(f"Error removing folder (attempt {attempt}): {e}")
        time.sleep(1 + attempt)
    print(f"Failed to remove folder after {max_retries} attempts: {path}")
    return False


def remove_user_and_profile(username, force_logoff=True):
    """Remove Windows user account and their profile folder."""
    if not is_admin():
        print("This script must be run as Administrator.")
        sys.exit(1)

    sessions = find_user_sessions(username)
    if sessions:
        print(f"User {username} is logged in sessions: {sessions}")
        if force_logoff:
            for s in sessions:
                logoff_session(s)
            time.sleep(2)
        else:
            print("User is logged in. Aborting delete.")
            return

    sid = get_sid_for_username(username)
    profile_path = get_profile_path_from_sid(sid) if sid else None

    deleted = delete_local_user(username)

    if not profile_path:
        guess = os.path.join(os.environ.get("SystemDrive", "C:"), "Users", username)
        print(f"Profile path not found; guessing: {guess}")
        profile_path = guess

    removed = remove_profile_folder(profile_path)

    if sid:
        delete_profile_registry_entry(sid)

    print(f"Done. user_deleted={deleted} profile_removed={removed}")


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python remove_user_force.py <username>")
        sys.exit(2)
    target_user = sys.argv[1]
    remove_user_and_profile(target_user)
