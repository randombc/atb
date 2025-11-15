import csv
import os
import re
from pathlib import Path

from core.navigation import NavigationNode
from core.utils import get_folder_path
from scripts.services_export import get_services_startup


def _get_storage_dir() -> str:
    return str(get_folder_path('Services'))


def _sanitize_name(name: str) -> str:
    name = name.strip()
    # заборонені символи для імен файлів у Windows
    name = re.sub(r'[<>:"/\\|?*]+', '_', name)
    name = re.sub(r'\s+', '_', name)
    return name


class SaveServices(NavigationNode):
    def get_name(self) -> str:
        return 'Save'

    def process(self):
        try:
            services = get_services_startup()
        except Exception as e:
            print(f"Error reading services: {e}")
            return self.wait_back()

        storage = _get_storage_dir()
        print("Enter a name to save the services profile.")
        print("Note: invalid characters will be replaced with '_' ; empty name is not allowed.")
        name = input("Profile name: ").strip()

        name = _sanitize_name(name)
        if not name:
            print("Error: empty profile name.")
            return self.wait_back()

        filename = f"{name}.csv"
        path = os.path.join(storage, filename)

        if os.path.exists(path):
            print(f"Error: profile '{filename}' already exists in '{storage}'. Choose another name.")
            return self.wait_back()

        with Path(path).open("w", encoding="utf-8", newline="") as f:
            writer = csv.writer(f)
            writer.writerow(["ServiceName", "DisplayName", "StartMode"])
            for arr in services:
                writer.writerow(arr)

        self.wait_back()
        return None
