# src/utilities/machine_setup/rdp.py

from core.navigation import FolderNode, NavigationNode
from scripts.enable_rdp_pywin32 import ensure_rdp_working, print_rdp_status


class RdpStatus(NavigationNode):
    def get_name(self) -> str:
        return "Status"

    def process(self):
        print_rdp_status()
        self.wait_back()


class RdpEnsure(NavigationNode):
    def get_name(self) -> str:
        return "Ensure"

    def process(self):
        ensure_rdp_working()
        self.wait_back()


class Rdp(FolderNode):
    CHILDREN = [
        RdpStatus(),
        RdpEnsure(),
    ]

    def get_name(self) -> str:
        return "RDP"
