from pathlib import Path
from typing import Optional

from prompt_toolkit import choice
from colorama import Fore, Style, init

from core.navigation import NavigationNode
from core.utils import get_folder_path
from scripts.installed_apps import list_installed_programs, search_installed_programs


class FindList(NavigationNode):

    def get_name(self):
        return 'Find Restricted'

    def process(self):
        init(autoreset=True)

        # Select file with list of restricted programs
        options: list[tuple[Optional[Path], str]] = [(None, '[...]')]
        programlist_dir = get_folder_path("ProgramList")
        program_lists = [f for f in programlist_dir.glob("*.txt") if f.is_file()]

        options += [
            (f, f.stem) for f in program_lists
        ]

        selected_file = choice(
            message='Select restricted programs file:',
            options=options,
        )

        if selected_file is None:
            self.move_back()
            return

        # Read file with patterns
        try:
            with selected_file.open('r', encoding='utf-8') as f:
                restricted_patterns = [line.strip() for line in f if line.strip() and not line.strip().startswith('#')]
        except FileNotFoundError:
            print(f"{Fore.RED}Error: File '{selected_file.name}' not found!{Style.RESET_ALL}")
            self.wait_back()
            return
        except Exception as e:
            print(f"{Fore.RED}Error reading file '{selected_file.name}': {e}{Style.RESET_ALL}")
            self.wait_back()
            return

        if not restricted_patterns:
            print(f"{Fore.YELLOW}Warning: No patterns found in {selected_file.name}{Style.RESET_ALL}")
            self.wait_back()
            return

        # Get list of all installed programs
        print("Loading installed programs...")
        all_apps = list_installed_programs(
            include_uwp=False,
            uwp_all_users=False,
            filter_system_components=True
        )

        # Search for restricted programs
        print(f"Searching for restricted programs (patterns: {len(restricted_patterns)})...")
        found_apps = search_installed_programs(
            patterns=restricted_patterns,
            apps=all_apps,
            mode="fuzzy",
            threshold=81,
            top_k_per_pattern=200
        )

        # Sort by name
        found_apps = sorted(found_apps, key=lambda item: (item.get('DisplayName') or item.get('Name', '')).lower())

        # Print results
        print("\n" + "=" * 80)
        if not found_apps:
            print(f"{Fore.GREEN}✓ No restricted programs found!{Style.RESET_ALL}")
        else:
            print(f"{Fore.RED}⚠ Found {len(found_apps)} restricted program(s):{Style.RESET_ALL}\n")
            for app in found_apps:
                name = app.get('DisplayName') or app.get('Name', 'N/A')
                version = app.get('DisplayVersion') or app.get('Version', '')
                app_type = app.get('Type', 'unknown')
                matched_patterns = ', '.join(app.get('MatchedPatterns', []))
                score = app.get('Score', 0)

                # Gradient from white to red for score 81-100
                # Normalize score to range 0-1
                normalized = (score - 80) / 20  # 81-100 -> 0.05-1.0

                # Limit value from 0 to 1
                normalized = max(0, min(1, normalized))

                # Gradient: white (255,255,255) -> red (255,0,0)
                # G and B components decrease from 255 to 0
                red = 255
                green = int(255 * (1 - normalized))
                blue = int(255 * (1 - normalized))

                color = f'\033[38;2;{red};{green};{blue}m'

                # Print with appropriate color
                print(f"{color}• {name}{Style.RESET_ALL}", end='')
                if version:
                    print(f" ({version})", end='')
                print(f" [{app_type}]")
                print(f"  Matched patterns: {matched_patterns} (score: {score})")

                if app_type == 'win32':
                    reg_root = app.get('RegistryRoot', '')
                    reg_view = app.get('RegistryView', '')
                    if reg_root and reg_view:
                        print(f"  Location: {reg_root}/{reg_view}")
                elif app_type == 'uwp':
                    family = app.get('FamilyName', '')
                    if family:
                        print(f"  Family: {family}")

                print()

        print("=" * 80)
        self.wait_back()
