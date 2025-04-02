import requests
import json
import pyotp
from django.conf import settings

from v2.supply_chains.constants import POLYGON
from v2.supply_chains.models.profile import Company, Farmer
from v2.products.models import Batch
from v2.supply_chains.models.supply_chain import SupplyChain
from v2.projects import synch

class ConnectAPI:
    def __init__(self) -> None:
        pass
        # login = synch.Login('admin@example.com', 'admin@connect', '1234567890')


    CONNECT_URL = settings.ROOT_URL + '/connect/v1/'
    # CONNECT_URL = "http://127.0.0.1:8003/connect/v1/"

    @staticmethod
    def check_response(response: requests.Response):
        if response.status_code not in [200, 201]:
            raise Exception("Error in pushing data to connect", response.json())
        
    @staticmethod
    def headers():
        return {
            "Content-Type": "application/json",
            "OTP": pyotp.TOTP(settings.LOGIN_TOTP_SECRET).now(),
        }


    def create_company(self, node: Company):
        """
        Create a new company in connect.

        Args:
            node (Company): The company node to initiate Connect for.
        """
        url = self.CONNECT_URL + "supply-chains/companies/"
        headers ={
            "OTP": pyotp.TOTP(settings.LOGIN_TOTP_SECRET).now(),
        }

        data = {
            "name": node.name,
            "street": node.street,
            "city": node.city,
            "state": node.province,
            "country": node.country,
            "zip_code": node.zipcode,
            "sso_id": node.sso_id,
        }
        if node.image_url:
            with open(node.image_url, 'rb') as image_file:
                files = {
                    'image': image_file
                }
                response = requests.post(
                    url, data=data,files=files,  headers=headers)
        else:
            response = requests.post(url, data=data,  headers=headers)
        self.check_response(response)
        return response.json()["data"]["id"]
    

    def initiate_connect(self, company: Company):
        """
        Initializes the Connect feature for a given company node.

        Args:
            node (Company): The company node to initiate Connect for.
        """
        # Create a new company in the Connect system
        if not company.external_id:
            node = synch.sync_company(company)

            # Set the connect_id of the company node to the newly created 
            # company_id
            company.external_id = node.external_id
            company.save()

        # Create a new user Connect system
        for member in company.members.all():
            external_id = synch.get_user(member.email)
            if not external_id:
                external_id = synch.add_user(member)
            member.external_id = external_id
            member.save()

            # Add all members of the company to the Connect system
            synch.sync_node_users(company, member)

        # Add all supply chains associated with the company node
        synch.create_products(company)

        # Print a message indicating that connect has been initialized for the 
        # company node
        print("Initialized Connect for", company.name, "with id", company.external_id)

