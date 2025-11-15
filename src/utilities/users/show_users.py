from typing import Optional

import wmi
from prompt_toolkit import choice, HTML

from core.navigation import NavigationNode
from utilities.users.user_info import UserInfo


def get_name(acc):
    if acc.Disabled:
        return HTML(f"<ansibrightblack>{acc.Name}</ansibrightblack>")
    return acc.Name

class ShowUsers(NavigationNode):

    def __init__(self):
        super().__init__()
        self._last_selected: Optional[NavigationNode] = None

    def get_name(self) -> str:
        return 'Show users'

    def process(self):
        options: list[tuple[Optional[NavigationNode], str]] = [(None, '[...]')]

        c = wmi.WMI()
        options += [
            (u, get_name(u)) for u in c.Win32_UserAccount(LocalAccount=True)
        ]

        # wait_to_select_back(self._move_back)
        self._last_selected = choice(
            message='',
            options=options,
            default=self._last_selected,
        )

        if self._last_selected is None:
            self.move_back()
            return

        self._move_next(UserInfo(self._last_selected))