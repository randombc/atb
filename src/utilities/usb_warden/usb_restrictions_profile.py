import os
import re
import json
from pathlib import Path
from typing import Optional

from core.navigation import FolderNode, NavigationNode
from core.utils import get_folder_path
from prompt_toolkit import choice


class SaveUsbRestrictions(NavigationNode):
    def get_name(self) -> str:
        return "Save"

    def process(self):
        storage = _get_storage_dir()
        os.makedirs(storage, exist_ok=True)

        print("Enter a file name to save USB restrictions settings.")
        print("Note: invalid characters will be replaced with '_' ; empty name is not allowed.")
        raw_name = input("Name: ").strip()

        name = _sanitize_name(raw_name)
        if not name:
            print("Error: empty name.")
            return self.wait_back()

        target_path = os.path.join(storage, f"{name}.json")
        if os.path.exists(target_path):
            print(f"Error: file '{os.path.basename(target_path)}' already exists in '{storage}'. Choose another name.")
            return self.wait_back()

        try:
            data = {
                "kind": "usb_restrictions",
                "version": 1,
                "name": name,
                "payload": {
                    # TODO: fill with actual policy/registry parameters
                }
            }
            with open(target_path, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
            print(f"Saved: {target_path}")
        except Exception as e:
            print(f"Failed to save file: {e}")

        return self.wait_back()


class LoadUsbRestrictions(NavigationNode):
    def get_name(self) -> str:
        return "Load"

    def process(self):
        storage = _get_storage_dir()
        os.makedirs(storage, exist_ok=True)

        files = [f for f in os.listdir(storage) if os.path.isfile(os.path.join(storage, f))]
        files.sort(key=str.lower)

        if not files:
            print("No USB restrictions settings files found.")
            return self.wait_back()

        options: list[tuple[Optional[str], str]] = [(None, '[...]')]
        for fname in files:
            options.append((fname, fname))

        selected = choice(
            message='Choose a file to load:',
            options=options,
        )

        if selected is None:
            return self.move_back()

        path = os.path.join(storage, selected)

        try:
            with open(path, "r", encoding="utf-8") as f:
                data = json.load(f)

            # TODO: apply actual settings from data["payload"]
            print(f"Loaded file: {path}")
            print("Applying settings is not implemented yet.")
        except Exception as e:
            print(f"Error while loading file: {e}")

        return self.wait_back()


class UsbRestrictions(FolderNode):
    CHILDREN = [
        SaveUsbRestrictions(),
        LoadUsbRestrictions(),
    ]

    def get_name(self) -> str:
        return "USB restrictions"


def _get_storage_dir() -> Path:
    return get_folder_path("USB")


def _sanitize_name(name: str) -> str:
    if not name:
        return ""

    result = re.sub(r"[^a-zA-Z0-9_\\-]+", "_", name)
    return result
