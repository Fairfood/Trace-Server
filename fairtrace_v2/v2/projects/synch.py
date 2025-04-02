import json
from pprint import pprint
from time import sleep
from django.conf import settings
import requests
from tqdm import tqdm
from v2.supply_chains.models.profile import Farmer
from v2.products.models import Product
from v2.projects.models import NodeCard, Payment, ProjectProduct
from v2.projects.constants import (BASE_PREMIUM, BASE_TRANSACTION, OPTIONS, 
                                   PREMIUM_APPLICABLE_ACTIVITY_BUY, 
                                   PREMIUM_APPLICABLE_ACTIVITY_SELL, 
                                   PREMIUM_TYPE_PER_FARMER, 
                                   PREMIUM_TYPE_PER_KG, 
                                   PREMIUM_TYPE_PER_TRANSACTION, 
                                   PREMIUM_TYPE_PER_UNIT_CURRENCY, 
                                   TRANSACTION_PREMIUM)
from v2.supply_chains.constants import (NODE_MEMBER_TYPE_ADMIN, 
                                        NODE_MEMBER_TYPE_MEMBER, 
                                        NODE_MEMBER_TYPE_VIEWER, 
                                        NODE_TYPE_COMPANY, NODE_TYPE_FARM)
from v2.supply_chains.models.node import Node
from v2.transactions.constants import (CLIENT_APP, VERIFICATION_METHOD_CARD, 
                                       VERIFICATION_METHOD_MANUAL)
from django.utils import timezone
from django.db.models import Q

from v2.transactions.models import ExternalTransaction

BASE_URL = settings.ROOT_URL + '/connect/v1/'
# BASE_URL = "http://127.0.0.1:8003/connect/v1/"

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
VERIFICATION_METHODS = {
    VERIFICATION_METHOD_MANUAL: "CARD",
    VERIFICATION_METHOD_CARD: "INVOICE",

}
PAYMENT_TYPE = {
    BASE_TRANSACTION : 'TRANSACTION',
    BASE_PREMIUM : 'PREMIUM',
    TRANSACTION_PREMIUM: 'TRANSACTION_PREMIUM'
}
FIELDS_TYPES = {
    "bool": "BOOLEAN",
    "string": "TEXT",
    "dropdown": "DROPDOWN",
    "date": "DATE",
    "radio": "RADIO",
    "int": "INTEGER",
    "float": "FLOAT"    
}
FORM_TYPES = {
    "buy_txn_fields": "PRODUCT",
    "farmer_fields": "FARMER",
    "buy_tnx_common_fields": "TRANSACTION"
}
VISIBILITY_TYPES = {
    "buy_txn_fields": "buy_txn",
    "farmer_fields": "add_farmer",
}

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
        self.access_token = ''

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
        
        url = BASE_URL + 'auth/login/'
        data = {'username': self.username, 
                'password': self.password,
                'device_id': self.device_id}
        response = requests.post(url, data=data)
        if response.status_code == 200:
            self.access_token = response.json()['data']['access']
            expires_in = response.json()['data']['expires_in']
            self.expires_on = (timezone.now() 
                              + timezone.timedelta(seconds=expires_in))
            return self.access_token
        raise Exception('Login failed')
    
user_name = settings.CONNECT_USER_NAME
password = settings.CONNECT_PASSWORD
device_id = settings.CONNECT_DEVICE_ID
login = Login(user_name, password, device_id)
    

def companies_from_transaction():
    """
    Retrieve companies associated with external transactions of a specified 
    client type.

    This function filters ExternalTransactions with the client type set to 
    CLIENT_APP, retrieves the destination node IDs from these transactions, 
    and then fetches the corresponding Node instances representing the 
    associated companies.

    Returns:
        QuerySet: A QuerySet of Node instances representing the associated 
        companies.

    Example:
        companies = companies_from_transaction()
        for company in companies:
            print(company.name)  # Access company attributes as needed.
    """
    transactions = ExternalTransaction.objects.filter(client_type=CLIENT_APP)
    node_ids = transactions.values_list('destination_id', flat=True)
    return Node.objects.filter(id__in=node_ids)

def get_project(node):
    return node.participating_projects.first()

def get_buyer(node):
    buyer = node.get_buyers().first()
    if buyer in companies_from_transaction():
        return buyer 
    return None

def add_user(user):
    """
    Adds a user to connect app.

    Args:
        user (User): The user object representing the user to be added.

    Returns:
        tuple: A tuple containing a boolean value indicating the success of
        the operation and the response object returned by the API.

    """
    url = BASE_URL + 'accounts/users/'

    data = {
        "first_name": user.first_name,
        "last_name": user.last_name,
        "email": user.email,
        "password": user.password
    }
    response = requests.post(
        url,
        data=data,
        headers={'Authorization': 'Bearer ' + login.access()}
    )
    if response.status_code != 201:
        raise Exception(f"User Sync failed")
    external_id = response.json()['data']['id']
    return external_id

def get_user(user_email):
    """
    get user with given email from connect.

    Args:

    Returns:
        tuple: A tuple containing a boolean value indicating the success of
        the operation and the response object returned by the API.

    """
    url = BASE_URL + 'accounts/users/'

    response = requests.get(
        url,
        headers={'Authorization': 'Bearer ' + login.access()},
        params={'email': user_email}
    )
    try:
        user_id = response.json()['data']['results'][0]['id']
        return user_id
    except:
        return None

def sync_company(node):
    node = Node.objects.get(id=node.id) # To get updated data
    company = node.company
    if not company:
        return None
    if node.external_id:
        return node
    
    buyer = get_buyer(node)
    buyer = initial_synch(buyer) if buyer else None
    project = get_project(node)
    
    data = {
      "name": company.name,
      "house_name": company.house_name,
      "street": company.street,
      "city": company.city,
      "sub_province": company.sub_province,
      "province": company.province,
      "latitude": company.latitude,
      "longitude": company.longitude,
      "zipcode": company.zipcode,
      "country": company.country,
      "email": company.email,
      "phone": company.phone,
      "description": company.description_basic,
      "buyer": buyer.external_id if buyer else None,
      "currency": "EUR",
      "buy_enabled": True,
      "allow_multiple_login": True
    }
    if project:
        data["buy_enabled"] = project.buy_enabled
        data["sell_enabled"] = project.sell_enabled
        data["quality_correction"] = project.quality_correction
        data["currency"] = project.currency

    url = BASE_URL + 'supply-chains/companies/'
    response = requests.post(
        url, data=data, headers={'Authorization': 'Bearer ' + login.access()})
    if response.status_code == 201:
        node.external_id = response.json()['data']['id']
        app_custom_fields = _create_forms(node)
        node.app_custom_fields = app_custom_fields
        node.save()
        # if not node.image or node.image == "":
        #     return node
        # image_url = BASE_URL + f'supply-chains/companies/{node.external_id}/'
        # sync_node_images(node, image_url)
        return node
    raise Exception(f"{company} --- Sync failed")

def _create_forms(node):
    fields = node.app_custom_fields
    if not fields:
        return None
    fields["forms"] = {}
    url = BASE_URL + 'forms/forms/'
    
    if 'custom_fields' in fields:
        for from_type, form in fields['custom_fields'].items():
            if form:
                data = {
                    "fields": [
                        {
                        "label": f['label']['en'],
                        "label_ind": f['label']['in'],
                        "type": FIELDS_TYPES[f['type']],
                        "key": f['key'],
                        "required": (True 
                                     if f.get('required') == 'true' 
                                     else False),
                        "default_value": f['value'],
                        "options": json.dumps(f.get('options', [])
                            )
                        } for f in form
                    ],
                    "form_type": FORM_TYPES[from_type],
                    "owner": node.external_id,
                    }
                
                visibility_type = VISIBILITY_TYPES.get(from_type, None)
                if ("field_visibility" in fields 
                    and visibility_type in fields["field_visibility"]):

                    data["field_config"] = [
                        {
                            "key": key,
                            "label": key,
                            "visibility": visibility,
                            "required": visibility    
                        } 
                        for key, visibility 
                        in fields[
                            "field_visibility"].get(visibility_type).items()
                    ]
                
                if not data["fields"]:
                    continue
                response = requests.post(
                    url, 
                    data=json.dumps(data),
                    headers={
                        'Authorization': 'Bearer ' + login.access(),
                        'Content-Type': 'application/json'
                        })
                if response.status_code == 201:
                    fields["forms"][
                        FORM_TYPES[from_type]] = response.json()["data"]["id"]
                else:
                    print(data)
                    print(response.json())
    return fields


def sync_node_users(node, user):
    url = BASE_URL + 'supply-chains/company-members/'
    data = {
        "company": node.external_id,
        "type": USER_MEMBER_TYPE[user.type],
        "user": user.external_id
        }
    response = requests.post(
        url, 
        data=json.dumps(data),
        headers={
            'Authorization': 'Bearer ' + login.access(),
            'Content-Type': 'application/json'
            })
    if response.status_code == 201:
        return True
    
def create_products(node):

    supply_chains = node.supply_chains.all()
    for supply_chain in supply_chains:
        products=supply_chain.products.all()

        url = BASE_URL + 'transactions/product-transactions/'

        if products:
            for product in tqdm(products):
                url = BASE_URL + 'catalogs/products/'
                data = {
                    "name": product.name,
                    "description": product.description,
                    }
                response = requests.post(
                    url, 
                    data=json.dumps(data),
                    headers={
                        'Authorization': 'Bearer ' + login.access(),
                        'Content-Type': 'application/json'
                        })
                if response.status_code == 201:
                    product = Product.objects.get(id=product.id)
                    product.external_id = response.json()['data']['id']
                    product.save()

        company_products = [product.external_id for product in products]
        update_company_products(node, company_products)

    
def sync_premiums(node):
    premiums = node.owned_premiums.filter(external_id__isnull=True)
    url = BASE_URL + 'catalogs/premiums/'
    for premium in tqdm(premiums):
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
            "owner": node.external_id,
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
      

        response = requests.post(
            url, 
            data=json.dumps(data),
            headers={
                'Authorization': 'Bearer ' + login.access(),
                'Content-Type': 'application/json'
                })
        if response.status_code == 201:
            premium.external_id = response.json()['data']['id']
            premium.save()
            continue
        raise Exception(f"{premium} --- Sync failed")
        

def sync_node_products(node):
    project = get_project(node)
    project_products = ProjectProduct.objects.filter(project=project)
    url = BASE_URL + 'supply-chains/company-products/'
    for p_product in tqdm(project_products):
        product = p_product.product
        data = {
            "product": {
                "name": product.name,
                "description": product.description,
            },
            "company": node.external_id,
            "premiums": list(p_product.premiums.values_list(
                    'external_id', flat=True)),
            "is_active": p_product.is_active
            }
        if product.external_id:
            data["product_id"] = product.external_id
        response = requests.post(
            url, 
            data=json.dumps(data),
            headers={
                'Authorization': 'Bearer ' + login.access(),
                'Content-Type': 'application/json'
                })
        if response.status_code == 201:
            product.external_id = response.json()['data']['product']['id']
            product.save()
            continue
        raise Exception(f"{product} --- Sync failed")
    
def sync_farmer(node):
    suppliers = node.get_suppliers().filter(type=NODE_TYPE_FARM)
    project = get_project(node)
    project_nodes = project.member_nodes.filter(id__in=suppliers)
    farmers = Farmer.objects.filter(
        id__in=project_nodes, external_id__isnull=True).distinct()
    
    url = BASE_URL + 'supply-chains/farmers/'
    
    for farmer in tqdm(farmers):
        data = {
            "created_on": (
                farmer.created_on.timestamp() 
                if farmer.created_on else None
                ),
            "description": farmer.description_basic,
            "house_name": farmer.house_name,
            "street": farmer.street,
            "city": farmer.city,
            "sub_province": farmer.sub_province,
            "province": farmer.province,
            "latitude": farmer.latitude,
            "longitude": farmer.longitude,
            "zipcode": farmer.zipcode,
            "country": farmer.country,
            "email": farmer.email,
            "phone": farmer.phone,
            "identification_no": farmer.identification_no,
            "reference_number": farmer.id_no,
            "first_name": farmer.first_name,
            "last_name": farmer.last_name,
            "date_of_birth": (farmer.dob.strftime("%Y-%m-%d") 
                              if farmer.dob 
                              else None),
            "gender": farmer.gender,
            "consent_status": "GRANTED",
            "buyer": node.external_id,
            "creator": farmer.creator.external_id if farmer.creator else None,
            }
        submission = _create_farmer_submissions(farmer, node)
        if submission:
            data['submission'] = submission
        response = requests.post(
            url, 
            data=json.dumps(data),
            headers={
                'Authorization': 'Bearer ' + login.access(),
                'Content-Type': 'application/json'
                })
        if response.status_code == 201:
            farmer.external_id = response.json()['data']['id']
            farmer.save()
            # if not farmer.image or farmer.image == "":
            #     continue
            # image_url = BASE_URL + f'supply-chains/farmers/{node.external_id}/'
            # sync_node_images(farmer, image_url)
            continue
        raise Exception(f"{farmer} --- Sync failed")
    
def _create_farmer_submissions(farmer, node):
        if not farmer.extra_fields:
            return []
        node = Node.objects.get(id=node.id) # To get updated data   
        
        custom_fields = farmer.extra_fields.get("custom_fields", {})

        
        if custom_fields:
           
            farmer_fields =  custom_fields.get(
                "farmer_fields", [])
            if farmer_fields:
                submission = {
                    "values": [
                        {
                        "value": field["value"],
                        "field": field["key"],
                        }
                        for field in farmer_fields if field["value"]
                    ],
                    "form": node.app_custom_fields[
                        "forms"]['FARMER'],
                    }
                if submission["values"]:
                    return submission
    
def sync_farmer_cards(node):
    project = node.owned_projects.first()
    if not project:
        return None
    
    nodes = project.member_nodes.values_list('id', flat=True)
    cards = NodeCard.objects.filter(node_id__in=nodes, 
                                    external_id__isnull=True)

    url = BASE_URL + 'supply-chains/entity-cards/'
    
    for card in tqdm(cards):
        if card.external_id or not card.node.external_id:
            continue
        data = {
            "card": {
                "card_id": card.card_id,
                "display_id": card.fairid,
            },
            "entity": card.node.external_id,
            }
        response = requests.post(
            url, 
            data=json.dumps(data),
            headers={
                'Authorization': 'Bearer ' + login.access(),
                'Content-Type': 'application/json'
                })
        if response.status_code == 201:
            card.external_id = response.json()['data']['card']['id']
            card.save()
            continue
        raise Exception(f"{card} Sync failed")
    
def sync_unassigned_cards():
    print("Innitial unassigned card sync...")
    cards = NodeCard.objects.filter(node=None, external_id__isnull=True)
    url = BASE_URL + 'catalogs/connect-cards/'
    
    for card in tqdm(cards):
        if card.external_id:
            continue
        data = {
            "card_id": card.card_id,
            "display_id": card.fairid,
            }
        response = requests.post(
            url, 
            data=json.dumps(data),
            headers={
                'Authorization': 'Bearer ' + login.access(),
                'Content-Type': 'application/json'
                })
        if response.status_code == 201:
            card.external_id = response.json()['data']['id']
            card.save()
            continue
        raise Exception(f"{card} ---  Sync failed")



def update_company_products(node, products):
    data = {
      "product_id": products,
      "company": node.external_id,
    }
    url = BASE_URL + f'supply-chains/company-products/'
    response = requests.post(
        url, data=data, 
        headers={'Authorization': 'Bearer ' + login.access()})
    if response.status_code != 201:
        raise Exception(f"Company product update failed")

def sync_products(node):

    transactions = ExternalTransaction.objects.filter(external_id__isnull=True)
    transactions = transactions.filter(destination=node).order_by('id')
    url = BASE_URL + 'transactions/product-transactions/'

    products = {transaction.product for transaction in 
                transactions if transaction.product.external_id is None}
    if products:
        for product in tqdm(products):
            url = BASE_URL + 'catalogs/products/'
            data = {
                "name": product.name,
                "description": product.description,
                }
            response = requests.post(
                url, 
                data=json.dumps(data),
                headers={
                    'Authorization': 'Bearer ' + login.access(),
                    'Content-Type': 'application/json'
                    })
            if response.status_code == 201:
                product = Product.objects.get(id=product.id)
                product.external_id = response.json()['data']['id']
                product.save()
        company_products = {transaction.product for transaction in transactions}
        products = [product.external_id for product in company_products]

        # for product in company_products:
        update_company_products(node, products)


def sync_transactions(node):
    transactions = ExternalTransaction.objects.filter(external_id__isnull=True)
    transactions = transactions.filter(destination=node).order_by('id')
    sources = Node.objects.filter(
        outgoing_transactions__in=transactions, 
        type=NODE_TYPE_COMPANY).distinct()
        
    if not sources.exists():
        transactions = transactions.filter(client_type=CLIENT_APP)
    for source in sources:
        print(f"\nSyncing --- {source}...")
        sync_all_against_node(source)
        print(f"Syncing completed --- {source}.\n\n")
    
    url = BASE_URL + 'transactions/product-transactions/'
    
    project = node.owned_projects.first()
    
    for transaction in tqdm(transactions):
        if not transaction.product.external_id:
            sync_products(transaction.product)
        if (transaction.source.type == NODE_TYPE_FARM 
            and not transaction.source.external_id):
            continue
        data = {
                "created_on": (
                    transaction.created_on.timestamp() 
                    if transaction.created_on else None),
                "transaction_payments": [
                    {
                    "payment_type": PAYMENT_TYPE[payment.payment_type],
                    "amount": payment.amount,
                    "premium": payment.premium.external_id,
                    "selected_option": (
                        payment.selected_option.name 
                        if payment.selected_option else None),
                    }
                    for payment in transaction.premium_paid
                ],
                "amount": transaction.price if transaction.price else 0.0,
                "currency": (transaction.currency or 
                             project.currency if project else "EUR"),
                "number": transaction.number,
                "date": transaction.date.timestamp(),
                "invoice_number": transaction.invoice_number,
                "verification_latitude": transaction.verification_latitude,
                "verification_longitude": transaction.verification_longitude,
                "method": VERIFICATION_METHODS[
                    transaction.verification_method],
                "quality_correction": transaction.quality_correction,
                "quantity": float(transaction.source_quantity),
                "creator": (transaction.creator.external_id 
                            if transaction.creator else None),
                "source": transaction.source.external_id,
                "destination": transaction.destination.external_id,
                "card": (
                    transaction.card.external_id 
                    if transaction.card else None),
                "product": transaction.product.external_id,
                }
        if transaction.parents.exists():
            parents = []
            for parent in transaction.parents.all():
                if parent.is_external:
                    parents.append(parent.externaltransaction.external_id)
                else:
                    parents.extend(list(parent.parents.values_list(
                            'externaltransaction__external_id', flat=True)))
            parents = list(set(parents))
            try:
                parents.remove(None)
            except ValueError:
                pass
            data['parents'] = parents
        
        submissions = _create_submissions(transaction, node)
        if submissions:
            data['submissions'] = submissions
        
        response = requests.post(
            url, 
            data=json.dumps(data),
            headers={
                'Authorization': 'Bearer ' + login.access(),
                'Content-Type': 'application/json'
                })
        if response.status_code == 201:
            transaction.external_id = response.json()['data']['id']
            transaction.save()
            continue
        raise Exception(f"{transaction} --- Sync failed")
    
def _create_submissions(transaction, node):
        submissions = []
        if not transaction.extra_fields:
            return []
        node = Node.objects.get(id=node.id) # To get updated data   
        
        custom_fields = transaction.extra_fields.get("custom_fields", {})

        
        if custom_fields:
           
            buy_tnx_common_fields =  custom_fields.get(
                "buy_tnx_common_fields", [])
            if buy_tnx_common_fields:
                submission = {
                    "values": [
                        {
                        "value": field["value"],
                        "field": field["key"],
                        }
                        for field in buy_tnx_common_fields if field["value"]
                    ],
                    "form": node.app_custom_fields[
                        "forms"]['TRANSACTION'],
                    }
                if submission["values"]:
                    submissions.append(submission)
            
            buy_tnx_fields = custom_fields.get("buy_txn_fields", [])
            if buy_tnx_fields:
                submission = {
                    "values": [
                        {
                        "value": field["value"],
                        "field": field["key"],
                        }
                        for field in buy_tnx_fields if field["value"]
                    ],
                    "form": node.app_custom_fields[
                        "forms"]['PRODUCT'],
                    "product": transaction.product.external_id
                    }
                if submission["values"]:
                    submissions.append(submission)
        return submissions

def sync_node_images(node, url):
    image_response = requests.get(node.image.url)
    if image_response.status_code != 200:
        return None

    image = image_response.content
    name = node.image.name.split('/')[-1]
    if "." not in name:
        name = name + ".png"
    
    files = {'image': (name, image)}

    # url = BASE_URL + f'supply-chains/farmers/{farmer.external_id}/'
    response = requests.patch(
        url, 
        files=files,
        headers={
            'Authorization': 'Bearer ' + login.access(),
            })
    if response.status_code != 200:
        raise Exception(f"{node} image upload --- Sync failed")
    else:
        print(f"{node} - {node.external_id} image uploaded")

def sync_all_node_images():
    print("Syncing images...")
    nodes = Node.objects.exclude(
        Q(image__isnull=True) | Q(image="" ) | Q(external_id__isnull=True))
    for node in tqdm(nodes):
        if node.type == NODE_TYPE_FARM:
            url = BASE_URL + f'supply-chains/farmers/{node.external_id}/'
        else:
            url = BASE_URL + f'supply-chains/companies/{node.external_id}/'
        sync_node_images(node, url)

def sync_transaction_invoice(transaction, url):
    invoice_response = requests.get(transaction.invoice.url)
    if invoice_response.status_code != 200:
        return None

    invoice = invoice_response.content
    name = transaction.invoice.name.split('/')[-1]
    if "." not in name:
        name = name + ".png"
    
    files = {'invoice': (name, invoice)}

    # url = BASE_URL + f'supply-chains/farmers/{farmer.external_id}/'
    response = requests.patch(
        url, 
        files=files,
        headers={
            'Authorization': 'Bearer ' + login.access(),
            })
    if response.status_code != 200:
        raise Exception(f"{transaction} file upload --- Sync failed")
    else:
        print(f"{transaction} - {transaction.external_id} file uploaded")

def sync_all_transaction_invoices():
    print("Syncing invoices...")
    transactions = ExternalTransaction.objects.exclude(
        Q(invoice__isnull=True) | Q(invoice="" ) | Q(external_id__isnull=True))
    for transaction in tqdm(transactions):
        url = (
            BASE_URL + 
            f'transactions/product-transactions/' 
            f'{transaction.external_id}/invoice/')
        sync_transaction_invoice(transaction, url)

def sync_payments(node):
    payments = Payment.objects.filter(Q(source=node) | Q(destination=node))
    payments = payments.filter(
        payment_type=BASE_PREMIUM, external_id__isnull=True).order_by('id')
    url = BASE_URL + 'transactions/payment-transactions/'
    
    for payment in tqdm(payments):
        data = {
            "created_on": payment.created_on.timestamp(),
            "date": payment.created_on.timestamp(),
            "invoice_number": payment.invoice_number,
            "verification_latitude": payment.verification_latitude,
            "verification_longitude": payment.verification_longitude,
            "method": (
                "NONE"
                if payment.method == "NOT_VERIFIED" 
                else payment.method),
            "payment_type": PAYMENT_TYPE[payment.payment_type],
            "amount": payment.amount,
            "creator": (
                payment.creator.external_id 
                if payment.creator else None),
            "source": payment.source.external_id,
            "destination": payment.destination.external_id,
            "card": payment.card.external_id if payment.card else None,
            "premium": payment.premium.external_id,
            "currency": payment.currency,
            }
        response = requests.post(
            url, 
            data=json.dumps(data),
            headers={
                'Authorization': 'Bearer ' + login.access(),
                'Content-Type': 'application/json'
                })
        if response.status_code == 201:
            payment.external_id = response.json()['data']['id']
            payment.save()
            continue
        raise Exception(f"{payment} Sync failed")
    
def initial_synch(node):
    print(f"\nSyncing --- Company")
    sync_company(node)
    node = Node.objects.get(id=node.id) # To get updated data
    print(f"\nSyncing --- Company Users")
    sync_node_users(node)
    print(f"\nSyncing --- Company Premiums")
    sync_premiums(node)
    print(f"\nSyncing --- Company Products")
    sync_node_products(node)
    print(f"\nSyncing --- Company Farmers")
    sync_farmer(node)
    print(f"\nSyncing --- Company Farmer Cards")
    sync_farmer_cards(node)
    return node

def sync_all_against_node(node):
    sleep(2)
    print(f"\nSyncing --- {node}...")
    print(f"Initial Syncing")
    node = initial_synch(node)
    print(f"\nSyncing --- Company Transactions")
    sync_transactions(node)
    print(f"\nSyncing --- Company Payments")
    sync_payments(node)
    print(f"Syncing completed --- {node}.\n\n")
    
def start(node=None):
    sync_unassigned_cards()
    if node:
        sync_all_against_node(node)
    else:
        companies = companies_from_transaction()
        for company in companies:
            sync_all_against_node(company)
