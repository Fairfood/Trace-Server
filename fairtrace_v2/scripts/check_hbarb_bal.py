import requests
from v2.supply_chains.models import BlockchainWallet

BLOCKCHAIN_WALLET_TYPE_HEDERA = 201


def get_bal(account):
    """
    Sample : {'balance': 731.405476, 'asOf': '2022-06-23T09:39:57.207Z'}
    """
    url = f"https://app.dragonglass.me/api/accounts/{account}/balance"
    response = requests.get(url=url)
    print(response.json())
    return response.json()


w_data = []
for wallet in BlockchainWallet.objects.filter(
    wallet_type=BLOCKCHAIN_WALLET_TYPE_HEDERA
):
    if not wallet.account_id:
        continue
    balance = get_bal(wallet.account_id)
    w_data.append(
        {
            "id": wallet.id,
            "account_id": wallet.account_id,
            "balance": balance["balance"],
        }
    )

# [{'id': 5836, 'account_id': '0.0.847202', 'balance': 1.085778},
# {'id': 5822, 'account_id': '0.0.847191', 'balance': 1.089811},
# {'id': 5660, 'account_id': '0.0.762454', 'balance': 1.070713},
# {'id': 5007, 'account_id': '0.0.847265', 'balance': 1.097719},
# {'id': 5001, 'account_id': '0.0.998315', 'balance': 1.089419},
# {'id': 4999, 'account_id': '0.0.998316', 'balance': 1.089419},
# {'id': 4997, 'account_id': '0.0.998318', 'balance': 1.089419},
# {'id': 4996, 'account_id': '0.0.998319', 'balance': 1.089419},
# {'id': 4986, 'account_id': '0.0.998329', 'balance': 1.089837},
# {'id': 4985, 'account_id': '0.0.998330', 'balance': 1.089408},
# {'id': 4984, 'account_id': '0.0.998331', 'balance': 1.089837},
# {'id': 4982, 'account_id': '0.0.998333', 'balance': 1.089408},
# {'id': 4981, 'account_id': '0.0.998334', 'balance': 1.089837},
# {'id': 4837, 'account_id': '0.0.998505', 'balance': 1.72543},
# {'id': 4832, 'account_id': '0.0.998510', 'balance': 1.090035},
# {'id': 4830, 'account_id': '0.0.998514', 'balance': 1.090035},
# {'id': 4824, 'account_id': '0.0.998520', 'balance': 1.090035},
# {'id': 4818, 'account_id': '0.0.998527', 'balance': 1.090035},
# {'id': 4813, 'account_id': '0.0.998533', 'balance': 1.090034},
# {'id': 4812, 'account_id': '0.0.998532', 'balance': 1.090035},
# {'id': 4803, 'account_id': '0.0.998543', 'balance': 1.090034},
# {'id': 4797, 'account_id': '0.0.998602', 'balance': 10.31018},
# {'id': 4792, 'account_id': '0.0.998129', 'balance': 1.291773},
# {'id': 4778, 'account_id': '0.0.998135', 'balance': 1.027319},
# {'id': 4774, 'account_id': '0.0.998134', 'balance': 5.025613},
# {'id': 4767, 'account_id': '0.0.998132', 'balance': 6.009849},
# {'id': 4681, 'account_id': '0.0.615761', 'balance': 761.333865},
# {'id': 4652, 'account_id': '0.0.610575', 'balance': 1.094814},
# {'id': 4651, 'account_id': '0.0.610571', 'balance': 1.093339},
# {'id': 4636, 'account_id': '0.0.604840', 'balance': 1.081289},
# {'id': 4624, 'account_id': '0.0.596206', 'balance': 1.059481},
# {'id': 4622, 'account_id': '0.0.847274', 'balance': 1.096024},
# {'id': 4590, 'account_id': '0.0.847239', 'balance': 1.092184},
# {'id': 4564, 'account_id': '0.0.847173', 'balance': 1.077506},
# {'id': 4532, 'account_id': '0.0.495783', 'balance': 515.927496}]
