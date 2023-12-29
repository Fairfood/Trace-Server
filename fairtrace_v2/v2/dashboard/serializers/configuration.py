"""Serializers for Project configurations."""
from common.currencies import CURRENCY_CHOICES
from v2.activity import constants as act_constants
from v2.claims import constants as claims_constants
from v2.communications import constants as notif_constants
from v2.products import constants as prod_constants
from v2.supply_chains import constants as sc_constants
from v2.transactions import constants as trans_constants


class ConfigurationsSerializer:
    """Config serializer class.

    Class defined to serialize the constants and return the
    configurations for all apps.
    """

    currencies = CURRENCY_CHOICES
    internal_transaction_types = trans_constants.INTERNAL_TRANS_TYPE_CHOICES
    external_transaction_types = trans_constants.EXTERNAL_TRANS_TYPE_CHOICES
    transaction_statuses = trans_constants.TRANSACTION_STATUS_CHOICES

    node_types = sc_constants.NODE_TYPE_CHOICES
    company_roles = sc_constants.COMPANY_ROLE_CHOICES
    farmer_additional_fields = sc_constants.FARMER_ADDITIONAL_FIELDS
    connections_status = sc_constants.CONNECTION_STATUS_CHOICES
    invitation_types = sc_constants.INVITATION_TYPE_CHOICES
    member_roles = sc_constants.NODE_MEMBER_TYPE_CHOICES
    actions = sc_constants.NODE_ACTION_CHOICES
    selected_theme = sc_constants.SELECTED_THEME_CHOICES
    wallet_types = sc_constants.BLOCKCHAIN_WALLET_TYPES

    units = prod_constants.UNIT_CHOICES

    claim_statuses = claims_constants.STATUS_CHOICES
    claim_field_types = claims_constants.FIELD_TYPE_CHOICES

    activity_type_choices = act_constants.ACTIVITY_TYPE_CHOICES
    object_type_choices = act_constants.OBJECT_TYPE_CHOICES

    notification_types = notif_constants.NOTIF_TYPE_CHOICES

    class Meta:
        """Meta class."""

        fields = (
            "currencies",
            "internal_transaction_types",
            "external_transaction_types",
            "transaction_statuses",
            "node_types",
            "company_roles",
            "farmer_additional_fields",
            "connections_status",
            "invitation_types",
            "member_roles",
            "actions",
            "selected_theme",
            "units",
            "claim_statuses",
            "claim_field_types",
            "activity_type_choices",
            "object_type_choices",
            "notification_types",
        )

    def to_representation(self):
        """Override serializer to rep to modify the response."""
        configurations = {}
        for field in self.Meta.fields:
            data = []
            for choice in getattr(self, field):
                data.append({"key": choice[0], "name": choice[1]})
            configurations[field] = data

        return configurations
