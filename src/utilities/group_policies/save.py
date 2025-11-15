import os
import re

from core.navigation import NavigationNode
from core.utils import get_folder_path
from prompt_toolkit.shortcuts import ProgressBar
from scripts.lgpo_manager import export_profile, profile_exists, LgpoError


def _get_storage_dir() -> str:
    return str(get_folder_path('Policies'))

def _sanitize_name(name: str) -> str:
    name = name.strip()
    # forbidden characters for file names in Windows
    name = re.sub(r'[<>:"/\\|?*]+', '_', name)
    name = re.sub(r'\s+', '_', name)
    return name


class SavePolicies(NavigationNode):
    def get_name(self) -> str:
        return 'Save'

    def process(self):
        storage = _get_storage_dir()
        os.makedirs(storage, exist_ok=True)

        print("Enter a profile name to export Local Group Policy (LGPO).")
        print("Note: invalid characters will be replaced with '_' ; empty name is not allowed.")
        raw_name = input("Profile name: ").strip()

        name = _sanitize_name(raw_name)
        if not name:
            print("Error: empty profile name.")
            return self.wait_back()

        # We store profiles as directories under Policies/<name>
        target_dir = os.path.join(storage, name)
        if profile_exists(name) or os.path.isdir(target_dir):
            print(f"Error: profile directory '{name}' already exists in '{storage}'. Choose another name.")
            return self.wait_back()

        # Show a simple progress bar while exporting via LGPO
        try:
            with ProgressBar(title="Exporting LGPO profile") as pb:
                for _ in pb(range(1), label="Running LGPO /b ..."):
                    export_profile(name, overwrite=False)
            print(f"Profile exported to: {target_dir}")
        except LgpoError as e:
            print(f"LGPO error: {e}")
        except Exception as e:
            print(f"Unexpected error: {e}")

        return self.wait_back()
