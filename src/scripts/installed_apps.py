# filename: installed_programs_full_no_ps.py
# English comments only. Windows-only.
# Win32 from registry + optional UWP/MSIX via WinRT (no PowerShell).
# Adds search_installed_programs(patterns=[...]) that returns unique matched apps list.

import re
import ctypes
import ctypes.wintypes as wintypes
from typing import List, Dict, Tuple, Optional
import winreg

# ---- WinRT for UWP/MSIX (no PowerShell), prefer split winrt packages; allow winsdk too ----
_HAS_WINRT = False
PackageManager = None  # type: ignore

try:
    # Preferred (less build pain): split PyWinRT packages
    from winrt.windows.management.deployment import PackageManager  # type: ignore
    _HAS_WINRT = True
except Exception:
    try:
        # Alternative: winsdk (may require build toolchain)
        from winsdk.windows.management.deployment import PackageManager  # type: ignore
        _HAS_WINRT = True
    except Exception:
        _HAS_WINRT = False  # UWP enumeration will be skipped

# ---- Fix for missing HRESULT in ctypes.wintypes (older Python) ----
if not hasattr(wintypes, "HRESULT"):
    wintypes.HRESULT = ctypes.c_long

# ---------- MUI resolver via SHLoadIndirectString ----------
_SHLoadIndirectString = ctypes.WinDLL("shlwapi").SHLoadIndirectString
_SHLoadIndirectString.argtypes = [
    wintypes.LPCWSTR,  # pszSource
    wintypes.LPWSTR,   # pszOutBuf
    wintypes.UINT,     # cchOutBuf
    ctypes.c_void_p,   # ppvReserved
]
_SHLoadIndirectString.restype = wintypes.HRESULT

def resolve_mui_string(value: str) -> str:
    """Resolve MUI resource strings like '@path,-id' using SHLoadIndirectString."""
    if not value or value[0] != "@":
        return value
    buf = ctypes.create_unicode_buffer(1024)
    hr = _SHLoadIndirectString(value, buf, 1024, None)
    if hr == 0:  # S_OK
        s = buf.value.strip()
        return s or value
    return value

# ---------- Registry helpers (Win32) ----------
UNINSTALL_REL_PATH = r"Software\Microsoft\Windows\CurrentVersion\Uninstall"
KEY_READ32 = winreg.KEY_READ | winreg.KEY_WOW64_32KEY
KEY_READ64 = winreg.KEY_READ | winreg.KEY_WOW64_64KEY
SID_RE = re.compile(r"^S-\d-\d+-(\d+-){1,14}\d+$")  # e.g., S-1-5-21-...

def _get_reg_value(key, name: str) -> Optional[str]:
    try:
        val, _ = winreg.QueryValueEx(key, name)
        if isinstance(val, bytes):
            try:
                return val.decode(errors="ignore")
            except Exception:
                return str(val)
        return str(val)
    except (FileNotFoundError, OSError):
        return None

def _get_reg_dword(key, name: str) -> Optional[int]:
    try:
        val, _ = winreg.QueryValueEx(key, name)
        if isinstance(val, int):
            return val
        try:
            return int(val)
        except Exception:
            return None
    except (FileNotFoundError, OSError):
        return None

def _root_name(root: int) -> str:
    return {
        winreg.HKEY_LOCAL_MACHINE: "HKLM",
        winreg.HKEY_CURRENT_USER: "HKCU",
        winreg.HKEY_USERS: "HKU",
    }.get(root, f"HIVE_{root}")

def _scan_uninstall_under(root: int, view_access: int, base_path: str) -> List[Dict[str, str]]:
    """Scan one uninstall branch (root + view) and return items with resolved names."""
    results: List[Dict[str, str]] = []
    try:
        with winreg.OpenKeyEx(root, base_path, 0, view_access) as root_key:
            subcount, _, _ = winreg.QueryInfoKey(root_key)
            for i in range(subcount):
                try:
                    subname = winreg.EnumKey(root_key, i)
                    with winreg.OpenKeyEx(root_key, subname, 0, view_access) as app_key:
                        sys_comp = _get_reg_dword(app_key, "SystemComponent")
                        raw_name = _get_reg_value(app_key, "DisplayName") or _get_reg_value(app_key, "DisplayNameResource")
                        if not raw_name:
                            continue
                        name = resolve_mui_string(raw_name.strip())
                        if not name:
                            continue
                        results.append({
                            "Type": "win32",
                            "DisplayName": name,
                            "DisplayVersion": (_get_reg_value(app_key, "DisplayVersion") or "").strip(),
                            "Publisher": (_get_reg_value(app_key, "Publisher") or "").strip(),
                            "InstallLocation": (_get_reg_value(app_key, "InstallLocation") or "").strip(),
                            "UninstallString": (_get_reg_value(app_key, "UninstallString") or "").strip(),
                            "RegistryKey": f"{base_path}\\{subname}",
                            "RegistryRoot": _root_name(root),
                            "RegistryView": "64" if view_access & winreg.KEY_WOW64_64KEY else "32",
                            "SystemComponent": str(sys_comp if sys_comp is not None else ""),
                        })
                except OSError:
                    continue
    except (FileNotFoundError, PermissionError):
        pass
    return results

def _enumerate_hku_sids() -> List[str]:
    sids: List[str] = []
    try:
        with winreg.OpenKey(winreg.HKEY_USERS, "") as hku:
            count, _, _ = winreg.QueryInfoKey(hku)
            for i in range(count):
                try:
                    name = winreg.EnumKey(hku, i)
                    if SID_RE.match(name) and not name.endswith("_Classes"):
                        sids.append(name)
                except OSError:
                    continue
    except OSError:
        pass
    return sids

# ---------- UWP/MSIX via WinRT (no PowerShell) ----------
def list_uwp_winrt(all_users: bool = False) -> List[Dict[str, str]]:
    """Enumerate UWP/MSIX packages using WinRT PackageManager."""
    if not _HAS_WINRT or PackageManager is None:
        return []

    pm = PackageManager()
    try:
        pkgs = pm.find_packages() if not all_users else pm.find_packages_for_user("")
    except Exception:
        pkgs = pm.find_packages()

    results: List[Dict[str, str]] = []
    for p in pkgs:
        try:
            pid = getattr(p, "id", None)
            name, full_name, family_name, version = "", "", "", ""
            if pid is not None:
                name = getattr(pid, "name", "") or ""
                full_name = getattr(pid, "full_name", "") or ""
                family_name = getattr(pid, "family_name", "") or ""
                ver = getattr(pid, "version", None)
                if ver is not None:
                    version = f"{getattr(ver,'major',0)}.{getattr(ver,'minor',0)}.{getattr(ver,'build',0)}.{getattr(ver,'revision',0)}"
            publisher = getattr(p, "publisher", "") or getattr(p, "publisherId", "") or ""
            install_location = getattr(p, "installed_location", None)
            install_loc_str = getattr(install_location, "path", "") if install_location else ""
            is_framework = bool(getattr(p, "is_framework", False)) or bool(getattr(p, "isFramework", False))
            results.append({
                "Type": "uwp",
                "Name": name or family_name,
                "PackageFullName": full_name,
                "FamilyName": family_name,
                "Version": version,
                "Publisher": publisher,
                "InstallLocation": install_loc_str,
                "IsFramework": is_framework,
            })
        except Exception:
            continue
    return results

# ---------- Public: inventory ----------
def list_installed_programs_advanced(
        *,
        include_hkcu: bool = True,
        include_hklm: bool = True,
        include_hku_profiles: bool = True,
        filter_system_components: bool = True,
        deduplicate: bool = True,
        include_uwp: bool = True,
        uwp_all_users: bool = False,
) -> List[Dict[str, str]]:
    """
    Return Win32 + (optionally) UWP/MSIX apps.
    - Win32 pulled from registry (HKLM/HKCU/HKU, both 32/64 views).
    - UWP/MSIX via WinRT (no PowerShell). If WinRT unavailable, UWP list empty.
    """
    collected: List[Dict[str, str]] = []

    # Win32
    if include_hklm:
        collected += _scan_uninstall_under(winreg.HKEY_LOCAL_MACHINE, KEY_READ64, UNINSTALL_REL_PATH)
        collected += _scan_uninstall_under(winreg.HKEY_LOCAL_MACHINE, KEY_READ32, UNINSTALL_REL_PATH)
    if include_hkcu:
        collected += _scan_uninstall_under(winreg.HKEY_CURRENT_USER, KEY_READ64, UNINSTALL_REL_PATH)
        collected += _scan_uninstall_under(winreg.HKEY_CURRENT_USER, KEY_READ32, UNINSTALL_REL_PATH)
    if include_hku_profiles:
        for sid in _enumerate_hku_sids():
            base = f"{sid}\\{UNINSTALL_REL_PATH}"
            collected += _scan_uninstall_under(winreg.HKEY_USERS, KEY_READ64, base)
            collected += _scan_uninstall_under(winreg.HKEY_USERS, KEY_READ32, base)

    # Filter SystemComponent if requested
    if filter_system_components:
        collected = [
            it for it in collected
            if not (it.get("SystemComponent") and it.get("SystemComponent").isdigit() and int(it["SystemComponent"]) == 1)
        ]

    # Deduplicate Win32 (keep HKLM/64 when duplicate with same name+version+publisher)
    if deduplicate:
        seen: dict[Tuple[str, str, str], Dict[str, str]] = {}
        priority = {"HKLM": 2, "HKCU": 1, "HKU": 0}
        tmp: List[Dict[str, str]] = []
        for it in collected:
            key = (
                (it.get("DisplayName") or "").lower(),
                (it.get("DisplayVersion") or "").lower(),
                (it.get("Publisher") or "").lower(),
            )
            if key not in seen:
                seen[key] = it
            else:
                old = seen[key]
                old_score = (priority.get(old.get("RegistryRoot", ""), -1), 1 if old.get("RegistryView") == "64" else 0)
                new_score = (priority.get(it.get("RegistryRoot", ""), -1), 1 if it.get("RegistryView") == "64" else 0)
                if new_score > old_score:
                    seen[key] = it
        tmp = list(seen.values())
        collected = tmp

    # Add UWP if requested
    if include_uwp:
        collected += list_uwp_winrt(all_users=uwp_all_users)

    return collected

def list_installed_programs(
        include_uwp: bool = True,
        uwp_all_users: bool = False,
        filter_system_components: bool = True,
) -> List[Dict[str, str]]:
    """Convenience wrapper; uses WinRT for UWP if available (no PowerShell)."""
    return list_installed_programs_advanced(
        include_hkcu=True,
        include_hklm=True,
        include_hku_profiles=True,
        filter_system_components=filter_system_components,
        deduplicate=True,
        include_uwp=include_uwp,
        uwp_all_users=uwp_all_users,
    )

# ---------- Search: substring / fuzzy over multiple patterns ----------
# Optional: RapidFuzz backend for better fuzzy quality; fallback to difflib
try:
    from rapidfuzz import fuzz  # pip install rapidfuzz
    _HAS_RAPIDFUZZ = True
except Exception:
    import difflib
    _HAS_RAPIDFUZZ = False

def _norm(s: str) -> str:
    return (s or "").casefold().strip()

def _score_similarity(needle: str, hay: str) -> int:
    """Return 0..100 similarity (RapidFuzz preferred, difflib fallback)."""
    n, h = _norm(needle), _norm(hay)
    if not n or not h:
        return 0
    if _HAS_RAPIDFUZZ:
        # partial_ratio (good for substrings) vs token_set_ratio (order-insensitive)
        p = fuzz.partial_ratio(n, h)
        t = fuzz.token_set_ratio(n, h)
        return max(int(p), int(t))
    else:
        if n in h:
            return 100
        return int(difflib.SequenceMatcher(None, n, h).ratio() * 100)

def search_installed_programs(
        patterns: List[str],
        apps: List[Dict[str, str]] = None,
        *,
        include_uwp: bool = True,
        uwp_all_users: bool = False,
        filter_system_components: bool = True,
        mode: str = "fuzzy",         # "fuzzy" | "substring"
        threshold: int = 70,         # min score for fuzzy mode
        top_k_per_pattern: int = 200 # internal cap per pattern; final set is unique
) -> List[Dict[str, str]]:
    """
    Multi-pattern search over installed apps. Returns a unique list of matched apps.

    Args:
        patterns: list of search strings (e.g., ["chrome", "visual c++", "acer purified voice"]).
        apps: optional pre-fetched inventory; if None, inventory is fetched here.
        include_uwp/uwp_all_users/filter_system_components: forwarded to inventory if apps is None.
        mode: "substring" (fast contains) or "fuzzy" (scored).
        threshold: minimal score for fuzzy matches (0..100).
        top_k_per_pattern: limit per pattern before union/dedup.

    Returns:
        List of unique app dicts. Each matched item is augmented with:
          - "Score" (best score among patterns, 0..100)
          - "MatchedPatterns" (list of patterns that matched)
    """
    # Prepare patterns
    queries = [p for p in (patterns or []) if isinstance(p, str) and p.strip()]
    if not queries:
        return []

    # Load inventory if needed
    if apps is None:
        apps = list_installed_programs(
            include_uwp=include_uwp,
            uwp_all_users=uwp_all_users,
            filter_system_components=filter_system_components,
        )

    # Build searchable label per app (DisplayName/Name + Publisher)
    def label_for(a: Dict[str, str]) -> str:
        name = a.get("DisplayName") or a.get("Name") or ""
        pub = a.get("Publisher") or ""
        return f"{name} {pub}".strip()

    # Accumulate matches
    matched_map: Dict[int, Dict[str, str]] = {}  # id(app) -> augmented app
    for q in queries:
        qn = _norm(q)
        scored: List[Tuple[int, Dict[str, str], int]] = []  # (score, app, idx)

        for idx, app in enumerate(apps):
            lbl = label_for(app)
            if mode == "substring":
                ok = qn in _norm(lbl)
                score = 100 if ok else 0
            else:
                score = _score_similarity(q, lbl)

            if score > 0 and (mode == "substring" or score >= threshold):
                scored.append((score, app, idx))

        # Sort best-first for this pattern and clip
        scored.sort(key=lambda t: -t[0])
        for score, app, idx in scored[:max(1, top_k_per_pattern)]:
            key = id(app)
            if key not in matched_map:
                # copy to avoid mutating original inventory
                aug = dict(app)
                aug["Score"] = score
                aug["MatchedPatterns"] = [q]
                matched_map[key] = aug
            else:
                # update best score and add pattern
                if score > int(matched_map[key].get("Score", 0)):
                    matched_map[key]["Score"] = score
                if q not in matched_map[key]["MatchedPatterns"]:
                    matched_map[key]["MatchedPatterns"].append(q)

    # Final unique list sorted by Score desc, then by name
    result = list(matched_map.values())
    def sort_name(a: Dict[str, str]) -> str:
        return _norm(a.get("DisplayName") or a.get("Name") or "")
    result.sort(key=lambda x: (-int(x.get("Score", 0)), sort_name(x)))
    return result
