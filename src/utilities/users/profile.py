from typing import Optional

from prompt_toolkit import choice

from common.list_drives import get_drives
from core.navigation import FolderNode
from core.navigation import NavigationNode
from core.utils import cls
from scripts.set_default_profile import set_profiles_directory
from scripts.show_profile_destination import print_profiles_directory


def get_name(d):
    return f"{d[0]:6} | {d[1]:9} | File system: {d[2].fstype}"


class SetProfile(NavigationNode):
    def get_name(self) -> str:
        return "Set default profile"

    def process(self):
        options: list[tuple[Optional[NavigationNode], str]] = [(None, '[...]')]

        options += [
            (d[0], get_name(d)) for d in get_drives()
        ]

        result = choice(
            message='',
            options=options,
        )

        if result is None:
            self.move_back()
            return

        assert result is not None

        cls()

        print("Done.")

        set_profiles_directory(str(result)[:-1])

        self.move_back()


class Profile(FolderNode):
    def get_name(self) -> str:
        return "Profile Folder"

    def process(self):
        print()
        print_profiles_directory()

        from prompt_toolkit import choice
        action_options: list[tuple[object, str]] = [
            ("change", "Change drive"),
            (None, "Back"),
        ]
        action = choice(message='', options=action_options, default=None)

        if action == "change":
            # Navigate to SetProfile to choose a new drive
            self._move_next(SetProfile())
            return

        # Default: go back
        self.move_back()
