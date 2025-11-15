import win32service
import csv
from pathlib import Path

# Map human-readable values to WinAPI constants
START_MODE_MAP = {
    "Auto": win32service.SERVICE_AUTO_START,
    "Manual": win32service.SERVICE_DEMAND_START,
    "Disabled": win32service.SERVICE_DISABLED,
}

def load_services_from_csv(filepath: Path):
    """
    Loads services configuration from a CSV file.
    Returns a list of dictionaries with keys: ServiceName, DisplayName, StartMode.
    """
    services = []
    with filepath.open("r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            services.append(row)
    return services

def apply_service_config(service_name: str, start_mode: str):
    """
    Applies a startup type configuration for a single service.
    """
    if start_mode not in START_MODE_MAP:
        print(f"[!] Unknown StartMode '{start_mode}' for service {service_name}, skipping...")
        return

    scm = win32service.OpenSCManager(None, None, win32service.SC_MANAGER_ALL_ACCESS)
    try:
        service = win32service.OpenService(scm, service_name, win32service.SERVICE_ALL_ACCESS)
        win32service.ChangeServiceConfig(
            service,
            win32service.SERVICE_NO_CHANGE,       # service type
            START_MODE_MAP[start_mode],           # start type
            win32service.SERVICE_NO_CHANGE,       # error control
            None, None, 0, None, None, None, None
        )
        print(f"[+] Restored {service_name} -> {start_mode}")
        win32service.CloseServiceHandle(service)
    except Exception as e:
        print(f"[!] Failed to restore {service_name}: {e}")
    finally:
        win32service.CloseServiceHandle(scm)

def restore_services(filepath: Path):
    """
    Restores all services from the given CSV file.
    """
    services = load_services_from_csv(filepath)
    for service in services:
        service_name = service["ServiceName"]
        start_mode = service["StartMode"]
        apply_service_config(service_name, start_mode)

if __name__ == "__main__":
    input_file = Path("services_startup.csv")
    if input_file.exists():
        restore_services(input_file)
        print("[*] Service configuration restore completed.")
    else:
        print(f"[!] File {input_file} not found.")
