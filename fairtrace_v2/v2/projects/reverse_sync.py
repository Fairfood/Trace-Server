import json
import logging
import requests
from io import BytesIO
from typing import Dict, Optional, Union
from urllib.parse import urlencode
from datetime import datetime, timedelta
from common.library import _encode, unix_to_datetime, decode
from django.conf import settings
from django.core.exceptions import ObjectDoesNotExist
from django.core.files.uploadedfile import InMemoryUploadedFile
from django.db import transaction
from django.db.models import Q
from django.utils import timezone
from sentry_sdk import capture_message
from tqdm import tqdm
from v2.accounts.models import FairfoodUser
from v2.products.constants import UNIT_KG
from v2.products.models import Product
from v2.projects.constants import (
    APP_TRANS_TYPE_INCOMING, APP_TRANS_TYPE_OUTGOING, ConnectURL, 
    SYNC_STATUS_FAILED, SYNC_STATUS_SUCCESS
)
from v2.projects.models import (
    NodeCard, PremiumOption, ProjectPremium, Synchronization
)
from v2.projects.serializers.nodes import ProjectFarmerInviteSerializer
from v2.projects.serializers.project import NodeCardSerializer
from v2.projects.serializers.transactions import (AppSentTransactionSerializer,
                                                  AppTransactionSerializer)
from v2.supply_chains.constants import (
    NODE_STATUS_ACTIVE, NODE_TYPE_FARM, LOCATION_TYPES, APPROXIMATE
)
from v2.supply_chains.models import Company, NodeSupplyChain
from v2.supply_chains.models.node import Node
from v2.supply_chains.models.profile import Farmer, NodeMember
from v2.supply_chains.serializers.node import (
    NodeMemberSerializer, FarmerSerializer
)
from v2.supply_chains.serializers.other import FarmerPlotSerializer
from v2.supply_chains.serializers.supply_chain import CompanyInviteSerializer
from v2.supply_chains.views.node import CreateListNodeMember
from v2.supply_chains.views.supply_chain import InviteCompany
from v2.transactions.constants import (VERIFICATION_METHOD_CARD,
                                       VERIFICATION_METHOD_MANUAL)
from v2.transactions.models import ExternalTransaction, InternalTransaction
from v2.transactions.serializers.internal import InternalTransactionSerializer
from v2.transactions.serializers.other import TransactionDeleteSerializer

BASE_URL = settings.ROOT_URL + "/connect/v1/"

from v2.supply_chains.constants import (NODE_MEMBER_TYPE_ADMIN,
                                        NODE_MEMBER_TYPE_MEMBER,
                                        NODE_MEMBER_TYPE_VIEWER,
                                        NODE_TYPE_FARM)

USER_MEMBER_TYPE = {
    'SUPER_ADMIN' : NODE_MEMBER_TYPE_ADMIN,
    'ADMIN' : NODE_MEMBER_TYPE_MEMBER,
    'REPORTER' : NODE_MEMBER_TYPE_VIEWER,
}

logger = logging.getLogger('celery')


class Login:
    """
    Represents a user login session with authentication.

    Attributes:
        username (str): The username used for authentication.
        password (str): The password used for authentication.
        expires_on (datetime): The timestamp indicating the expiration of the
            login session.
        access_token (str): The access token obtained after successful
            authentication.

    Methods:
        access(): Retrieves the access token, either from the stored token or by
                  performing a login request if the stored token has expired.

    Raises:
        LoginFailedError: If the login fails.

    Example:
        login = Login(username='john_doe', password='secure_password')
        token = login.access()
        print(token)  # Access token or raises a LoginFailedError if login
            fails.
    """

    def __init__(self, username, password, device_id):
        """
        Initialize a Login instance.

        Args:
            username (str): The username for authentication.
            password (str): The password for authentication.
        """
        self.username = username
        self.password = password
        self.device_id = device_id
        self.expires_on = timezone.now()
        self.access_token = ""

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

        url = BASE_URL + "auth/login/"
        data = {
            "username": self.username,
            "password": self.password,
            "device_id": self.device_id,
            "force_logout": True,
        }
        response = requests.post(url, data=data)
        if response.status_code == 200:
            self.access_token = response.json()["data"]["access"]
            expires_in = response.json()["data"]["expires_in"]
            self.expires_on = timezone.now() + timezone.timedelta(seconds=expires_in)
            return self.access_token
        raise Exception("Login failed")


user_name = settings.CONNECT_USER_NAME
password = settings.CONNECT_PASSWORD
device_id = settings.CONNECT_DEVICE_ID
login = Login(user_name, password, device_id)


class ReverseSync:
    """
    A class to handle "reverse sync" operations for a single node:
    - Farmers
    - Cards
    - Transactions (external, internal, buy, sent)
    """

    def __init__(self, node_id: str, sync_id: str, created_on=None):
        """
        Initialize with a node_id (the decoded Node primary key) and
        retrieve the corresponding Node object.
        """
        self.messages = []
        self._supplier_buyer_ids = None
        self.created_on = unix_to_datetime(created_on) if created_on else None
        self.sync = Synchronization.objects.get(id=decode(sync_id))
        try:
            self.node = Node.objects.get(id=decode(node_id))
        except Exception as e:
            self.node = None
            self.messages.append(f"Node {node_id} not found {str(e)}")

    @property
    def supplier_buyer_ids(self):
        """
        Lazily load and cache the supplier and buyer IDs for this node.
        """
        if self._supplier_buyer_ids is None:
            suppliers = self.node.get_suppliers()
            buyers = self.node.get_buyers()
            self._supplier_buyer_ids = set(suppliers) | set(buyers)
        return self._supplier_buyer_ids

    @staticmethod
    def _get_context(user_id: str, node_id: str) -> Dict[str, Optional[dict]]:
        """
        Retrieve a user and node context for serialization.
        If user/node can't be found, return a meaningful response with 
        a message.
        
        Args:
            user_id (str): The external ID of the user.
            node_id (str): The external ID of the node.

        Returns:
            dict: A dictionary with the user, node, and a message or error 
            details.
        """
        context = {
            "user": None,
            "node": None,
            "success": False,
            "message": "Both user_id and node_id must be provided."
        }

        if not user_id or not node_id:
            return context

        try:
            context["user"] = FairfoodUser.objects.get(external_id=user_id)
        except Exception as e:
            context["message"] = f"User with ID {user_id} not found-{str(e)}"
            return context

        try:
            context["node"] = Node.objects.get(external_id=node_id)
        except Exception as e:
            context["message"] = f"Node with ID {node_id} not found-{str(e)}"
            return context

        context["success"] = True
        context["message"] = "Successfully retrieved user and node."
        return context
    
    def _check_response_status(
            self, 
            response: requests.models.Response, 
            url: str
        ) -> bool:
        """
        Helper function to check the response status and log any errors.
        
        :param response: The response object.
        :param url: The URL that was requested.
        :return: True if response status is OK, False if not.
        """
        if response.status_code != 200:
            self.messages.append(f"API call failed for URL: {url}")
            return False
        return True

    def _make_get_request(
            self, 
            url: str, 
            recursive: bool
        ) -> Union[requests.models.Response, list, dict]:
        """
        Performs a GET request to the provided URL and checks for a 
        successful response.

        :param url: The URL to make the GET request to.
        :param recursive: A boolean flag indicating whether to follow 
            pagination links.

        :return: The response object if the status code is 200, an empty list 
            (for recursive) or an empty dict (for non-recursive) if the 
            request fails.
        """
        response = requests.get(
            url,
            headers={
                "Authorization": "Bearer " + login.access(),
                "Content-Type": "application/json",
            },
        )
        if not self._check_response_status(response, url):
            return [] if recursive else {}
        return response
    
    def _make_requests(self, url: str, recursive: bool) -> list:
        """
        Fetch data from the provided URL and handle pagination if needed.

        This method makes an initial GET request and, if the response is 
        paginated (contains a 'next' link),it will recursively fetch all 
        pages of results.

        :param url: The URL to make the GET request to.
        :param recursive: A boolean flag indicating whether to handle 
            pagination. If True, the function will recursively fetch data 
            from all available pages.

        :return: A list of results containing all pages of data (if recursive), 
            or a single batch of data (if not recursive).
        """
        response = self._make_get_request(url, recursive)
        if not response:
            return [] if recursive else {}

        data = response.json().get("data", {})
        results = data.get("results", [])

        # If not recursive, return just this batch's data
        if not recursive:
            return results

        # If recursive, accumulate all pages
        final_results = results
        while data.get("next"):
            next_url = data["next"]
            response = self._make_get_request(next_url, recursive)
            if not response:
                self.messages.append(
                    f"Reverse Sync paginated call failed: {next_url}"
                )
                break
            data = response.json().get("data", {})
            final_results += data.get("results", [])

        return final_results

    def _fetch_data(
            self, 
            url: str, 
            recursive: bool=True, 
            external_id: str=None, 
            created_on: datetime=None, 
            updated_on: datetime=None, 
            node_id: str=None
        ) -> list:
        """
        A unified data-fetching method that can either pull a single batch or 
        recursively handle paginated data based on the 'recursive' parameter.
        
        :param url:         The URL to fetch from.
        :param recursive:   Whether to follow pagination links.
        :param external_id: Optional external_id to filter by (for farmers).
        :param created_on:  Optional datetime for 'created_after'.
        :param updated_on:  Optional datetime for 'updated_after'.
        :param node_id:     Optional node external_id to filter by.
        :return:            List (recursive) or dict (single batch) of results.
        """
        # Build final URL with query params

        params = {
            "created_after_farmer": external_id,
            "created_after": int(created_on.timestamp()) if created_on \
                else None,
            "updated_after": int(updated_on.timestamp()) if updated_on \
                else None,
            "entity": node_id,
            "skip_only_connect": "true",
            "reverse_sync": "True"
        }

        # Iterate over the dictionary and add each parameter to the URL
        params = {
            key: value for key, value in params.items() if value is not None
        }

        query_string = urlencode(params)
        url = f"{url}?{query_string}"
        results = self._make_requests(url, recursive)
        return results
    
    def _get_kwargs(self, url: str, updated_on: datetime) -> dict:
        """
        Constructs a dictionary of keyword arguments based on the provided 
        parameters.
        """
        #taking one day before as updated on to avoid missing data from connect
        updated_on_with_buffer = updated_on - timedelta(days=1) \
            if updated_on else None
        kwargs = {
            'url': url,
            'updated_on': updated_on_with_buffer,
            'node_id': self.node.external_id
        }
        if self.created_on:
            kwargs.pop('updated_on')
            kwargs['created_on'] = self.created_on
        return kwargs

    def _get_last_farmer(self) -> Farmer:
        """
        Return the last updated Farmer object (by updated_on)
        among the suppliers or buyers of self.node.
        """
        return (
            Farmer.objects.filter(
                external_id__isnull=False, 
                node_ptr__in=self.supplier_buyer_ids
            ).order_by("updated_on").last()
        )
    
    def _save_image_from_url(
            self, 
            image_url: str, 
            external_id: str,
            model_name: str
        ) -> Optional[InMemoryUploadedFile]:
        """fn to save image from url"""
        image_response = requests.get(image_url, stream=True)
        
        if not image_response.status_code == 200:
            self.messages.append(
                f"{model_name} external id-{external_id} - Image-\
                {image_response.reason}"
            )
            return None
        
        # Create a BytesIO stream from the image content
        image_content = BytesIO(image_response.content)
        # Extract the file name from the URL
        image_name = image_url.split("/")[-1]  
        
        # Wrap it as InMemoryUploadedFile
        image_file = InMemoryUploadedFile(
            image_content,  # The BytesIO object
            field_name='image',  # The field name in the form
            name=image_name,  # The filename
            content_type="image/jpeg",
            size=len(image_response.content),  # Size of the image
            charset=None
        )
        return image_file
    
    @staticmethod
    def _get_plot_name(farmer: Farmer) -> str:
        """Get plot name for farmer on increment basis"""
        base_name = "plot"
        plot_number = 1
        name = f"{base_name}{plot_number}"

        while farmer.plots.filter(name=name).exists():
            plot_number += 1
            name = f"{base_name}{plot_number}"
        
        return name
    
    def _get_plot_data(
            self, 
            farmer: dict, 
            farmer_instance: Farmer, 
            location_type: str
        ) -> dict:
        plot = {
            "name": self._get_plot_name(farmer_instance),
            "farmer": farmer_instance.idencode,
            "location_type": location_type,
            "geo_json": json.dumps(farmer["plots"]),
            "street": farmer_instance.street,
            "city": farmer_instance.city,
            "province": farmer_instance.province,
            "country": farmer_instance.country,
            "zipcode": farmer_instance.zipcode,
            "latitude": farmer_instance.latitude,
            "longitude": farmer_instance.longitude
        }
        return plot
    
    def _add_or_update_plot(self, farmer: dict) -> dict:
        """Add or update farmer plot. Checks for existing plots with same 
        geojson and if found multiple keeps first and deletes rest."""
        if not farmer["plots"]:
            return
        
        location_type = farmer["plots"]["geometry"].get(
            "type", APPROXIMATE
        ).upper()

        # Check if location_type exists in LOCATION_TYPES, else default 
        # to APPROXIMATE
        location_type = next(
            (value for value, _ in LOCATION_TYPES if value == location_type), 
            APPROXIMATE
        )

        farmer_instance = Farmer.objects.get(external_id=farmer["id"])
        plot = self._get_plot_data(farmer, farmer_instance, location_type)

        serializer = FarmerPlotSerializer(data=plot)
        existing_plots = farmer_instance.plots.filter(
            geo_json=plot["geo_json"]
        )
        if existing_plots:
            serializer = FarmerPlotSerializer(existing_plots.first(), plot)
            
            #delete plots with same geo json
            if existing_plots.count() > 1:
                existing_plots.exclude(id=existing_plots.first().id).delete()
        
        if not serializer.is_valid():
            self.messages.append(
                f"Farmer {farmer['id']}: invalid plot data - \
                {json.dumps(serializer.errors)}"
            )
            return
        
        serializer.save()
        
    def _get_farmer_data(self, farmer: dict, node: Node) -> dict:
        """
        Serializes a farmer's information along with related node details.

        Args:
            farmer (dict): A dictionary containing the farmer's information
            node (Node): The node object associated with the farmer, which is 
                expected to contain a "participating_projects" field. 
                The first project is associated with the serialized data.

        Returns:
            dict: A dictionary containing the serialized data of the farmer
        
        Notes:
            - If any field in the farmer data is `None` or missing, an empty 
                string or `None` will be used.
            - The "extra_fields" is serialized as a JSON string.
            - The "created_on" field is converted to a datetime object using 
                `unix_to_datetime`.
        """
        data = {
            "external_id": farmer["id"],
            "first_name": farmer["first_name"],
            "last_name": farmer["last_name"],
            "identification_no": farmer["identification_no"] or "",
            "street": farmer["street"] or "",
            "city": farmer["city"] or "",
            "province": farmer["province"],
            "country": farmer["country"],
            "latitude": farmer["latitude"],
            "longitude": farmer["longitude"],
            "zipcode": farmer["zipcode"] or "",
            "email": farmer["email"],
            "id_no": farmer["reference_number"] or "",
            "extra_fields": json.dumps(farmer["submission"]),
            "created_on": unix_to_datetime(farmer["created_on"])
        }
        project = node.participating_projects.first()
        if project:
            data["project"] = project
        if farmer["phone"]:
            data["phone"] = farmer["phone"]
        if image_url := farmer.get("image"):
            if image := self._save_image_from_url(
                image_url, farmer["id"], "Farmer"
            ):
                data['image'] = image
        return data

    @transaction.atomic
    def _create_or_update_farmers(self, farmers: list):
        """Create or update farmers from connect"""

        for farmer in tqdm(farmers):
            user_id = farmer["creator"]
            node_id = farmer.get("buyer", None)
            context = self._get_context(user_id, node_id)

            if not context['success']:
                self.messages.append(context['message'])
                continue

            try:
                farmer_instance = Farmer.objects.get(external_id=farmer["id"])
            except ObjectDoesNotExist:
                farmer_instance = None
            except Exception as e:
                self.messages.append(f"Famer with external id-{str(e)}")
                continue

            data = self._get_farmer_data(farmer, self.node)
            context.update({'skip_farmer_invite_validation': True})

            serializer = FarmerSerializer(
                farmer_instance, data=data, context=context
            )
            if not farmer_instance:
                serializer = ProjectFarmerInviteSerializer(
                    data=data, context=context
                )

            if not serializer.is_valid():
                self.messages.append(
                    f"Farmer {farmer['id']}: invalid data - \
                    {json.dumps(serializer.errors)}"
                )
                continue

            serializer.save()
            self._add_or_update_plot(farmer)

    def _sync_farmers(self):
        """Sync farmers from Connect to Trace for self.node."""
        url = ConnectURL.FARMERS.value
        last_farmer = self._get_last_farmer()
        updated_on = last_farmer.updated_on if last_farmer else None

        kwargs = self._get_kwargs(url, updated_on)
        data = self._fetch_data(**kwargs)
        self._create_or_update_farmers(data)

        logger.info("Sync farmers completed")

    def _get_last_card(self) -> NodeCard:
        """
        Return the last updated NodeCard among the suppliers/buyers of 
        self.node.
        """
        return (
            NodeCard.objects.filter(
                external_id__isnull=False, 
                node_id__in=self.supplier_buyer_ids
            ).order_by(
                "updated_on"
            ).last()
        )

    @transaction.atomic
    def _sync_node_cards(self):
        """Sync entity card(node card) from connect to trace"""
        url = ConnectURL.ENTITY_CARDS.value
        last_card = self._get_last_card()
        updated_on = last_card.updated_on if last_card else None

        kwargs = self._get_kwargs(url, updated_on)
        cards = self._fetch_data(**kwargs)

        for card in tqdm(cards):
            try:
                node_obj = Node.objects.get(external_id=card["entity"])
            except Exception as e:
                self.messages.append(
                    f"Node with external id {card['entity']} issue {str(e)}"
                )
                continue

            data = {
                "node": node_obj.idencode,
                "card_id": card["card"]["card_id"],
                "external_id": card["card"]["id"],
                "fairid": card["card"].get("display_id") or "",
            }

            serializer = NodeCardSerializer(data=data)
            if not serializer.is_valid():
                self.messages.append(
                    f"Card {card['card']['card_id']}: invalid data - \
                    {json.dumps(serializer.errors)}"
                )
                continue

            serializer.save()

        logger.info("Sync cards completed")

    def _get_last_transaction(self) -> ExternalTransaction:
        """
        Return the last updated ExternalTransaction involving self.node 
        (as source or destination).
        """
        query = Q(source=self.node) | Q(destination=self.node)
        return (
            ExternalTransaction.objects.filter(external_id__isnull=False)
            .filter(query)
            .order_by("updated_on")
            .last()
        )

    def _get_transactions(self):
        """Fetch product transactions from Connect for self.node."""
        url = ConnectURL.PRODUCT_TRANSACTIONS.value
        last_txn = self._get_last_transaction()
        updated_on = last_txn.updated_on if last_txn else None

        kwargs = self._get_kwargs(url, updated_on)
        return self._fetch_data(**kwargs)
    

    @staticmethod
    def _is_bal_loss(transaction: dict) -> bool:
        """
        Determines if the transaction is a balance loss based on quantity 
        comparison.

        Args:
            transaction (dict): A dictionary containing the transaction 
                details, which should include:
                - "quantity": The current quantity.
                - "source_quantity": The initial or source quantity.

        Returns:
            bool: Returns `True` if the transaction's "quantity" is less 
                than "source_quantity", indicating a balance loss. Returns 
                `False` otherwise.

        Notes:
            - This method checks if the current quantity is less than the 
            source quantity, which is used to identify a loss in balance 
            during the transaction.
        """
        return transaction["quantity"] < transaction["source_quantity"]

    def _get_premium_data(self, premium: dict) -> dict:
        """
        Serializes a premium object, including its associated premium option, 
        if available.

        Args:
            premium (dict): A dictionary containing the premium data. Expected 
                keys include:
                - "premium": The external ID of the premium
                - "selected_option": The name of the selected premium 
                    option (optional).
                - "amount": The amount of the premium.

        Returns:
            dict or None: Returns a dictionary containing the serialized data 
                if successful, or `None` if the premium or its selected option 
                could not be found.

        Notes:
            - If the specified premium or the selected option is not found, 
                an error message is appended to `self.messages`.
            - The "premium" field in the returned dictionary contains the 
                primary key (PK) of the corresponding ProjectPremium instance.
            - The "selected_option" field in the returned dictionary 
                contains the primary key (PK) of the corresponding 
                PremiumOption if a valid option is provided.
            - If no valid selected option is found, it is omitted from 
                the returned dictionary.
        """
        try:
            premium_instance = ProjectPremium.objects.get(
                external_id=premium["premium"]
            )
        except Exception as e:
            self.messages.append(f"Premium {premium['premium']} {str(e)}")
            return
        
        data = {
            "premium": premium_instance.pk,
            "amount": premium["amount"],
        }
        
        if premium.get("selected_option_details"):
            try:
                selected_option, _ = PremiumOption.objects.get_or_create(
                    name=premium["selected_option_details"]["name"], 
                    premium=premium_instance
                )
                data["selected_option"] = selected_option
            except Exception as e:
                self.messages.append(
                    f"Premium Option {premium['selected_option']}-{str(e)}"
                )

        return data

    def _get_transaction_premiums(self, transaction: dict) -> list:
        """
        Retrieves and serializes premium data from a given transaction, 
        excluding the main "TRANSACTION" payment.

        Args:
            transaction (dict): A dictionary representing the transaction. 

        Returns:
            list: A list of serialized premium data. Each entry is a dictionary 
                containing serialized data for a premium, or an empty list 
                if no premiums are found or if the "TRANSACTION" payment is 
                the only payment type.

        Notes:
            - The method excludes payments with the type "TRANSACTION" and 
                only processes payments related to premiums.
            - The serialized premium data is returned as a list of 
                dictionaries, each of which represents a valid premium.
        """
        premiums = []
        for payment in transaction.get("transaction_payments", []):
            # Skip if it's the main "TRANSACTION" payment
            if payment["payment_type"] == "TRANSACTION":
                continue
            if premium_data := self._get_premium_data(payment):
                premiums.append(premium_data)
        return premiums


    def _get_batch_data(self, transaction_id: str) -> list:
        """
        Given a transaction's external ID (for both External and Internal),
        fetch and serialize the batches into {'batch': batch_id, 
        'quantity': x }.
        """
        txn = (
            ExternalTransaction.objects.filter(
                external_id=transaction_id
            ).last()
            or 
            InternalTransaction.objects.filter(
                external_id=transaction_id
            ).last()
        )
        if not txn:
            return []

        return [
            {"batch": b.idencode, "quantity": b.current_quantity}
            for b in txn.result_batches.all()
        ]
    
    def _get_batches(self, transaction: dict) -> list:
        """
        Retrieves and serializes batches associated with a given transaction.

        Args:
            transaction (dict): A dictionary representing the transaction. 

        Returns:
            list: A list of serialized batches corresponding to the unique 
                parent IDs in the transaction.

        Notes:
            - The method ensures that each parent ID is unique by 
                converting the list of parents into a set.
            - The method uses the `serialize_batches` function to 
                retrieve and serialize the batches for each parent ID.
            - The resulting list of serialized batches is returned.
        """
        batches = []
        for parent_id in set(transaction["parents"]):
            batches.extend(self._get_batch_data(parent_id))
        return batches


    @staticmethod
    def _set_card_details(
            data: dict, 
            card_details: dict, 
        ) -> dict:
        """
        Sets card id an fairid
        """
        data["card_id"] = card_details.get("card_id")
        data["fairid"] = card_details.get("fairid")
    
    def _get_transaction_dict(self, transaction: dict) -> dict:
        """
        Serializes a transaction object into a standardized dictionary format 
        for further processing.
        """
        data = {
            "external_id": transaction["id"],
            "unit": UNIT_KG,
            "quantity": transaction["quantity"],
            "price": transaction["amount"],
            "currency": transaction["currency_details"]["code"],
            "created_on": transaction["date"],
            "premiums": self._get_transaction_premiums(transaction),
            "quality_correction": transaction["quality_correction"],
            "verification_longitude": transaction["verification_longitude"],
            "verification_latitude": transaction["verification_latitude"],
            "extra_fields": json.dumps(transaction["submissions"]),
            "send_seperately": transaction["send_seperately"],
            "source_quantity": transaction.get("source_quantity"),
            "destination_quantity": transaction.get("current_quantity"),
            "deleted": transaction.get("is_deleted", False),
        }
        if invoice_num := transaction.get("invoice_number"):
            data["invoice_number"] = invoice_num
        if invoice_url := transaction.get("invoice"):
            if invoice := self._save_image_from_url(
                invoice_url, transaction["id"], "Transaction"
            ):
                data['invoice'] = invoice
        if reference := transaction.get("reference"):
            data["buyer_ref_number"] = reference
        return data

    def _get_transaction_data(
        self, 
        transaction: dict, 
        transaction_type: str
    ) -> dict:
        """
        Serializes a transaction object into a standardized dictionary format 
        for further processing.

        Args:
            transaction (dict): The transaction data.
            transaction_type (str): The type of the transaction 
                (either "sent" or "received").

        Returns:
            dict: A dictionary with the serialized transaction data, 
                including card details, node, product, premiums, and other 
                relevant fields. Returns an empty dictionary if node or 
                product cannot be found.
        """
        data = self._get_transaction_dict(transaction)

        # Set card details or manual verification
        if transaction.get("card_details"):
            self._set_card_details(data, transaction["card_details"])
            data["verification_method"] = VERIFICATION_METHOD_CARD
        else:
            data["verification_method"] = VERIFICATION_METHOD_MANUAL

        if transaction_type == "sent":
            node_key = "destination"
            data["is_bal_loss"] = self._is_bal_loss(transaction)
            data["batches"] = self._get_batches(transaction)
            data["type"] = APP_TRANS_TYPE_OUTGOING
            data["force_create"] = True
        else:
            node_key = "source"
            data["type"] = APP_TRANS_TYPE_INCOMING
        
        try:
            data["node"] = Node.objects.get(
                external_id=transaction[node_key]
            ).pk
            data["product"] = Product.objects.get(
                external_id=transaction["product"]
            ).idencode
        except Exception as e:
            self.messages.append(f"{str(e)}")
            data = {}

        return data

    def _create_buy_transaction(self, transaction: dict):
        """
        Creates a "buy" transaction, where goods are received by a node 

        This method serializes the transaction data, validates it, and either 
        creates a new transaction or updates an existing one. It handles 
        errors and appends relevant messages to`self.messages` for 
        further action.

        Args:
            transaction (dict): A dictionary representing the transaction data.

        Returns:
            None: The method either saves the transaction (new or updated) or 
                appends error messages.If there are errors or invalid data, 
                it doesn't return anything.
        """
        # Serialize the transaction data with type "buy"
        data = self._get_transaction_data(transaction, "buy")
        if not data:
            return

        user_id = transaction["creator"]
        node_id = transaction["destination"]
        context = self._get_context(user_id, node_id)

        if not context['success']:
            self.messages.append(context['message'])
            return

        # Check if the transaction already exists in the database
        try:
            ext_txn_instance = ExternalTransaction.objects.get(
                external_id=transaction["id"]
            )
        except ObjectDoesNotExist:
            ext_txn_instance = None
        except Exception as e:
            self.messages.append(
                f"Ext txn with ext id {transaction['id']} - {str(e)}"
            )
            return
            
        # Use the appropriate serializer based on whether it's a new or existing transaction
        serializer = AppTransactionSerializer(data=data, context=context)
        if ext_txn_instance:
            serializer = TransactionDeleteSerializer(
                instance=ext_txn_instance, data=data
            )

        if not serializer.is_valid():
            self.messages.append(
                f"Buy txn {transaction['id']} - invalid data: \
                {json.dumps(serializer.errors)}"
            )
            return

        serializer.save()

    def _create_sent_transaction(self, transaction: dict):
        """
        Creates or updates a "sent" transaction, where goods are sent 
        from a source node.

        This method serializes the transaction data, checks the user and 
        node context, validates the data using a serializer, and either 
        creates a new transaction or updates an existing one. If there 
        are any errors, they are logged in `self.messages`.

        Args:
            transaction (dict): A dictionary containing the transaction details.

        Returns:
            None: The method either creates or updates the transaction, 
                or logs errors in `self.messages`.
        """
        data = self._get_transaction_data(transaction, "sent")
        if not data:
            return

        user_id = transaction["creator"]
        node_id = transaction["source"]
        context = self._get_context(user_id, node_id)

        if not context['success']:
            self.messages.append(context['message'])
            return

        try:
            ext_txn_instance = ExternalTransaction.objects.get(
                external_id=transaction["id"]
            )
        except ObjectDoesNotExist:
            ext_txn_instance = None
        except Exception as e:
            self.messages.append(
                f"Ext Txn with ext id {transaction['id']}-{str(e)}"
            )
            return
        
        serializer = AppSentTransactionSerializer(data=data, context=context)
        if ext_txn_instance:
            serializer = TransactionDeleteSerializer(
                instance=ext_txn_instance, data=data
            )
    
        if not serializer.is_valid():
            self.messages.append(
                f"Sent txn {transaction['id']} - invalid data: \
                {json.dumps(serializer.errors)}"
            )
            return

        serializer.save()

    def _get_internal_txn_data(self, transaction: dict) -> dict:
        """
        This method converts an internal transaction's data into a 
        standardized dictionary format, including information about 
        the product, supply chain, batches, and quantities. If the product
        for the transaction is not found, an error message is logged.

        Args:
            transaction (dict): The transaction data

        Returns:
            dict or None: A dictionary with serialized transaction data or 
                None if the product is invalid.
        """
        try:
            product = Product.objects.get(external_id=transaction["product"])
        except Exception as e:
            self.messages.append(
                f"Internal txn {transaction['id']} product-{str(e)}"
            )
            return
        
        return {
            "external_id": transaction["id"],
            "type": 3,  # Example enum/type for "internal"
            "created_on": transaction["date"],
            "supply_chain": product.supply_chain.idencode,
            "destination_batches": [
                {
                    "product": product.idencode,
                    "quantity": transaction["quantity"],
                    "unit": UNIT_KG,
                }
            ],
            "source_batches": self._get_batches(transaction),
        }

    def _create_internal_transaction(self, transaction: dict):
        """
        Creates or updates an internal transaction.

        This method serializes the internal transaction data, checks the 
        user and node context, validates the data using a serializer, 
        and either creates a new transaction or updates an existing one. 
        If there are any errors, they are logged in `self.messages`.

        Args:
            transaction (dict): A dictionary containing the transaction details.

        Returns:
            None: The method either creates or updates the transaction, or 
                logs errors in `self.messages`.
        """
        # Serialize the internal transaction data
        data = self._get_internal_txn_data(transaction)
        if not data:
            return

        user_id = transaction["creator"]
        node_id = transaction["source"]
        context = self._get_context(user_id, node_id)

        # Check if the context is valid
        if not context['success']:
            self.messages.append(context['message'])
            return

        try:
            int_txn_instance = InternalTransaction.objects.get(
               external_id=transaction["id"]
            )
        except ObjectDoesNotExist:
            int_txn_instance = None
        except Exception as e:
            self.messages.append(f"Int Txn Error {str(e)}")
            return

        # Use the appropriate serializer
        serializer = InternalTransactionSerializer(
            data=data, context=context
        )
        if int_txn_instance:
            serializer = TransactionDeleteSerializer(
                instance=int_txn_instance, data=data
            )

        # Validate and save the serializer
        if not serializer.is_valid():
            self.messages.append(
                f"Internal txn {transaction['id']} - invalid data: \
                {json.dumps(serializer.errors)}"
            )
            return

        serializer.save()


    @transaction.atomic
    def _sync_transactions(self):
        """Sync transactions for connect to trace"""
        transactions = sorted(
            self._get_transactions(), key=lambda x: x["created_on"]
        )

        for txn in tqdm(transactions):
            src = txn["source"]
            dst = txn["destination"]

            # Internal transaction if source == destination
            if src == dst:
                self._create_internal_transaction(txn)
            else:
                # If source is a farm, it's a "buy"/incoming txn for node
                try:
                    source_obj = Node.objects.get(external_id=src)
                except Exception as e:
                    self.messages.append(
                        f"Txn {txn['id']}: Source node Issue-{str(e)})"
                    )
                    continue

                if source_obj.type == NODE_TYPE_FARM:
                    self._create_buy_transaction(txn)
                else:
                    self._create_sent_transaction(txn)

        logger.info("Sync transactions completed")
    
    def _update_sync_status(self):
        """Update sync status"""
        self.sync.status = SYNC_STATUS_SUCCESS
        if self.messages:
            self.sync.status = SYNC_STATUS_FAILED
            self.sync.error = "\n".join(self.messages)
            capture_message(f"Reverse Sync Failed - {self.node.full_name}")
        self.sync.save()

    def start_sync(self):
        """
        Start the reverse sync process for self.node.
        """
        if self.node:
            self._sync_farmers()
            self._sync_node_cards()
            self._sync_transactions()
        self._update_sync_status()


def create_serializer_context(url, view=None, node=None, view_kwargs=None):
    context = {}
    sync_user = get_sync_user()
    if not node:
        node = get_default_node()
    else:
        node = Node.objects.filter(external_id=node).first()
    context["request"] = get_request_object(url, "post")
    context["request"].user = sync_user
    if node and view:
        view_args = {}
        if view_kwargs:
            view_args = view_kwargs if view_kwargs and isinstance(view_kwargs, dict) else {}
        view_args["node"] = node
        setattr(view, "kwargs", view_args)
        context["view"] = view
    return context


def format_company_data(data):
    formated_data  = {
        "external_id": data["id"],
        "street":  data["street"] if data["street"] else "",
        "city":  data["city"] if data["city"] else "",
        "province":  data["province"] if data["province"] else "",
        "country":  data["country"] if data["country"] else "",
        "zipcode":  data["zipcode"] if data["zipcode"] else "",
        "name":  data["name"] if data["name"] else "",
        "latitude":  data["latitude"] if data["latitude"] else 0.0,
        "longitude":  data["longitude"] if data["longitude"] else 0.0,
        "email":  data["email"] if data["email"] else None,
        "phone":  data["phone"] if data["phone"] else "",
        "send_email": False,
        "create_user_without_invitation" : True,
        "status": NODE_STATUS_ACTIVE,
        "description": data["description"],
        "relation": 1,
    }
    if not formated_data["country"]:
        formated_data.pop("country")
    return formated_data


def get_product_supplychains(products=None):
    if products:
        return Product.objects.filter(external_id__in=products).values_list("supply_chain", flat=True).all()
    return []


def get_incharge_person(company_id=None):
    if company_id:
        url = BASE_URL + "supply-chains/company/<company_id>/members/?limit=1"
        url =  url.replace("<company_id>", company_id)
        response = pull_data_batch_wise(url)
        if response and"user" in response[0]:
            return {
                "first_name": response[0]["user"]["first_name"],
                "last_name": response[0]["user"]["last_name"],
                "email": response[0]["user"]["email"]
            }
    return None


def create_companies(companies=None):
    if companies:
        serializer_klass = CompanyInviteSerializer
        inserted_companies = []
        existing_companies = []
        for company in tqdm(companies):
            supply_chains = get_product_supplychains(company["products"])
            supply_chains = list(set(supply_chains))
            if not Company.objects.filter(external_id=company["id"]).exists():
                if supply_chains and company["members"]:
                    incharge = get_incharge_person(company["id"])
                    if incharge:
                        company_data = format_company_data(company)
                        company_data["incharge"] = incharge
                        company_obj = Company.objects.filter(name__iexact=company["name"]).first()
                        if company["name"] and company_obj:
                            company_obj.external_id = company["id"]
                            company_obj.save()
                        else:
                            context = create_serializer_context('v2/supply-chain/invite/company/', InviteCompany)
                            company_data["supply_chain"] = _encode(supply_chains[0])
                            serializer = serializer_klass(data=company_data, context=context)
                            serializer.is_valid(raise_exception=True)
                            company_obj = serializer.save()

                        for idx in range(1, len(supply_chains)-1):
                            _, _ = NodeSupplyChain.objects.get_or_create(
                                node=company_obj, supply_chain=supply_chains[idx]
                            )
                        inserted_companies.append(company_data["external_id"])
            elif supply_chains and company["members"]:
                existing_companies.append(company["id"])
            elif not supply_chains and company["products"]:
                capture_message("Missing product in trace -> " + ", ".join(company["products"]))
        return (inserted_companies, existing_companies)
    return ([], [])

def get_request_object(url, method="get"):
    from django.test.client import RequestFactory
    factory = RequestFactory()
    if hasattr(factory, method):
        return getattr(factory, method)(url)
    return factory.get("test")


def format_member_data(data):
    formated_data  = {
        "first_name":  data["user"]["first_name"] if data["user"] else "",
        "last_name":  data["user"]["last_name"] if data["user"] else "",
        "type":  USER_MEMBER_TYPE[data["type"]] if data["type"] and data["type"] in USER_MEMBER_TYPE else 1,
        "email":  data["user"]["email"] if data["user"]["email"] else None,
        "email_verified": True
    }
    return formated_data


def create_company_members(members=None):
    inserted_members = []
    if members:
        serializer_klass = NodeMemberSerializer
        from common.backends.sso import SSORequest
        sso = SSORequest()
        for member in tqdm(members):
            member_obj = NodeMember.objects.filter(user__external_id=member["user"]["id"]).first()
            if not member_obj:
                context = create_serializer_context(
                    'v2/supply-chain/node/member/', CreateListNodeMember, member["company"],
                    {"silent_registration": True, "set_default_password": True})
                member_data = format_member_data(member)
                serializer = serializer_klass(data=member_data, context=context)
                serializer.is_valid(raise_exception=True)
                member_obj = serializer.save()
                if not member_obj.user.external_id:
                    member_obj.user.external_id = member["user"]["id"]
                    member_obj.user.save()
                    sso.add_user_to_connect(member_obj.user, member_obj.node.company, enable_connect=True)
                inserted_members.append(member["user"]["id"])
            else:
                sso.add_user_to_connect(member_obj.user, member_obj.node.company, enable_connect=True)
    return inserted_members

def get_sync_user():
    sync_user_id = settings.SYNC_USER_ID
    if sync_user_id:
        sync_user = FairfoodUser.objects.filter(id=sync_user_id).first()
        if sync_user:
            return sync_user
    return None

def get_default_node():
    sync_node_id = settings.SYNC_NODE_ID
    if sync_node_id:
        sync_node = Node.objects.filter(id=sync_node_id).first()
        if sync_node:
            return sync_node
    return None


def fetch_data(url):
    response = requests.get(
        url,
        headers={
            "Authorization": "Bearer " + login.access(),
            "Content-Type": "application/json",
        },
    )
    if response.status_code != 200:
        raise Exception("Sync api call failed")
    return response.json()["data"]


def pull_data_batch_wise(url, callback=None, response_handler=None):
    responses = []
    while True:
        result = fetch_data(url=url)
        if callback:
            with transaction.atomic():
                response = callback(result["results"])
                if response:
                    if response_handler:
                        response_handler(response)
                    else:
                        responses.append(response)
        else:
            if not responses:
                responses = result["results"]
            else:
                responses.extend(result["results"])
        if not result["next"]:
            break
        url = result["next"]
    return responses


def sync_companies(company_id=None):
    url = BASE_URL + "supply-chains/companies/"
    pull_data_batch_wise(url, create_companies, sync_company_members)


def sync_company_members(response_data=None):
    comapnies = response_data[0] + response_data[1]
    if comapnies and isinstance(comapnies, list):
        for company_id in comapnies:
            url = BASE_URL + "supply-chains/company/<company_id>/members/"
            url =  url.replace("<company_id>", company_id)
            pull_data_batch_wise(url, create_company_members)

def migrate_company_and_members():
    sync_companies()