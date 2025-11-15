# -*- coding: utf-8 -*-
# Conversation: Ukrainian
# Code comments & variable names: English
# Purpose: extract Windows and Office product keys + version info, and augment with slmgr/ospp status

import os
import re
import subprocess
import sys
import winreg
from typing import List, Dict, Optional, Tuple

CHARS = "BCDFGHJKMPQRTVWXY2346789"

# --- Decoding DigitalProductId -> Product Key ---

def decode_product_key(dpid: bytes) -> str:
    """Decode Microsoft DigitalProductId into readable product key."""
    key_start_index = 52
    d = bytearray(dpid)
    is_win8 = (d[66] & 0x80) != 0
    if is_win8:
        d[66] = d[66] & 0x7F
    decoded_chars = []
    for i in range(24, -1, -1):
        acc = 0
        for j in range(14, -1, -1):
            acc = acc * 256 ^ d[key_start_index + j]
            d[key_start_index + j] = acc // 24
            acc = acc % 24
        decoded_chars.insert(0, CHARS[acc])
        if ((25 - i) % 5) == 0 and i != 0:
            decoded_chars.insert(0, '-')
    return ''.join(decoded_chars)

# --- Registry helpers ---

def read_registry_value(root, path: str, name: str):
    try:
        with winreg.OpenKey(root, path, 0, winreg.KEY_READ) as key:
            val, _ = winreg.QueryValueEx(key, name)
            return val
    except Exception:
        return None

# --- Windows info (from registry) ---

def get_windows_info() -> Optional[Tuple[str, str, str]]:
    """
    Return (name, version, product_key) for Windows from registry.
    Version composed from ProductName, EditionID, CurrentBuild, DisplayVersion.
    """
    path = r"SOFTWARE\Microsoft\Windows NT\CurrentVersion"
    product_name = read_registry_value(winreg.HKEY_LOCAL_MACHINE, path, "ProductName") or "Windows"
    edition = read_registry_value(winreg.HKEY_LOCAL_MACHINE, path, "EditionID")
    build = read_registry_value(winreg.HKEY_LOCAL_MACHINE, path, "CurrentBuild")
    version_display = read_registry_value(winreg.HKEY_LOCAL_MACHINE, path, "DisplayVersion")
    dpid = read_registry_value(winreg.HKEY_LOCAL_MACHINE, path, "DigitalProductId")

    version = f"{product_name} {edition or ''} (Build {build or '?'} - {version_display or '?'})".strip()
    key = decode_product_key(dpid) if dpid else None
    if key:
        return (product_name, version, key)
    return None

# --- Office info (from registry) ---

def enum_office_keys() -> List[Tuple[str, str, str]]:
    """
    Enumerate Office product keys from registry with version info.
    Returns list of tuples: (name, version_string, product_key)
    """
    results: List[Tuple[str, str, str]] = []
    bases = [
        r"SOFTWARE\Microsoft\Office",
        r"SOFTWARE\WOW6432Node\Microsoft\Office"
    ]
    for base in bases:
        try:
            with winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, base) as root:
                i = 0
                while True:
                    try:
                        sub = winreg.EnumKey(root, i)
                    except OSError:
                        break
                    i += 1
                    version_name = f"Office {sub}"
                    reg_path = base + "\\" + sub + "\\Registration"
                    # Try Registration subkeys
                    try:
                        with winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, reg_path) as regroot:
                            j = 0
                            while True:
                                try:
                                    subreg = winreg.EnumKey(regroot, j)
                                except OSError:
                                    break
                                j += 1
                                full = reg_path + "\\" + subreg
                                dpid = read_registry_value(winreg.HKEY_LOCAL_MACHINE, full, "DigitalProductId")
                                pname = read_registry_value(winreg.HKEY_LOCAL_MACHINE, full, "ProductName")
                                if dpid:
                                    results.append((pname or version_name, version_name, decode_product_key(dpid)))
                    except Exception:
                        # Maybe stored directly under base\<version>
                        dpid = read_registry_value(winreg.HKEY_LOCAL_MACHINE, base + "\\" + sub, "DigitalProductId")
                        pname = read_registry_value(winreg.HKEY_LOCAL_MACHINE, base + "\\" + sub, "ProductName")
                        if dpid:
                            results.append((pname or version_name, version_name, decode_product_key(dpid)))
        except Exception:
            continue
    return results

# --- Command runner ---

def run_cmd(cmd: List[str], timeout: int = 60) -> str:
    """Run a command and return stdout text (no exception on non-zero)."""
    try:
        p = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, shell=False)
        out, _ = p.communicate(timeout=timeout)
        return out or ""
    except Exception as e:
        return f"ERROR: {e}"

# --- slmgr.vbs parser (Windows) ---

def get_windows_slmgr_details() -> Dict[str, str]:
    """
    Run 'slmgr.vbs /dlv' and extract useful fields.
    We attempt to support multiple locales by matching common keywords.
    """
    slmgr = os.path.join(os.environ.get("SystemRoot", r"C:\Windows"), "System32", "slmgr.vbs")
    if not os.path.exists(slmgr):
        return {"error": "slmgr.vbs not found"}

    out = run_cmd(["cscript.exe", "//nologo", slmgr, "/dlv"])

    patterns = {
        "partial_key": [
            r"(Partial Product Key|Останні 5 символів|Последние 5 символов|Últimos 5 caracteres|Letzte 5 Zeichen)\s*:\s*([A-Z0-9]{5})"
        ],
        "license_status": [
            r"(License Status|Стан ліцензування|Состояние лицензион|Estado de la licen|Lizenzstatus)\s*:\s*(.+)"
        ],
        "kms_machine": [
            r"(KMS machine name|Ім'?я комп'ютера KMS|Имя узла KMS|Nombre de equipo KMS|KMS-Computername)\s*:\s*(\S+)"
        ],
        "kms_port": [
            r"(KMS machine port|Порт служби KMS|Порт узла KMS|Puerto de KMS|KMS-Port)\s*:\s*(\d+)"
        ],
        "expiration": [
            r"(Expiration|Закінчення строку|Истечение срока|Caducidad|Ablauf)\s*:\s*(.+)"
        ],
    }

    details: Dict[str, str] = {"raw": out.strip()}
    for key, pats in patterns.items():
        for pat in pats:
            m = re.search(pat, out, flags=re.IGNORECASE)
            if m:
                details[key] = m.group(m.lastindex).strip()
                break
    return details

# --- OSPP.VBS parser (Office) ---

def find_ospp_script() -> Optional[str]:
    """
    Try to locate OSPP.VBS across typical Office locations.
    """
    candidates = []
    pf = os.environ.get("ProgramFiles", r"C:\Program Files")
    pfx86 = os.environ.get("ProgramFiles(x86)", r"C:\Program Files (x86)")
    office_versions = ["Office16", "Office15", "Office14"]

    for root in (pf, pfx86):
        for ver in office_versions:
            candidates.append(os.path.join(root, "Microsoft Office", ver, "OSPP.VBS"))

    for c in candidates:
        if os.path.exists(c):
            return c
    return None

def get_office_ospp_details() -> List[Dict[str, str]]:
    """
    Run 'OSPP.VBS /dstatus' and parse licenses found.
    Returns a list of dicts per license block.
    """
    ospp = find_ospp_script()
    if not ospp:
        return [{"error": "OSPP.VBS not found"}]

    out = run_cmd(["cscript.exe", "//nologo", ospp, "/dstatus"])
    if not out.strip():
        return [{"error": "No output from OSPP.VBS"}]

    # Split by blank lines into blocks
    blocks = [b.strip() for b in re.split(r"\n\s*\n", out) if b.strip()]
    results: List[Dict[str, str]] = []

    # Patterns with multi-locale keywords
    rx_map = {
        "license_name": [
            r"(LICENSE NAME|ІМ'?Я ЛІЦЕНЗІЇ|ИМЯ ЛИЦЕНЗИИ|NOMBRE DE LA LICENCIA|LIZENZNAME)\s*:\s*(.+)"
        ],
        "license_desc": [
            r"(LICENSE DESCRIPTION|ОПИС ЛІЦЕНЗІЇ|ОПИСАНИЕ ЛИЦЕНЗИИ|DESCRIPCIÓN DE LA LICENCIA|LIZENZBESCHREIBUNG)\s*:\s*(.+)"
        ],
        "license_status": [
            r"(LICENSE STATUS|СТАТУС ЛІЦЕНЗІЇ|СТАТУС ЛИЦЕНЗИИ|ESTADO DE LA LICENCIA|LIZENZSTATUS)\s*:\s*(.+)"
        ],
        "last5": [
            r"(Last 5 characters|Останні 5 символів|Последние 5 символов|Últimos 5 caracteres|Letzte 5 Zeichen)\s*:\s*([A-Z0-9]{5})"
        ],
        "expiration": [
            r"(Expiration|Закінчення|Истечение|Caducidad|Ablauf)\s*:\s*(.+)"
        ],
        "product_key_channel": [
            r"(PRODUCT KEY CHANNEL|КАНАЛ КЛЮЧА ПРОДУКТА|КАНАЛ КЛЮЧА ПРОДУКТА|CANAL DE CLAVE|PRODUKTSCHLÜSSELKANAL)\s*:\s*(.+)"
        ],
    }

    for block in blocks:
        d: Dict[str, str] = {"raw": block}
        for key, pats in rx_map.items():
            for pat in pats:
                m = re.search(pat, block, flags=re.IGNORECASE)
                if m:
                    d[key] = m.group(m.lastindex).strip()
                    break
        # Only keep blocks that look relevant (have status or last5 or name)
        if any(k in d for k in ("license_status", "last5", "license_name")):
            results.append(d)

    if not results:
        results.append({"raw": out.strip(), "note": "No recognizable license blocks parsed"})
    return results

# --- Main ---

def main():
    print("=== Product Key & License Info ===\n")

    # Windows (registry)
    win = get_windows_info()
    if win:
        print(f"[Windows]\nName: {win[0]}\nVersion: {win[1]}\nKey: {win[2]}")
    else:
        print("[Windows]\nKey not found or digital license in use (no registry key).")

    # Windows (slmgr)
    print("\n-- Windows slmgr (/dlv) --")
    wdlv = get_windows_slmgr_details()
    if "error" in wdlv and wdlv["error"]:
        print(f"Error: {wdlv['error']}")
    else:
        if "partial_key" in wdlv:
            print(f"Partial Key: {wdlv['partial_key']}")
        if "license_status" in wdlv:
            print(f"License Status: {wdlv['license_status']}")
        if "kms_machine" in wdlv:
            print(f"KMS Host: {wdlv['kms_machine']}:{wdlv.get('kms_port', '')}".rstrip(":"))
        if "expiration" in wdlv:
            print(f"Expiration: {wdlv['expiration']}")
        # Always keep raw available for troubleshooting
        if not any(k in wdlv for k in ("partial_key", "license_status", "kms_machine", "expiration")):
            print("(Could not parse fields reliably; raw output below)")
        print("\n[Raw slmgr output]\n" + wdlv.get("raw", "").strip())

    # Office (registry)
    print("\n--- Office (registry) ---")
    office = enum_office_keys()
    if office:
        for name, version, key in office:
            print(f"{name} ({version})\nKey: {key}\n")
    else:
        print("No Office keys found in registry (Click-to-Run/subscription/KMS may not store visible key).")

    # Office (OSPP)
    print("-- Office OSPP (/dstatus) --")
    olist = get_office_ospp_details()
    for idx, item in enumerate(olist, 1):
        if "error" in item:
            print(f"[{idx}] Error: {item['error']}")
            continue
        if "license_name" in item:
            print(f"[{idx}] License: {item['license_name']}")
        if "license_desc" in item:
            print(f"    Desc: {item['license_desc']}")
        if "product_key_channel" in item:
            print(f"    Channel: {item['product_key_channel']}")
        if "license_status" in item:
            print(f"    Status: {item['license_status']}")
        if "last5" in item:
            print(f"    Last5: {item['last5']}")
        if "expiration" in item:
            print(f"    Expiration: {item['expiration']}")
        if not any(k in item for k in ("license_name", "license_desc", "license_status", "last5", "expiration", "product_key_channel")):
            print(f"[{idx}] (Unparsed) See raw below")
        # Raw block for debugging
        print("\n    [Raw]\n    " + "\n    ".join(item.get("raw", "").splitlines()))

if __name__ == "__main__":
    # Admin rights recommended for registry + WScript access
    main()
