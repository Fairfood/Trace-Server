import os

from django.utils import timezone

from .. import constants


def get_file_path(instance, filename):
    """
    Function to get filepath for a file to be uploaded
    Args:
        instance: instance of the file object
        filename: uploaded filename

    Returns:
        path: Path of file
    """
    _type = instance.__class__.__name__.lower()
    filename = os.path.splitext(filename)
    path = "%s/%s/%s:%s" % (
        _type,
        instance.idencode,
        constants.CUSTOM_TEMP_NAME + "_",
        str(timezone.now().strftime("%d-%m-%Y_%H:%M:%S")) + str(filename[1]),
    )
    return path
