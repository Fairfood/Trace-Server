import copy

from v2.communications import constants as comm_constants
from v2.transactions import constants as trans_constants


def get_notification_data(object):
    """
    Get notification data from transaction object
    Args:
        object: ExternalTransaction object

    Returns:
        data: Notifications

    """
    notifications = []
    notif_params = {
        "token": None,
        "event": object,
        "send_to": "",
        "supply_chain": object.product.supply_chain,
    }
    if object.type == trans_constants.EXTERNAL_TRANS_TYPE_INCOMING:
        notif_params["actor_node"] = object.destination
        notif_params["target_node"] = object.source
        notif_params["notif_type"] = comm_constants.NOTIF_TYPE_SENT_STOCK

        for member in object.source.subscribers:
            notif_data = copy.deepcopy(notif_params)
            notif_data["user"] = member
            notifications.append(notif_data)

    elif object.type == trans_constants.EXTERNAL_TRANS_TYPE_OUTGOING:
        notif_params["actor_node"] = object.source
        notif_params["target_node"] = object.destination
        notif_params["notif_type"] = comm_constants.NOTIF_TYPE_RECEIVE_STOCK

        for member in object.destination.subscribers:
            notif_data = copy.deepcopy(notif_params)
            notif_data["user"] = member
            notifications.append(notif_data)

    elif object.type == trans_constants.EXTERNAL_TRANS_TYPE_REVERSAL:
        notif_params["actor_node"] = object.source
        notif_params["target_node"] = object.destination
        notif_params[
            "notif_type"
        ] = comm_constants.NOTIF_TYPE_TRANSACTION_REJECTED

        for member in object.destination.subscribers:
            notif_data = copy.deepcopy(notif_params)
            notif_data["user"] = member
            notifications.append(notif_data)
    return notifications
