import base64
import json
import os
import requests
from io import BufferedReader, BytesIO
from urllib.parse import urlparse
from typing import Optional
from django.conf import settings
from django.utils import timezone
from requests_toolbelt.multipart.encoder import MultipartEncoder
from sentry_sdk import capture_message
from tqdm import tqdm
from common.library import decode
from v2.projects.models import Synchronization
from v2.projects.constants import (
    BASE_PREMIUM, OPTIONS, PREMIUM_APPLICABLE_ACTIVITY_BUY, 
    PREMIUM_APPLICABLE_ACTIVITY_SELL, PREMIUM_TYPE_PER_FARMER, 
    PREMIUM_TYPE_PER_KG, PREMIUM_TYPE_PER_TRANSACTION, 
    PREMIUM_TYPE_PER_UNIT_CURRENCY, TRANSACTION_PREMIUM, 
    SYNC_STATUS_FAILED, SYNC_STATUS_SUCCESS, SYNC_TYPE_CONNCET
)
from v2.supply_chains.constants import (NODE_MEMBER_TYPE_ADMIN,
                                        NODE_MEMBER_TYPE_MEMBER,
                                        NODE_MEMBER_TYPE_VIEWER)
from v2.supply_chains.models.cypher import TAGS
from v2.supply_chains.models.profile import Company, Node, NodeMember, Farmer

USER_MEMBER_TYPE = {
    NODE_MEMBER_TYPE_ADMIN: 'SUPER_ADMIN',
    NODE_MEMBER_TYPE_MEMBER: 'ADMIN',
    NODE_MEMBER_TYPE_VIEWER: 'REPORTER',
}
PREMIUM_CATEGORY = {
    BASE_PREMIUM: 'PAYOUT',
    TRANSACTION_PREMIUM: 'TRANSACTION',
}
PREMIUM_TYPE = {
    PREMIUM_TYPE_PER_TRANSACTION: 'PER_TRANSACTION',
    PREMIUM_TYPE_PER_KG: 'PER_KG',
    PREMIUM_TYPE_PER_UNIT_CURRENCY: 'PER_UNIT_CURRENCY',
    PREMIUM_TYPE_PER_FARMER: 'PER_FARMER',
}

PREMIUM_APPLIABLE_ACTIVITY = {
    PREMIUM_APPLICABLE_ACTIVITY_BUY: 'BUY',
    PREMIUM_APPLICABLE_ACTIVITY_SELL: 'SELL'
}


class Login:
    """
    Class representing the login functionality.

    Attributes:
        CLIENT_ID (str): The client ID for OAuth2 authentication.
        CLIENT_SECRET (str): The client secret for OAuth2 authentication.
        access_token (str): The access token obtained after successful login.
        expires_on (datetime): The expiration date and time of the access
            token.

    Methods:
        access(): Retrieve the access token, either from the stored token or
            by performing a login request if the stored token has expired.

    Raises:
        LoginFailedError: If the login fails.
    """

    access_token = ''
    expires_on = None

    def __init__(self):
        self.CONNECT_URL = settings.ROOT_URL + '/connect/v1/'
        self.CLIENT_ID = settings.CONNECT_OAUTH2_CLIENT_ID
        self.CLIENT_SECRET = settings.CONNECT_OAUTH2_CLIENT_SECRET

    def access(self):
        """
        Retrieve the access token, either from the stored token or by
        performing a login request if the stored token has expired.

        Returns:
            str: The access token.

        Raises:
            LoginFailedError: If the login fails.
        """
        if self.access_token and self.expires_on > timezone.now():
            return self.access_token

        url = self.CONNECT_URL + 'oauth/token/'
        credential = f"{self.CLIENT_ID}:{self.CLIENT_SECRET}"
        token = base64.b64encode(credential.encode("utf-8"))
        data = {
            "grant_type": "client_credentials",
        }
        headers = {
            'Authorization': "Basic " + token.decode("utf-8"),
            "X-Entity-ID" : settings.CONNECT_SYNC_COMPANY_ID
        }
        response = requests.post(
            url, data=data,
            headers=headers)

        if response.status_code == 200:
            content = response.json()
            self.access_token = content["access_token"]
            expires_in = content["expires_in"]
            self.expires_on = (timezone.now()
                              + timezone.timedelta(seconds=expires_in))
            return self.access_token
        raise Exception('Login failed')

class ConnectAPI:


    def __init__(self, sync_id: Optional[str] = None):
        self.auth = Login()
        self.CONNECT_URL = settings.ROOT_URL + '/connect/v1/'
        self.messages = []
        if sync_id:
            self.sync = Synchronization.objects.get(id=decode(sync_id))

    @staticmethod
    def check_response(response: requests.Response):
        if response.status_code not in [200, 201]:
            raise Exception("Error in pushing data to connect", response.json())

    def get_auth_headers(self, is_form_data=False, encoder=None):
        """
        Returns the headers required for API requests.

        Returns:
            dict: The headers dictionary.
        """
        header =  {
            "Authorization": "Bearer {0}".format(self.auth.access()),
            "Auth-Type": "client_credentials"
        }
        if not is_form_data:
            header["Content-Type"] = 'application/json'
        else:
            header["Content-Type"] = encoder.content_type
        return header

    def handle_failure(self, response, key):
        # log user creation issue
        # capture_message(response.text)
        print(response, response.text)

    def format_input_data(self, data):
        return json.dumps(data)

    def get_file_content_type(self, file=None):
        _, file_extension = os.path.splitext(file.name)
        return f'image/{file_extension[1:]}' if file_extension else 'application/octet-stream'

    def send_data(self, url, data, headers=None):
        if not headers:
            headers = self.get_auth_headers()
        data = self.format_input_data(data)
        return requests.post(url, data=data,  headers=headers)

    def map_company_buyer(self, company: Company=None, buyer: Company=None):
        """
        Add buyer to a company

        Args:
            company (Company): The company node to initiate Connect for.
            buyer (Company): The company node to map with.
        """
        url = self.CONNECT_URL + "supply-chains/companies/map-buyer/"

        data = {
            "buyer": buyer.external_id,
            "company": company.external_id
        }
        response = self.send_data(url, data)
        if response.status_code != 201:
            self.handle_failure(response, "map_company_buyer")
            return False
        return True

    def create_company(self, node: Company=None):
        """
        Create a new company in connect.

        Args:
            node (Company): The company node to initiate Connect for.
        """
        url = self.CONNECT_URL + "supply-chains/companies/"

        data = {
            "name": node.name,
            "street": node.street,
            "city": node.city,
            "province": node.province,
            "country": node.country,
            "zip_code": node.zipcode,
            "currency": settings.CONNECT_SYNC_DEFAULT_CURRENCY_CODE,
        }
        if node.image_url:
            # Check if the URL is an S3 URL or a local file path
            parsed_url = urlparse(node.image_url)
            if parsed_url.scheme in ['http', 'https']:  # S3 URL
                # Download the image from S3
                response = requests.get(node.image_url, stream=True)
                response.raise_for_status()  # Ensure the download was successful
                image_file_bytes = BytesIO(response.content)
                image_file_bytes.name = os.path.basename(parsed_url.path)  # Set a name for the file
                image_file = BufferedReader(image_file_bytes)
                setattr(image_file, 'len', len(response.content))
                file_type = response.headers.get('Content-Type', 'application/octet-stream')
            else:
                image_path = settings.BASE_DIR + node.image_url
                image_file = open(image_path, 'rb')
                file_type = self.get_file_content_type(image_file)
            data["image"] = (image_file.name, image_file, file_type)
            encoder = MultipartEncoder(fields=data)
            response = requests.post(
                url, data=encoder,  headers=self.get_auth_headers(is_form_data=True, encoder=encoder))
            # Close the file if it's a local file (S3 response will automatically be closed)
            if not isinstance(image_file, requests.models.Response):
                image_file.close()
        else:
            response = self.send_data(url, data)
        if response.status_code not in [201, 200]:
            self.handle_failure(response, "company_creation")
            return None
        else:
            return response.json()["data"]["id"]
    
    def update_company(self, company: Company):
        """Update company details"""
        url = self.CONNECT_URL + f"supply-chains/companies/{company.external_id}/"

        data = {
            "name": company.name,
            "street": company.street,
            "city": company.city,
            "province": company.province,
            "country": company.country,
            "zip_code": company.zipcode,
            "make_farmers_private": company.make_farmers_private
        }
        
        response = requests.patch(
            url, data=json.dumps(data), headers=self.get_auth_headers()
        )
        if not response.status_code == 200:
            self.messages.append(
                f"Company {company.idencode} Invalid- {response.reason}"
            )

    def create_company_as_buyer(self, node: Company=None, source_company:Company=None):
        """
        Create a new company in connect as a buyer.

        Args:
            node (Company): The company node to initiate Connect for.
        """
        url = self.CONNECT_URL + "supply-chains/companies/buyer/"

        data = {
            "name": node.name,
            "street": node.street,
            "city": node.city,
            "province": node.province,
            "country": node.country,
            "zip_code": node.zipcode,
            "currency": settings.CONNECT_SYNC_DEFAULT_CURRENCY_CODE,
            "source_company_id" : source_company.external_id
        }
        if node.image_url:
            # Check if the URL is an S3 URL or a local file path
            parsed_url = urlparse(node.image_url)
            if parsed_url.scheme in ['http', 'https']:  # S3 URL
                # Download the image from S3
                response = requests.get(node.image_url, stream=True)
                response.raise_for_status()  # Ensure the download was successful
                image_file_bytes = BytesIO(response.content)
                image_file_bytes.name = os.path.basename(parsed_url.path)  # Set a name for the file
                image_file = BufferedReader(image_file_bytes)
                setattr(image_file, 'len', len(response.content))
                file_type = response.headers.get('Content-Type', 'application/octet-stream')
            else:
                image_path = settings.BASE_DIR + node.image_url
                image_file = open(image_path, 'rb')
                file_type = self.get_file_content_type(image_file)
            data["image"] = (image_file.name, image_file, file_type)
            encoder = MultipartEncoder(fields=data)
            response = requests.post(
                url, data=encoder,  headers=self.get_auth_headers(is_form_data=True, encoder=encoder))
            # Close the file if it's a local file (S3 response will automatically be closed)
            if not isinstance(image_file, requests.models.Response):
                image_file.close()
        else:
            response = self.send_data(url, data)
        if response.status_code not in [201, 200]:
            self.handle_failure(response, "company_creation")
            return None
        else:
            return response.json()["data"]["id"]

    def add_user(self, user):
        """
        Adds a user to connect app.

        Args:
            user (User): The user object representing the user to be added.

        Returns:
            tuple: A tuple containing a boolean value indicating the success of
            the operation and the response object returned by the API.

        """
        url = self.CONNECT_URL + 'accounts/users/'

        data = {
            "first_name": user.first_name,
            "last_name": user.last_name,
            "email": user.email
        }
        response = self.send_data(url, data)
        if response.status_code != 201:
            self.handle_failure(response, "user_creation")
            return None
        else:
            external_id = response.json()['data']['id']
        return external_id

    def map_user_and_company(self, member, company):
        if member.external_id and company.external_id:
            url = self.CONNECT_URL + 'supply-chains/company-members/'
            data = {
                "company": company.external_id,
                "type": USER_MEMBER_TYPE[member.type],
                "user": member.external_id
            }
            response = self.send_data(url, data)
            if response.status_code != 201:
                self.handle_failure(response, "user_creation")
                return False
            return True
        capture_message("Trying to add compnay member without having connect id , company"+ str(company.id)+" user: "+str(member.id))
        return False

    def check_user_exist(self, email):
        """
        get user with given email from connect.

        Args:

        Returns:
            tuple: A tuple containing a boolean value indicating the success of
            the operation and the response object returned by the API.

        """
        url = self.CONNECT_URL + 'accounts/users/'

        response = requests.get(
            url,
            headers=self.get_auth_headers(),
            params={'email': email}
        )
        try:
            user_id = response.json()['data']['results'][0]['id']
            return user_id
        except:
            return None

    def create_company_member(self, member: NodeMember):
        if member:
            external_id = self.check_user_exist(member.user.email)
            if not external_id:
                external_id = self.add_user(member.user)
                if external_id:
                    member.user.external_id = external_id
                    member.user.save()
            self.map_user_and_company(member.user, member.node) # check duplication and handle error

    def create_company_supply_chains(self, company):
        supply_chains = company.supply_chains.all()
        for supply_chain in supply_chains:
            products=supply_chain.products.all()
            if products:
                for product in tqdm(products):
                    if not product.external_id:
                        url = self.CONNECT_URL + 'catalogs/products/'
                        data = {
                            "name": product.name,
                            "description": product.description,
                        }
                        response = self.send_data(url, data)
                        if response.status_code == 201:
                            product.external_id = response.json()['data']['id']
                            product.save()
                        else:
                            self.handle_failure(response, "product_creation_creation")

            company_products = [product.external_id for product in products]
            for company_product in company_products:
                data = {
                    "product_id": company_product,
                    "company": company.external_id,
                }
                url = self.CONNECT_URL + f'supply-chains/company-products/'
                response = self.send_data(url, data)
                if response.status_code != 201:
                    self.handle_failure(response, "company_product_creation")

    def create_premiums(self, company):
        premiums = company.owned_premiums.filter(external_id__isnull=True)
        url = self.CONNECT_URL + 'catalogs/premiums/'
        for premium in tqdm(premiums):
            if not premium.external_id:
                data = {
                    "category": PREMIUM_CATEGORY[premium.category],
                    "name": premium.name,
                    "type": PREMIUM_TYPE[premium.type],
                    "amount": premium.amount,
                    "included": premium.included,
                    "dependant_on_card": premium.dependant_on_card,
                    "applicable_activity": PREMIUM_APPLIABLE_ACTIVITY[
                        premium.applicable_activity],
                    "calculation_type": premium.calculation_type,
                    "is_active": premium.is_active,
                    "owner": company.external_id,
                }
                if premium.calculation_type == OPTIONS:
                    options = []
                    for option in premium.options.all():
                        options.append({
                            "name": option.name,
                            "amount": option.amount,
                            "is_active": option.is_active
                            })
                    if options:
                        data['options'] = options

                response = self.send_data(url, data)
                if response.status_code == 201:
                    premium.external_id = response.json()['data']['id']
                    premium.save()
                    continue
                raise Exception(f"{premium} --- Sync failed")

    def map_buyers(self, company=None):
        supply_chains = company.supply_chains.all()
        for supply_chain in supply_chains:
            t1_buyers = []
            if company.graph_node:
                buyers = company.map_buyer_pks(supply_chain=supply_chain)
                nodes = Node.objects.filter(pk__in=buyers)
                for n in nodes:
                    tier = 0
                    data = n.graph_node.map_suppliers(
                        supply_chain, None, target_node=company.graph_node
                    )
                    if data:
                        tier = -(len(data[0][TAGS]) + 1)
                    if tier == 0:
                        data = n.graph_node.map_buyers(
                            supply_chain, None, target_node=company.graph_node
                        )
                        if data:
                            tier = len(data[0][TAGS]) + 1
                    if tier == -1:
                        t1_buyers.append(n)
            for t1_buyer in t1_buyers:
                if not t1_buyer.external_id and t1_buyer.is_company():
                    external_id = self.create_company_as_buyer(t1_buyer.company, company)
                    if external_id:
                        t1_buyer.external_id = external_id
                        t1_buyer.save()
                elif t1_buyer.external_id and t1_buyer.is_company():
                    self.map_company_buyer(company, t1_buyer.company)

    @staticmethod
    def get_farmer_reference(farmer):
        """Get co-operative farmer reference"""
        reference = farmer.farmer_references.filter(
            reference__name="Co-Operative ID"
        ).first()
        if not reference:
            return
        return reference.number
    
    def serializer_farmer_data(self, farmer: Farmer, company: Company):
        """format farmer data"""
        data = {
            "name": farmer.name,
            "street": farmer.street,
            "city": farmer.city,
            "sub_province": farmer.sub_province,
            "province": farmer.province,
            "country": farmer.country,
            "zipcode": farmer.zipcode,
            "phone": farmer.phone,
            "description": farmer.description_basic,
            "house_name": farmer.house_name,
            "reference_number": self.get_farmer_reference(farmer),
            "identification_no": farmer.identification_no,
            "latitude": farmer.latitude,
            "longitude": farmer.longitude,
            "email": farmer.email,
            "first_name": farmer.first_name,
            "last_name": farmer.last_name,
            "buyer": company.external_id
        }
        return data
    
    def add_farmer(self, farmer: Farmer, company: Company):
        """Add trace farmer to connect"""
        url = self.CONNECT_URL + "supply-chains/farmers/?sync_from_trace=True"
        data = self.serializer_farmer_data(farmer, company)
        response = requests.post(
            url, data=json.dumps(data), headers=self.get_auth_headers()
        )
        if not response.status_code == 201:
            self.messages.append(
                f"Farmer {farmer.idencode} Invalid- {response.reason}"
            )
            return
        return response.json()["data"]["id"]
    
    def update_farmer(self, farmer: Farmer, company: Company):
        """Update farmer details of trace to connect"""
        url = self.CONNECT_URL + f"supply-chains/farmers/{farmer.external_id}/"
        data = self.serializer_farmer_data(farmer, company)
        data.pop('buyer') #only need buyer for creation
        response = requests.patch(
            url, data=json.dumps(data), headers=self.get_auth_headers()
        )
        if not response.status_code == 200:
            self.messages.append(
                f"Farmer {farmer.idencode} Invalid- {response.reason}"
            )
        return
    
    def map_farmers(self, company):
        """Sync farmers from trace to connect"""
        farmers = company.get_farmer_suppliers()
        #Iterate over each farmer
        for farmer in farmers:
            # Add the farmer to the connect system and get the external ID
            if not farmer.external_id:
                if farmer_id := self.add_farmer(farmer, company):
                    # Update the farmer's external ID and save the changes
                    farmer.external_id = farmer_id
                    farmer.save()
            else:
                self.update_farmer(farmer, company)

    def _update_sync_status(self, company: Company):
        """Update sync status"""
        self.sync.status = SYNC_STATUS_SUCCESS
        if self.messages:
            self.sync.status = SYNC_STATUS_FAILED
            self.sync.error = "\n".join(self.messages)
            capture_message(f"Connect Initail Sync Failed - {company.name}")
        self.sync.save()

    def initiate_mapping(self, company: Company):
        """
        Initializes the Connect feature for a given company node.

        Args:
            node (Company): The company node to initiate Connect for.
        """
        # Create a new company in the Connect system
        if not company.external_id:
            external_id = self.create_company(company)
            # Set the connect_id of the company node to the newly created
            # company_id
            if external_id:
                company.external_id = external_id
                company.save()
        else:
            self.update_company(company)

        # Create a new user Connect system
        for member in company.nodemembers.all():
            self.create_company_member(member)

        # Add all supply chains associated with the company node
        self.create_company_supply_chains(company)
        self.create_premiums(company)
        self.map_buyers(company)
        self.map_farmers(company)
        self._update_sync_status(company)

        print("Mapped company ", company.name, " in connect with id", company.external_id)
