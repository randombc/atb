import os
from pathlib import Path
from typing import List

from core.navigation import NavigationNode, FolderNode
from core.utils import get_folder_path
from scripts.services_restore import load_services_from_csv, apply_service_config


def _get_storage_dir() -> str:
    return str(get_folder_path('Services'))


def _list_profiles() -> List[str]:
    storage = _get_storage_dir()
    if not os.path.isdir(storage):
        return []
    return sorted([f for f in os.listdir(storage) if f.lower().endswith('.csv')])


class SavedProfileView(NavigationNode):
    def __init__(self, profile_path: str):
        super().__init__()
        self._path = profile_path

    def get_name(self) -> str:
        return os.path.splitext(os.path.basename(self._path))[0]

    def process(self):
        if not os.path.exists(self._path):
            print("Profile file not found.")
            return self.wait_back()

        services = load_services_from_csv(Path(self._path))
        for service in services:
            service_name = service["ServiceName"]
            start_mode = service["StartMode"]
            apply_service_config(service_name, start_mode)

        return self.wait_back()


class LoadServices(FolderNode):
    def __init__(self):
        super().__init__()

    def get_name(self) -> str:
        return 'Load'

    def process(self):
        storage = _get_storage_dir()
        files = _list_profiles()
        self.CHILDREN = [
            SavedProfileView(os.path.join(storage, fname)) for fname in files
        ]

        super().process()
