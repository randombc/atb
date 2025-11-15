from core.navigation import FolderNode
from utilities.programs.print_list import PrintList
from utilities.programs.find_list import FindList


class Programs(FolderNode):
    CHILDREN = [
        PrintList(),
        FindList(),
    ]

    def get_name(self):
        return 'Programs'
