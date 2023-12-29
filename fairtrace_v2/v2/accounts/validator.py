"""Module for accounts field custom Validator."""
from common.library import _validate_email
from v2.accounts.models import FairfoodUser


def validate_username(username):
    """Function to validate username.

    Input Params:
        username(str): username to check
        user_type(int): user type.
    Return:
        data(dict): data dictionary with,
            valid(bool): true if valid
            available(bool): true if available.
            message(str): message
    """
    response = {"available": False, "valid": False}

    valid, message = _validate_email(username)
    if not valid:
        response["message"] = message
        return response
    response["valid"] = True
    if FairfoodUser.objects.filter(username=username).exists():
        response["message"] = "Username is already taken."
        return response
    response["message"] = "Username is available."
    response["available"] = True
    return response
