from core.navigation import FolderNode
from utilities.group_policies import GroupPolicies
from utilities.machine_info import MachineInfo
from utilities.machine_setup import MachineSetUp
from utilities.programs.programs import Programs
from utilities.services import Services
from utilities.usb_warden import USBWarden
from utilities.users import Users


class RootNode(FolderNode):
    CHILDREN = [
        MachineInfo(),
        Users(),
        GroupPolicies(),
        MachineSetUp(),
        Services(),
        Programs(),
        USBWarden(),
    ]

    def get_name(self):
        return 'Root'
