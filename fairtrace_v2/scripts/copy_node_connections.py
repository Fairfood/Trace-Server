"""Script for copy the connections of node with supply chain."""
from django.db import transaction
from django.db.models import Q
from v2.accounts.constants import VTOKEN_STATUS_UNUSED
from v2.accounts.constants import VTOKEN_TYPE_INVITE
from v2.accounts.models import ValidationToken
from v2.dashboard.models import CITheme
from v2.dashboard.models import DashboardTheme
from v2.dashboard.models import NodeStats
from v2.supply_chains import constants
from v2.supply_chains.models import Company
from v2.supply_chains.models import Connection
from v2.supply_chains.models import ConnectionTag
from v2.supply_chains.models import Farmer
from v2.supply_chains.models import Invitation
from v2.supply_chains.models import Node
from v2.supply_chains.models import NodeFeatures
from v2.supply_chains.models import NodeMember
from v2.supply_chains.models import NodeSupplyChain
from v2.supply_chains.models import SupplyChain
from v2.supply_chains.models.graph import ConnectionGraphModel
from v2.supply_chains.models.graph import NodeGraphModel


def create_graph_node(node):
    """To perform function create_graph_node."""
    graph_node = NodeGraphModel(
        ft_node_id=node.id,
        ft_node_idencode=node.idencode,
        type=node.type,
        full_name=node.full_name,
    )
    graph_node.save()
    print("graph_node____________after", graph_node.uid)
    node.graph_uid = graph_node.uid
    node.save()
    managers = [
        {"id": i.idencode, "name": i.full_name} for i in node.managers.all()
    ]
    graph_node.full_name = node.full_name
    graph_node.managers = managers
    graph_node.save()


def create_reload_graph_node(node):
    """To perform function create_reload_graph_node."""
    transaction.on_commit(lambda: create_graph_node(node))
    transaction.on_commit(lambda: node.update_cache())


def create_conn_graph(conn):
    """To perform function create_conn_graph."""
    dist = conn.distance
    sc_id = conn.supply_chain.id
    graph_node = ConnectionGraphModel(connection_id=conn.id)
    graph_node.status = conn.status
    graph_node.active = conn.active
    graph_node.distance = dist
    graph_node.supply_chain_id = sc_id
    graph_node.email_sent = conn.invitation.email_sent
    graph_node.labels = [
        {"id": i.id, "name": i.name} for i in conn.labels.all()
    ]
    graph_node.save()
    conn.graph_uid = graph_node.uid
    conn.save()
    if not conn.buyer.graph_node:
        conn.buyer.create_or_update_graph_node()
    rel1 = graph_node.buyer.connect(conn.buyer.graph_node)
    rel1.supply_chain_id = sc_id
    rel1.save()

    if not conn.supplier.graph_node:
        conn.supplier.create_or_update_graph_node()
    rel2 = graph_node.supplier.connect(conn.supplier.graph_node)
    rel2.supply_chain_id = sc_id
    rel2.save()
    return graph_node, True


def create_connection_graph(conn):
    """To perform function create_connection_graph."""
    transaction.on_commit(lambda: create_conn_graph(conn))


def copy_nsc(
    node_id, company_new, supply_chain_id, source_sc_id, conn_node=None
):
    """To copy node supply-chain."""
    nsc = NodeSupplyChain.objects.filter(
        node__id=node_id, supply_chain__id=source_sc_id
    )
    target_sc = SupplyChain.objects.get(id=supply_chain_id)
    for nodesc in nsc:
        if NodeSupplyChain.objects.filter(
            node=company_new,
            supply_chain=target_sc,
            primary_operation=nodesc.primary_operation,
        ).exists():
            return False
        nodesc.pk = None
        nodesc.id = None
        nodesc.node = company_new
        nodesc.supply_chain = target_sc
        nodesc.save()
        print("nodesc@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@", nodesc)
    if not nsc:
        if conn_node:
            nsc_obj = NodeSupplyChain.objects.filter(node=conn_node).first()
            print("nsc_obj!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!try!!!!!", nsc_obj)
        else:
            nsc_obj = NodeSupplyChain.objects.filter(node__id=node_id).first()
            print("nsc_obj!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!! except!!!!", nsc_obj)
        NodeSupplyChain.objects.create(
            node=company_new,
            supply_chain=target_sc,
            primary_operation=nsc_obj.primary_operation,
        )
    return True


def copy_node_member(node_id, company_new):
    """To perform function copy_node_member."""
    node_member = NodeMember.objects.filter(node__id=node_id)
    for member in node_member:
        try:
            vtoken = ValidationToken.objects.create(
                user=member.user,
                status=VTOKEN_STATUS_UNUSED,
                type=VTOKEN_TYPE_INVITE,
                creator=member.user,
            )
            member.pk = None
            member.id = None
            member.vtoken = vtoken
            member.node = company_new
            try:
                member.theme = company_new.dashboard_theme
            except Exception:
                pass
            member.save()
        except Exception:
            pass


def copy_theme(node_id, company_new, name, source_sc_id, supply_chain_id):
    """To perform function copy_theme."""
    nodeft, created = NodeFeatures.objects.get_or_create(node=company_new)
    if created:
        nodeft.dashboard_theming = True
        nodeft.consumer_interface_theming = True
        nodeft.save()
    ci_theme = CITheme.objects.filter(
        node__id=node_id, supply_chains__id=source_sc_id
    )
    print("ci_theme@@@@@@@@@@@@@@@@@@", ci_theme)
    for theme in ci_theme:
        if not CITheme.objects.filter(name=theme.name + name).exists():
            theme.pk = None
            theme.id = None
            theme.name = theme.name + name
            theme.node = company_new
            theme.save()
            theme.supply_chains.add(
                SupplyChain.objects.get(id=supply_chain_id)
            )
            theme.save()
    dash_themes = DashboardTheme.objects.filter(node__id=node_id)
    for dash_theme in dash_themes:
        if not DashboardTheme.objects.filter(node=company_new).exists():
            dash_theme.pk = None
            dash_theme.id = None
            dash_theme.node = company_new
            dash_theme.save()
        print("dash_theme@@@@@@@@@@@@@@@@@@@@@@@@@@@@@", dash_theme)


def copy_company(node_id, name):
    """To perform function copy_company."""
    company_new = Company.objects.get(id=node_id)
    company_new.pk = None
    company_new.id = None
    company_new.name = company_new.name + name
    company_new.blockchain_account = None
    company_new.save()
    stats, created = NodeStats.objects.get_or_create(node=company_new)
    stats.outdate(outdated_by=company_new)
    create_reload_graph_node(company_new)
    print("company_____________________", company_new.id, company_new)
    return company_new


def copy_other_datas(
    node_id, company_new, supply_chain_id, name, source_sc_id, conn_node=None
):
    """Copy other data."""
    copy_nsc(node_id, company_new, supply_chain_id, source_sc_id, conn_node)
    copy_theme(node_id, company_new, name, source_sc_id, supply_chain_id)


def create_new_node(conn_node, name, supply_chain_id, source_sc_id):
    """To perform function create_new_node."""
    if conn_node.type == constants.NODE_TYPE_COMPANY:
        conn_node_new = Company.objects.get(id=conn_node.id)
        try:
            conn_node_new = Company.objects.get(name=conn_node_new.name + name)
            print("conn_node_new@@@@@@@@@@@@@!!!!!!!!!!!!!!!!!", conn_node_new)
        except Exception:
            print("except())))))))))))))))))))))))))))))))))))))))))))")
            conn_node_new.pk = None
            conn_node_new.id = None
            conn_node_new.name = conn_node_new.name + name
            conn_node_new.blockchain_account = None
            conn_node_new.save()
            print(
                "conn_node_new@@@@@@@!!!!!!!!!!!!!!!!! except", conn_node_new
            )

    elif conn_node.type == constants.NODE_TYPE_FARM:
        conn_node_new = Farmer.objects.get(id=conn_node.id)
        try:
            conn_node_new = Company.objects.get(
                last_name=conn_node_new.last_name + name
            )
            print("conn_node_new@@@@@@@@@!!!!!!!!!!!!!!!!!!!!", conn_node_new)
        except Exception:
            conn_node_new.pk = None
            conn_node_new.id = None
            conn_node_new.last_name = conn_node_new.last_name + name
            conn_node_new.blockchain_account = None
            conn_node_new.save()
            print("conn_node_new@@@@@@@@@@@@@!!!!!!!!!! except", conn_node_new)
    stats, created = NodeStats.objects.get_or_create(node=conn_node_new)
    stats.outdate(outdated_by=conn_node_new)
    create_reload_graph_node(conn_node_new)
    print("conn_node_new-------------------@@@@@@@@", conn_node_new)
    copy_other_datas(
        conn_node.id,
        conn_node_new,
        supply_chain_id,
        name,
        source_sc_id,
        conn_node,
    )
    return conn_node_new


def copy_connection_node(con, supply_chain_id, name, conn_node, source_sc_id):
    """To perform function copy_connection_node."""
    print("con----------------------------^^^^^", con)
    invitation_new = Invitation.objects.get(connection__id=con.id)
    invitation_new.pk = None
    invitation_new.id = None
    invitation_new.connection = None
    invitation_new.save()
    try:
        if invitation_new.inviter.type == constants.NODE_TYPE_COMPANY:
            inviter = Company.objects.get(
                name=invitation_new.inviter.full_name + name
            )
        elif invitation_new.inviter.type == constants.NODE_TYPE_FARM:
            inviter = Farmer.objects.get(
                name=invitation_new.inviter.full_name + name
            )
        invitation_new.inviter = inviter
        invitation_new.invitee = None
    except Exception:
        try:
            if invitation_new.invitee.type == constants.NODE_TYPE_COMPANY:
                invitee = Company.objects.get(
                    name=invitation_new.invitee.full_name + name
                )
            elif invitation_new.invitee.type == constants.NODE_TYPE_FARM:
                invitee = Farmer.objects.get(
                    name=invitation_new.invitee.full_name + name
                )
            invitation_new.invitee = invitee
            invitation_new.inviter = None
        except Exception:
            inviter = create_new_node(
                invitation_new.inviter, name, supply_chain_id, source_sc_id
            )
            invitation_new.inviter = inviter
            invitation_new.invitee = None
    invitation_new.save()
    conn_node_new = create_new_node(
        conn_node, name, supply_chain_id, source_sc_id
    )

    if not invitation_new.invitee:
        print("if !!!!!!!!!!!!!!!!!!!!!!!", conn_node_new)
        invitation_new.invitee = conn_node_new
    else:
        print("else!!!!!!!!!!!!!!!!!!!!!!!", conn_node_new)
        invitation_new.inviter = conn_node_new
    invitation_new.save()
    return conn_node_new, invitation_new


def create_supplier_connection(
    con, suppliers, target_sc_id, name, source_sc_id
):
    """To create supplier connection."""
    print("con.buyer!!!!!!!!!!!!!!!!!!!!!!!!!!!", con.buyer)
    supplier_new, invitation_new = copy_connection_node(
        con, target_sc_id, name, con.supplier, source_sc_id
    )
    if not supplier_new:
        return False, False

    con.pk = None
    con.id = None
    con.buyer = suppliers
    con.supplier = supplier_new
    con.invitation = invitation_new
    con.supply_chain = SupplyChain.objects.get(id=target_sc_id)
    con.save()
    print("con_________________@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@after", con)
    create_connection_graph(con)
    invitation_new.connection = con
    invitation_new.save()
    print("conQQQQQQQQQQQQQQQQQQQQQQQQQQQQQQQQQQQQQ", con)
    print("con.buyerQQQQQQQQQQQQQQQQQQQQQQQQQQQQQQQ", con.buyer)
    try:
        inviter_node = Connection.objects.get(supplier=con.buyer).buyer
        print("suppliersQQQQQQQQQQQQQQQQQQQQQQ", inviter_node)
    except Exception:
        print("except!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!", con.buyer)
        inviter_node = con.buyer
    if con.buyer.id != inviter_node.id:
        con.tag_buyers([inviter_node])
    print("supplier_new+++++++++++++++++++++++++++++++++++++", supplier_new)
    return supplier_new, invitation_new


def create_buyer_connection(con, buyers, target_sc_id, name, source_sc_id):
    """To perform function create_buyer_connection."""
    buyer_new, invitation_new = copy_connection_node(
        con, target_sc_id, name, con.buyer, source_sc_id
    )
    if not buyer_new:
        return False, False
    con.pk = None
    con.id = None
    con.buyer = buyer_new
    con.supplier = buyers
    con.invitation = invitation_new
    con.supply_chain = SupplyChain.objects.get(id=target_sc_id)
    con.save()
    create_connection_graph(con)
    print("con_________________@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@after", con)
    invitation_new.connection = con
    invitation_new.save()
    # inviter_node = Node.objects.get(id=invitation_new.inviter.id)
    try:
        inviter_node = Connection.objects.get(buyer=con.supplier).supplier
        print("suppliersQQQQQQQQQQQQQQQQQQQQQQ", inviter_node)
    except Exception:
        print(
            "except!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!supplier", con.supplier
        )
        inviter_node = con.supplier
    if con.supplier.id != inviter_node.id:
        con.tag_suppliers([inviter_node])
    return buyer_new, invitation_new


def copy_supplier_connections(
    node,
    company_new,
    source_sc_id,
    name,
    target_sc_id,
    suppliers=None,
    supplier_old=None,
    buyer_old=None,
):
    """To copy supplier connections."""
    node_old = Node.objects.get(id=node)
    if suppliers:
        query = Q(buyer__id=supplier_old.id)
        query &= Q(supply_chain__id=source_sc_id)
        sup_cons = Connection.objects.filter(query)
        supplier_node = suppliers
        buy_con = Connection.objects.filter(
            supplier__id=supplier_old.id,
            supply_chain__id=source_sc_id,
            buyer_id=buyer_old.id,
        ).first()
        connections = Connection.objects.none()
        for sup_con in sup_cons:
            if ConnectionTag.objects.filter(
                buyer_connection=buy_con, supplier_connection=sup_con
            ).exists():
                connections |= Connection.objects.filter(id=sup_con.id)
        print("connections^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^1if", connections)
    else:
        query = Q(buyer__id=node)
        query &= Q(supply_chain__id=source_sc_id)
        sup_cons = Connection.objects.filter(query)
        supplier_node = company_new
        connections = sup_cons
        if supplier_old:
            buy_con = Connection.objects.filter(
                supplier__id=supplier_old.id,
                supply_chain__id=source_sc_id,
                buyer_id=node_old,
            ).first()
            connections = Connection.objects.none()
            for sup_con in sup_cons:
                if ConnectionTag.objects.filter(
                    buyer_connection=buy_con, supplier_connection=sup_con
                ).exists():
                    connections |= Connection.objects.filter(id=sup_con.id)

        print(
            "connections@@@@else!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!", connections
        )
    for cons in connections:
        supplier_old = cons.supplier
        buyer_old = cons.buyer
        supplier_new, invitation_new = create_supplier_connection(
            cons, supplier_node, target_sc_id, name, source_sc_id
        )
        if not supplier_new:
            continue
        copy_supplier_connections(
            node,
            company_new,
            source_sc_id,
            name,
            target_sc_id,
            supplier_new,
            supplier_old,
            buyer_old,
        )


def copy_buyer_connections(
    node,
    company_new,
    source_sc_id,
    name,
    target_sc_id,
    buyers=None,
    buyer_old=None,
    supplier_old=None,
):
    """To copy buyer connections."""
    node_old = Node.objects.get(id=node)
    if buyers:
        query = Q(supplier__id=buyer_old.id)
        query &= Q(supply_chain__id=source_sc_id)
        buy_cons = Connection.objects.filter(query)
        buyer_node = buyers
        sup_con = Connection.objects.filter(
            buyer__id=buyer_old.id,
            supply_chain__id=source_sc_id,
            supplier_id=supplier_old.id,
        ).first()
        connections = Connection.objects.none()
        for buy_con in buy_cons:
            if ConnectionTag.objects.filter(
                supplier_connection=sup_con, buyer_connection=buy_con
            ).exists():
                connections |= Connection.objects.filter(id=buy_con.id)
    else:
        query = Q(supplier__id=node)
        query &= Q(supply_chain__id=source_sc_id)
        buy_cons = Connection.objects.filter(query)
        buyer_node = company_new
        connections = buy_cons
        if buyer_old:
            sup_con = Connection.objects.filter(
                buyer__id=buyer_old.id,
                supply_chain__id=source_sc_id,
                supplier_id=node_old,
            ).first()
            connections = Connection.objects.none()
            for buy_con in buy_cons:
                if ConnectionTag.objects.filter(
                    supplier_connection=sup_con, buyer_connection=buy_con
                ).exists():
                    connections |= Connection.objects.filter(id=buy_con.id)
    print("connections^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^", connections)
    for con in connections:
        buyer_old = con.buyer
        supplier_old = con.supplier
        buyer_new, invitation_new = create_buyer_connection(
            con, buyer_node, target_sc_id, name, source_sc_id
        )
        if not buyer_new:
            continue
        copy_buyer_connections(
            node,
            company_new,
            source_sc_id,
            name,
            target_sc_id,
            buyer_new,
            buyer_old,
            supplier_old,
        )
