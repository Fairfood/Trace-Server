from . import constants

ACTIVITY_TEXT = {
    constants.USER_UPDATED_EMAIL: {
        # NOT IMPLEMENTED
        "user": "Your email was updated.",
        "node": "",
    },
    constants.USER_LOGGED_IN_FROM_NEW_DEVICE: {
        # NOT IMPLEMENTED
        "user": "Signed in from a new device.",
        "node": "",
    },
    constants.USER_GENERATED_MAGIC_LINK_TO_LOGIN: {
        # NOT IMPLEMENTED
        "user": "Logged in to account using magic link.",
        "node": "",
    },
    constants.USER_UPDATED_PROFILE_IMAGE: {
        # NOT IMPLEMENTED
        "user": "Changed profile pic.",
        "node": "",
    },
    constants.USER_CHANGED_PASSWORD: {
        # NOT IMPLEMENTED
        "user": "Your password was updated.",
        "node": "",
    },
    constants.USER_RESET_PASSWORD: {
        # NOT IMPLEMENTED
        "user": "Your password was reset.",
        "node": "",
    },
    constants.USER_CREATED_COMPANY: {
        "user": "Created company {event.node.full_name}.",
        "node": "{event.user.name} created company.",
    },
    constants.UPDATED_NODE_DETAILS: {
        "user": "Updated {context[updated_fields]} of {event.full_name}.",
        "node": "{event.updater.name} updated {context[updated_fields]}.",
    },
    constants.ADDED_AS_MEMBER: {
        "user": "Were added as team member for {event.node.full_name}.",
        "node": "{event.creator.name} added {event.user.name} to team.",
    },
    constants.REMOVED_MEMBER: {
        "user": "Were removed from the {event.node.full_name} team.",
        "node": (
            "{event.user.name} was removed from the {event.node.full_name}"
            " team by {context[user_name]}."
        ),
    },
    constants.USER_MADE_ADMIN: {
        "user": "Made Admin of {event.node.full_name}.",
        "node": (
            "Role of {event.user.name} was changed to Admin by"
            " {event.updater.name}."
        ),
    },
    constants.USER_MADE_MEMBER: {
        "user": "Made Member of {event.node.full_name}.",
        "node": (
            "Role of {event.user.name} was changed to Member by"
            " {event.updater.name}."
        ),
    },
    constants.USER_MADE_VIEWER: {
        "user": "Made Viewer of {event.node.full_name}.",
        "node": (
            "Role of {event.user.name} was changed to Viewer by"
            " {event.updater.name}."
        ),
    },
    constants.ADDED_NODE_DOCUMENT: {
        "user": "Added document {event.name} to {event.node.full_name}.",
        "node": "{event.creator.name} added document {event.name}.",
    },
    constants.DELETED_NODE_DOCUMENT: {
        "user": (
            "Deleted document {context[file_name]} from {event.full_name}."
        ),
        "node": (
            "{context[member_name]} deleted document {context[file_name]}."
        ),
    },
    constants.NODE_INVITED_NODE: {
        "user": "",
        "node": (
            "Sent invitation to {event.invitee.full_name} in"
            " {event.connection.supply_chain.name} supply chain."
        ),
    },
    constants.NODE_RECEIVED_INVITATION: {
        "user": "",
        "node": (
            "{event.invitee.full_name} received invitation to"
            " {event.connection.supply_chain.name} supply chain from"
            " {event.inviter.full_name}"
        ),
    },
    constants.NODE_SENT_STOCK: {
        "user": "",
        "node": (
            "Sent {event.result_batch.initial_quantity_rounded}"
            "{event.result_batch.unit_display} of "
            "{event.result_batch.product.name} to "
            "{event.destination.full_name}"
        ),
    },
    constants.NODE_RECEIVED_STOCK: {
        "user": "",
        "node": (
            "Received {event.result_batch.initial_quantity_rounded}{"
            "event.result_batch.unit_display} of "
            "{event.result_batch.product.name} from "
            "{event.source.full_name}"
        ),
    },
    constants.NODE_USER_INTERNAL_TRANSACTION: {
        "user": "{context[message]} at {event.node.full_name}.",
        "node": "{event.creator.name} {context[message]}.",
    },
    constants.NODE_SYSTEM_INTERNAL_TRANSACTION: {
        "user": "",
        "node": "System {context[message]}.",
    },
    constants.NODE_USER_REJECTED_TRANSACTION: {
        "user": "",
        "node": (
            "Rejected the transaction of "
            "{event.result_batch.initial_quantity_rounded}"
            "{event.result_batch.unit_display} "
            "of {event.result_batch.product.name} from {"
            "event.destination.full_name}"
        ),
    },
    constants.NODE_STOCK_WAS_RETURNED: {
        "user": "",
        "node": (
            "{event.source.full_name} returned "
            "{event.result_batch.initial_quantity_rounded}"
            "{event.result_batch.unit_display} "
            "of {event.result_batch.product.name}"
        ),
    },
    constants.NODE_USER_ADDED_COMMENT_TO_BATCH: {
        # NOT IMPLEMENTED
        "user": (
            "Commented on batch #{event.batch.number} of"
            " {event.batch.node.full_name}"
        ),
        "node": (
            "{event.creator.name} commented on batch #{event.batch.number}"
        ),
    },
    constants.NODE_CREATED_STOCK_REQUEST: {
        "user": "",
        "node": (
            "Sent stock request for {event.quantity}{event.unit_display}"
            " of {event.product.name} to {event.requestee.full_name}"
        ),
    },
    constants.NODE_RECEIVED_STOCK_REQUEST: {
        "user": "",
        "node": (
            "{event.requestee.full_name} received stock request for"
            " {event.quantity}{event.unit_display} of {event.product.name}"
            " from {event.requester.full_name}"
        ),
    },
    constants.NODE_DECLINED_STOCK_REQUEST: {
        "user": "",
        "node": (
            "Declined stock request for {event.quantity}{event.unit_display}"
            " of {event.product.name} from {event.requester.full_name}"
        ),
    },
    constants.STOCK_REQUEST_WAS_DECLINED: {
        "user": "",
        "node": (
            "Stock request for {event.quantity}{event.unit_display} of"
            " {event.product.name} to {event.requestee.full_name} was declined"
        ),
    },
    constants.NODE_CREATED_CLAIM_REQUEST: {
        "user": "",
        "node": (
            "Sent claim request to {event.requestee.full_name} for"
            " {event.claim.name} claim"
        ),
    },
    constants.NODE_RECEIVED_CLAIM_REQUEST: {
        "user": "",
        "node": (
            "{event.requestee.full_name} received claim request from"
            " {event.requester.full_name} for {event.claim.name} claim"
        ),
    },
    constants.NODE_DECLINED_CLAIM_REQUEST: {
        "user": "",
        "node": (
            "Claim request from {event.requester.full_name} for"
            " {event.claim.name} was declined."
        ),
    },
    constants.CLAIM_REQUEST_WAS_DECLINED: {
        "user": "",
        "node": (
            "{event.requestee.full_name} declined request for"
            " {event.claim.name}"
        ),
    },
    constants.NODE_CREATED_INFORMATION_REQUEST: {
        "user": "",
        "node": "Sent request for information to {event.requestee.full_name}",
    },
    constants.NODE_RECEIVED_INFORMATION_REQUEST: {
        "user": "",
        "node": (
            "{event.requestee.full_name} received request for information from"
            " {event.requester.full_name}"
        ),
    },
    constants.NODE_DECLINED_INFORMATION_REQUEST: {
        "user": "",
        "node": (
            "Request for information from {event.requester.full_name} was"
            " declined."
        ),
    },
    constants.INFORMATION_REQUEST_WAS_DECLINED: {
        "user": "",
        "node": "{event.requestee.full_name} declined request for information",
    },
    constants.NODE_CREATED_CONNECTION_REQUEST: {
        "user": "",
        "node": (
            "Sent request to map connection to {event.requestee.full_name}."
        ),
    },
    constants.NODE_RECEIVED_CONNECTION_REQUEST: {
        "user": "",
        "node": (
            "{event.requestee.full_name} received request to map connection"
            " from {event.requester.full_name}."
        ),
    },
    constants.NODE_USER_ATTACHED_CLAIM_TO_BATCH: {
        "user": (
            "Attached {event.claim.name} claim to batch #{event.batch.number}"
            " of {event.batch.node.full_name}"
        ),
        "node": (
            "{event.creator.name} attached {event.claim.name} claim to batch"
            " #{event.batch.number}"
        ),
    },
    constants.NODE_ATTACHED_CLAIM_TO_TRANSACTION: {
        "user": "",
        "node": (
            "{context[target_name]} attached {event.claim.name} claim to"
            " transaction #{event.transaction.number}"
        ),
    },
    constants.NODE_ADDED_COMPANY_CLAIM: {
        "user": "Attached {event.claim.name} claim to {event.node.full_name}.",
        "node": (
            "{event.creator.name} attached {event.claim.name} claim for"
            " company."
        ),
    },
    constants.NODE_SENT_VERIFICATION_REQUEST: {
        "user": "",
        "node": (
            "Assigned {event.verifier.full_name} to verify {event.claim.name}"
            " claim."
        ),
    },
    constants.NODE_RECEIVED_VERIFICATION_REQUEST: {
        "user": "",
        "node": "Received request to verify {event.claim.name} claim.",
    },
    constants.VERIFIER_APPROVED_CLAIM: {
        "user": "",
        "node": "Approved {event.claim.name} claim.",
    },
    constants.NODE_CLAIM_APPROVED: {
        "user": "",
        "node": "{event.claim.name} claim was approved.",
    },
    constants.VERIFIER_REJECTED_CLAIM: {
        "user": "",
        "node": "Rejected {event.claim.name} claim.",
    },
    constants.NODE_CLAIM_REJECTED: {
        "user": "",
        "node": "{event.claim.name} claim was rejected",
    },
    constants.SENT_COMMENT_ON_CLAIM: {
        "user": "",
        "node": (
            "Commented on verification of {event.attached_claim.claim.name}"
            " claim"
        ),
    },
    constants.RECEIVED_COMMENT_ON_CLAIM: {
        "user": "",
        "node": (
            "{event.sender.full_name} commented on verification of"
            " {event.attached_claim.claim.name} claim"
        ),
    },
    constants.CONNECTION_REQUEST_WAS_DECLINED: {
        "user": "",
        "node": (
            "{event.requestee.full_name} declined request for"
            " {event.supply_chain.name} "
        ),
    },
    constants.NODE_DECLINED_CONNECTION_REQUEST: {
        "user": "",
        "node": (
            "Connection request from {event.requester.full_name} for"
            " {event.supply_chain.name} was declined."
        ),
    },
    constants.CLAIM_RECEIVED_RESPONSE: {
        "user": "",
        "node": (
            "Received claim request response from {event.requestee.full_name}"
            " for {event.claim.name} claim"
        ),
    },
    constants.NODE_RESPOND_CLAIM_REQUEST: {
        "user": "",
        "node": (
            "Responded claim request to {event.requester.full_name} for"
            " {event.claim.name} claim"
        ),
    },
    constants.INFORMATION_RECEIVED_RESPONSE: {
        "user": "",
        "node": (
            "Received information request response from"
            " {event.requestee.full_name} "
        ),
    },
    constants.NODE_RESPOND_INFORMATION_REQUEST: {
        "user": "",
        "node": "Responded information request to {event.requester.full_name}",
    },
    constants.FFADMIN_INVITED_COMPANY: {
        "user": "You got an invitation to {event.set_activity_user}",
        "node": "{event.set_activity_text}",
    },
    constants.NODE_RECEIVED_INVITATION_FROM_FFADMIN: {
        "user": "You got an invitation to {event.set_activity_user}",
        "node": "{event.set_activity_text}",
    },
    constants.NODE_JOINED_FFADMIN_INVITE: {
        "user": "You got an invitation to {event.set_activity_user}",
        "node": "{event.set_joined_activity_text}",
    },
    constants.FARMER_CREATED: {
        "user": "",
        "node": "Farmer got invited by {event.creator.name}.",
    },
    constants.FARMER_EDITED: {
        "user": "",
        "node": "{event.updater.name} updated farmer details.",
    },
    constants.CARD_ADDED: {
        "user": "",
        "node": "New card assigned to this farmer",
    },
    constants.CARD_REMOVED: {
        "user": "",
        "node": "A Card removed from the farmer",
    },
}


def get_activity_text(activity_type, event, context):
    """To perform function get_activity_text."""
    template = ACTIVITY_TEXT[activity_type]
    try:
        user_text = template["user"].format(**vars())
        node_text = template["node"].format(**vars())
    except AttributeError:
        user_text = template["user"]
        node_text = template["node"]
    if user_text:
        user_text = user_text[0].upper() + user_text[1:]
    if node_text:
        node_text = node_text[0].upper() + node_text[1:]
    text = {"user": user_text, "node": node_text}
    return text
