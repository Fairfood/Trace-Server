"""Choices used in the app transactions."""
import enum


@enum.unique
class FieldType(enum.IntEnum):
    """FieldType choices."""

    STRING = 1
    NUMBER = 2
    DATE = 3
    EMAIL = 4
    CHOICE = 5
