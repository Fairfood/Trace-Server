"""Custom exception handler to maintain same format in success and error."""
from rest_framework.views import exception_handler
from sentry_sdk import capture_exception


def custom_exception_handler(exc, context):
    """To prepare custom exception."""
    response = exception_handler(exc, context)
    if getattr(exc, "send_to_sentry", True):
        capture_exception(exc)
    if response is not None:
        errors = []
        message = response.data
        if not message:
            try:
                for field, value in response.data.items():
                    errors.append("{} : {}".format(field, " ".join(value)))
                    message = errors
            except Exception:
                message = response.data

        response.data = {
            "success": False,
            "detail": message,
            "code": response.status_code,
            "data": {},
        }

    return response
