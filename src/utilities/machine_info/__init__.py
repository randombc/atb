from core.navigation import FolderNode
from utilities.machine_info.licenses import Licenses
from utilities.machine_info.windows_info import WindowsInfo


class MachineInfo(FolderNode):
    CHILDREN = [
        WindowsInfo(),
        Licenses(),
    ]

    def get_name(self) -> str:
        return "Machine info"
