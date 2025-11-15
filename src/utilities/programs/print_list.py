from prompt_toolkit.shortcuts import radiolist_dialog, checkboxlist_dialog

from core.navigation import NavigationNode
from scripts.installed_apps import list_installed_programs


class PrintList(NavigationNode):

    def get_name(self):
        return 'List'

    def process(self):
        default_values = [
            'filter_system_components',
        ]

        result = checkboxlist_dialog(
            title="Settings",
            text="Select options:",
            values=[
                ("filter_system_components", "Filter System Components"),
            ],
            default_values=default_values,
        ).run()

        if result is None:
            self.move_back()

        include_uwp = "include_uwp" in result
        uwp_all_users = "uwp_all_users" in result
        filter_system_components = "filter_system_components" in result

        items = list_installed_programs(include_uwp, uwp_all_users, filter_system_components)
        items = sorted(items, key=lambda item: item['DisplayName'])

        print(f"Total apps: {len(items)}")
        for it in items:
            print(f"- {it['DisplayName']} ({it.get('DisplayVersion','')}) [{it['RegistryRoot']}/{it['RegistryView']}]")

        self.wait_back()
