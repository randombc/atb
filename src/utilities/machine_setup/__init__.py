from core.navigation import FolderNode
from utilities.machine_setup.context_menu import ContextMenu
from utilities.machine_setup.privacy import Privacy
from utilities.machine_setup.rdp import Rdp


class MachineSetUp(FolderNode):
    CHILDREN = [
        Rdp(),
        Privacy(),
        ContextMenu()
    ]

    def get_name(self):
        return 'machine setup'
