import psutil

# Mapping of drive types for readability
DRIVE_TYPES = {
    "removable": "Removable",
    "fixed": "Fixed",
    "cdrom": "CD-ROM",
    "network": "Network",
    "unknown": "Unknown"
}

def get_drive_type(partition):
    """Try to guess drive type based on psutil information"""
    if 'cdrom' in partition.opts:
        return DRIVE_TYPES["cdrom"]
    if 'removable' in partition.opts:
        return DRIVE_TYPES["removable"]
    if partition.fstype:  # if filesystem is defined → fixed or network
        if partition.device.startswith("\\\\"):  # network path
            return DRIVE_TYPES["network"]
        else:
            return DRIVE_TYPES["fixed"]
    return DRIVE_TYPES["unknown"]

def get_drives():
    result = []
    for partition in psutil.disk_partitions(all=False):
        drive = partition.device
        dtype = get_drive_type(partition)
        result.append((drive, dtype, partition))
    return result

