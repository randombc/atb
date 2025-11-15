import os
from typing import List

from core.navigation import FolderNode, NavigationNode
from core.utils import get_folder_path
from prompt_toolkit.shortcuts import ProgressBar
from scripts.lgpo_manager import list_profiles, apply_profile, LgpoError
import subprocess


def _get_storage_dir() -> str:
    return str(get_folder_path('Policies'))


class PolicyFileNode(NavigationNode):
    def __init__(self, profile_name: str):
        super().__init__()
        self._profile_name = profile_name

    def get_name(self) -> str:
        # Show profile directory name
        return self._profile_name

    def process(self):
        print(f"Applying profile: {self._profile_name}")
        try:
            # Single-step progress bar while LGPO applies the profile
            with ProgressBar(title="Applying LGPO profile") as pb:
                for _ in pb(range(1), label="Running LGPO /g ..."):
                    apply_profile(self._profile_name)
            print("Profile applied successfully.")
            print("Running 'gpupdate /force' ...")
            subprocess.run(["gpupdate", "/force"], check=False)
            print("Group Policy updated.")
        except LgpoError as e:
            print(f"LGPO error: {e}")
        except Exception as e:
            print(f"Unexpected error: {e}")

        self.wait_back()


class LoadPolicies(FolderNode):
    def __init__(self):
        super().__init__()
        # Do not build CHILDREN here to avoid stale list
        self.CHILDREN = []

    def process(self):
        # Rebuild list every time user opens Load
        files = list_profiles()
        self.CHILDREN = [PolicyFileNode(profile_name=f) for f in files]

        super().process()

    def get_name(self) -> str:
        return 'Load'
