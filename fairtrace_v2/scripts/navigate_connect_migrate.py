from v2.supply_chains.models.profile import Company
from v2.supply_chains.tasks import initial_sync_to_connect
from v2.projects.navigate import NavigateAPI


def sync_all_company():
    """Sync all companies with link naviagate true"""

    companies = Company.objects.filter(features__link_navigate=True)
    for company in companies:
        print('starting company sync', company)
        api = NavigateAPI()
        api.initiate_mapping(company)
    print("completed!!")


def sync_all_company_to_connect():
    """Sync all companies with link connect true"""

    companies = Company.objects.filter(features__link_connect=True)
    for company in companies:
        initial_sync_to_connect.delay(company.idencode)
    print("completed!!")