from tqdm import tqdm
from v2.supply_chains.models import Company
from v2.supply_chains.models import Farmer


def format_farmers():
    """Formats the fields of all farmers.

    This function iterates over all farmers in the database and formats
    specific fields such as first name, last name, street, and city by applying
    title casing. It saves the updated farmer objects.

    Note:
    - The function uses the 'tqdm' library to display a progress bar during
        iteration.
    """
    for farmer in tqdm(Farmer.objects.all()):
        try:
            farmer.first_name = farmer.first_name.title()
            farmer.last_name = farmer.last_name.title()
            farmer.street = farmer.street.title()
            farmer.city = farmer.city.title()
            farmer.save()
        except Exception as e:
            print(e)
            continue


def format_companies():
    """Formats the fields of all companies.

    This function iterates over all companies in the database and formats
    specific fields such as name, street, and city by applying title casing.
    It saves the updated company objects.

    Note:
    - The function uses the 'tqdm' library to display a progress bar during
        iteration.
    """
    for company in tqdm(Company.objects.all()):
        try:
            company.name = company.name.title()
            company.street = company.street.title()
            company.city = company.city.title()
            company.save()
        except Exception as e:
            print(e)
            continue


def run():
    """Runs the formatting process for farmers and companies.

    This function executes the formatting process for farmers and
    companies. It calls the 'format_farmers()' and 'format_companies()'
    functions to perform the necessary formatting tasks.
    """
    format_farmers()
    format_companies()
