import requests
from django.conf import settings
from .constants import TESTNET_URL, MAINNET_URL


def get_hedera_balance_hbar(account_id: str) -> float:
    """
    Fetches the HBAR balance of a given Hedera account using the Mirror Node 
    REST API.

    Args:
        account_id (str): The Hedera account ID (e.g., "0.0.1234").
    Returns:
        float: Balance in HBAR, or -1.0 if the request fails.
    """
    base_url = TESTNET_URL
    if settings.ENVIRONMENT == 'production':
        base_url = MAINNET_URL

    url = f"{base_url}/api/v1/accounts/{account_id}"

    try:
        response = requests.get(url)
        response.raise_for_status()
        data = response.json()
        tinybars = data["balance"]["balance"]
        hbars = tinybars / 100000000  # Convert tinybars to HBAR
        return hbars
    except Exception as e:
        print(f"Error fetching balance: {e}")
        return -1.0
