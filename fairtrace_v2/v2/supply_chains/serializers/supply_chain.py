"""Serializers for supply chain related APIs."""
import copy

from common import library as comm_lib
from common.backends.sso import SSORequest
from common.drf_custom import fields as custom_fields
from common.drf_custom.serializers import DynamicModelSerializer
from common.exceptions import BadRequest
from django.db import transaction as django_transaction
from django.utils.timezone import datetime
from openpyxl import load_workbook
from rest_framework import serializers
from sentry_sdk import capture_exception
from v2.accounts.models import FairfoodUser
from v2.accounts.serializers import user as user_serializers
from v2.products import constants as prod_constants
from v2.products.models import Product
from v2.supply_chains.cache_resetters import reload_related_statistics
from v2.supply_chains.constants import (
    BULK_UPLOAD_TYPE_CONNECTION_ONLY, BULK_UPLOAD_TYPE_CONNECTION_TRANSACTION,
    CONNECTION_STATUS_CLAIMED, CONNECTION_STATUS_VERIFIED,
    INVITATION_TYPE_DIRECT, INVITATION_TYPE_INDIRECT, INVITE_RELATION_BUYER,
    INVITE_RELATION_CHOICES, INVITE_RELATION_SUPPLIER, NODE_DISCLOSURE_FULL,
    NODE_STATUS_ACTIVE, NODE_TYPE_FARM)
from v2.supply_chains.farmer_bulk.farmer_sheet import FarmerExcel
from v2.supply_chains.models import (AdminInvitation, BulkExcelUploads,
                                     Company, Connection, Farmer, Invitation,
                                     Label, Node, NodeSupplyChain, SupplyChain)
from v2.supply_chains.models.supply_chain import UploadFarmerMapping
from v2.supply_chains.models.profile import FarmerReference
from v2.supply_chains.serializers import node as node_serializers
from v2.supply_chains.serializers.node import (NodeSerializer,
                                               OperationSerializer)
from v2.supply_chains.serializers.public import NodeBasicSerializer
from v2.supply_chains.tasks import upload_bulk_connection_transaction
from v2.transactions import constants as trans_constants
from v2.transactions import constants as txn_constants

# from v2.supply_chains.cache_resetters import reload_statistics


class SupplyChainSerializer(serializers.ModelSerializer):
    """Serializer for SupplyChains."""

    id = custom_fields.IdencodeField()

    class Meta:
        """Meta Data."""

        model = SupplyChain
        fields = ("id", "name", "description", "image")


class InviteSerializer(node_serializers.NodeSerializer):
    """Serializer for Invitation."""

    connected_to = custom_fields.IdencodeField(
        serializer=node_serializers.CompanySerializer,
        related_model=Node,
        required=False,
    )
    supply_chain = custom_fields.IdencodeField(related_model=SupplyChain)
    products = custom_fields.ManyToManyIdencodeField(
        required=False, related_model=Product
    )
    supplier_for = custom_fields.ManyToManyIdencodeField(
        required=False, related_model=Node
    )
    buyer_for = custom_fields.ManyToManyIdencodeField(
        required=False, related_model=Node
    )
    map_all_suppliers = serializers.BooleanField(required=False, default=False)
    map_all_buyers = serializers.BooleanField(required=False, default=False)
    message = serializers.CharField(required=False, allow_blank=True)
    primary_operation = custom_fields.IdencodeField(
        serializer=OperationSerializer, required=False, allow_null=True
    )
    other_operations = custom_fields.ManyToManyIdencodeField(
        serializer=OperationSerializer, required=False
    )

    @django_transaction.atomic
    def serializer_create(self, validated_data, NodeModel):
        """Overriding the create method.

        - Add incharge
        - Update Creator
        - Update Updator
        """
        # TODO: update creator and updater from authentication and
        #  pop out creator in update methods
        try:
            inviter = self.context["view"].kwargs["node"]
            current_user = self.context["request"].user
        except Exception:
            inviter = self.context["node"]  # In case of bulk
            current_user = self.context["user"]
        validated_data["creator"] = current_user
        validated_data["updater"] = current_user
        connected_to = validated_data.pop("connected_to", inviter)
        supplier_for = validated_data.pop("supplier_for", [])
        buyer_for = validated_data.pop("buyer_for", [])
        map_all_suppliers = validated_data.pop("map_all_suppliers", False)
        map_all_buyers = validated_data.pop("map_all_buyers", False)
        supply_chain = validated_data.pop("supply_chain")
        relation = validated_data.pop("relation")
        message = validated_data.pop("message", "")

        if "node_object" in validated_data.keys():
            node = validated_data["node_object"].node_ptr
            incharge = validated_data["node_object"].incharge
        else:
            node = super(InviteSerializer, self).serializer_create(
                validated_data, NodeModel
            )
            # If test node is creating the connection, then the new node will
            # also be in test.
            if inviter.is_test:
                node.is_test = True
                node.save()
            incharge = validated_data.get("incharge", None)
            node.managers.add(inviter)
            if node.type == NODE_TYPE_FARM:
                node.managers.add(connected_to)
        if node == inviter:
            raise BadRequest("Cannot connect to yourself")

        access_node, created = NodeSupplyChain.objects.get_or_create(
            node=node, supply_chain=supply_chain
        )
        access_node.primary_operation = validated_data["primary_operation"]
        access_node.save()
        other_operations = None
        if "other_operations" in validated_data.keys():
            other_operations = validated_data["other_operations"]

        if other_operations:
            for operation in other_operations:
                access_node.other_operations.add(operation)

        if node.date_joined:
            connect_status = CONNECTION_STATUS_VERIFIED
        else:
            connect_status = CONNECTION_STATUS_CLAIMED

        if relation == INVITE_RELATION_BUYER:
            connection, created = Connection.objects.get_or_create(
                buyer=node, supplier=connected_to, supply_chain=supply_chain
            )
            if map_all_suppliers:
                buyer_for = connected_to.get_suppliers(
                    supply_chain=supply_chain)

            if not created:
                raise BadRequest("Connection already exists")

            connection.status = connect_status
            connection.creator = current_user
            connection.updater = current_user
            connection.save()
            connection.tag_suppliers(buyer_for)

        else:
            connection, created = Connection.objects.get_or_create(
                buyer=connected_to, supplier=node, supply_chain=supply_chain
            )

            if map_all_buyers:
                supplier_for = connected_to.get_buyers(
                    supply_chain=supply_chain)

            if not created:
                raise BadRequest("Connection already exists")

            connection.status = connect_status
            connection.creator = current_user
            connection.updater = current_user
            connection.save()
            connection.tag_buyers(supplier_for)

        if inviter in [connection.buyer, connection.supplier]:
            invite_type = INVITATION_TYPE_DIRECT
        else:
            invite_type = INVITATION_TYPE_INDIRECT
        invitation = Invitation.objects.create(
            inviter=inviter,
            connection=connection,
            message=message,
            creator=current_user,
            updater=current_user,
            type=invite_type,
            incharge=incharge,
            invitee=node,
            relation=relation,
        )
        inviter.stats.outdate()
        # reload_statistics.delay(inviter.stats.id)
        if node.is_company():
            django_transaction.on_commit(
                lambda: self.update_values(access_node, node)
            )
        else:
            django_transaction.on_commit(access_node.update_values)
        return invitation

    @staticmethod
    def update_values(access_node, node):
        """To perform function update_values."""
        access_node.update_values()
        node.stats.update_values()


class CompanyInviteSerializer(InviteSerializer):
    """Serializer for Company."""

    relation = serializers.ChoiceField(choices=INVITE_RELATION_CHOICES)
    incharge = user_serializers.PersonSerializer(required=False)
    name = serializers.CharField(required=False)
    company = custom_fields.IdencodeField(
        required=False,
        serializer=node_serializers.CompanySerializer,
        related_model=Company,
    )
    send_email = serializers.BooleanField(required=False, default=True)
    create_user_without_invitation = serializers.BooleanField(required=False, default=False)

    class Meta(node_serializers.NodeSerializer.Meta):
        """Meta data."""

        model = Company

    @django_transaction.atomic
    def create(self, validated_data):
        """Overriding the create method.

        - Add incharge
        - Update Creator
        - Update Updator
        """
        email_send = validated_data.pop("send_email", True)
        create_user_without_invitation = validated_data.pop("create_user_without_invitation", False)
        connected_to = validated_data.get("connected_to", None)
        relation = validated_data.get("relation", None)
        if "company" not in validated_data.keys():
            if "incharge" not in validated_data.keys():
                raise BadRequest("Incharge details not found")
            if (
                "phone" not in validated_data["incharge"]
                or not validated_data["incharge"]["phone"]
            ):
                validated_data["incharge"]["phone"] = validated_data.get(
                    "phone", ""
                )
            if (
                "email" not in validated_data["incharge"]
                or not validated_data["incharge"]["email"]
            ):
                validated_data["incharge"]["email"] = validated_data.get(
                    "email", ""
                )
            incharge_serializer = user_serializers.PersonSerializer(
                data=validated_data["incharge"],
                context={"request": self.context["request"]},
            )
            if not incharge_serializer.is_valid():
                raise BadRequest(incharge_serializer.errors)
            incharge = incharge_serializer.save()
            validated_data["incharge"] = incharge
            validated_data["email"] = incharge.email
            validated_data["phone"] = incharge.phone
            validated_data["status"] = NODE_STATUS_ACTIVE
            # if email_send or create_user_without_invitation:
            validated_data["admin"] = incharge.get_or_create_user()
        else:
            validated_data["node_object"] = validated_data["company"]
        instance = super(CompanyInviteSerializer, self).serializer_create(
            validated_data, Company
        )

        if "incharge" in validated_data:
            user = FairfoodUser.objects.get(email=incharge.email)
            user.is_active=True
            user.save()
            sso = SSORequest()
            args = sso.create_user(user)
            if not args[1]:
                sso.update_user(user)

            if user.is_fairtrace_admin:
                return None
            company = user.usernodes.all().last().node.company
            args = sso.create_node(company, user)
            if not args[1]:
                sso.update_node(company)
            # company.refresh_from_db()
            # sso.create_user_node(
            #     user, company)  

        if relation == INVITE_RELATION_BUYER and connected_to and \
            connected_to.is_company() and connected_to.features and \
            connected_to.features.link_connect and \
            instance.invitee.is_company() and not instance.invitee.external_id:
            #sent connect request as a buyer
            from v2.projects import connect as map_connect
            connect_api = map_connect.ConnectAPI()
            external_company_id = connect_api.create_company_as_buyer(
                instance.invitee.company, instance.inviter.company)
            if external_company_id:
                instance.invitee.external_id = external_company_id
                instance.invitee.save()

        instance.log_activity()
        if email_send:
            instance.send_invite()
        return instance

    def to_representation(self, instance):
        """Representation."""
        data = {"status": "Success", "id": instance.invitee.idencode}
        return data


class FarmerInviteSerializer(InviteSerializer):
    """Serializer for Farmer Invite."""

    # primary_operation = custom_fields.IdencodeField(
    #    serializer=OperationSerializer)
    # id_no = serializers.CharField(required=False)
    family_members = serializers.CharField(
        required=False, allow_null=True, allow_blank=True
    )
    farm_area = serializers.CharField(
        required=False, allow_null=True, allow_blank=True
    )
    income_from_main_product = serializers.CharField(
        required=False, allow_null=True, allow_blank=True
    )
    income_from_other_sources = serializers.CharField(
        required=False, allow_null=True, allow_blank=True
    )

    class Meta(node_serializers.NodeSerializer.Meta):
        """Meta data."""

        model = Farmer
    
    def validate(self, attrs):

        try:
            node = self.context["view"].kwargs["node"]
        except Exception:
            node = self.context["node"]
        if 'identification_no' in attrs and attrs['identification_no']:
            suppliers = node.map_supplier_pks()
            buyers = node.map_buyer_pks()
            ids = list(suppliers)+list(buyers)
            if FarmerReference.objects.filter(
                number=attrs['identification_no'], 
                farmer__node_ptr__in=ids
            ).exists():
                raise BadRequest(
                    "Identification Number Already Exists!", 
                    send_to_sentry=False
                )
        return super().validate(attrs)

    def validate_family_members(self, value):
        """To perform function validate_family_members."""
        if not value:
            return None
        try:
            return int(value)
        except ValueError:
            raise serializers.ValidationError("You must supply an integer")

    def validate_income_from_main_product(self, value):
        """To perform function validate_income_from_main_product."""
        if not value:
            return None
        try:
            return float(value)
        except ValueError:
            raise serializers.ValidationError("You must supply an float")

    @django_transaction.atomic
    def create(self, validated_data):
        """Overriding the create method.

        - Add incharge
        - Update Creator
        - Update Updator
        """
        validated_data["relation"] = INVITE_RELATION_SUPPLIER
        invitation = super(FarmerInviteSerializer, self).serializer_create(
            validated_data, Farmer
        )
        invitation.is_created = True
        return invitation

    def to_representation(self, instance):
        """Representation."""
        data = {
            "status": "Success",
            "id": instance.invitee.idencode,
            "is_created": instance.is_created,
        }
        return data


class ConnectionsSerializer(serializers.ModelSerializer):
    """Class to handle ConnectionsSerializer and functions."""

    managed_nodes = None
    supply_chain = None

    class Meta:
        model = Node
        fields = ("idencode", "full_name", "latitude", "longitude", "status")

    def can_manage(self, node):
        """To perform function can_manage."""
        return node in self.managed_nodes

    def can_read(self, node):
        """To perform function can_read."""
        return (
            node.disclosure_level == NODE_DISCLOSURE_FULL
            or node in self.managed_nodes
        )

    def get_node_data(self, nodes, tier_data, supply_chain_id):
        """To perform function get_node_data."""
        if not supply_chain_id:
            encoded_supply_chain_id = self.context["request"].query_params.get(
                "supply_chain", None
            )
            supply_chain_id = comm_lib._decode(encoded_supply_chain_id)
        data = []
        for node in nodes:
            node_data = NodeBasicSerializer(
                node,
                tier_data=tier_data,
                pseudonymize=not (self.can_read(node)),
                can_manage=self.can_manage(node),
            ).data
            # add primary_operation to the node list.
            node_data["primary_operation"] = {"id": None, "name": None}
            if supply_chain_id:
                nsc = node.nodesupplychain_set.filter(
                    supply_chain_id=supply_chain_id,
                    primary_operation__isnull=False,
                ).first()
                if nsc:
                    node_data["primary_operation"] = {
                        "id": nsc.primary_operation.idencode,
                        "name": nsc.primary_operation.name,
                    }
            data.append(node_data)
        return data

    def get_connection_data(self, instance, sc_id=None):
        """To perform function get_connection_data."""
        if not sc_id:
            sc_id = comm_lib._decode(
                self.context["request"].query_params.get("supply_chain", None)
            )
        try:
            supply_chain = SupplyChain.objects.get(id=sc_id)
        except Exception:
            raise BadRequest("Invalid SupplyChain ID")
        self.managed_nodes = instance.get_managed_nodes(
            supply_chain=supply_chain
        )
        self.supply_chain = supply_chain

        supplier_query, supplier_tier_data = instance.get_supplier_chain(
            include_self=True, supply_chain=supply_chain
        )
        buyer_query, buyer_tier_data = instance.get_buyer_chain(
            supply_chain=supply_chain
        )
        supplier_data = self.get_node_data(
            supplier_query, supplier_tier_data, sc_id
        )
        # node_serializers.NodeBasicSerializer(
        #     supplier_query, many=True, tier_data=supplier_tier_data,
        #     supply_chain=supply_chain, base_node=instance).data
        buyer_data = self.get_node_data(buyer_query, buyer_tier_data, sc_id)
        # buyer_data = node_serializers.NodeBasicSerializer(
        #     buyer_query, many=True, tier_data=buyer_tier_data,
        #     supply_chain=supply_chain, base_node=instance).data
        supplier_data_sorted = sorted(supplier_data, key=lambda i: i["tier"])
        buyer_data_sorted = sorted(
            buyer_data, key=lambda i: i["tier"], reverse=True
        )
        data = supplier_data_sorted + buyer_data_sorted
        return data


class MapConnectionsSerializer(ConnectionsSerializer):
    """Class to handle MapConnectionsSerializer and functions."""

    class Meta(ConnectionsSerializer.Meta):
        pass

    def to_representation(self, instance, sc_id=None):
        """To perform function to_representation."""
        connection_data = super(
            MapConnectionsSerializer, self
        ).get_connection_data(instance, sc_id)
        return {"chain": connection_data}


class TableConnectionsSerializer(ConnectionsSerializer):
    """Class to handle TableConnectionsSerializer and functions."""

    class Meta(ConnectionsSerializer.Meta):
        pass

    def to_representation(self, instance):
        """To perform function to_representation."""
        connection_data = super(
            TableConnectionsSerializer, self
        ).get_connection_data(instance)
        chain_dict = {}
        for item in connection_data:
            comm_lib._safe_append_to_dict_key(chain_dict, item["tier"], item)

        return {"chain": chain_dict}


class FarmerTemplateSerializer(serializers.ModelSerializer):
    """Serializer to validate uploaded excel."""

    user = custom_fields.KWArgsObjectField(
        related_model=FairfoodUser, write_only=True
    )
    node = custom_fields.KWArgsObjectField(related_model=Node, write_only=True)
    supply_chain = custom_fields.IdencodeField(
        related_model=SupplyChain, write_only=True, required=False
    )
    file = serializers.FileField(write_only=True)

    class Meta:
        model = BulkExcelUploads
        fields = ("user", "node", "supply_chain", "file")

    def validate(self, attrs):
        """To perform function validate."""
        if "file" not in attrs:
            raise serializers.ValidationError("File not attached.")
        return attrs

    def check_duplicate_hash(self, file_hash):
        """Function for check the file is already used or not."""
        try:
            bulkexcelupload = BulkExcelUploads.objects.get(
                file_hash=file_hash, used=True
            )
            message = txn_constants.DUPLICATE_TXN_MSG % (
                str(bulkexcelupload.updated_on.strftime("%d %B %Y"))
            )
            return True, message
        except Exception:
            return False, None

    def create_bulk_upload_file(self, validated_data, data):
        """Function for create bulk excel upload file."""
        validated_data["data"] = data
        validated_data["creator"] = validated_data.pop("user")
        validated_data["updater"] = validated_data["creator"]
        validated_data["type"] = BULK_UPLOAD_TYPE_CONNECTION_ONLY
        validated_data["farmers_to_add"] = data["farmers_to_add"]
        validated_data["farmers_to_update"] = data["farmers_to_update"]

        bulk_file = super(FarmerTemplateSerializer, self).create(
            validated_data
        )
        return bulk_file

    def check_fair_id(self, encoded_id):
        """Function for verify fair_id in excel is valid or not."""
        is_farmer = True
        farmer_encoded_id = encoded_id
        if farmer_encoded_id:
            farmer_id = comm_lib._decode(farmer_encoded_id)
            farmer_object = Farmer.objects.filter(id=farmer_id)
            if not farmer_object:
                is_farmer = False
        return is_farmer

    def create(self, validated_data):
        """To perform function create."""
        res = BulkExcelUploads.is_file_exists(
            validated_data["file"], validated_data["node"]
        )
        validated_data["file_hash"] = res["file_hash"]
        if res["valid"]:
            data = {
                "valid": False,
                "message": res["message"],
                "status": txn_constants.DUPLICATE_TXN,
            }
            return data
        try:
            wb = load_workbook(validated_data["file"], data_only=True)
        except Exception:
            raise BadRequest("Could not read this file. Format incorrect")
        try:
            sc_id = comm_lib._decode(
                self.context["request"].query_params["supply_chain"]
            )
            supply_chain = SupplyChain.objects.get(id=sc_id)
        except Exception:
            supply_chain = None
        excel = FarmerExcel(workbook=wb)
        data = excel.validate(validated_data["node"], supply_chain)

        for row_data in data["excel_data"]["row_data"]:
            is_farmer = self.check_fair_id(row_data["id"]["value"])
            if not is_farmer:
                msg = txn_constants.FILE_CORRUPTED_MSG % "FairID"
                response = {
                    "valid": False,
                    "message": msg,
                    "status": txn_constants.FILE_CORRUPTED_STATUS,
                }
                return response

        bulk_file = self.create_bulk_upload_file(validated_data, data)
        data["farmers"] = data["excel_data"].pop("row_data")
        data.pop("excel_data")
        data["file"] = bulk_file.idencode
        return data

    def to_representation(self, data):
        """To perform function to_representation."""
        return data


# class FarmerTemplateSerializer(serializers.Serializer):
#     """ Serializer to validate uploaded excel """
#     file = custom_fields.BulkTemplateField(
#         excel_template=FarmerExcel)
#
#     class Meta:
#         fields = ('file',)
#
#     def create(self, validated_data):
#         return validated_data
#
#     def to_representation(self, instance):
#         file = instance.pop('file')
#         instance['valid'] = file['valid']
#         instance['message'] = file['message']
#         instance['farmers'] = file['excel_data']['row_data']
#         return instance


class FarmerBulkSerializer(serializers.ModelSerializer):
    """Serializer for Bulk Invitation of farmers."""

    id = custom_fields.IdencodeField(read_only=True)
    user = custom_fields.KWArgsObjectField(
        related_model=FairfoodUser, write_only=True
    )
    node = custom_fields.KWArgsObjectField(related_model=Node, write_only=True)

    file = custom_fields.IdencodeField(
        related_model=BulkExcelUploads, required=False, write_only=True
    )
    connected_to = custom_fields.IdencodeField(
        related_model=Node, required=False, write_only=True
    )
    supply_chain = custom_fields.IdencodeField(
        related_model=SupplyChain, required=False, write_only=True
    )
    supplier_for = custom_fields.ManyToManyIdencodeField(
        related_model=Node, required=False, write_only=True
    )

    farmers = serializers.ListField(
        allow_empty=False, write_only=True, required=False
    )

    class Meta:
        model = BulkExcelUploads
        fields = (
            "id",
            "user",
            "node",
            "supply_chain",
            "file",
            "connected_to",
            "supplier_for",
            "farmers",
            "file_hash",
            "used",
        )

    def validate_connected_to(self, value):
        """To perform function validate_connected_to."""
        return value.id

    def validate_supplier_for(self, value):
        """To perform function validate_supplier_for."""
        return [i.id for i in value]

    def create(self, validated_data):
        """To perform function create."""
        file = validated_data.pop("file", None)
        user = validated_data.pop("user")
        node = validated_data.pop("node")
        supply_chain = validated_data.pop("supply_chain")
        bulk_temp_data = {
            "data": validated_data,
            "node": node,
            "supply_chain": supply_chain,
            "type": BULK_UPLOAD_TYPE_CONNECTION_TRANSACTION,
            "updater": user,
            "used": True,
        }
        bulk_file = super(FarmerBulkSerializer, self).update(
            instance=file, validated_data=bulk_temp_data
        )
        django_transaction.on_commit(
            lambda: upload_bulk_connection_transaction.delay(bulk_file.id)
        )
        return bulk_file


class FarmerBulkInviteSerializerAsync(serializers.Serializer):
    """Serializer for Bulk Invitation of farmers."""

    user = custom_fields.IdencodeField(
        related_model=FairfoodUser, write_only=True
    )
    node = custom_fields.IdencodeField(related_model=Node, write_only=True)

    connected_to = serializers.CharField(required=False)
    supply_chain = serializers.CharField(required=False)
    supplier_for = serializers.ListField(required=False)

    farmers = serializers.ListField(allow_empty=False)

    def validate(self, data):
        """To perform function validate."""
        # farmers_list = attrs['farmers']
        node = data["node"]
        current_user = data["user"]
        farmer_list = data.pop("farmers")

        farmers_data_list = []
        for farmer in farmer_list:
            if "id" in farmer and farmer["id"]:
                farmer_encoded_id = farmer.pop("id")
                farmer_id = comm_lib._decode(farmer_encoded_id)
                farmer_object = Farmer.objects.get(id=farmer_id)
                if not node.can_manage(farmer_object):
                    raise serializers.ValidationError(
                        f"Cannot update farmer {farmer_object.full_name}"
                    )
                farmer["updater"] = current_user.idencode
                farmers_data = {"id": farmer_object.id, "data": farmer}
            else:
                temp_data = copy.deepcopy(data)
                temp_data["user"] = temp_data["user"].id
                temp_data["node"] = temp_data["node"].id
                farmers_data = {"id": None, "data": {**temp_data, **farmer}}

            try:
                transaction_data = {}
                transaction_data["product"] = farmers_data["data"][
                    "product_id"
                ]
                transaction_data["date"] = farmers_data["data"][
                    "transaction_date"
                ]
                transaction_data["unit"] = farmers_data["data"]["unit"]
                transaction_data["currency"] = farmers_data["data"]["currency"]
                transaction_data["invoice_number"] = farmers_data["data"][
                    "invoice_number"
                ]

                quantity = farmers_data["data"]["quantity"]
                quantity = float(quantity) if quantity else 0
                transaction_data["quantity"] = quantity

                price_per_unit = farmers_data["data"]["price_per_unit"]
                price_per_unit = float(price_per_unit) if price_per_unit else 0
                # price = quantity * price_per_unit
                transaction_data["price"] = price_per_unit

                for k, val in transaction_data.items():
                    if k != "invoice_number":
                        assert val
            except KeyError as e:
                capture_exception(e)
                transaction_data = {}
            except AssertionError as e:
                capture_exception(e)
                transaction_data = {}
            except Exception as e:
                capture_exception(e)
                raise e

            farmers_data["transaction_data"] = transaction_data
            farmers_data_list.append(farmers_data)

        data["farmers"] = farmers_data_list
        return data

    # @django_transaction.atomic
    def create(self, validated_data):
        """To perform function create."""
        total = len(validated_data["farmers"])
        success = 0
        to_add = 0
        added = 0
        to_update = 0
        updated = 0
        transaction_to_add = 0
        transaction_added = 0
        errors = []
        farmer_list = []
        for farmer_data in validated_data["farmers"]:
            if farmer_data["id"]:
                to_update += 1
                farmer_serializer = node_serializers.FarmerSerializer(
                    instance=Farmer.objects.get(id=farmer_data["id"]),
                    data=farmer_data["data"],
                    partial=True,
                    context=self.context,
                )
                if not farmer_serializer.is_valid():
                    errors.append(farmer_serializer.errors)
                    break
                farmer = farmer_serializer.save()
                updated += 1
            else:
                farmer_data["data"]["supply_chain"] = validated_data[
                    "supply_chain"
                ]
                to_add += 1
                farmer_invite_serializer = FarmerInviteSerializer(
                    data=farmer_data["data"], context=self.context
                )
                if not farmer_invite_serializer.is_valid():
                    errors.append(farmer_invite_serializer.errors)
                    break
                farmer = farmer_invite_serializer.save().invitee
                added += 1
                farmer_list.append(farmer)
            # Add or update primary_operation in NodeSupplyChain
            NodeSupplyChain.objects.filter(
                node_id=farmer.id,
                supply_chain=comm_lib._decode(validated_data["supply_chain"]),
            ).update(
                primary_operation_id=comm_lib._decode(
                    farmer_data["data"]["primary_operation"]
                )
            )

            if farmer_data["transaction_data"]:
                time = datetime.now().time()
                date = (
                    farmer_data["transaction_data"]["date"] + "-" + str(time)
                )
                farmer_data["transaction_data"]["date"] = datetime.strptime(
                    date, "%d-%m-%Y-%H:%M:%S.%f"
                )
                transaction_to_add += 1
                from v2.transactions.serializers.external import \
                    ExternalTransactionSerializer

                farmer_data["transaction_data"]["node"] = farmer.idencode
                farmer_data["transaction_data"][
                    "type"
                ] = trans_constants.EXTERNAL_TRANS_TYPE_INCOMING
                # through excel always create txn object, if txn is also
                # duplicate. so pass force_create key as true.
                farmer_data["transaction_data"]["force_create"] = True
                transaction_serializer = ExternalTransactionSerializer(
                    data=farmer_data["transaction_data"], context=self.context
                )
                if not transaction_serializer.is_valid():
                    raise serializers.ValidationError(
                        transaction_serializer.errors
                    )
                transaction_serializer.save()
                transaction_added += 1
            success += 1
        self._update_upload_farmer_mapping(farmer_list)

        resp = {
            "farmers_to_add": to_add,
            "farmers_added": added,
            "farmers_to_update": to_update,
            "farmers_updated": updated,
            "transaction_to_add": transaction_to_add,
            "transaction_added": transaction_added,
            "total": total,
            "success": success,
            "errors": errors,
        }
        return resp

    def to_representation(self, instance):
        """To perform function to_representation."""
        return instance

    def _update_upload_farmer_mapping(self, farmers):
        """Updates the upload-farmer mapping for the provided list of farmers.

        This method creates UploadFarmerMapping objects to establish a mapping
        between each farmer in the given list and the bulk file provided in the
        context.

        Args:
            farmers (list): A list of Farmer objects representing the farmers
            to update the mapping for.

        Notes:
            - The bulk file object should be available in the context under the
              key 'bulk_file'.
            - The method uses the bulk_create() method to efficiently create
              multiple UploadFarmerMapping objects in a single database query.
        """
        bulk_file = self.context.get("bulk_file")
        if bulk_file:
            data = map(
                lambda farmer: UploadFarmerMapping(
                    farmer=farmer, upload=bulk_file
                ),
                farmers,
            )
            UploadFarmerMapping.objects.bulk_create(
                data, ignore_conflicts=True
            )


class ResendInviteSerializer(serializers.Serializer):
    """Serializer for resend companies which is not joined."""

    user = custom_fields.KWArgsObjectField(
        related_model=FairfoodUser, write_only=True
    )
    supply_chain = custom_fields.IdencodeField(related_model=SupplyChain)
    node = custom_fields.IdencodeField(related_model=Node)
    message = serializers.CharField(required=False, allow_blank=True)

    def create(self, validated_data):
        """Overriding the create method."""

        inviter = self.context["view"].kwargs["node"]
        invitee = validated_data["node"]
        supply_chain = validated_data["supply_chain"]
        message = validated_data.get("message", "")
        invites = Invitation.objects.filter(
            connection__supply_chain=supply_chain,
            invitee=invitee,
            inviter=inviter,
        )
        for invitation in invites:
            if message and not invitation.message:
                invitation.message = message
                invitation.save()
            invitation.send_invite(validated_data["user"])
        return {"status": True, "message": "Invite sent"}

    def to_representation(self, instance):
        """To perform function to_representation."""
        return instance


class UpdateTagSerializer(serializers.Serializer):
    """Serializer to update the tags of the direct connections of the signed in
    node."""

    supplier_for = custom_fields.ManyToManyIdencodeField(
        required=False, related_model=Node, allow_blank=True
    )
    buyer_for = custom_fields.ManyToManyIdencodeField(
        required=False, related_model=Node, allow_blank=True
    )
    supply_chain = custom_fields.IdencodeField(related_model=SupplyChain)

    def update(self, instance, validated_data):
        """To perform function update."""
        base_node = self.context["view"].kwargs.get("node", None)
        connection = None
        if "supplier_for" in validated_data:
            connections = Connection.objects.filter(
                buyer=base_node,
                supplier=instance,
                supply_chain=validated_data["supply_chain"],
            )
            if not connections.exists():
                raise BadRequest(
                    "Not connected. You can only change tags of your direct"
                    " connection"
                )
            connection = connections[0]
            for tag in connection.buyer_tags.exclude(
                buyer_connection__buyer__in=validated_data["supplier_for"]
            ):
                # looped over tags to call delete method in model
                tag.delete()
            connection.tag_buyers(validated_data["supplier_for"])
        if connection:
            django_transaction.on_commit(
                lambda: reload_related_statistics.delay(connection.supplier.id)
            )
        if "buyer_for" in validated_data:
            connections = Connection.objects.filter(
                buyer=instance,
                supplier=base_node,
                supply_chain=validated_data["supply_chain"],
            )
            if not connections.exists():
                raise BadRequest(
                    "Not connected. You can only change tags of your direct"
                    " connection"
                )
            connection = connections[0]
            for tag in connection.supplier_tags.exclude(
                supplier_connection__supplier__in=validated_data["buyer_for"]
            ):
                # looped over tags to call delete method in model
                tag.delete()
            connection.tag_suppliers(validated_data["buyer_for"])
        if connection:
            django_transaction.on_commit(
                lambda: reload_related_statistics.delay(connection.buyer.id)
            )
        # if connection:
        #     django_transaction.on_commit(
        #         lambda: recompute_connection_cache.delay(connection.id))
        return True

    def to_representation(self, instance):
        """To perform function to_representation."""
        return {"status": True, "message": "Tag updated"}


class NodeSupplyChainSerializer(serializers.ModelSerializer):
    """Serializer for NodeSupplyChain."""

    id = custom_fields.IdencodeField(read_only=True)
    supply_chain = custom_fields.IdencodeField(
        serializer=SupplyChainSerializer
    )
    primary_operation = custom_fields.IdencodeField(
        serializer=OperationSerializer, required=False, allow_null=True
    )
    verifier = serializers.BooleanField(required=False)

    class Meta:
        """Meta Data."""

        model = NodeSupplyChain
        fields = (
            "id",
            "supply_chain",
            "tier_count",
            "farmer_count",
            "company_count",
            "primary_operation",
            "other_operations",
            "verifier",
        )


class AddNodeSupplyChainSerializer(serializers.Serializer):
    """Serializer for NodeSupplyChain."""

    supply_chains = NodeSupplyChainSerializer(many=True)
    primary_operation = custom_fields.IdencodeField(
        required=False, allow_null=True
    )
    other_operations = custom_fields.ManyToManyIdencodeField(
        serializer=OperationSerializer, required=False
    )

    class Meta:
        """Meta Data."""

        fields = ("supply_chain", "primary_operation", "other_operations")

    def create(self, validated_data):
        """To perform function create."""
        supply_chains = validated_data.pop("supply_chains")
        node_id = self.context["view"].kwargs["pk"]
        node = Node.objects.get(id=node_id)

        admin_invitation = AdminInvitation.objects.create(invitee=node)

        node_supply_chains = {"node": {"id": comm_lib._encode(node_id)}}
        supply_chain_data = []
        for data in supply_chains:
            node_supply_chain, created = NodeSupplyChain.objects.get_or_create(
                node=node, supply_chain=data["supply_chain"]
            )
            node_supply_chain.primary_operation = data["primary_operation"]
            node_supply_chain.save()
            admin_invitation.node_supply_chains.add(node_supply_chain)
            if not created:
                raise BadRequest("SupplyChain already exists")

            try:
                supplychain = {
                    "id": data["supply_chain"].idencode,
                    "name": data["supply_chain"].name,
                }
            except Exception:
                pass

            supply_chain_data.append(supplychain)

        node_supply_chains["supply_chain"] = supply_chain_data
        admin_invitation.send_invite()
        admin_invitation.log_activity()
        node.stats.update_values()
        return node_supply_chains

    def to_representation(self, instance):
        """To perform function to_representation."""
        return instance


class NodeSearch:
    """Class to search a node in the connections of another node."""

    base_node = None
    supply_chain = None

    def __init__(self, base_node=None, supply_chain=None):
        """To perform function __init__."""
        self.base_node = base_node
        self.supply_chain = supply_chain

    def search_node(self, target):
        """To perform function search_node."""
        connections = self.base_node.search_node(target, self.supply_chain)
        paths = []
        managed_nodes = self.base_node.get_managed_nodes(
            supply_chain=self.supply_chain
        )
        for connection in connections:
            sc_data = SupplyChainSerializer(connection["supply_chain"]).data
            path = []
            for node in connection["path"]:
                can_read = False
                if (
                    node.disclosure_level == NODE_DISCLOSURE_FULL
                    or node in managed_nodes
                ):
                    can_read = True
                path.append(
                    NodeBasicSerializer(node, pseudonymize=(not can_read)).data
                )
            path = {
                "supply_chain": sc_data,
                "connection": {
                    "id": connection["connection"].idencode,
                    "connection_status": connection["connection"].status,
                },
                "tier": connection["tier"],
                "path": path,
                "labels": [],
            }
            if connection["tier"] == 1:
                path["labels"] = [
                    LabelSerializer(i).data
                    for i in connection["connection"].labels.all()
                ]
            paths.append(path)

        return paths


class LabelSerializer(serializers.ModelSerializer):
    """Serializer to list the labels in the system."""

    id = custom_fields.IdencodeField(read_only=True)
    added_by = custom_fields.IdencodeField(read_only=True)
    supply_chains = custom_fields.ManyToManyIdencodeField(
        related_model=SupplyChain, write_only=True
    )
    node = custom_fields.KWArgsObjectField(write_only=True, source="added_by")
    removable = serializers.BooleanField(read_only=True)

    class Meta:
        model = Label
        fields = (
            "id",
            "name",
            "node",
            "added_by",
            "supply_chains",
            "removable",
        )

    def to_representation(self, instance):
        """To perform function to_representation."""
        data = super(LabelSerializer, self).to_representation(instance)
        data["supply_chains"] = []
        for sc in instance.supply_chains.all():
            sc_data = SupplyChainSerializer(sc).data
            sc_data["count"] = instance.connections.filter(
                supply_chain=sc
            ).count()
            data["supply_chains"].append(sc_data)
        return data


class ConnecionLabelSerializer(serializers.ModelSerializer):
    """Serializer to add or remove connection labels."""

    node = custom_fields.KWArgsObjectField()
    labels = custom_fields.ManyToManyIdencodeField(related_model=Label)

    class Meta:
        model = Connection
        fields = (
            "node",
            "labels",
        )

    def update(self, connection, validated_data):
        """To perform function update."""
        labels = []
        for label in validated_data["labels"]:
            if label not in connection.labels.all():
                connection.labels.add(label)
            labels.append(label)

        connection.labels.remove(
            *connection.labels.exclude(id__in=validated_data["labels"])
        )

        django_transaction.on_commit(lambda: connection.update_graph_node())
        return {
            "status": "Success",
            "message": "Labels updated",
            "labels": [
                {"id": i.id, "name": i.name} for i in connection.labels.all()
            ],
        }

    def to_representation(self, data):
        """Representation."""
        return data


class ProductSerializer(serializers.ModelSerializer):
    """Product serializer."""

    id = custom_fields.IdencodeField(read_only=True)
    user = custom_fields.KWArgsObjectField(write_only=True)
    supply_chain = custom_fields.IdencodeField(
        serializer=SupplyChainSerializer
    )
    image = serializers.FileField(
        max_length=None, allow_empty_file=True, allow_null=True, required=False
    )

    class Meta:
        model = Product
        fields = (
            "id",
            "user",
            "name",
            "supply_chain",
            "description",
            "image",
            "image_name",
        )

    def create(self, validated_data):
        """To perform function create."""
        user = validated_data.pop("user")
        validated_data["creator"] = user
        validated_data["updater"] = user
        validated_data["type"] = prod_constants.PRODUCT_TYPE_GLOBAL
        if "image" in validated_data:
            validated_data["image_name"] = validated_data["image"]

        existing_products = Product.objects.filter(
            name__iexact=validated_data["name"],
            supply_chain=validated_data["supply_chain"],
        )
        if existing_products.exists():
            raise BadRequest("Product already exists")
        else:
            product = super(ProductSerializer, self).create(validated_data)
            product.create_token()
        return product


class ConnectionNodeSerializer(DynamicModelSerializer):
    """Serializer for the ConnectionNode model.

    This serializer provides serialization and deserialization of Node
    involved in a Connection. It inherits from DynamicModelSerializer,
    allowing dynamic field selection based on the request.
    """

    can_manage = serializers.SerializerMethodField()
    can_read = serializers.SerializerMethodField()
    managers = NodeSerializer(
        many=True, read_only=True, fields=["id", "full_name"]
    )
    email_sent = serializers.SerializerMethodField()
    connection_details = serializers.SerializerMethodField()
    primary_operation = serializers.SerializerMethodField()

    class Meta:
        model = Node
        fields = [
            "id",
            "full_name",
            "can_manage",
            "can_read",
            "managers",
            "type",
            "email_sent",
            "status",
            "connection_details",
            "primary_operation",
        ]

    def get_can_manage(self, instance):
        """Determine if the current user can manage the given Connection."""
        try:
            node = self.context["view"].kwargs.get("node")
        except KeyError:
            return False

        managed_nodes_pks = self.get_managers(instance)

        return node.pk in managed_nodes_pks

    def get_can_read(self, instance):
        """Determine if the current user can read the given Connection."""

        try:
            node = self.context["view"].kwargs.get("node")
        except KeyError:
            return None

        managed_nodes_pks = self.get_managers(instance)

        return (
            node.disclosure_level == NODE_DISCLOSURE_FULL
            or node.pk in managed_nodes_pks
        )

    def get_managers(self, instance):
        """Retrieve the managed nodes associated with the given Connection."""

        try:
            view = self.context["view"]
            if not hasattr(view, "get_supply_chain"):
                return []
            supply_chain = view.get_supply_chain()
        except KeyError:
            supply_chain = None
        managers = instance.managers.all()
        managers = managers.union(
            instance.get_suppliers(supply_chain=supply_chain))
        managers = managers.union(
            instance.get_buyers(supply_chain=supply_chain))

        return managers.values_list("id", flat=True)

    def get_email_sent(self, instance):
        """Determine if the email has been sent to the given Connection."""

        try:
            node = self.context["view"].kwargs.get("node")
        except KeyError:
            return None

        invitations = instance.invitations_received.filter(inviter=node)
        if not invitations.exists():
            return False
        return any(invitations.values_list("email_sent", flat=True))

    def get_connection_details(self, instance):
        """Determine if the tier of the given Connection."""
        try:
            node = self.context["view"].kwargs.get("node")
        except KeyError:
            return None

        try:
            view = self.context["view"]
            if not hasattr(view, "get_supply_chain"):
                return []
            supply_chain = view.get_supply_chain()
        except KeyError:
            supply_chain = None

        tier, connection_type, status = instance.get_tier(
            supply_chain=supply_chain, target_node=node.graph_node
        )

        return {
            "tier": tier,
            "connection_type": connection_type,
            "node": node.idencode,
            "status": status,
        }

    def get_primary_operation(self, instance):
        """Get primary operation."""
        try:
            view = self.context["view"]
            if not hasattr(view, "get_supply_chain"):
                return []
            supply_chain = view.get_supply_chain()
        except KeyError:
            supply_chain = None

        if supply_chain:
            nsc = instance.nodesupplychain_set.filter(
                supply_chain=supply_chain,
                primary_operation__isnull=False,
            ).first()
            if nsc:
                return {
                    "id": nsc.primary_operation.idencode,
                    "name": nsc.primary_operation.name,
                }
        return {"id": None, "name": None}

    def to_representation(self, instance):
        """Representation."""
        data = super().to_representation(instance)
        if not self.get_can_read(instance):
            data["full_name"] = "Anonymous"
        return data
