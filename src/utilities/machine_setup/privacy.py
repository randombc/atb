from typing import Optional

from prompt_toolkit import choice

from core.navigation import NavigationNode
from core.utils import cls
from scripts.privacy_manager import OperationMode, manage_privacy_rules


class Privacy(NavigationNode):
    def get_name(self) -> str:
        return "Privacy"

    def process(self):
        options: list[tuple[Optional[OperationMode], str]] = [
            (None, '[...]'),
            (OperationMode.PRINT, 'View'),
            (OperationMode.DEFAULT, 'Set default'),
            (OperationMode.APPLY, 'Set all disabled'),
        ]

        mode = choice(
            message='',
            options=options,
        )

        if mode is None:
            self.move_back()

        cls()

        manage_privacy_rules(mode)

        self.wait_back()
