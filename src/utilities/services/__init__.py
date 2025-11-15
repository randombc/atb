from core.navigation import FolderNode
from .load import LoadServices
from .save import SaveServices


class Services(FolderNode):
    CHILDREN = [
        SaveServices(),
        LoadServices(),
    ]

    def get_name(self) -> str:
        return 'Services'
