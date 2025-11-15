import win32service
import win32serviceutil
import csv
from pathlib import Path

# Map WinAPI service start types to human-readable values
START_TYPE_MAP = {
    win32service.SERVICE_AUTO_START: "Auto",
    win32service.SERVICE_DEMAND_START: "Manual",
    win32service.SERVICE_DISABLED: "Disabled",
}

def get_services_startup():
    """
    Collects Windows services and their startup type (Auto, Manual, Disabled).
    Returns a list of tuples: (service_name, display_name, start_type).
    """
    services = []
    scm = win32service.OpenSCManager(None, None, win32service.SC_MANAGER_ENUMERATE_SERVICE)

    try:
        statuses = win32service.EnumServicesStatus(scm, win32service.SERVICE_WIN32, win32service.SERVICE_STATE_ALL)
        for (service_name, display_name, status) in statuses:
            try:
                h_service = win32service.OpenService(scm, service_name, win32service.SERVICE_QUERY_CONFIG)
                config = win32service.QueryServiceConfig(h_service)
                start_type = START_TYPE_MAP.get(config[1], "Unknown")  # config[1] = start_type
                services.append((service_name, display_name, start_type))
                win32service.CloseServiceHandle(h_service)
            except Exception as e:
                print(f"[!] Could not query {service_name}: {e}")
    finally:
        win32service.CloseServiceHandle(scm)

    return services

def save_services_to_csv(filepath: Path):
    """
    Saves the list of services to a CSV file.
    """
    services = get_services_startup()
    with filepath.open("w", encoding="utf-8", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(["ServiceName", "DisplayName", "StartMode"])
        for name, display_name, mode in services:
            writer.writerow([name, display_name, mode])

if __name__ == "__main__":
    output_file = Path("services_startup.csv")
    save_services_to_csv(output_file)
    print(f"[+] Services list saved to {output_file.resolve()}")
