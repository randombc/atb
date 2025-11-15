from pathlib import Path
from typing import Optional

from prompt_toolkit import choice, prompt

from core.navigation import NavigationNode
from core.utils import get_folder_path
from scripts.create_users_pywin32_only import process_list_file


class CreateUserList(NavigationNode):
    def get_name(self) -> str:
        return "Create user list"

    def process(self):
        options: list[tuple[Optional[Path], str]] = [(None, '[...]')]
        userlist_dir = get_folder_path("UserList")
        userlist = [f for f in userlist_dir.glob("*.list") if f.is_file()]

        options += [
            (f, f.stem) for f in userlist
        ]

        user_list = choice(
            message='',
            options=options,
        )

        if user_list is None:
            self.move_back()
            return

        answer = prompt(
            f"You are going to create a list of users from {user_list.name} file. Are you sure? (y/n):").strip().lower()

        if answer != "y":
            return

        process_list_file(user_list)

        self.wait_back()
