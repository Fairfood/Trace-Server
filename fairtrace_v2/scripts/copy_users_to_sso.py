from pprint import pprint
from tqdm import tqdm

from common.backends.sso import SSORequest
from v2.supply_chains.constants import NODE_TYPE_COMPANY
from v2.supply_chains.models import Node
from v2.accounts.models import FairfoodUser


def copy_users():
    ee = []
    for node in Node.objects.filter(type=NODE_TYPE_COMPANY):
        print(node)
        sso = SSORequest()
        t, r = sso.create_node(node.company)
        node.refresh_from_db()
        if not t:
            ee.append(('node', node, r.json()))
        members = node.members.all()

        for user in tqdm(members):
            t, r = sso.create_user(user)
            if not t:
                ee.append(('user', user, r.json()))
            t, r = sso.create_user_node(user, node.company)
            if not t:
                ee.append(('node-user', user, node, r.json()))
    users = FairfoodUser.objects.filter(type__in=[1, 2])
    print('---Admin Users----')
    for user in tqdm(users):
        t, r = sso.create_user(user)
        if not t:
            ee.append(('user', user, r.json()))
    if ee:
        pprint(ee, indent=2)




    

