from unittest import TestCase

from v2.accounts.constants import USER_STATUS_COMPANY_ADDED
from v2.accounts.models import AbstractPerson


class AbstractPersonTestCase(TestCase):
    def test_get_or_create_user_with_all_fields(self):
        person = AbstractPerson(
            first_name="John",
            last_name="Doe",
            id_no="123456789",
            gender="Male",
            dob="1990-01-01",
            birth_city="New York",
            marital_status="Single",
            email="john.doe@example.com",
            phone="1234567890"
        )
        user = person.get_or_create_user()
        assert user.first_name == "John"
        assert user.last_name == "Doe"
        assert user.dob == "1990-01-01"
        assert user.phone == "1234567890"
        assert user.status == USER_STATUS_COMPANY_ADDED
