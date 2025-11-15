import platform
import subprocess

from core.navigation import NavigationNode
from prompt_toolkit import choice


class WindowsInfo(NavigationNode):
    def get_name(self) -> str:
        return "Windows info"

    def process(self):
        print()
        print("=" * 70)
        print("WINDOWS INFORMATION")
        print("=" * 70)

        # Basic information about Windows
        print(f"OS:               {platform.system()}")
        print(f"Release:          {platform.release()}")
        print(f"Version:          {platform.version()}")
        print(f"Edition:          {platform.win32_edition()}")
        print(f"Platform:         {platform.platform()}")

        # Additional information via systeminfo (if available)
        try:
            result = subprocess.run(
                ['systeminfo'],
                capture_output=True,
                text=True,
                timeout=10,
                encoding='cp866'  # Windows console encoding
            )

            if result.returncode == 0:
                lines = result.stdout.split('\n')

                # Filter required lines
                keywords = [
                    'OS Name',
                    'OS Version',
                    'OS Manufacturer',
                    'OS Configuration',
                    'OS Build Type',
                    'Registered Owner',
                    'Registered Organization',
                    'Product ID',
                    'Original Install Date',
                    'System Boot Time',
                    'System Manufacturer',
                    'System Model',
                ]

                print()
                print("-" * 70)
                for line in lines:
                    for keyword in keywords:
                        if True:
                            print(line.strip())
                            break
        except Exception as e:
            print(f"\nCould not retrieve detailed system info: {e}")

        print("=" * 70)
        print()

        options = [
            (None, '[Back]'),
        ]

        choice(
            message='',
            options=options,
        )

        self.move_back()
