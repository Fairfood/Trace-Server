"""File to define all the error messages."""


class Colour:
    """Class to manage ANSI colors."""

    HEADER = "\033[95m"
    OKBLUE = "\033[94m"
    OKCYAN = "\033[96m"
    OKGREEN = "\033[92m"
    WARNING = "\033[93m"
    FAIL = "\033[91m"
    ENDC = "\033[0m"
    BOLD = "\033[1m"
    UNDERLINE = "\033[4m"
    ERROR_HEAD = "\033[4m\u001b[31;1m"


MSG_INVALID_FORMAT = (
    Colour.ERROR_HEAD + f"INVALID COMMIT MESSAGE FORMAT !!!{Colour.ENDC}"
)

MSG_FORMAT = (
    Colour.FAIL
    + """
Please follow the following commit message format,
"""
    + Colour.OKBLUE
    + """
-------------------------------------------------------------------
<type>: <description min length 40> : [optional Reference Jira issue]

[optional body]

[optional footer(s)]
-------------------------------------------------------------------
"""
    + Colour.ENDC
)

MSA_TYPES = (
    Colour.ERROR_HEAD
    + """
Allowed types
"""
    + Colour.ENDC
    + Colour.FAIL
    + """
feat- Feature implementation
fix- Fixing an issue
hotfix- Fix for an issue running in production
refactor- Changing the existing code
patch- Quick update to already pushed fix
ci- CI/CD related
doc- Updates in the documentations or read me
wip- Work in progress commit  when you wanted to commit the incomplete work

"""
    + Colour.ERROR_HEAD
    + """
Example:
"""
    + Colour.ENDC
    + Colour.FAIL
    + """
feat: sample feature commit message with min description length 40

"""
    + Colour.ENDC
)

MSG_INVALID_TYPE = (
    Colour.ERROR_HEAD + f"INVALID COMMIT MESSAGE TYPE !!!{Colour.ENDC}"
)
