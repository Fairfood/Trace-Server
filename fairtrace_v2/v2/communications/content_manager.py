"""Module to manage notification content.

This module act as a content creator for notifications.
The content and emails template of each type of user for
each notification types are defined in the content
dictionary. content is generated based on the user type
and notification type.

Only object of the corresponding event is allowed as
context variables in messages.
"""
from django.conf import settings
from v2.activity import constants as act_constants

from . import constants as notif_constants

INACTIVE_NODE_NOTIFICATION_TEMPLATE = (
    "/emails/invite/inactive_node_notification.html"
)

content = {
    notif_constants.NOTIF_TYPE_VERIFY_EMAIL: {
        "title_en": "Almost there!",
        "title_loc": "Almost there!",
        "body_en": "To start using the Trace system you must first verify your"
        " email address by clicking the link below.",
        "body_loc": "To start using the Trace system you must first verify "
        "your email address by clicking the link below.",
        "action_text": "Verify email",
        "visibility": False,
        "action": notif_constants.NOTIF_ACTION_EMAIL,
        "email_template": "/emails/account/verify_email.html",
        "event": act_constants.OBJECT_TYPE_USER,
        "from_email": "Trace <trace@fairfood.org>",
        "action_url": settings.LOGIN_ROOT_URL
        + "/?notification={notification.idencode}"
        "&user={user.idencode}",
    },
    notif_constants.NOTIF_TYPE_CHANGE_EMAIL: {
        "title_en": "Change email.",
        "title_loc": "Change email.",
        "body_en": (
            "Click the below link to change email id for your "
            "Fairfood account."
        ),
        "body_loc": (
            "Click the below link to change email id for your "
            "Fairfood account."
        ),
        "action_text": "Verify email",
        "visibility": True,
        "action": notif_constants.NOTIF_ACTION_EMAIL,
        "email_template": "/emails/account/verify_new_email.html",
        "event": act_constants.OBJECT_TYPE_USER,
        "from_email": "Trace <trace@fairfood.org>",
        "action_url": settings.LOGIN_ROOT_URL
        + "/verify/?notification={notification.idencode}"
        "&user={user.idencode}",
    },
    notif_constants.NOTIF_TYPE_RESET_PASSWORD: {
        "title_en": "Reset password.",
        "title_loc": "Reset password.",
        "body_en": (
            "Click the below link to reset your Fairfood account password."
        ),
        "body_loc": (
            "Click the below link to reset your Fairfood account password."
        ),
        "action_text": "Reset password",
        "visibility": False,
        "action": notif_constants.NOTIF_ACTION_EMAIL,
        "email_template": "/emails/account/reset_password.html",
        "event": act_constants.OBJECT_TYPE_USER,
        "from_email": "Trace <trace@fairfood.org>",
        "action_url": settings.FRONT_ROOT_URL
        + "/reset/?notification={notification.idencode}&user={user.idencode}",
    },
    notif_constants.NOTIF_TYPE_MAGIC_LOGIN: {
        "title_en": "Your requested Magic Link.",
        "title_loc": "Your requested Magic Link.",
        "body_en": (
            "Click the below link to sign in to your Trace account in just one"
            " click"
        ),
        "body_loc": (
            "Click the below link to sign in to your Trace account in just one"
            " click"
        ),
        "action_text": "Click here to sign in",
        "visibility": False,
        "action": notif_constants.NOTIF_ACTION_EMAIL,
        "email_template": "/emails/account/magic_login.html",
        "event": act_constants.OBJECT_TYPE_USER,
        "from_email": "Trace <trace@fairfood.org>",
        "action_url": settings.FRONT_ROOT_URL
        + "/login/?notification={notification.idencode}&user={user.idencode}",
    },
    notif_constants.NOTIF_TYPE_MAGIC_LOGIN_ADMIN: {
        "title_en": "Your requested Magic Link.",
        "title_loc": "Your requested Magic Link.",
        "body_en": (
            "Click the below link to sign in to your Trace account "
            "in just one click"
        ),
        "body_loc": (
            "Click the below link to sign in to your Trace account "
            "in just one click"
        ),
        "action_text": "Click here to sign in",
        "visibility": False,
        "action": notif_constants.NOTIF_ACTION_EMAIL,
        "email_template": "/emails/account/magic_login.html",
        "event": act_constants.OBJECT_TYPE_USER,
        "from_email": "Trace <trace@fairfood.org>",
        "action_url": settings.ADMIN_FRONT_ROOT_URL
        + "/login/?notification={notification.idencode}"
        "&user={user.idencode}",
    },
    notif_constants.NOTIF_TYPE_EMAIL_LOGIN: {
        "title_en": "Your requested email login code {event.key}.",
        "title_loc": "Your requested email login code {event.key}.",
        "body_en": (
            "Click the below link to sign in to your Trace account "
            "in just one click"
        ),
        "body_loc": (
            "Click the below link to sign in to your Trace account "
            "in just one click"
        ),
        "action_text": "Click here to sign in",
        "visibility": False,
        "action": notif_constants.NOTIF_ACTION_EMAIL,
        "email_template": "/emails/account/email_login.html",
        "event": act_constants.OBJECT_TYPE_VALIDATION_TOKEN,
        "from_email": "Trace <trace@fairfood.org>",
        "action_url": "",
    },
    notif_constants.NOTIF_TYPE_MEMBER_INVITE: {
        "title_en": "You have been added as Team Member",
        "title_loc": "You have been added as Team Member.",
        "body_en": (
            "You have been added as {"
            "event.get_lower_type_display_name} to "
            "{event.node.full_name} in Trace."
        ),
        "body_loc": (
            "You have been added as {"
            "event.get_lower_type_display_name} to {"
            "event.node.full_name} in Trace."
        ),
        "action_text": "Accept Invitation",
        "visibility": True,
        "action": notif_constants.NOTIF_ACTION_PUSH_N_EMAIL,
        "email_template": "/emails/invite/member_invite.html",
        "event": act_constants.OBJECT_TYPE_NODE_MEMBER,
        "from_email": "Trace <trace@fairfood.org>",
        "action_url": settings.LOGIN_ROOT_URL
        + "/accept-member-invite/?notification={notification.idencode}"
        "&user={user.idencode}&node_id={event.node.idencode}",
    },
    notif_constants.NOTIF_TYPE_NEW_NODE_INVITE: {
        "title_en": "{sender.name} from {event.inviter.full_name} "
        "sent you a transparency request.",
        "title_loc": "{sender.name} from {event.inviter.full_name} "
        "sent you a transparency request.",
        "body_en": "{sender.name} from {event.inviter.full_name} sent you a "
        "transparency request about the {event.connection.supply_chain.name} "
        "you {event.relation_text} them.",
        "body_loc": "{sender.name} from {event.inviter.full_name} sent you a "
        "transparency request about the {event.connection.supply_chain.name} "
        "you {event.relation_text} them.",
        "action_text": "Join",
        "visibility": True,
        "action": notif_constants.NOTIF_ACTION_PUSH_N_EMAIL,
        "email_template": "/emails/invite/new_node_invite.html",
        "event": act_constants.OBJECT_TYPE_INVITATION,
        "from_email": "Trace <trace@fairfood.org>",
        "action_url": settings.LOGIN_ROOT_URL
        + (
            "/accept-node-invite/?notification={notification.idencode}&user={"
            "user.idencode}&node_id={event.invitee.idencode}&supply_chain={"
            "supply_chain.idencode}"
        ),
    },
    notif_constants.NOTIF_TYPE_EXISTING_NODE_INVITE: {
        "title_en": (
            "{event.inviter.full_name} invites you to join the"
            " {event.connection.supply_chain.name} supply chain."
        ),
        "title_loc": (
            "{event.inviter.full_name} invites you to join the"
            " {event.connection.supply_chain.name} supply chain."
        ),
        "body_en": (
            "{sender.name} from {event.inviter.full_name} has added you to the"
            " {event.connection.supply_chain.name} supply chain in Trace."
        ),
        "body_loc": (
            "{sender.name} from {event.inviter.full_name} has added you to the"
            " {event.connection.supply_chain.name} supply chain in Trace."
        ),
        "action_text": "Accept invitation",
        "visibility": True,
        "action": notif_constants.NOTIF_ACTION_PUSH_N_EMAIL,
        "email_template": "/emails/invite/exist_node_invite.html",
        "event": act_constants.OBJECT_TYPE_INVITATION,
        "from_email": "Trace <trace@fairfood.org>",
        "action_url": settings.FRONT_ROOT_URL
        + "/email-notification/?notification={notification.idencode}"
        + "&user={user.idencode}",
    },
    notif_constants.NOTIF_TYPE_WEEK_ONE_REMINDER: {
        "title_en": "Why it makes sense to bring more transparency to your "
        "{event.connection.supply_chain.name}",
        "title_loc": "Why it makes sense to bring more transparency to your "
        "{event.connection.supply_chain.name}",
        "body_en": "",
        "body_loc": "",
        "action_text": "Join",
        "visibility": True,
        "action": notif_constants.NOTIF_ACTION_EMAIL,
        "email_template": "/emails/invite/week_one_reminder_email.html",
        "event": act_constants.OBJECT_TYPE_INVITATION,
        "from_email": "Trace <trace@fairfood.org>",
        "action_url": settings.LOGIN_ROOT_URL
        + (
            "/accept-node-invite/?notification={notification.idencode}&user={"
            "user.idencode}&node_id={event.invitee.idencode}&supply_chain={"
            "supply_chain.idencode}"
        ),
    },
    notif_constants.NOTIF_TYPE_WEEK_TWO_REMINDER: {
        "title_en": "{notification.user.name}, we need you to uncover the "
        "{event.connection.supply_chain.name} supply chain.",
        "title_loc": "{notification.user.name}, we need you to uncover the "
        "{event.connection.supply_chain.name} supply chain.",
        "body_en": "",
        "body_loc": "",
        "action_text": "Join",
        "visibility": True,
        "action": notif_constants.NOTIF_ACTION_EMAIL,
        "email_template": "/emails/invite/week_two_reminder_email.html",
        "event": act_constants.OBJECT_TYPE_INVITATION,
        "from_email": "Trace <trace@fairfood.org>",
        "action_url": settings.LOGIN_ROOT_URL
        + (
            "/accept-node-invite/?notification={notification.idencode}&user={"
            "user.idencode}&node_id={event.invitee.idencode}&supply_chain={"
            "supply_chain.idencode}"
        ),
    },
    notif_constants.NOTIF_TYPE_RECEIVE_STOCK: {
        "title_en": (
            "Received {event.result_batch.product.name} from {"
            "event.source.full_name}"
        ),
        "title_loc": (
            "Received {event.result_batch.product.name} from {"
            "event.source.full_name}"
        ),
        "body_en": (
            "{event.destination.full_name} received "
            "{event.result_batch.initial_quantity_rounded}{"
            "event.result_batch.unit_display} "
            "of {event.result_batch.product.name} from {"
            "event.source.full_name}."
        ),
        "body_loc": "{event.destination.full_name} received "
        "{event.result_batch.initial_quantity_rounded}{"
        "event.result_batch.unit_display} "
        "of {event.result_batch.product.name} "
        "from {event.source.full_name}.",
        "action_text": "View details",
        "visibility": True,
        "action": notif_constants.NOTIF_ACTION_PUSH_N_EMAIL,
        "email_template": "/emails/transaction/incoming_transaction.html",
        "event": act_constants.OBJECT_TYPE_EXT_TRANSACTION,
        "from_email": "Trace <trace@fairfood.org>",
        "action_url": settings.FRONT_ROOT_URL
        + "/email-notification/?notification={notification.idencode}"
        "&user={user.idencode}",
    },
    notif_constants.NOTIF_TYPE_SENT_STOCK: {
        "title_en": "Sent {event.result_batch.initial_quantity_rounded} "
        "{event.result_batch.unit_display} of "
        "{event.result_batch.product.name} to {event.destination.full_name}",
        "title_loc": "Sent {event.result_batch.product.name} to "
        "{event.source.full_name}",
        "body_en": "",
        "body_loc": "",
        "action_text": "View",
        "visibility": True,
        "action": notif_constants.NOTIF_ACTION_PUSH,
        "email_template": "",
        "event": act_constants.OBJECT_TYPE_EXT_TRANSACTION,
        "from_email": "Trace <trace@fairfood.org>",
        "action_url": settings.FRONT_ROOT_URL
        + "/email-notification/?notification={notification.idencode}"
        "&user={user.idencode}",
    },
    notif_constants.NOTIF_TYPE_TRANSACTION_REJECTED: {
        "title_en": "{event.source.full_name} rejected your transaction",
        "title_loc": "{event.source.full_name} rejected your transaction",
        "body_en": (
            "{event.source.full_name} has rejected your transaction "
            "of {event.result_batch.initial_quantity_rounded}"
            "{event.result_batch.unit_display} of "
            "{event.result_batch.product.name}."
        ),
        "body_loc": (
            "{event.source.full_name} has rejected your transaction of "
            "{event.result_batch.initial_quantity_rounded}"
            "{event.result_batch.unit_display} "
            "of {event.result_batch.product.name}."
        ),
        "action_text": "View details",
        "visibility": True,
        "action": notif_constants.NOTIF_ACTION_PUSH_N_EMAIL,
        "email_template": "/emails/transaction/reject_transaction.html",
        "event": act_constants.OBJECT_TYPE_EXT_TRANSACTION,
        "from_email": "Trace <trace@fairfood.org>",
        "action_url": settings.FRONT_ROOT_URL
        + "/email-notification/?notification={notification.idencode}"
        "&user={user.idencode}",
    },
    notif_constants.NOTIF_TYPE_RECEIVE_STOCK_REQUEST: {
        "title_en": (
            "Received request for stock from {event.requester.full_name}"
        ),
        "title_loc": (
            "Received request for stock from {event.requester.full_name}"
        ),
        "body_en": (
            "{event.requestee.full_name} received a request for stock from"
            " {event.requester.full_name}."
        ),
        "body_loc": (
            "{event.requestee.full_name} received a request for stock from"
            " {event.requester.full_name}."
        ),
        "action_text": "View request",
        "visibility": True,
        "action": notif_constants.NOTIF_ACTION_PUSH_N_EMAIL,
        "email_template": (
            "/emails/transparency_request/receive_stock_request.html"
        ),
        "event": act_constants.OBJECT_TYPE_TRANSACTION_REQUEST,
        "from_email": "Trace <trace@fairfood.org>",
        "action_url": settings.FRONT_ROOT_URL
        + "/email-notification/?notification={notification.idencode}&user={"
        "user.idencode}",
    },
    notif_constants.NOTIF_TYPE_DECLINE_STOCK_REQUEST: {
        "title_en": "{event.requestee.full_name} declined request for stock",
        "title_loc": "{event.requestee.full_name} declined request for stock",
        "body_en": (
            "{event.requestee.full_name} declined your request for"
            " {event.quantity}{event.unit_display} of {event.product.name}"
            " stock."
        ),
        "body_loc": (
            "{event.requestee.full_name} declined your request for"
            " {event.quantity}{event.unit_display} of {event.product.name}"
            " stock."
        ),
        "action_text": "View request",
        "visibility": True,
        "action": notif_constants.NOTIF_ACTION_PUSH_N_EMAIL,
        "email_template": (
            "/emails/transparency_request/decline_stock_request.html"
        ),
        "event": act_constants.OBJECT_TYPE_TRANSACTION_REQUEST,
        "from_email": "Trace <trace@fairfood.org>",
        "action_url": settings.FRONT_ROOT_URL
        + "/email-notification/?notification={notification.idencode}&user={"
        "user.idencode}",
    },
    notif_constants.NOTIF_TYPE_RECEIVE_CLAIM_REQUEST: {
        "title_en": (
            "Received request for claim from {event.requester.full_name}"
        ),
        "title_loc": (
            "Received request for claim from {event.requester.full_name}"
        ),
        "body_en": (
            "{event.requester.full_name} sent you a request to add"
            " {event.claim.name} claim."
        ),
        "body_loc": (
            "{event.requester.full_name} sent you a request to add"
            " {event.claim.name} claim."
        ),
        "action_text": "View request",
        "visibility": True,
        "action": notif_constants.NOTIF_ACTION_PUSH_N_EMAIL,
        "email_template": (
            "/emails/transparency_request/receive_claim_request.html"
        ),
        "event": act_constants.OBJECT_TYPE_CLAIM_REQUEST,
        "from_email": "Trace <trace@fairfood.org>",
        "action_url": settings.FRONT_ROOT_URL
        + "/email-notification/?notification={notification.idencode}&user={"
        "user.idencode}",
    },
    notif_constants.NOTIF_TYPE_DECLINE_CLAIM_REQUEST: {
        "title_en": (
            "{event.requestee.full_name} declined request for company claim"
        ),
        "title_loc": (
            "{event.requestee.full_name} declined request for company claim"
        ),
        "body_en": (
            "{event.requestee.full_name} declined your request to add"
            " {event.claim.name} claim."
        ),
        "body_loc": (
            "{event.requestee.full_name} declined your request to add"
            " {event.claim.name} claim."
        ),
        "action_text": "View request",
        "visibility": True,
        "action": notif_constants.NOTIF_ACTION_PUSH_N_EMAIL,
        "email_template": (
            "/emails/transparency_request/decline_claim_request.html"
        ),
        "event": act_constants.OBJECT_TYPE_CLAIM_REQUEST,
        "from_email": "Trace <trace@fairfood.org>",
        "action_url": settings.FRONT_ROOT_URL
        + "/email-notification/?notification={notification.idencode}&user={"
        "user.idencode}",
    },
    notif_constants.NOTIF_TYPE_RECEIVE_INFORMATION_REQUEST: {
        "title_en": (
            "Received request for information from {event.requester.full_name}"
        ),
        "title_loc": (
            "Received request for information from {event.requester.full_name}"
        ),
        "body_en": (
            "{event.requester.full_name} sent you a request for information."
        ),
        "body_loc": (
            "{event.requester.full_name} sent you a request for information."
        ),
        "action_text": "View request",
        "visibility": True,
        "action": notif_constants.NOTIF_ACTION_PUSH_N_EMAIL,
        "email_template": (
            "/emails/transparency_request/receive_information_request.html"
        ),
        "event": act_constants.OBJECT_TYPE_CLAIM_REQUEST,
        "from_email": "Trace <trace@fairfood.org>",
        "action_url": settings.FRONT_ROOT_URL
        + "/email-notification/?notification={notification.idencode}&user={"
        "user.idencode}",
    },
    notif_constants.NOTIF_TYPE_DECLINE_INFORMATION_REQUEST: {
        "title_en": (
            "{event.requestee.full_name} declined request for information"
        ),
        "title_loc": (
            "{event.requestee.full_name} declined request for information"
        ),
        "body_en": (
            "{event.requestee.full_name} declined your request for"
            " information."
        ),
        "body_loc": (
            "{event.requestee.full_name} declined your request for"
            " information."
        ),
        "action_text": "View request",
        "visibility": True,
        "action": notif_constants.NOTIF_ACTION_PUSH_N_EMAIL,
        "email_template": (
            "/emails/transparency_request/decline_information_request.html"
        ),
        "event": act_constants.OBJECT_TYPE_TRANSACTION_REQUEST,
        "from_email": "Trace <trace@fairfood.org>",
        "action_url": settings.FRONT_ROOT_URL
        + "/email-notification/?notification={notification.idencode}&user={"
        "user.idencode}",
    },
    notif_constants.NOTIF_TYPE_RECEIVE_CONNECTION_REQUEST: {
        "title_en": (
            "Received request to map suppliers from"
            " {event.requester.full_name}"
        ),
        "title_loc": (
            "Received request to map suppliers from"
            " {event.requester.full_name}"
        ),
        "body_en": (
            "{event.requester.full_name} sent you a request to map suppliers"
            " in your {event.supply_chain.name} supply chain"
        ),
        "body_loc": (
            "{event.requester.full_name} sent you a request to map suppliers"
            " in your {event.supply_chain.name} supply chain"
        ),
        "action_text": "View request",
        "visibility": True,
        "action": notif_constants.NOTIF_ACTION_PUSH_N_EMAIL,
        "email_template": (
            "/emails/transparency_request/receive_connection_request.html"
        ),
        "event": act_constants.OBJECT_TYPE_CONNECTION_REQUEST,
        "from_email": "Trace <trace@fairfood.org>",
        "action_url": settings.FRONT_ROOT_URL
        + "/email-notification/?notification={notification.idencode}&user={"
        "user.idencode}",
    },
    notif_constants.NOTIF_TYPE_DECLINE_CONNECTION_REQUEST: {
        "title_en": (
            "{event.requestee.full_name} declined request for connection"
        ),
        "title_loc": (
            "{event.requestee.full_name} declined request for connection"
        ),
        "body_en": (
            "{event.requestee.full_name} declined your request to add"
            " {event.supply_chain.name} connection."
        ),
        "body_loc": (
            "{event.requestee.full_name} declined your request to add"
            " {event.supply_chain.name} connection."
        ),
        "action_text": "View request",
        "visibility": True,
        "action": notif_constants.NOTIF_ACTION_PUSH_N_EMAIL,
        "email_template": (
            "/emails/transparency_request/decline_connection_request.html"
        ),
        "event": act_constants.OBJECT_TYPE_CONNECTION_REQUEST,
        "from_email": "Trace <trace@fairfood.org>",
        "action_url": settings.FRONT_ROOT_URL
        + "/email-notification/?notification={notification.idencode}&user={"
        "user.idencode}",
    },
    notif_constants.NOTIF_TYPE_RECEIVE_VERIFICATION_REQUEST: {
        "title_en": (
            "Received verification request from {event.attached_by.full_name}"
        ),
        "title_loc": (
            "Received verification request from {event.attached_by.full_name}"
        ),
        "body_en": (
            "{event.attached_by.full_name} has assigned you to verify"
            " {event.claim.lower_name} claim."
        ),
        "body_loc": (
            "{event.attached_by.full_name} has assigned you to verify"
            " {event.claim.lower_name} claim."
        ),
        "action_text": "Verify claim",
        "visibility": True,
        "action": notif_constants.NOTIF_ACTION_PUSH_N_EMAIL,
        "email_template": "/emails/claim/claim_verification.html",
        "event": act_constants.OBJECT_TYPE_ATTACHED_CLAIM,
        "from_email": "Trace <trace@fairfood.org>",
        "action_url": settings.FRONT_ROOT_URL
        + "/email-notification/?notification={notification.idencode}&user={"
        "user.idencode}",
    },
    notif_constants.NOTIF_TYPE_APPROVED_CLAIM: {
        "title_en": "{event.claim.name} claim approved.",
        "title_loc": "{event.claim.name} claim approved.",
        "body_en": "{event.verifier.full_name} has approved the claim.",
        "body_loc": "{event.verifier.full_name} has approved the claim.",
        "action_text": "View claim",
        "visibility": True,
        "action": notif_constants.NOTIF_ACTION_PUSH_N_EMAIL,
        "email_template": "/emails/claim/claim_approved.html",
        "event": act_constants.OBJECT_TYPE_ATTACHED_CLAIM,
        "from_email": "Trace <trace@fairfood.org>",
        "action_url": settings.FRONT_ROOT_URL
        + "/email-notification/?notification={notification.idencode}&user={"
        "user.idencode}",
    },
    notif_constants.NOTIF_TYPE_REJECTED_CLAIM: {
        "title_en": "{event.claim.name} claim rejected.",
        "title_loc": "{event.claim.name} claim rejected.",
        "body_en": "{event.verifier.full_name} has rejected the claim.",
        "body_loc": "{event.verifier.full_name} has rejected the claim.",
        "action_text": "View details",
        "visibility": True,
        "action": notif_constants.NOTIF_ACTION_PUSH_N_EMAIL,
        "email_template": "/emails/claim/claim_rejected.html",
        "event": act_constants.OBJECT_TYPE_ATTACHED_CLAIM,
        "from_email": "Trace <trace@fairfood.org>",
        "action_url": settings.FRONT_ROOT_URL
        + "/email-notification/?notification={notification.idencode}&user={"
        "user.idencode}",
    },
    notif_constants.NOTIF_TYPE_CLAIM_COMMENT: {
        "title_en": "{event.sender.full_name} commented on verification.",
        "title_loc": "{event.sender.full_name} commented on verification.",
        "body_en": "",
        "body_loc": "",
        "action_text": "View claim",
        "visibility": True,
        "action": notif_constants.NOTIF_ACTION_PUSH,
        "email_template": "",
        "event": act_constants.OBJECT_TYPE_CLAIM_COMMENT,
        "from_email": "Trace <trace@fairfood.org>",
        "action_url": settings.FRONT_ROOT_URL
        + "/email-notification/?notification={notification.idencode}&user={"
        "user.idencode}",
    },
    notif_constants.NOTIF_TYPE_INFORMATION_RESPONSE: {
        "title_en": (
            "Received response for information request from"
            " {event.requestee.full_name}"
        ),
        "title_loc": (
            "Received response for information request from"
            " {event.requestee.full_name}"
        ),
        "body_en": (
            "{event.requestee.full_name} responded to your request for"
            " information."
        ),
        "body_loc": (
            "{event.requestee.full_name} responded to your request for"
            " information."
        ),
        "action_text": "View request",
        "visibility": True,
        "action": notif_constants.NOTIF_ACTION_PUSH_N_EMAIL,
        "email_template": (
            "/emails/transparency_request/response_information_request.html"
        ),
        "event": act_constants.OBJECT_TYPE_CLAIM_REQUEST,
        "from_email": "Trace <trace@fairfood.org>",
        "action_url": settings.FRONT_ROOT_URL
        + "/email-notification/?notification={notification.idencode}&user={"
        "user.idencode}",
    },
    notif_constants.NOTIF_TYPE_CLAIM_RESPONSE: {
        "title_en": (
            "Received company claim response from {event.requestee.full_name}"
        ),
        "title_loc": (
            "Received company claim response from {event.requestee.full_name}"
        ),
        "body_en": (
            "{event.requestee.full_name} responded to your request for company"
            " claim."
        ),
        "body_loc": (
            "{event.requestee.full_name} responded to your request for company"
            " claim."
        ),
        "action_text": "View request",
        "visibility": True,
        "action": notif_constants.NOTIF_ACTION_PUSH_N_EMAIL,
        "email_template": (
            "/emails/transparency_request/response_claim_request.html"
        ),
        "event": act_constants.OBJECT_TYPE_CLAIM_REQUEST,
        "from_email": "Trace <trace@fairfood.org>",
        "action_url": settings.FRONT_ROOT_URL
        + "/email-notification/?notification={notification.idencode}&user={"
        "user.idencode}",
    },
    notif_constants.NOTIF_TYPE_FFADMIN_NEW_NODE_INVITE: {
        "title_en": "FairFood invites you to join {event.email_sc_text}",
        "title_loc": "FairFood invites you to join {event.email_sc_text}",
        "body_en": (
            "Your company {event.invitee.full_name} has been Invited "
            "to join {event.email_sc_text}."
        ),
        "body_loc": (
            "Your company {event.invitee.full_name} has been "
            "Invited to join {event.email_sc_text}."
        ),
        "action_text": "Accept and sign up",
        "visibility": True,
        "action": notif_constants.NOTIF_ACTION_PUSH_N_EMAIL,
        "email_template": "/emails/invite/ffadmin_new_node_invite.html",
        "event": act_constants.OBJECT_TYPE_FFADMIN_INVITATION,
        "from_email": "Trace <trace@fairfood.org>",
        "action_url": settings.LOGIN_ROOT_URL
        + "/accept-node-invite/?notification={notification.idencode}"
        "&user={user.idencode}&node_id={event.invitee.idencode}"
        "&supply_chain={supply_chain.idencode}",
    },
    notif_constants.NOTIF_TYPE_FFADMIN_EXISTING_NODE_INVITE: {
        "title_en": "FairFood invites you to join {event.email_sc_text}",
        "title_loc": "FairFood invites you to join {event.email_sc_text}",
        "body_en": (
            "Your company {event.invitee.full_name} has been Invited to join"
            " {event.email_sc_text}."
        ),
        "body_loc": (
            "Your company {event.invitee.full_name} has been Invited to join"
            " {event.email_sc_text}."
        ),
        "action_text": "Dashboard",
        "visibility": True,
        "action": notif_constants.NOTIF_ACTION_PUSH_N_EMAIL,
        "email_template": "/emails/invite/ffadmin_exist_node_invite.html",
        "event": act_constants.OBJECT_TYPE_FFADMIN_INVITATION,
        "from_email": "Trace <trace@fairfood.org>",
        "action_url": settings.FRONT_ROOT_URL
        + "/email-notification/?notification={notification.idencode}"
        + "&user={user.idencode}&node_id={event.invitee.idencode}&"
        + "supply_chain={supply_chain.idencode}",
    },
}


def get_content(notif_type):
    """Function to get notification content.

    Input params:
        notif_type(int): notification type.
        user_type(int): user type.
    Returns:
        Dictionary with,
        title_en(str): notification title in English.
        title_loc(str): notification title in local language.
        body_en(str): notification body in English.
        body_loc(str): notification body in local language.
        action(int): notification action.
    """
    try:
        data = content[notif_type]
        data["title_en"] = data["title_en"].capitalize()
        data["title_loc"] = data["title_loc"].capitalize()
        data["body_en"] = data["body_en"].capitalize()
        data["body_loc"] = data["body_loc"].capitalize()
    except Exception:
        data = {
            "title_en": "",
            "title_loc": "",
            "body_en": "",
            "body_loc": "",
            "visibility": True,
            "action": notif_constants.NOTIF_ACTION_NORMAL,
            "event": 0,
            "action_url": "",
        }
    return data
