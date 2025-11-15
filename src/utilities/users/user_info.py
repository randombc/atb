from core.navigation import NavigationNode


class UserInfo(NavigationNode):
    def __init__(self, user_account):
        super().__init__()
        self._user_account = user_account

    def get_name(self) -> str:
        return self._user_account.Name

    # Validation helpers moved from process() into class methods
    def _is_builtin_or_protected(self, acc) -> bool:
        # Block deletion of built-in or protected accounts
        name = str(getattr(acc, "Name", "")).lower()
        protected_names = {"administrator", "guest", "defaultaccount", "wdagutilityaccount"}
        if name in protected_names:
            return True
        sid = str(getattr(acc, "SID", "")).strip()
        # Built-in Administrator (…-500) and Guest (…-501)
        if sid.endswith("-500") or sid.endswith("-501"):
            return True
        # Extra guard: non-local accounts shouldn't be deleted here
        if not getattr(acc, "LocalAccount", True):
            return True
        return False

    def _is_current_user(self, acc) -> bool:
        # Prevent deleting the currently logged-in user
        try:
            import getpass
            current = getpass.getuser()
        except Exception:
            return False
        return str(getattr(acc, "Name", "")) == current

    def process(self):
        print()

        from tabulate import tabulate

        data = [
            ["Name", self._user_account.Name],
            ["FullName", self._user_account.FullName],
            ["AccountType", self._user_account.AccountType],
            ["LocalAccount", self._user_account.LocalAccount],
            ["Domain", self._user_account.Domain],
            ["Disabled", self._user_account.Disabled],
            ["Lockout", self._user_account.Lockout],
            ["PasswordChangeable", self._user_account.PasswordChangeable],
            ["PasswordExpires", self._user_account.PasswordExpires],
            ["PasswordRequired", self._user_account.PasswordRequired],
            ["SID", self._user_account.SID],
            ["SIDType", self._user_account.SIDType],
            ["Status", self._user_account.Status],
        ]

        print(tabulate(data, tablefmt="plain"))

        # Prepare actions: compute delete availability BEFORE building options
        from prompt_toolkit import choice, prompt
        from scripts.delete_user_profiles import remove_user_and_profile

        # Determine if delete should be offered
        can_delete = not self._is_builtin_or_protected(self._user_account) and not self._is_current_user(self._user_account)

        # Build action options dynamically
        action_options: list[tuple[object, str]] = []
        if can_delete:
            action_options.append(("delete", "Delete this user"))
        action_options.append((None, "[...]"))

        action = choice(message='', options=action_options, default=None)

        if action == "delete":
            username = getattr(self._user_account, "Name", "")
            confirm = prompt(
                f"YOU ARE ABOUT TO PERMANENTLY DELETE the local user '{username}' and their profile. "
                f"Type the username again to confirm or 'n' to cancel: "
            ).strip()

            if confirm.lower() == "n" or confirm != username:
                print("Cancelled.")
                self.wait_back()
                return

            try:
                # Use centralized deletion (user account + profile folder + registry cleanup)
                remove_user_and_profile(username)
                print("Deletion process finished. See logs for details.")
            except SystemExit:
                # The underlying script may call sys.exit(1) when not run as Administrator
                print("Administrator privileges are required to delete the user and their profile.")
            except Exception as ex:
                print(f"Error during deletion: {ex}")

            self.wait_back()
            return

        # Default/back
        self.move_back()