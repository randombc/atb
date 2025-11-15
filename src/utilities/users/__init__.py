from core.navigation import FolderNode
from utilities.users.create_user_list import CreateUserList
from utilities.users.show_users import ShowUsers
from utilities.users.profile import Profile


class Users(FolderNode):

    CHILDREN = [
        Profile(),
        ShowUsers(),
        CreateUserList(),
    ]

    def get_name(self):
        return 'users'