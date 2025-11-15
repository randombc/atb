# src/utilities/machine_setup/context_menu.py
from prompt_toolkit import choice

from core.navigation import NavigationNode
from scripts.context_menu import is_new_context_menu_enabled, set_new_context_menu


class ContextMenu(NavigationNode):
    def get_name(self) -> str:
        return "New context menu"

    def process(self):
        new_menu = is_new_context_menu_enabled()
        print()
        if new_menu:
            print("New context menu is enabled.")
        else:
            print("New context menu is disabled.")

        options = [
            (None, '[...]'),
            (True, 'Switch'),
        ]

        if choice(
                message='',
                options=options,
        ) is None:
            self.move_back()
            return

        set_new_context_menu(not new_menu)
