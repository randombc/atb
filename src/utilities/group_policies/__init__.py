from core.navigation import FolderNode
from .save import SavePolicies
from .load import LoadPolicies


class GroupPolicies(FolderNode):
    CHILDREN = [
        SavePolicies(),
        LoadPolicies(),
    ]

    def get_name(self):
        return 'group policies'