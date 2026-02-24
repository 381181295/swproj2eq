"""Minimal interactive TUI wrapper.

No new logic here; delegates to existing command handlers.
"""

from types import SimpleNamespace

from swproj2eq.commands import doctor_cmd, quickstart_cmd, rollback_cmd, status_cmd
from swproj2eq.constants import ExitCode
from swproj2eq.tui.views.menu import print_menu


def run_tui():
    while True:
        print_menu()
        choice = input("Select: ").strip()

        if choice == "1":
            profile = input("Path to .swproj: ").strip()
            set_default = input("Set default sink? [y/N]: ").strip().lower() in ("y", "yes")
            args = SimpleNamespace(profile=profile, set_default=set_default, yes=False, force=False)
            code = quickstart_cmd.run(args)
            print(f"quickstart exit: {int(code)}")
        elif choice == "2":
            code = status_cmd.run(SimpleNamespace(json=False))
            print(f"status exit: {int(code)}")
        elif choice == "3":
            code = doctor_cmd.run(SimpleNamespace(json=False))
            print(f"doctor exit: {int(code)}")
        elif choice == "4":
            code = rollback_cmd.run(SimpleNamespace(yes=True, force=False))
            print(f"rollback exit: {int(code)}")
        elif choice == "5":
            return ExitCode.OK
        else:
            print("invalid selection")
