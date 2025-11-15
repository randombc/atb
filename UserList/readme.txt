# This directory should contain one or more files with the extension ".list".
# Each .list file defines a set of local users that will be created by the script.
# Lines starting with "#" are comments and will be ignored.
#
# Inside every .list file, each user must be defined on a single line in the format:
# username;password;is_admin(yes/no);rdp(yes/no);chg_pwd(yes/no);never_expire_pwd(yes/no)
#
# Parameters:
#   username         – login name of the new local user account
#   password         – initial password assigned to the account
#   is_admin         – "yes" to add the user to the local Administrators group
#   rdp              – "yes" to add the user to the Remote Desktop Users group
#   chg_pwd          – "yes" to force the user to change the password at the next logon
#   never_expire_pwd – "yes" if the password never expires,
#                      "no"  if the password expires according to local policy
#
# Example entries in a .list file:
# user1;Qwerty123!;yes;yes;yes;yes
# user2;SecretPass!;no;no;no;no
