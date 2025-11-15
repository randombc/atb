from core.navigation import FolderNode
from utilities.usb_warden.manage_restrictions import ManageRestrictions
from utilities.usb_warden.plugged import ShowPluggedUSB


class USBWarden(FolderNode):
    CHILDREN = [
        ShowPluggedUSB(),
        ManageRestrictions()
    ]

    def get_name(self):
        return 'USB Warden'
