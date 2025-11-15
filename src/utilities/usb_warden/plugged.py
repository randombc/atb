from prompt_toolkit import choice, HTML

from core.navigation import NavigationNode
from scripts.usb.plugged import list_usb_storage_devices, UsbStorageDevice


def get_drive_letters(device: UsbStorageDevice) -> str:
    if not device.volumes:
        return 'unmounted'

    return ' '.join([f'{v.drive_letter}[{v.label}] ' for v in device.volumes])

def get_device_entry(device:UsbStorageDevice):
    entry = f'({get_drive_letters(device)}) {device.drive_model or device.name}'

    if not device.is_installed:
        entry = f'<ansibrightyellow>{entry}</ansibrightyellow> '

    return entry

class ShowPluggedUSB(NavigationNode):
    def __init__(self):
        super().__init__()
        self._drown_drives_count = None

    def get_name(self) -> str:
        return "Show plugged"

    def process(self):
        device_list = list_usb_storage_devices(check_fs_health=True)
        choices = [
                      (device, HTML(get_device_entry(device))) for device in device_list
                  ] + [(None, '[...]')]
        mode = choice(
            message='',
            options=choices,
        )

        if mode is None:
            self.move_back()
            return