import ctypes
import os
import sys

from core.loop import main_loop


def is_admin():
    """Check if the current process is running as administrator"""
    try:
        return ctypes.windll.shell32.IsUserAnAdmin()
    except:
        return False


def run_as_admin():
    """Restart the script with admin rights using UAC elevation"""
    if not is_admin():
        # sys.executable -> path to Python or compiled .exe
        # " ".join(sys.argv) -> pass current arguments to the new process
        # "runas" verb -> tells Windows to run with elevation (UAC prompt)
        ctypes.windll.shell32.ShellExecuteW(
            None,  # handle to parent window (None = no parent)
            "runas",  # operation to perform
            sys.executable,  # executable to run
            " ".join(sys.argv),  # command line parameters
            None,  # working directory (None = current)
            1  # window style (1 = normal window)
        )

        sys.exit()


if __name__ == "__main__":
    run_as_admin()

    sys.stdout.reconfigure(encoding="utf-8")
    sys.stderr.reconfigure(encoding="utf-8")

    main_loop()

    os.system("pause")
