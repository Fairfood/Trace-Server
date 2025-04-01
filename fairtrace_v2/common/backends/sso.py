import base64
import json

import requests
from django.conf import settings
from django.db import transaction
from django.utils import timezone
from v2.supply_chains.models.node import Node

NOT_AVAILABLE = 'Not Available'

BASE_URL = settings.TRACE_OAUTH2_BASE_URL

def get_user_type(user_type):
    types = {
        1: "USER_NODE",
        2: "MANAGER",
        3: "ADMIN"
    }
    return types[user_type]

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

    CLIENT_ID = settings.TRACE_OAUTH2_CLIENT_ID
    CLIENT_SECRET = settings.TRACE_OAUTH2_CLIENT_SECRET
    
    access_token = ''
    expires_on = None


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
        
        url = BASE_URL + 'token/'
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
    

class SSORequest:
    """
    SSO request handler
    """
    login = Login()

    def create_user(self, user, set_default_password=False):
        """
        Creates a user in the SSO system.

        Args:
            user: An instance of the User class representing the user to be 
            created.

        Returns:
            A tuple containing a boolean value indicating the success of the 
            operation and a response object.

        Raises:
            None.
        """
        if user.sso_user_id:
            return True, {}
        url = BASE_URL + 'api/users/'
        data = self.user_post_data(user, set_default_password)
        response = requests.post(
            url,
            data=json.dumps(data),
            headers=self.headers
        )
        if response.status_code == 201:
            self.update_user_data(response.json()["data"], user)
            return True, response
        else:
            return False, response

    def update_user(self, user):
        """
        Updates the user information in the SSO backend.

        Args:
            user: The user object containing the updated information.

        Returns:
            A tuple containing a boolean value indicating whether the update 
            was successful and the response object.

        Raises:
            None.
        """
        url = BASE_URL + f'api/users/{user.sso_user_id}/'
        data = self.user_post_data(user)
        if user.updated_email:
            data["email"] = user.updated_email
        
        data.pop("password", None)
        data.pop("email_verified", None)
        response = requests.put(
            url,
            data=json.dumps(data),
            headers=self.headers
        )
        if response.status_code == 200:
            return True, response
        else:
            return False, response
        
    def deactivate_user(self, user):
        """
        deactivate the user information in the SSO backend.

        Args:
            user: The user object containing the updated information.

        Returns:
            A tuple containing a boolean value indicating whether the update 
            was successful and the response object.

        Raises:
            None.
        """
        url = BASE_URL + f'api/users/{user.sso_user_id}/'
        data = {"is_active": False}
        response = requests.patch(
            url,
            data=json.dumps(data),
            headers=self.headers
        )
        if response.status_code == 200:
            return True, response
        else:
            return False, response


    def create_node(self, company, user=None):
        """
        Creates a node for the given company.

        Args:
            company (Company): The company object for which the node needs to 
            be created.

        Returns:
            tuple: A tuple containing the updated company data and the response 
            object.
        """
        if company.sso_id and company.sso_id != NOT_AVAILABLE:
            return True, {}
        
        url = BASE_URL + f'api/nodes/companies/'
        data = {
            "name": company.name,
            "description": company.description_basic or company.name,
        }

        response = requests.post(
            url,
            data=json.dumps(data),
            headers=self.headers
        )
        if response.status_code != 201:
            return False, response
        if user:
            transaction.on_commit(
                lambda: self.update_company_data(response, company, user))
        return True, response

    def update_node(self, company):
        """
        Updates a node in the SSO backend with the provided company 
        information.

        Args:
            company (Company): The company object containing the updated 
            information.

        Returns:
            tuple: A tuple containing a boolean value indicating the success 
            of the update and the updated company data.

        """
        url = BASE_URL + f'api/nodes/companies/{company.sso_id}/'
        data = {
            "name": company.name,
            "description": company.description_basic,
        }
        response = requests.put(
            url,
            data=json.dumps(data),
            headers=self.headers
        )
        if response.status_code != 200:
            return False, data
        return True, data
        

    def create_user_node(self, user, company):
        """
        Creates a user node by sending a POST request to the specified URL.

        Args:
            user (User): The user object.
            node (Node): The node object.

        Returns:
            tuple: A tuple containing a boolean value indicating the success of 
            the request and the response object.

        """
        url = BASE_URL + 'api/nodes/user-nodes/'
        data = {
            "user": user.sso_user_id,
            "node": company.sso_id
        }
        response = requests.post(
            url,
            data=json.dumps(data),
            headers=self.headers
        )
        if response.status_code != 201:
            return False, response
        return True, response

    def get_user_node(self, user, company):
        """
        Get a user node by sending a GET request to the specified URL.

        Args:
            user (User): The user object.
            node (Node): The node object.

        Returns:
            bool: True if user node exists. else False.

        """
        url = BASE_URL + 'api/nodes/user-nodes/'
        
        params = {
            "user": user.sso_user_id,
            "node": company.sso_id
        }
        response = requests.get(
            url,
            headers=self.headers,
            params=params
        )
        if response.status_code != 200:
            return False, response
        return True, response  
      
    def add_user_to_navigate(self, user, company, enable_navigate):
        """
        Adds a user to navigate a specific node.

        Args:
            user (User): The user object representing the user to be added.
            node (Node): The node object representing the node to be navigated.

        Returns:
            tuple: A tuple containing a boolean value indicating the success of
            the operation and the response object returned by the API.

        """
        url = BASE_URL + 'api/nodes/user-nodes/add-to-navigate/'
        data = {
            "user": user.sso_user_id,
            "node": company.sso_id, 
            "enable_navigate": enable_navigate
        }
        response = requests.post(
            url,
            data=json.dumps(data),
            headers=self.headers
        )
        if response.status_code != 201:
            return False, response
        return True, response

    def add_user_to_connect(self, user, company, enable_connect):
        """
        Adds a user to connect a specific node.

        Args:
            user (User): The user object representing the user to be added.
            node (Node): The node object representing the node to be connectd.

        Returns:
            tuple: A tuple containing a boolean value indicating the success of
            the operation and the response object returned by the API.

        """
        url = BASE_URL + 'api/nodes/user-nodes/add-to-connect/'
        data = {
            "user": user.sso_user_id,
            "node": company.sso_id,
            "enable_connect": enable_connect
        }
        response = requests.post(
            url,
            data=json.dumps(data),
            headers=self.headers
        )
        if response.status_code != 201:
            return False, response
        return True, response


    def user_post_data(self, user, set_default_password=False):
        """
        Prepare the user data to be sent in a POST request.

        Args:
            user: The user object containing the user's information.

        Returns:
            A dictionary containing the user data to be sent in the POST 
            request.

        """
        data = {
            "email": user.email,
            "first_name": user.first_name,
            "last_name": user.last_name,
            "date_joined": int(user.date_joined.timestamp()),
            "user_type": get_user_type(user.type),
            "email_verified": user.email_verified,
        }

        if user.password:
            data["password"] = user.password
        if set_default_password:
            data["password"] = settings.SYNC_USER_DEFAULT_PASSWORD
        return data

    def update_company_data(self, response, company, user):
        """
        Updates the company data based on the response from the SSO API.

        Args:
            response (Response): The response object from the SSO API.
            company (Company): The company object to be updated.

        Returns:
            bool: True if the company data was successfully updated, False 
            otherwise.
        """
        if response.status_code in [201, 200]:
            content = response.json()["data"]
            node_filter = Node.objects.filter(pk=company.pk)
            node_filter.update(sso_id=content["id"])
            company.refresh_from_db()
            self.create_user_node(
                user, company)  
            return True
        else:
            return False
        
    def update_user_data(self, data, user):
        """
        Updates the user data with the provided SSO data.

        Args:
            data (dict): A dictionary containing the SSO data.
            user (User): The user object to update.

        Returns:
            None
        """
        sso_user_id = data["id"]
        user.sso_user_id = sso_user_id
        user.save()
    
    @property
    def headers(self):
        """
        Returns the headers required for API requests.

        Returns:
            dict: The headers dictionary.
        """
        return {
            "Authorization": "Bearer {0}".format(self.login.access()),
            "Content-Type": "application/json"
        }



