import base64
import json
import os
from io import BufferedReader, BytesIO
from urllib.parse import urlparse
from typing import Optional
import requests
from django.conf import settings
from django.utils import timezone
from requests_toolbelt.multipart.encoder import MultipartEncoder
from sentry_sdk import capture_message
from common.library import decode
from v2.products.models import Batch
from v2.projects.models import Synchronization
from v2.projects.constants import (
    BASE_PREMIUM, PREMIUM_APPLICABLE_ACTIVITY_BUY, 
    PREMIUM_APPLICABLE_ACTIVITY_SELL, PREMIUM_TYPE_PER_FARMER, 
    PREMIUM_TYPE_PER_KG, PREMIUM_TYPE_PER_TRANSACTION, 
    PREMIUM_TYPE_PER_UNIT_CURRENCY, TRANSACTION_PREMIUM, 
    SYNC_STATUS_FAILED, SYNC_STATUS_SUCCESS
)
from v2.supply_chains.constants import (NODE_MEMBER_TYPE_ADMIN,
                                        NODE_MEMBER_TYPE_MEMBER,
                                        NODE_MEMBER_TYPE_VIEWER, POLYGON)
from v2.supply_chains.models.profile import Company, Farmer, Node, NodeMember

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
        self.NAVIGATE_URL = settings.NAVIGATE_URL + '/navigate/'
        self.CLIENT_ID = settings.NAVIGATE_OAUTH2_CLIENT_ID
        self.CLIENT_SECRET = settings.NAVIGATE_OAUTH2_CLIENT_SECRET

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

        url = self.NAVIGATE_URL + 'oauth/token/'
        credential = f"{self.CLIENT_ID}:{self.CLIENT_SECRET}"
        token = base64.b64encode(credential.encode("utf-8"))
        data = {
            "grant_type": "client_credentials",
        }
        headers = {
            'Authorization': "Basic " + token.decode("utf-8"),
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

class NavigateAPI:

    def __init__(self, sync_id: Optional[str] = None):
        self.messages = []
        self.auth = Login()
        self.NAVIGATE_URL = settings.NAVIGATE_URL + '/navigate/'
        self.sync = None
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

    def format_input_data(self, data):
        return json.dumps(data)

    def get_file_content_type(self, file=None):
        _, file_extension = os.path.splitext(file.name)
        return f'image/{file_extension[1:]}' if file_extension else \
            'application/octet-stream'

    def send_data(self, url, data, headers=None, method='post'):
        if not headers:
            headers = self.get_auth_headers()
        data = self.format_input_data(data)
        if hasattr(requests, method):
            # print(getattr(requests, method), type(getattr(requests, method)))
            return getattr(requests, method)(url, data=data,  headers=headers)
        return requests.post(url, data=data,  headers=headers)

    def create_company(self, node: Company):
        """
        Create a new company in connect.

        Args:
            node (Company): The company node to initiate Connect for.
        """
        url = self.NAVIGATE_URL + "supply-chains/companies/"

        data = {
            "name": node.name,
            "street": node.street,
            "city": node.city,
            "state": node.province if node.province else \
                settings.NAVIGATE_DEFAULT_STATE,
            "country": node.country if node.country else \
                settings.NAVIGATE_DEFAULT_COUNTRY,
            "zip_code": node.zipcode,
            "sso_id": node.sso_id,
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
                file_type = response.headers.get(
                    'Content-Type', 'application/octet-stream')
            else:
                image_path = settings.BASE_DIR + node.image_url
                image_file = open(image_path, 'rb')
                file_type = self.get_file_content_type(image_file)
            data["image"] = (image_file.name, image_file, file_type)
            encoder = MultipartEncoder(fields=data)
            response = requests.post(
                url, data=encoder,  headers=self.get_auth_headers(
                    is_form_data=True, encoder=encoder))
            # Close the file if it's a local file (S3 response will automatically be closed)
            if not isinstance(image_file, requests.models.Response):
                image_file.close()
        else:
            response = self.send_data(url, data)
        if response.status_code != 201:
            self.messages.append(
                f"company with sso id {node.sso_id} not created while \
                navigate sync {response.text}"
            )
            return None
        else:
            return response.json()["data"]["id"]

    def update_company(self, node: Company):
        """
        Update company in navigate.

        Args:
            node (Company): The company node to initiate Navigate for.
        """
        url = self.NAVIGATE_URL + f"supply-chains/companies/{node.navigate_id}/"

        data = {
            "name": node.name,
            "street": node.street,
            "city": node.city,
            "state": node.province if node.province else \
                settings.NAVIGATE_DEFAULT_STATE,
            "country": node.country if node.country else \
                settings.NAVIGATE_DEFAULT_COUNTRY,
            "zip_code": node.zipcode,
            "sso_id": node.sso_id,
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
                file_type = response.headers.get(
                    'Content-Type', 'application/octet-stream')
            else:
                image_path = settings.BASE_DIR + node.image_url
                image_file = open(image_path, 'rb')
                file_type = self.get_file_content_type(image_file)
            data["image"] = (image_file.name, image_file, file_type)
            encoder = MultipartEncoder(fields=data)
            response = requests.patch(
                url, data=encoder,  headers=self.get_auth_headers(
                    is_form_data=True, encoder=encoder))
            # Close the file if it's a local file (S3 response will 
            # automatically be closed)
            if not isinstance(image_file, requests.models.Response):
                image_file.close()
        else:
            response = self.send_data(url, data, method="patch")
        if response.status_code != 200:
            self.messages.append(
                f"company with sso id {node.sso_id} not updated while \
                navigate sync {response.text}"
            )
            return None
        else:
            return response.json()["data"]["id"]


    def add_or_update_user(self, member, company):
        """
        Adds a user to navigate app.

        Args:
            user (User): The user object representing the user to be added.

        Returns:
            tuple: A tuple containing a boolean value indicating the success of
            the operation and the response object returned by the API.

        """
        url = self.NAVIGATE_URL + f'supply-chains/companies/{company.navigate_id}/add-user/'
        data = {
            "first_name": member.user.first_name,
            "last_name": member.user.last_name,
            "email": member.user.email,
            "sso_id": member.user.sso_user_id,
        }
        response = self.send_data(url, data)
        if response.status_code not in [201, 200]:
            self.messages.append(
                f"user with sso id {member.user.sso_user_id} not created \
                while navigate sync {response.text}"
            )
            return False
        return True

    def check_user_exist(self, email):
        """
        get user with given email from connect.

        Args:

        Returns:
            tuple: A tuple containing a boolean value indicating the success of
            the operation and the response object returned by the API.

        """
        url = self.NAVIGATE_URL + f'supply-chains/user/search/{email}/'

        response = requests.get(
            url,
            headers=self.get_auth_headers(),
        )
        try:
            user_id = response.json()['data']['id']
            return user_id
        except:
            return None

    def create_company_member(self, member: NodeMember, company: Company):
        if member:
            is_added = self.add_or_update_user(member, company)
            if not is_added:
                self.messages.append(
                    "Failed: add company member  to navigate, \
                    company"+ str(member.node.id)+" user: "+str(member.id)
                )

    def farm_data(self, obj):
        return {
            "external_id": obj.idencode,
            "street": obj.street,
            "city": obj.city,
            "state": obj.province or obj.farmer.province,
            "country": obj.country or obj.farmer.country,
            "zip_code": obj.zipcode,
        }

    def generate_point_geo_json(self, latitude: float, longitude: float):
        return {
            "type": "Feature",
            "geometry": {
                "type": "Point",
                "coordinates": [latitude, longitude]
            }
        }

    def get_farm_data(self, farmer: Farmer):
        plots = farmer.plots.filter(sync_with_navigate=False)
        data_list = []
        for plot in plots:
            data = self.farm_data(plot)
            if plot.location_type == POLYGON:
                data["geo_json"] = plot.geo_json
            else:
                data["geo_json"] = self.generate_point_geo_json(
                    plot.latitude, plot.longitude)
            data_list.append(data)
        return data_list

    def add_company_farmers(self, company: Company):
        url = self.NAVIGATE_URL + "supply-chains/farmers/"
        supply_chains = company.supply_chains.all()
        farmer_ids = []
        for supply_chain in supply_chains:
            suppliers = company.map_supplier_pks(supply_chain=supply_chain)
            farmers_count= Farmer.objects.filter(
                pk__in=suppliers, navigate_id__isnull=True).count()
            for idx in range (0, farmers_count+1, 100):
                farmers= Farmer.objects.filter(
                    pk__in=suppliers, navigate_id__isnull=True)[idx:idx+100]
                for farmer in farmers:
                    data = {
                        "external_id": farmer.idencode,
                        "name": farmer.name,
                        "street": farmer.street,
                        "city": farmer.city,
                        "state": farmer.province,
                        "country": farmer.country,
                        "zip_code": farmer.zipcode,
                        "company": company.navigate_id,
                        "supply_chain_name": supply_chain.name,
                    }
                    farm_data = self.get_farm_data(farmer)
                    if farm_data:
                        data["farms"] = farm_data

                    response = self.send_data(url, data)
                    if response.status_code != 201:
                        self.messages.append(
                            f"farmer with external id {farmer.idencode} \
                            not created while navigate sync {response.text}"
                        )
                    else:
                        farmer.navigate_id = response.json()["data"]["id"]
                        farmer.save()
                        farmer_ids.append(
                            {farmer.id: response.json()["data"]["id"]})
        return farmer_ids

    def add_company_farmer(self, company: Company, farmer:Farmer, supply_chain_name=""):

        def create_farmer(farmer, supl_name):
            try:
                data = {
                    "external_id": farmer.idencode,
                    "name": farmer.name,
                    "street": farmer.street,
                    "city": farmer.city,
                    "state": farmer.province,
                    "country": farmer.country,
                    "zip_code": farmer.zipcode,
                    "company": company.navigate_id,
                    "supply_chain_name": supl_name,
                }
                farm_data = self.get_farm_data(farmer)
                if farm_data:
                    data["farms"] = farm_data
                response = self.send_data(url, data)
                if response.status_code != 201:
                    self.messages.append(
                        f"farmer with external id {farmer.idencode} \
                        not created while navigate sync {response.text}"
                    )
                    return None
                else:
                    farmer.plots.filter(
                        sync_with_navigate=False).update(sync_with_navigate=True)
                    return response.json()["data"]["id"]
            except Exception as e:
                self.messages.append(f"{str(e)}")

        url = self.NAVIGATE_URL + "supply-chains/farmers/"
        if not supply_chain_name:
            supply_chains = company.supply_chains.all()
            for supply_chain in supply_chains:
                suppliers = company.map_supplier_pks(supply_chain=supply_chain)
                if farmer.id in suppliers:
                   return create_farmer(farmer, supply_chain.name)
        else:
            return create_farmer(farmer, supply_chain_name)
        return None

    def create_company_supply_chains(self, company):
        supply_chains = company.supply_chains.all()
        url = self.NAVIGATE_URL + f"supply-chains/companies/{company.navigate_id}/add-supply-chain/"
        for supply_chain in supply_chains:
            data = {
                "name": supply_chain.name,
            }
            response = self.send_data(url, data)
            if response.status_code != 201:
                self.messages.append(
                    f"Supply chain {supply_chain.name} not created while \
                    navigate sync {response.text}"
                )

    def add_company_batch(self, farmer_ids: list, batch: Batch, supply_chain_name: str):
        try:
            url = self.NAVIGATE_URL + "supply-chains/batches/"
            data = {
                "external_id": batch.idencode,
                "supply_chain_name": supply_chain_name,
                "farmers": farmer_ids,
            }
            response = self.send_data(url, data)
            if response.status_code != 201:
                self.messages.append(
                    f"Batch with external id {batch.idencode} not created while \
                    navigate sync {response.text}"
                )
                return None
            return response.json()["data"]["id"]
        except Exception as e:
            self.messages.append(
                f"Batch with external id {batch.idencode} not created while \
                navigate sync {response.text}"
            )

    def update_company_farmer(self, farmer: Farmer):
        try:
            url = self.NAVIGATE_URL + f"supply-chains/farmers/{farmer.navigate_id}/"
            data = {
                "external_id": farmer.idencode,
                "name": farmer.name,
                "street": farmer.street,
                "city": farmer.city,
                "state": farmer.province,
                "country": farmer.country,
                "zip_code": farmer.zipcode,
            }
            farm_data = self.get_farm_data(farmer)
            if farm_data:
                data = {"farms": farm_data}
            response = self.send_data(url, data, method='patch')
            if response.status_code != 200:
                self.messages.append(
                    f"farmer with external id {farmer.external_id} not updated \
                    while navigate sync {response.text}"
                )
                return False
            farmer.plots.filter(
                sync_with_navigate=False).update(sync_with_navigate=True)
        except Exception as e:
            self.messages.append(f"{str(e)}")
        return True
    
    def create_company_farmers(self, company):
        """Create all farmers under company from trace to navigate"""

        suppliers = company.map_supplier_pks()
        farmers= Farmer.objects.filter(pk__in=suppliers)
        try:
            #Iterate over each farmer
            for farmer in farmers:
                # Add the farmer to the Navigate system and get the Navigate ID
                if not farmer.navigate_id:
                    farmer_id = self.add_company_farmer(company, farmer)

                    # Update the farmer's Navigate ID and save the changes
                    farmer.navigate_id = farmer_id
                    farmer.save()
                else:
                    self.update_company_farmer(farmer)
        except Exception as e:
            self.messages.append(f"{str(e)}")

    def create_company_batches(self, company, supply_chain):
        # Get all batches with non-zero current quantity for the given node
        # and navigate ID is null.

        batches = Batch.objects.filter(
            node=company, current_quantity__gt=0, navigate_id__isnull=True)

        # Filter batches by supply chain if specified
        if supply_chain:
            batches = batches.filter(product__supply_chain=supply_chain)

        # Iterate over each batch
        for batch in batches:
            # Get new farmers associated with the batch that do not have a # Navigate ID
            farmers = Farmer.objects.filter(farmer_batches__batch=batch)
            # non_navigate_farmers = farmers.filter(navigate_id__isnull=True)
            farmer_ids = farmers.values_list(
                    "navigate_id", flat=True)
            # # If no farmers were pushed, continue to the next batch
            if not farmer_ids.exists():
                continue

            # # Add the batch to the Navigate system and get the Navigate ID
            batch_id = self.add_company_batch(
                list(farmer_ids), batch, batch.product.supply_chain.name)

            # # Update the batch's Navigate ID and save the changes
            batch.navigate_id = batch_id
            batch.save()
    
    def _update_sync_status(self, company):
        """Update sync status"""
        self.sync.status = SYNC_STATUS_SUCCESS
        if self.messages:
            self.sync.status = SYNC_STATUS_FAILED
            self.sync.error = "\n".join(self.messages)
            capture_message(f"Navigate Sync Failed - {company.name}")
        self.sync.save()

    def initiate_mapping(self, company: Company):
        """
        Initializes the Connect feature for a given company node.

        Args:
            node (Company): The company node to initiate Connect for.
        """
        if company.navigate_id:
            _ = self.update_company(company)
        else:
            navigate_id = self.create_company(company)
            # Set the connect_id of the company node to the newly created
            # company_id
            if navigate_id:
                company.navigate_id = navigate_id
                company.save()

        # Create a new user Connect system
        for member in company.nodemembers.all():
            self.create_company_member(member, company)

        # Add all supply chains associated with the company node
        self.create_company_supply_chains(company)

        #add company farmers
        self.add_company_farmers(company)

        #create company batches
        supply_chains = company.supply_chains.all()
        for supply_chain in supply_chains:
            self.create_company_batches(company, supply_chain)
        
        if self.sync:
            self._update_sync_status(company)
