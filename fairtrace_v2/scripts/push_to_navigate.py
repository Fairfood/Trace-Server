import requests
import json
import pyotp
import base64
from io import BytesIO
from django.conf import settings
from django.utils import timezone

from v2.supply_chains.constants import POLYGON
from v2.supply_chains.models.profile import Company, Farmer
from v2.products.models import Batch
from v2.supply_chains.models.supply_chain import SupplyChain

class NavigateAPI:
    NAVIGATE_URL = settings.NAVIGATE_URL+"/navigate/"
    CLIENT_ID = settings.NAVIGATE_OAUTH2_CLIENT_ID
    CLIENT_SECRET = settings.NAVIGATE_OAUTH2_CLIENT_SECRET

    def __init__(self):
        
        credential = f"{self.CLIENT_ID}:{self.CLIENT_SECRET}"
        token = base64.b64encode(credential.encode("utf-8"))
        url = settings.NAVIGATE_URL+"/navigate/oauth/token/"
        headers = {
            'Authorization': "Basic " + token.decode("utf-8"),
        }
        data = {
            "grant_type": "client_credentials",
        }
        
        response = requests.post(url, data=data, headers=headers)
        
        if response.status_code in [200, 201]:
            content = response.json()
            self.access_token = content["access_token"]
        
    @staticmethod
    def check_response(response: requests.Response):
        if response.status_code not in [200, 201]:
            raise Exception("Error in pushing data to navigate", response.json())
        
    def headers(self):
        return {
            "Content-Type": "application/json",
            "Auth-Type": 'client_credentials',
            "Authorization": f'Bearer {self.access_token}'
        }

    @staticmethod
    def generate_point_geo_json(latitude: float, longitude: float):
        return {
            "type": "Feature",
            "geometry": {
                "type": "Point",
                "coordinates": [latitude, longitude]
            }
        }

    @staticmethod
    def farm_data(obj):
        return {
            "external_id": obj.idencode,
            "street": obj.street,
            "city": obj.city,
            "state": obj.province,
            "country": obj.country,
            "zip_code": obj.zipcode,
        }

    def create_company(self, node: Company):
        """
        Create a new company in navigate.

        Args:
            node (Company): The company node to initiate Navigate for.
        """
        url = self.NAVIGATE_URL + "supply-chains/companies/"
        headers ={
            "Auth-Type": 'client_credentials',
            "Authorization": f'Bearer {self.access_token}'
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
        files = {}
        if node.image_url:
            try:
                image_response = requests.get(node.image_url, stream=True)
                image_response.raise_for_status()
                files['image'] = ('image', BytesIO(image_response.content))
            except requests.RequestException:
                pass       
        response = requests.post(url, data=data, files=files,  headers=headers)
        self.check_response(response)
        return response.json()["data"]["id"]

    def update_company(self, node: Company):
        """
        Update company in navigate.

        Args:
            node (Company): The company node to initiate Navigate for.
        """
        url = self.NAVIGATE_URL + f"supply-chains/companies/{node.navigate_id}/"
        headers = {
            "Auth-Type": 'client_credentials',
            "Authorization": f'Bearer {self.access_token}'
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

        files = {}
        if node.image_url:
            try:
                image_response = requests.get(node.image_url, stream=True)
                image_response.raise_for_status()
                files['image'] = ('image', BytesIO(image_response.content))
            except requests.RequestException:
                pass       

        response = requests.patch(url, data=data, files=files, headers=headers)
        self.check_response(response)
        return response.json()["data"]["id"]


    def add_company_to_supply_chain(self, company_id: int, supply_chain_name: str):
        url = self.NAVIGATE_URL + f"supply-chains/companies/{company_id}/add-supply-chain/"
        data = {
            "name": supply_chain_name,
        }
        response = requests.post(url, data=json.dumps(data), headers=self.headers())
        self.check_response(response)

    def add_company_user(self, company_id: int, user):
        url = self.NAVIGATE_URL + f"supply-chains/companies/{company_id}/add-user/"
        data = {
            "email": user.email,
            "first_name": user.first_name,
            "last_name": user.last_name,
            "sso_id": user.sso_user_id,
        }
        response = requests.post(url, data=json.dumps(data), headers=self.headers())
        self.check_response(response)

    def add_company_farmer(self, company_id: int, farmer: Farmer, supply_chain_name: str):
        url = self.NAVIGATE_URL + "supply-chains/farmers/"
        data = {
            "external_id": farmer.idencode,
            "name": farmer.name,
            "street": farmer.street,
            "city": farmer.city,
            "state": farmer.province,
            "country": farmer.country,
            "zip_code": farmer.zipcode,
            "company": company_id,
            "supply_chain_name": supply_chain_name,
        }
        farm_data = self.get_farm_data(farmer)
        if farm_data:
            data["farms"] = farm_data
        response = requests.post(url, data=json.dumps(data), headers=self.headers())
        self.check_response(response)
        return response.json()["data"]["id"]
    
    def update_company_farmer(self, farmer: Farmer):
        url = self.NAVIGATE_URL + f"supply-chains/farmers/{farmer.navigate_id}/"
        farm_data = self.get_farm_data(farmer)
        if farm_data:
            data = {"farms": farm_data}
            response = requests.patch(url, data=json.dumps(data), headers=self.headers())
            self.check_response(response)
            farmer.plots.filter(sync_with_navigate=False).update(sync_with_navigate=True)

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
        if not plots.exists():
            data = self.farm_data(farmer)
            data["geo_json"] = self.generate_point_geo_json(
                farmer.latitude, farmer.longitude)
            data_list.append(data)
        return data_list
    
    def add_company_batch(self, farmer_ids: list, batch: Batch, supply_chain_name: str):
        url = self.NAVIGATE_URL + "supply-chains/batches/"
        data = {
            "external_id": batch.idencode,
            "supply_chain_name": supply_chain_name,
            "farmers": farmer_ids,
        }
        response = requests.post(url, data=json.dumps(data), headers=self.headers())
        self.check_response(response)
        return response.json()["data"]["id"]


    def initiate_navigate(self, company: Company):
        """
        Initializes the Navigate feature for a given company node.

        Args:
            node (Company): The company node to initiate Navigate for.
        """
        if company.navigate_id:
            company_id = self.update_company(company)
            return None

        # Create a new company in the Navigate system
        company_id = self.create_company(company)

        # Set the navigate_id of the company node to the newly created 
        # company_id
        company.navigate_id = company_id
        company.save()

        # Add all members of the company to the Navigate system
        for member in company.members.all():
            self.add_company_user(company_id, member)

        # Add all supply chains associated with the company node
        for supply_chain in company.supply_chains.all():
            self.add_company_to_supply_chain(company_id, supply_chain.name)

        # Print a message indicating that Navigate has been initialized for the 
        # company node
        print("Initialized Navigate for", company.name, "with id", company_id)

    def sync_farmers(self, node: Company, supply_chain: SupplyChain=None):
        """
        Synchronizes farmers with the Navigate system.

        Args:
            node (Company): The company node.
            supply_chain (SupplyChain, optional): The supply chain to filter 
                batches. Defaults to None.

        """
        # Check if the company node has a Navigate ID
        if not node.navigate_id:
            return None

        # Get all batches with non-zero current quantity for the given node 
        # and navigate ID is null.
        batches = Batch.objects.filter(node=node, current_quantity__gt=0, 
                                       navigate_id__isnull=True)

        # Filter batches by supply chain if specified
        if supply_chain:
            batches = batches.filter(product__supply_chain=supply_chain)

        # Iterate over each batch
        for batch in batches:
            # Get new farmers associated with the batch that do not have a 
            # Navigate ID
            farmers = Farmer.objects.filter(farmer_batches__batch=batch)
            # Iterate over each farmer
            for farmer in farmers:
                # Add the farmer to the Navigate system and get the Navigate ID
                if not farmer.navigate_id:
                    farmer_id = self.add_company_farmer(
                        node.navigate_id, farmer,  
                        batch.product.supply_chain.name)

                    # Update the farmer's Navigate ID and save the changes
                    farmer.navigate_id = farmer_id
                    farmer.save()
                else:
                    self.update_company_farmer(farmer)


                # Print a message indicating the farmer and batch that were 
                # pushed
                print("Pushed farmer", farmer.id, "for batch", batch.id)

            # Print a message indicating the farmers and batch that were pushed
            print("Pushed farmers for batch", batch.id)

            farmer_ids = Farmer.objects.filter(
                farmer_batches__batch=batch, 
                navigate_id__isnull=False).values_list(
                    "navigate_id", flat=True)
            # If no farmers were pushed, continue to the next batch
            if not farmer_ids.exists():
                continue

            # Add the batch to the Navigate system and get the Navigate ID
            batch_id = self.add_company_batch(list(farmer_ids), batch, 
                                              batch.product.supply_chain.name)

            # Update the batch's Navigate ID and save the changes
            batch.navigate_id = batch_id
            batch.save()

            # Add batch received from supplier to Navigate
            company = batch.source_transaction.supplier
            api = NavigateAPI()
            api.initiate_navigate(company)
            batch_id = self.add_company_batch(list(company), batch, 
                                              batch.product.supply_chain.name)

            # Update the batch's Navigate ID and save the changes
            batch.navigate_id = batch_id
            batch.save()

            # Print a message indicating the batch that was pushed
            print("Pushed batch", batch.id)

