#!/usr/bin/env python3
"""
Enable/check RDP (Remote Desktop) to match Windows UI toggle.

- Registry via winreg
- Services via pywin32
- Firewall via netsh (with fallback)
- Policy rights via pywin32 (LsaAddAccountRights)
- Requires: pywin32 (pip install pywin32)
- Best run as Administrator
"""
import subprocess
import time
import winreg as reg

import win32con
import win32service
import win32security
import pywintypes

# Registry paths
RDP_REG_PATH = r"SYSTEM\CurrentControlSet\Control\Terminal Server"
NLA_REG_PATH = r"SYSTEM\CurrentControlSet\Control\Terminal Server\WinStations\RDP-Tcp"
F_DENY_NAME = "fDenyTSConnections"
NLA_NAME = "UserAuthentication"

TERMSRV = "TermService"


# ---------------- Registry helpers ----------------
def reg_read_dword(root, sub_key, value_name):
    try:
        k = reg.OpenKey(root, sub_key, 0, reg.KEY_READ | getattr(reg, "KEY_WOW64_64KEY", 0))
        val, _ = reg.QueryValueEx(k, value_name)
        reg.CloseKey(k)
        return int(val)
    except Exception:
        return None


def reg_write_dword(root, sub_key, value_name, value):
    try:
        k = reg.CreateKeyEx(root, sub_key, 0, reg.KEY_SET_VALUE | getattr(reg, "KEY_WOW64_64KEY", 0))
        reg.SetValueEx(k, value_name, 0, reg.REG_DWORD, int(value))
        reg.CloseKey(k)
        print(f"[OK] Set {sub_key}\\{value_name} = {value}")
        return True
    except Exception as e:
        print(f"[ERROR] Failed to write registry {sub_key}\\{value_name}: {e}")
        return False


def enable_rdp_registry(enable=True):
    desired = 0 if enable else 1
    return reg_write_dword(reg.HKEY_LOCAL_MACHINE, RDP_REG_PATH, F_DENY_NAME, desired)


def enable_nla_registry(enable=True):
    desired = 1 if enable else 0
    return reg_write_dword(reg.HKEY_LOCAL_MACHINE, NLA_REG_PATH, NLA_NAME, desired)


# ---------------- Service helpers ----------------
def ensure_termservice_autostart_and_running(timeout=15):
    try:
        sc = win32service.OpenSCManager(None, None, win32service.SC_MANAGER_ALL_ACCESS)
        svc = win32service.OpenService(sc, TERMSRV, win32service.SERVICE_ALL_ACCESS)
    except Exception as e:
        print(f"[ERROR] Could not open {TERMSRV}: {e}")
        return False

    try:
        # Set start type = auto
        try:
            win32service.ChangeServiceConfig(
                svc,
                win32service.SERVICE_NO_CHANGE,
                win32service.SERVICE_AUTO_START,
                win32service.SERVICE_NO_CHANGE,
                None, None, 0, None, None, None
            )
        except Exception:
            pass

        # Query status
        status = win32service.QueryServiceStatus(svc)
        if status[1] == win32service.SERVICE_RUNNING:
            return True

        # Try to start
        try:
            win32service.StartService(svc, None)
        except pywintypes.error as e:
            print(f"[INFO] StartService result: {e}")

        deadline = time.time() + timeout
        while time.time() < deadline:
            status = win32service.QueryServiceStatus(svc)
            if status[1] == win32service.SERVICE_RUNNING:
                return True
            time.sleep(1)
        return False
    finally:
        win32service.CloseServiceHandle(svc)
        win32service.CloseServiceHandle(sc)


# ---------------- Firewall helpers ----------------
def run_cmd(cmd):
    proc = subprocess.run(cmd, shell=True, capture_output=True, text=True)
    return proc.returncode, (proc.stdout + proc.stderr).strip()


def enable_firewall_for_rdp():
    """Enable built-in Remote Desktop firewall rules, or add custom rule if group not found."""
    rc, out = run_cmd('netsh advfirewall firewall set rule group="remote desktop" new enable=Yes')
    if rc == 0:
        print("[OK] Remote Desktop firewall group enabled.")
        return True
    else:
        print(f"[WARN] Could not enable firewall group: {out}")
        print("[INFO] Adding custom firewall rule for TCP 3389 ...")
        rc2, out2 = run_cmd(
            'netsh advfirewall firewall add rule '
            'name="Allow RDP (3389)" dir=in action=allow protocol=TCP localport=3389'
        )
        if rc2 == 0:
            print("[OK] Custom RDP firewall rule created.")
            return True
        else:
            print(f"[ERROR] Could not create custom firewall rule: {out2}")
            return False


# ---------------- Policy helpers ----------------
def ensure_group_in_rdp_policy(group_name="Remote Desktop Users"):
    """
    Ensure that the specified group has the right:
    'Allow log on through Remote Desktop Services' (SeRemoteInteractiveLogonRight).
    """
    try:
        sid, domain, _ = win32security.LookupAccountName(None, group_name)
        policy = win32security.LsaOpenPolicy(None, win32security.POLICY_ALL_ACCESS)

        rights = []
        try:
            rights = win32security.LsaEnumerateAccountRights(policy, sid)
        except Exception:
            rights = []

        if "SeRemoteInteractiveLogonRight" in rights:
            print(f"[INFO] Group '{group_name}' already has SeRemoteInteractiveLogonRight")
        else:
            win32security.LsaAddAccountRights(policy, sid, ["SeRemoteInteractiveLogonRight"])
            print(f"[OK] Added '{group_name}' to 'Allow log on through Remote Desktop Services'")

        win32security.LsaClose(policy)
        return True
    except Exception as e:
        print(f"[ERROR] Failed to update RDP logon policy for {group_name}: {e}")
        return False


def ensure_group_in_network_access(group_name="Users"):
    """
    Ensure that the specified group has 'Access this computer from the network' right (SeNetworkLogonRight).
    """
    try:
        sid, domain, _ = win32security.LookupAccountName(None, group_name)
        policy = win32security.LsaOpenPolicy(None, win32security.POLICY_ALL_ACCESS)

        rights = []
        try:
            rights = win32security.LsaEnumerateAccountRights(policy, sid)
        except Exception:
            rights = []

        if "SeNetworkLogonRight" in rights:
            print(f"[INFO] Group '{group_name}' already has SeNetworkLogonRight")
        else:
            win32security.LsaAddAccountRights(policy, sid, ["SeNetworkLogonRight"])
            print(f"[OK] Added '{group_name}' to 'Access this computer from the network'")

        win32security.LsaClose(policy)
        return True
    except Exception as e:
        print(f"[ERROR] Failed to update network access policy for {group_name}: {e}")
        return False


# ---------------- Status check ----------------
def print_rdp_status():
    """Print current RDP, NLA, TermService and firewall status."""
    rdp_flag = reg_read_dword(reg.HKEY_LOCAL_MACHINE, RDP_REG_PATH, F_DENY_NAME)
    nla_flag = reg_read_dword(reg.HKEY_LOCAL_MACHINE, NLA_REG_PATH, NLA_NAME)

    rdp_enabled = (rdp_flag == 0)
    nla_enabled = (nla_flag == 1)

    try:
        sc = win32service.OpenSCManager(None, None, win32service.SC_MANAGER_CONNECT)
        svc = win32service.OpenService(sc, TERMSRV, win32service.SERVICE_QUERY_STATUS)
        status = win32service.QueryServiceStatus(svc)
        svc_running = (status[1] == win32service.SERVICE_RUNNING)
        win32service.CloseServiceHandle(svc)
        win32service.CloseServiceHandle(sc)
    except Exception:
        svc_running = False

    rc, out = run_cmd('netsh advfirewall firewall show rule name=all')
    fw_ok = (rc == 0 and ("3389" in out or "Remote Desktop" in out))

    print("---- RDP Status ----")
    print(f"RDP Enabled (fDenyTSConnections=0): {rdp_enabled}")
    print(f"NLA Enabled (UserAuthentication=1): {nla_enabled}")
    print(f"TermService running: {svc_running}")
    print(f"Firewall rule for 3389 present: {fw_ok}")


# ---------------- Main ----------------
def ensure_rdp_working(enable_nla=True):
    """Enable RDP like the UI toggle does, including policy assignment."""
    print("=== Ensure RDP Working (UI equivalent) ===")
    enable_rdp_registry(True)
    enable_nla_registry(enable_nla)
    ensure_termservice_autostart_and_running()
    enable_firewall_for_rdp()

    # Rights for RDP logon
    ensure_group_in_rdp_policy("Administrators")
    ensure_group_in_rdp_policy("Remote Desktop Users")

    # Rights for network access
    ensure_group_in_network_access("Administrators")
    ensure_group_in_network_access("Users")


if __name__ == "__main__":
    ensure_rdp_working()
    print_rdp_status()
