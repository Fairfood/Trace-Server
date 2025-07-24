from common.drf_custom.fields import PhoneNumberField
from common.drf_custom.serializers import IdencodeModelSerializer
from django.db.models import Q
from rest_framework import serializers
from v2.supply_chains.constants import NODE_TYPE_FARM
from v2.supply_chains.models import Company
from v2.supply_chains.models import Farmer
from v2.transactions.models import ExternalTransaction


class AdminFarmerModelSerializer(IdencodeModelSerializer):
    """Serializer class for admin farmer list."""

    name = serializers.CharField(read_only=True)
    phone = PhoneNumberField(read_only=True)
    supply_chains = serializers.SerializerMethodField()
    buyers = serializers.SerializerMethodField()
    total_area_in_use = serializers.FloatField(read_only=True)
    all_crop_types = serializers.CharField(read_only=True)
    total_income = serializers.DictField(read_only=True)
    cards = serializers.SerializerMethodField()

    class Meta:
        model = Farmer
        fields = [
            "id",
            "created_on",
            "name",
            "image",
            "identification_no",
            "street",
            "city",
            "sub_province",
            "province",
            "country",
            "farm_area",
            "zipcode",
            "description_basic",
            "dob",
            "birth_city",
            "gender",
            "email",
            "phone",
            "description_full",
            "supply_chains",
            "buyers",
            "income_from_main_product",
            "income_from_other_sources",
            "main_product",
            "consent_status",
            "total_area_in_use",
            "all_crop_types",
            "total_income",
            "cards",
        ]

    @staticmethod
    def get_supply_chains(instance):
        """Returns a list of supply-chain names."""
        return instance.supply_chains.values_list("name", flat=True)

    @staticmethod
    def get_buyers(instance):
        """Returns a list of buyer names."""
        # Expecting only companies.
        return instance.get_buyers().values_list("company__name", flat=True)

    def get_cards(self, instance):
        """Function for filter the latest active card details of farmer."""
        query_set = instance.cards.filter(status=101).order_by("-updated_on")[
            :1
        ]
        data = query_set.values("card_id", "fairid")
        return data


class AdminCompanyModelSerializer(IdencodeModelSerializer):
    """Serializer class for admin company list."""

    supply_chain_names = serializers.SerializerMethodField()
    farmers_connected_count = serializers.SerializerMethodField()
    transaction_count = serializers.SerializerMethodField()

    class Meta:
        model = Company
        fields = [
            "id",
            "created_on",
            "name",
            "country",
            "supply_chain_names",
            "farmers_connected_count",
            "transaction_count",
            "status",
        ]

    @staticmethod
    def get_supply_chain_names(instance):
        """Returns a list of active supply chain names."""
        return (
            instance.supply_chains.filter(active=True)
            .distinct("name")
            .values_list("name", flat=True)
        )

    @staticmethod
    def get_farmers_connected_count(instance):
        """Returns connected farmers count."""
        connected_farmers = instance.get_suppliers().filter(
            type=NODE_TYPE_FARM
        )
        return connected_farmers.count()

    @staticmethod
    def get_transaction_count(instance):
        """Returns external count."""
        txn = ExternalTransaction.objects.filter(
            (Q(source=instance) | Q(destination=instance)) & Q(deleted=False)
        )
        return txn.count()
