# !/usr/bin/python3
# Module to manage pre-commit git hook.
# This script is executed each time when the git commit command is runs
# by the user. This hook script will check the commit log message.
# Called by "git commit" with one argument, the name of the file
# that has the commit message.  The hook should exit with non-zero
# status after issuing an appropriate message if it wants to stop the
# commit.  The hook is allowed to edit the commit message file.
import argparse
import string
import sys


MIN_LEN_DESC = 30

# ANSI colors.

HEADER = "\033[95m"
OKBLUE = "\033[94m"
OKCYAN = "\033[96m"
WARNING = "\033[93m"
FAIL = "\033[91m"
ENDC = "\033[0m"
BOLD = "\033[1m"
UNDERLINE = "\033[4m"
ERROR_HEAD = "\033[4m\u001b[31;1m"
OFF = "\033[0m"
ITALIC = "\033[3m"
WHITE = OFF + "\033[97m"
BLACK = OFF + "\033[30m"
RED = OFF + "\033[31m"
GREEN = OFF + "\033[32m"
YELLOW = OFF + "\033[33m"
BLUE = OFF + "\033[34m"
MAGENTA = OFF + "\033[35m"
CAYAN = OFF + "\033[36m"
DEFAULT = OFF + "\033[39m"

FILLER = OFF + "\033[;7m"
WHITEFONE = FILLER + "\033[37m"
BLACKFONE = FILLER + "\033[30m"
REDFONE = FILLER + "\033[31m"
BLUEFONE = FILLER + "\033[34m"
GREENFONE = FILLER + "\033[32m"
VIOLETFONE = FILLER + "\033[35m"
YELLOWFONE = FILLER + "\033[33m"

MSG_INVALID_FORMAT = (
    f"{ERROR_HEAD}     INVALID COMMIT MESSAGE FORMAT !!!{ENDC}\n\n"
)

MSG_FORMAT = (
    f"{FAIL}     Please follow the following commit message format,\n{OKBLUE} "
    "   -------------------------------------------------------------------\n"
    "    <type>: <description min length 40> : [optional Reference Jira"
    " issue]\n    \n    [optional body]\n    \n    [optional footer(s)]\n   "
    " -------------------------------------------------------------------\n  "
    f"  {ENDC}"
)

MSA_TYPES = (
    f"{ERROR_HEAD}Allowed types{ENDC}{FAIL}\n    feat- Feature implementation"
    " \n    fix- Fixing an issue \n    hotfix- Fix for an issue running in"
    " production \n    refactor- Changing the existing code \n    patch-"
    " Quick update to already pushed fix \n    ci- CI/CD related \n    doc-"
    " Updates in the documentations or read me \n    wip- Work in progress, "
    f" when you wanna commit the incomplete work \n    {ERROR_HEAD} \n    \n  "
    f"  Example: {ENDC}{FAIL}\n    feat: sample feature commit message with"
    f" min description length 40 \n    {ENDC}"
)


MSG_INVALID_TYPE = (
    f"{ERROR_HEAD}     INVALID COMMIT MESSAGE TYPE !!!{ENDC}\n\n"
)

MSG_INVALID_DESC = (
    f"{ERROR_HEAD}     DESCRIPTION SHOULD BE {MIN_LEN_DESC} CHARACTERS"
    f" !!!{ENDC}\n\n"
)


MIN_WORDS = 2
COMMIT_EDITMSG = ".git/COMMIT_EDITMSG"

MESSAGE_TYPES = [
    "feat",
    "fix",
    "hotfix",
    "refactor",
    "patch",
    "ci",
    "doc",
    "wip",
]

HELP_URL = "https://tinyurl.com/2p9dhnm4"
HINT = f"Check how to format your commit message in {HELP_URL}"


def check_subject_format(message: str) -> str:
    """Function to validate commit message.

    The function will split the commit message using ':'' and the
    validate the message type and message.
    """
    err_msg = ""
    msg_parts = message.split(":")
    if len(msg_parts) < 2:
        err_msg = MSG_INVALID_FORMAT + MSG_FORMAT + MSA_TYPES
        return err_msg
    if not (msg_parts[0] in MESSAGE_TYPES):
        err_msg = MSG_INVALID_TYPE + MSG_FORMAT + MSA_TYPES
        return err_msg

    if len(msg_parts[1]) < MIN_LEN_DESC:
        err_msg = MSG_INVALID_DESC + MSG_FORMAT + MSA_TYPES
        return err_msg
    return err_msg


def read_msg(path: str) -> str:
    """Extract commit message content.

    Try to read the message on the given path.
    If fail, abort commit(exit nonzero), display appropriate error and hint
    Args:
        path (str): The path of the file with commit message
    Returns:
        str: The commit message.
    """
    try:
        with open(path, "r", encoding="utf-8") as file:
            msg = file.read()
            # cut the commented text
            msg = msg.split("#", 1)[0]
    except FileNotFoundError:
        print(
            f"\n{ERROR_HEAD}            error:\tthe path  {OKCYAN}{path}      "
            f"       not found!\n{WARNING}            hint:\tthe commit"
            " message is usually stored in             "
            f" {OKCYAN} {COMMIT_EDITMSG}{ENDC}\n"
        )
        sys.exit(1)
    return msg


def run_hook(msg: str):
    """Run the main logic of the hook.

    If one of the validations failed, abort commit(exit nonzero),
    display appropriate errors and hints.
    Otherwise exit zero and allow the `git commit` command.
    Args:
        msg (str): The commit message to validate.
    """
    global default_prefixes
    subj_line_errors = validate_subj_line(msg)
    body_errors = validate_body(msg)
    if subj_line_errors or body_errors:
        print(subj_line_errors + body_errors + HINT)
        sys.exit(1)
    sys.exit(0)


def validate_subj_line(msg: str) -> str:
    """Validate the subject line of a commit message.

    Slice subject line of commit message and validate it according to
    chaos-hub team commit rules
    Args:
        msg (str): The commit message
    Returns:
        str: The detected errors(empty in a case of no errors)
    """
    subject = msg.splitlines()[0]
    format_err = check_subject_format(subject)
    if format_err:
        return format_err
    meaningful_errors = check_meaningful(subject)
    # prefix_errors = check_prefix(subject)
    # imperatives_errors = check_for_imperative(subject)
    ending_errors = check_ending(subject)
    errors = meaningful_errors + ending_errors
    return errors


def validate_body(msg: str) -> str:
    """Validate the body of a commit message.

    Slice body of commit message and validate it according to chaos-hub
    team commit rules.
    Args:
        msg (str): The commit message
    Returns:
        str: The detected errors(empty in a case of no errors)
    """
    errors = ""
    if len(msg.splitlines()) > 1:
        body = msg.splitlines()[1:]
        if body[0].strip() != "":
            errors += (
                f"\n{RED}error:\tseparate the subject line from            "
                f" the message body with a blank line{OFF}\n"
            )
        for i in range(len(body)):
            line_msg = body[i].strip()
            if line_msg:
                line_msg = remove_bullet(line_msg)
                if line_msg:
                    meaningful_errors = check_meaningful(line_msg)
                    prefix_errors = check_prefix(line_msg)
                    ending_errors = check_ending(line_msg)
                    errors += meaningful_errors + prefix_errors + ending_errors
                else:
                    errors += (
                        f"\n{RED}error:\tthe message body can't               "
                        f"          be empty{OFF}\n"
                    )
    return errors


def remove_bullet(body_line: str) -> str:
    """Remove line bullet if exist.

    Ex: get `* Fix bugs` return `Fix bugs`.
    Args:
        body_line (str): The single line of message body.
    Returns:
        str: The message without non-alpha characters at the beginning of
            the line.
    """
    content = ""
    if body_line:
        for i in range(len(body_line)):
            if body_line[i].isalpha():
                content = body_line[i:]
                break
    return content


def check_meaningful(msg: str) -> str:
    """Check if a commit message less than 2 word.

    If message contains less than 2 words, generate an appropriate error
    message.
    Args:
        msg (str): The part of commit mesage(subject line or body).
    Returns:
        str: The detected errors(empty in a case of no errors).
    """
    errors = ""
    words = msg.strip(string.punctuation).split()
    if len(words) < MIN_WORDS:
        errors += (
            f"\n{RED}            error:\tone-word message "
            f" {GREEN}{ITALIC}{words[0]}{RED}  is             not informative,"
            f" please add more details{OFF}\n"
        )
    return errors


def check_prefix(msg: str) -> str:
    """Check if the prefix of the message is correct casefold.

    If validation failed, generate an appropriate error message.
    Args:
        msg (str): The part of commit mesage(subject line or body).
    Returns:
        str: The detected errors(empty in a case of no errors).
    """
    errors = ""
    first_word = msg.split()[0].strip(string.punctuation)
    if first_word[0].islower():
        errors += (
            f"\n{RED}error:\tcapitalise the word             "
            f" {GREEN}{ITALIC}{first_word}{OFF}\n"
        )
    if not first_word[1:].islower():
        errors += (
            f"\n{RED}            error:\tthe word "
            f" {GREEN}{ITALIC}{first_word}{RED}  must be in             letter"
            f" case and not uppercase or mixed{OFF}\n"
        )
    return errors


def check_ending(msg: str) -> str:
    """Check whether the message ends with a dot or not.

    If the message ends with a dot, generate an appropriate error message.
    Args:
        msg (str): The part of commit mesage(subject line or body).
    Returns:
        str: The detected errors(empty in a case of no errors).
    """
    errors = ""
    if msg != msg.strip(string.punctuation):
        errors += (
            f"\n{RED}            error:\tdo not end the line "
            f" {GREEN}{ITALIC}{msg}{RED}              with any punctuation"
            f" character{OFF}\n"
        )
    return errors


def main():
    """Perform validations of the commit message.

    Extract arguments from command line and run the hook logic
    """
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "path",
        nargs="?",
        type=str,
        default=COMMIT_EDITMSG,
        help="the path of commit message file",
    )
    args = parser.parse_args()
    msg = read_msg(args.path)
    if not msg.strip():
        print(
            f"ֿ\n{ERROR_HEAD}            Error:\tcommit message can't be"
            f" empty{ENDC}\n"
        )
        sys.exit(1)
    run_hook(msg)


if __name__ == "__main__":
    main()
