from __future__ import annotations
import os
from typing import Optional, List, Dict
import wmi


def normalize_pnp_id(pnp_id: str) -> str:
    """
    Normalize PNPDeviceID so that multiple entries for the same physical device
    (e.g. with &0, &1, &LUN0 suffixes) are grouped into a single key.

    Example:
        USBSTOR\\DISK&VEN_FOO&PROD_BAR\\12345678&0  -> USBSTOR\\DISK&VEN_FOO&PROD_BAR\\12345678
        USBSTOR\\DISK&VEN_FOO&PROD_BAR\\12345678&1  -> USBSTOR\\DISK&VEN_FOO&PROD_BAR\\12345678
    """
    up = pnp_id.upper()
    for suffix in ("&0", "&1", "&2", "&3", "&LUN0", "&LUN1", "&LUN2", "&LUN3"):
        if up.endswith(suffix):
            return up[: -len(suffix)]
    return up


class UsbVolume:
    """
    Represents a single volume of a USB storage device (drive letter, filesystem,
    size, label, filesystem state).
    """

    def __init__(
            self,
            drive_letter: Optional[str],
            filesystem: Optional[str],
            size_bytes: Optional[int],
            free_bytes: Optional[int],
            label: Optional[str],
    ):
        self.drive_letter: Optional[str] = drive_letter
        self.filesystem: Optional[str] = filesystem
        self.size_bytes: Optional[int] = size_bytes
        self.free_bytes: Optional[int] = free_bytes
        self.label: Optional[str] = label

        # Filesystem health status:
        # None  – not checked / cannot be checked
        # False – healthy
        # True  – OS error when accessing the root directory
        self.is_broken: Optional[bool] = None
        self.error_message: Optional[str] = None

    def check_filesystem_health(self) -> None:
        """
        Attempts to list the root directory to check filesystem validity.
        If OSError is raised → filesystem is damaged or inaccessible.
        """
        if not self.drive_letter:
            self.is_broken = None
            self.error_message = "No drive letter, cannot check filesystem"
            return

        root_path = self.drive_letter + "\\"

        try:
            os.listdir(root_path)
            self.is_broken = False
            self.error_message = None
        except OSError as e:
            self.is_broken = True
            self.error_message = f"{e.__class__.__name__}: {e}"

    def __repr__(self) -> str:
        return (
            f"UsbVolume(letter={self.drive_letter}, label={self.label}, "
            f"fs={self.filesystem}, size={self.size_bytes}, broken={self.is_broken})"
        )


class UsbStorageDevice:
    """
    Unified representation of a physical USB storage device.

    Contains:
    - PnP layer info (USBSTOR)
    - Disk layer info (if the device is installed as a disk)
    """

    def __init__(self, normalized_pnp_id: str):
        # Normalized PNP id used as a grouping key
        self.normalized_pnp_id: str = normalized_pnp_id

        # PnP layer information (aggregated from Win32_PnPEntity entries)
        self.name: Optional[str] = None
        self.pnp_ids: List[str] = []          # all raw PnP IDs (including &0, &1, ...)
        self.status: Optional[str] = None
        self.error_code: Optional[int] = None

        # Disk layer information (only if the OS created DiskDrive entries)
        self.drive_model: Optional[str] = None
        self.device_id: Optional[str] = None
        self.size_bytes: Optional[int] = None
        self.volumes: List[UsbVolume] = []

        # Whether the device is fully installed and mounted as a disk
        self.is_installed: bool = False

    def update_pnp_info(
            self,
            name: Optional[str],
            raw_pnp_id: str,
            status: Optional[str],
            error_code: Optional[int],
    ) -> None:
        """
        Merge PnP information from a single Win32_PnPEntity row into this device.
        Prefer a "short" (non-suffixed) PNP ID for display if possible.
        """
        self.pnp_ids.append(raw_pnp_id)

        # Choose a display name / status / error_code using a simple heuristic:
        # - Prefer an ID without &0/&1/&LUN0 suffix (shorter base PnP)
        # - Otherwise keep the first one
        if self.name is None or self._is_better_pnp_id(raw_pnp_id):
            self.name = name
            self.status = status
            self.error_code = error_code

    def _is_better_pnp_id(self, new_pnp: str) -> bool:
        """
        Decide if the new PnP ID is a "better" representative for the device.
        Here we simply prefer the shortest one (usually without &0/&1 suffix).
        """
        if not self.pnp_ids:
            return True
        current = self.pnp_ids[0]
        return len(new_pnp) < len(current)

    def attach_disk_info(
            self,
            model: Optional[str],
            device_id: Optional[str],
            size_bytes: Optional[int],
            volumes: Optional[List[UsbVolume]],
    ) -> None:

        self.drive_model = model
        self.device_id = device_id
        self.size_bytes = size_bytes
        self.volumes = volumes or []

        # Device is considered installed only if DiskDrive exists AND
        # ConfigManagerErrorCode is 0 or None
        if self.error_code in (None, 0):
            self.is_installed = True
        else:
            self.is_installed = False

    def __repr__(self) -> str:
        return (
            f"UsbStorageDevice(name={self.name}, normalized_pnp={self.normalized_pnp_id}, "
            f"is_installed={self.is_installed}, volumes={self.volumes})"
        )


def list_usb_storage_devices(check_fs_health: bool = False) -> List[UsbStorageDevice]:
    """
    Returns a list of UsbStorageDevice — one per physical USB storage device.

    - All USBSTOR PnP entries (&0, &1, &LUN0, ...) for the same device
      are grouped into a single UsbStorageDevice.
    - is_installed:
        True  → the OS successfully created DiskDrive/LogicalDisk
        False → installation failed or was blocked by Device Installation GPO
    """
    c = wmi.WMI()

    # --- 1. Collect USB disks from Win32_DiskDrive + LogicalDisk, grouped by normalized PNP ---
    disks_by_norm_pnp: Dict[str, Dict[str, object]] = {}

    for disk in c.Win32_DiskDrive():
        if disk.InterfaceType != "USB":
            continue

        raw_pnp = disk.PNPDeviceID or ""
        norm_pnp = normalize_pnp_id(raw_pnp)

        model: Optional[str] = disk.Model
        device_id: Optional[str] = disk.DeviceID
        size_bytes: Optional[int] = int(disk.Size) if disk.Size else None

        volumes: List[UsbVolume] = []

        # Link DiskDrive → Partition → LogicalDisk
        for partition in disk.associators("Win32_DiskDriveToDiskPartition"):
            for logical in partition.associators("Win32_LogicalDiskToPartition"):
                vol = UsbVolume(
                    drive_letter=logical.DeviceID,
                    filesystem=logical.FileSystem,
                    size_bytes=int(logical.Size) if logical.Size else None,
                    free_bytes=int(logical.FreeSpace) if logical.FreeSpace else None,
                    label=logical.VolumeName,
                )
                if check_fs_health:
                    vol.check_filesystem_health()
                volumes.append(vol)

        disks_by_norm_pnp[norm_pnp] = {
            "model": model,
            "device_id": device_id,
            "size_bytes": size_bytes,
            "volumes": volumes,
        }

    # --- 2. Collect all USBSTOR devices from Win32_PnPEntity and group them ---
    devices_by_norm_pnp: Dict[str, UsbStorageDevice] = {}

    for dev in c.Win32_PnPEntity():
        raw_pnp = dev.PNPDeviceID
        if not raw_pnp:
            continue

        up = raw_pnp.upper()
        # Only real USBSTOR root devices, ignore STORAGE\..., SWD\WPDBUSENUM\...
        if not up.startswith("USBSTOR\\"):
            continue


        norm_pnp = normalize_pnp_id(raw_pnp)

        name: Optional[str] = dev.Name
        status: Optional[str] = dev.Status
        error_code: Optional[int] = getattr(dev, "ConfigManagerErrorCode", None)

        device = devices_by_norm_pnp.get(norm_pnp)
        if device is None:
            device = UsbStorageDevice(normalized_pnp_id=norm_pnp)
            devices_by_norm_pnp[norm_pnp] = device

        device.update_pnp_info(
            name=name,
            raw_pnp_id=raw_pnp,
            status=status,
            error_code=error_code,
        )

    # --- 3. Attach disk information (if any) to each grouped device ---
    for norm_pnp, disk_info in disks_by_norm_pnp.items():
        device = devices_by_norm_pnp.get(norm_pnp)
        if not device:
            # DiskDrive exists but we didn't see a matching USBSTOR PnP entry (rare case)
            # We could optionally create a "disk-only" UsbStorageDevice here.
            continue

        device.attach_disk_info(
            model=disk_info["model"],         # type: ignore[arg-type]
            device_id=disk_info["device_id"], # type: ignore[arg-type]
            size_bytes=disk_info["size_bytes"],   # type: ignore[arg-type]
            volumes=disk_info["volumes"],     # type: ignore[arg-type]
        )

    return list(devices_by_norm_pnp.values())
