from prompt_toolkit import choice

from core.navigation import NavigationNode
from scripts.usb.usb_whitelist_toggle import get_whitelist_status, enable_whitelist_mode, disable_whitelist_mode


class ManageRestrictions(NavigationNode):
    def __init__(self):
        super().__init__()
        self._drown_drives_count = None

    def get_name(self) -> str:
        return "Manage restrictions"

    def process(self):
        status = get_whitelist_status()

        if status:
            print("USB whitelist mode is enabled.")
        else:
            print("USB whitelist mode is disabled.")

        choices = [
            (enable_whitelist_mode, 'Enable') if not status else (disable_whitelist_mode, 'Disable'),
            (None, '[...]'),
        ]
        mode = choice(
            message='',
            options=choices,
        )

        if mode is None:
            self.move_back()
            return

        mode()
