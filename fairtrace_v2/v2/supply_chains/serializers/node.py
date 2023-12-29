"""Serializers for node related APIs."""
import json

from common import library as comm_lib
from common.country_data import COUNTRIES
from common.country_data import DIAL_CODE_NAME_MAP
from common.drf_custom import fields as custom_fields
from common.drf_custom.serializers import DynamicModelSerializer
from common.exceptions import BadRequest
from django.core.exceptions import ObjectDoesNotExist
from django.core.exceptions import ValidationError
from django.db import IntegrityError
from django.db import transaction
from rest_framework import serializers
from v2.accounts.constants import USER_STATUS_COMPANY_ADDED
from v2.accounts.models import FairfoodUser
from v2.accounts.serializers import user as user_serializers
from v2.activity import constants as act_constants
from v2.activity.models import Activity
from v2.dashboard.models import NodeStats
from v2.supply_chains import constants
from v2.supply_chains.constants import NODE_DISCLOSURE_CUSTOM
from v2.supply_chains.constants import NODE_MEMBER_TYPE_ADMIN
from v2.supply_chains.constants import VISIBLE_FIELDS
from v2.supply_chains.models import BlockchainWallet
from v2.supply_chains.models import Company
from v2.supply_chains.models import Farmer
from v2.supply_chains.models import Node
from v2.supply_chains.models import NodeDocument
from v2.supply_chains.models import NodeFeatures
from v2.supply_chains.models import NodeMember
from v2.supply_chains.models import NodeSupplyChain
from v2.supply_chains.models import Operation
from v2.supply_chains.models import SupplyChain

from .public import NodeBasicSerializer


# from v2.supply_chains.cache_resetters import reload_statistics


# from v2.supply_chains.cache_resetters import reload_statistics


class SupplyChainSerializer(serializers.ModelSerializer):
    """Serializer for SupplyChains."""

    id = custom_fields.IdencodeField()

    class Meta:
        """Meta Data."""

        model = SupplyChain
        fields = ("id", "name", "description", "image")


class NodeFeaturesSerializer(serializers.ModelSerializer):
    """Serialize available features of a node."""

    class Meta:
        model = NodeFeatures
        fields = ("dashboard_theming", "consumer_interface_theming")


class ValidateCompanyNameSerializer(serializers.Serializer):
    """Serializer to check the username availability."""

    name = serializers.CharField()

    def to_representation(self, obj):
        """Overriding the value returned when returning th serializer."""
        data = {}
        if Company.objects.filter(name=obj["name"]).exists():
            data["available"] = False
            data["valid"] = False
            data["message"] = "Company name already taken"
        else:
            data["available"] = True
            data["valid"] = True
            data["message"] = "Company name available"
        return data


class OperationSerializer(serializers.ModelSerializer):
    """Serializer for Operations."""

    id = custom_fields.IdencodeField(read_only=True)
    name = serializers.CharField()

    class Meta:
        model = Operation
        fields = ("id", "name", "node_type")


class NodeMemberSerializer(serializers.ModelSerializer):
    """Serializer for NodeMember."""

    id = custom_fields.IdencodeField(read_only=True)
    node = custom_fields.IdencodeField(
        serializer="NodeSerializer", read_only=True
    )
    user = custom_fields.IdencodeField(
        serializer=user_serializers.UserSerializer, required=False
    )

    first_name = serializers.CharField(required=False)
    last_name = serializers.CharField(required=False)
    email = serializers.CharField(required=False)
    dob = serializers.DateField(required=False)
    phone = custom_fields.PhoneNumberField(required=False, allow_blank=True)
    address = serializers.CharField(required=False)
    image = serializers.ImageField(required=False)
    type = serializers.IntegerField(required=True)

    terms_accepted = serializers.BooleanField(required=False)
    privacy_accepted = serializers.BooleanField(required=False)
    email_verified = serializers.BooleanField()

    password = serializers.CharField(write_only=True, required=False)

    class Meta:
        model = NodeMember
        fields = [
            "id",
            "first_name",
            "last_name",
            "email",
            "dob",
            "phone",
            "address",
            "password",
            "terms_accepted",
            "privacy_accepted",
            "email_verified",
            "type",
            "image",
            "node",
            "user",
        ]

    def to_representation(self, instance):
        """To perform function to_representation."""
        pf = custom_fields.PhoneNumberField()
        phone = pf.to_representation(instance.user.phone)
        data = {
            "id": instance.idencode,
            "node_id": instance.node.idencode,
            "node": instance.node.full_name,
            "user_id": instance.user.idencode,
            "first_name": instance.user.first_name,
            "last_name": instance.user.last_name,
            "email": instance.user.email,
            "type": instance.type,
            "active": instance.active,
            "image": instance.user.image_url,
            "phone": phone,
        }
        return data

    def create(self, validated_data):
        """Overriding create to send email."""
        validated_data["node"] = self.context["view"].kwargs["node"]
        current_user = self.context["request"].user
        validated_data["creator"] = current_user
        validated_data["updater"] = current_user
        validated_data["status"] = USER_STATUS_COMPANY_ADDED
        _type = validated_data.pop("type", None)
        if "user" not in validated_data.keys():
            try:
                validated_data["user"] = FairfoodUser.objects.get(
                    email=validated_data["email"]
                )
            except Exception:
                user_serializer = user_serializers.UserSerializer(
                    data=validated_data
                )
                if not user_serializer.is_valid():
                    raise BadRequest(user_serializer.errors)
                user = user_serializer.save()
                validated_data["user"] = user

        extra_keys = list(
            set([field.name for field in NodeMember._meta.get_fields()])
            ^ set([*validated_data])
        )
        comm_lib._pop_out_from_dictionary(validated_data, extra_keys)

        member, created = NodeMember.objects.get_or_create(
            node=validated_data["node"], user=validated_data["user"]
        )
        if created:
            member.type = _type
            member.creator = current_user
            member.updater = current_user
            member.save()
            member.send_invite(current_user)
            member.log_added_activity()
            member.unhide_notifications()
        mem_user = member.user
        mem_user.status = USER_STATUS_COMPANY_ADDED
        mem_user.save()
        return member

    def update(self, instance, validated_data):
        """To perform function update."""
        current_user = self.context["view"].kwargs["user"]
        user_fields = ["first_name", "last_name"]

        user_data = {
            i: validated_data[i] for i in user_fields if i in validated_data
        }
        if user_data:
            user_serializer = user_serializers.UserSerializer(
                instance.user, user_data, partial=True
            )
            if not user_serializer.is_valid():
                raise serializers.ValidationError(user_serializer.errors)
            user_serializer.save()

        if "email" in validated_data:
            if FairfoodUser.objects.filter(
                email=validated_data["email"]
            ).exists():
                raise serializers.ValidationError("Email already taken")
            instance.user.update_email(validated_data["email"])
            instance.send_invite(sender=current_user)
        if "type" in validated_data:
            instance.type = validated_data["type"]
            instance.save()
        return instance


class NodeMemberUpdateSerializer(serializers.ModelSerializer):
    """Serializer to update node member type."""

    user = custom_fields.KWArgsObjectField(
        related_model=FairfoodUser, write_only=True
    )

    class Meta:
        model = NodeMember
        fields = ("type", "user")

    def validate(self, attrs):
        """To perform function validate."""
        if "type" not in attrs:
            raise serializers.ValidationError("Type is required")
        return attrs

    def update(self, instance, validated_data):
        """To perform function update."""
        if validated_data["type"] == constants.NODE_MEMBER_TYPE_ADMIN:
            instance.make_admin(validated_data["user"])
        elif validated_data["type"] == constants.NODE_MEMBER_TYPE_MEMBER:
            instance.make_member(validated_data["user"])
        elif validated_data["type"] == constants.NODE_MEMBER_TYPE_VIEWER:
            instance.make_viewer(validated_data["user"])
        return instance


class NodeDocumentSerializer(serializers.ModelSerializer):
    """Serializer for node documents."""

    id = custom_fields.IdencodeField(read_only=True)
    node = custom_fields.IdencodeField(required=False)

    class Meta:
        fields = ("id", "name", "file", "node")
        model = NodeDocument

    def create(self, validated_data):
        """To perform function create."""
        validated_data["node"] = self.context["view"].kwargs["node"]
        current_user = self.context["request"].user
        validated_data["creator"] = current_user
        validated_data["updater"] = current_user
        document = NodeDocument.objects.create(**validated_data)
        document.log_activity()
        return document


class NodeSerializer(DynamicModelSerializer):
    """Serializer for Node model.

    Used as base for Farmer and Company
    """

    id = custom_fields.IdencodeField(read_only=True)
    type = serializers.IntegerField(required=False)
    name = serializers.CharField(required=False)
    phone = custom_fields.PhoneNumberField(required=False, allow_blank=True)
    latitude = serializers.FloatField(allow_null=True, default=0.0)
    longitude = serializers.FloatField(allow_null=True, default=0.0)
    image = custom_fields.RemovableImageField(required=False, allow_blank=True)
    full_name = serializers.CharField(read_only=True)
    date_invited = serializers.DateTimeField(read_only=True)
    date_joined = serializers.DateTimeField(read_only=True)

    projects = custom_fields.ManyToManyIdencodeField(
        source="participating_projects", read_only=True
    )
    members = custom_fields.ManyToManyIdencodeField(
        source="nodemembers", required=False, serializer=NodeMemberSerializer
    )
    managers = custom_fields.ManyToManyIdencodeField(read_only=True)
    documents = custom_fields.ManyToManyIdencodeField(
        read_only=True, serializer=NodeDocumentSerializer
    )
    supply_chains = custom_fields.ManyToManyIdencodeField(read_only=True)
    products = custom_fields.ManyToManyIdencodeField(
        read_only=True, source="unique_products"
    )
    verifier_supply_chains = custom_fields.ManyToManyIdencodeField(
        read_only=True, serializer=SupplyChainSerializer
    )
    features = custom_fields.IdencodeField(
        serializer=NodeFeaturesSerializer, read_only=True
    )

    supplier_for = serializers.SerializerMethodField("get_t2_buyers")
    buyer_for = serializers.SerializerMethodField("get_t2_suppliers")

    visible_fields = custom_fields.JsonField(required=False)
    profile_completion = serializers.FloatField(read_only=True)
    email_sent = serializers.BooleanField(read_only=True)
    primary_operation = custom_fields.IdencodeField(
        required=False, allow_null=True
    )

    user = None
    node = None
    supply_chain = None

    class Meta:
        """Meta data."""

        model = Node
        exd_trans_fls = [
            f.name
            for f in model._meta.fields
            if f.__class__.__name__ == "TranslationCharField"
        ]
        exclude = ["suppliers", "blockchain_account"] + exd_trans_fls
        extra_kwargs = {
            "creator": {"write_only": True, "required": False},
            "updater": {"write_only": True, "required": False},
        }

    def __init__(self, *args, **kwargs):
        """To perform function __init__."""
        super(NodeSerializer, self).__init__(*args, **kwargs)
        try:
            sc_id = comm_lib._decode(
                self.context["request"].query_params["supply_chain"]
            )
            if sc_id:
                self.supply_chain = SupplyChain.objects.get(id=sc_id)
            try:
                self.node = self.context["view"].kwargs["node"]
                self.user = self.context["request"].user
            except Exception:
                self.node = self.context["node"]  # In case of bulk
                self.user = self.context["user"]  # In case of bulk
        except Exception:
            pass

    def get_t2_suppliers(self, instance):
        """To perform function get_t2_suppliers."""
        if not self.supply_chain or not self.node:
            return []
        data = []
        for node in instance.get_t2_suppliers(
            through=self.node, supply_chain=self.supply_chain
        ):
            data.append(NodeBasicSerializer(node).data)
        return data

    def get_t2_buyers(self, instance):
        """To perform function get_t2_buyers."""
        if not self.supply_chain or not self.node:
            return []
        data = []
        for node in instance.get_t2_buyers(
            through=self.node, supply_chain=self.supply_chain
        ):
            data.append(NodeBasicSerializer(node).data)
        return data

    def validate(self, attrs):
        """To perform function validate."""
        if "country" in attrs and "province" in attrs:
            if (
                "latitude" not in attrs
                or "longitude" not in attrs
                or not attrs["latitude"]
                or not attrs["longitude"]
            ):
                attrs["latitude"] = COUNTRIES[attrs["country"]][
                    "sub_divisions"
                ][attrs["province"]]["latlong"][0]
                attrs["longitude"] = COUNTRIES[attrs["country"]][
                    "sub_divisions"
                ][attrs["province"]]["latlong"][1]
        return attrs

    def serializer_create(self, validated_data, NodeModel):
        """Overriding the create method.

        - Update Creator
        - Update Updator
        """
        try:
            current_user = self.context["request"].user
        except Exception:
            current_user = self.context["user"]
        validated_data["creator"] = current_user
        validated_data["updater"] = current_user
        admin = validated_data.get("admin", None)

        comm_lib._pop_out_from_dictionary(validated_data, ["admin"])
        primary_operation = validated_data.pop("primary_operation", None)
        try:
            node = NodeModel.objects.create(**validated_data)
        except IntegrityError as e:
            if "duplicate key value violates unique constraint" in str(e):
                raise ValidationError("Company already exist in the system.")
            raise e

        if node.is_company():
            NodeStats.objects.create(node=node)
            NodeFeatures.objects.create(node=node)
            # transaction.on_commit(lambda: reload_statistics.delay(stats.id))

        # if other_operations:
        #    for operation in other_operations:
        #        node.other_operations.add(operation)
        validated_data["primary_operation"] = primary_operation
        if admin:
            member = NodeMember.objects.create(
                node=node,
                user=admin,
                creator=current_user,
                updater=current_user,
                type=constants.NODE_MEMBER_TYPE_ADMIN,
            )
            member.log_added_activity()
            mem_user = member.user
            mem_user.default_node = node
            mem_user.status = USER_STATUS_COMPANY_ADDED
            mem_user.save()

        return node

    def to_representation(self, instance):
        """
        Pseudonimize data
        Args:
            instance:

        Returns:
        """
        data = super(NodeSerializer, self).to_representation(instance)
        try:
            sc_id = comm_lib._decode(
                self.context["request"].query_params["supply_chain"]
            )
            supply_chain = SupplyChain.objects.get(id=sc_id)
        except Exception:
            supply_chain = None
        try:
            current_user = self.context["request"].user
        except Exception:
            current_user = self.context.get("user")
        try:
            data["member_role"] = NodeMember.objects.get(
                node=instance, user=current_user
            ).type
        except Exception:
            data["member_role"] = 0
        try:
            base_node = self.context["view"].kwargs.get("node", None)
        except Exception:
            base_node = self.context.get("node", None)
        try:

            nsc = NodeSupplyChain.objects.filter(
                node=instance.id, supply_chain=supply_chain
            ).first()
            data["primary_operation"] = {
                "id": nsc.primary_operation.idencode,
                "name": nsc.primary_operation.name,
            }
        except Exception:
            data["primary_operation"] = None
            if instance.primary_operation:
                data["primary_operation"] = {
                    "id": instance.primary_operation.idencode,
                    "name": instance.primary_operation.name,
                }
        data["add_connections"] = False
        data["pseudonimized"] = False
        if base_node:
            if base_node.can_manage(instance, supply_chain=supply_chain):
                data["add_connections"] = True
            if not base_node.can_read(instance, supply_chain=supply_chain):
                data["pseudonimized"] = True
                hidden_fields = instance.get_hidden_fields()
                comm_lib._pop_out_from_dictionary(
                    data, ["members", "visible_fields", "documents"]
                )
                for field in hidden_fields:
                    if field in data:
                        data[field] = comm_lib._pseudonymize_data(
                            field, data[field]
                        )

            stats_obj, created = NodeStats.objects.get_or_create(
                node=base_node
            )
            # if created or stats_obj.is_outdated:
            #     transaction.on_commit(lambda: stats_obj.update_values())

            # reload_statistics.delay(stats_obj.id)
        return data

    def update(self, instance, validated_data):
        """To perform function update."""
        if "disclosure_level" in validated_data:
            if validated_data["disclosure_level"] == NODE_DISCLOSURE_CUSTOM:
                show = False
            else:
                show = True
            visible_fields = {}
            for field in VISIBLE_FIELDS[instance.type].keys():
                visible_fields[field] = show
            validated_data["visible_fields"] = json.dumps(visible_fields)
        data = super(NodeSerializer, self).update(instance, validated_data)
        instance.update_cache()
        return data


class FarmerSerializer(NodeSerializer):
    """Serializer for Farmer model."""

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
    total_area_in_use = serializers.FloatField(read_only=True)
    all_crop_types = serializers.CharField(read_only=True)
    total_income = serializers.DictField(read_only=True)
    cards = serializers.SerializerMethodField()
    is_editable = serializers.SerializerMethodField()

    class Meta(NodeSerializer.Meta):
        """Meta data."""

        model = Farmer

    def get_is_editable(self, instance):
        """A flag which provide editable option according to the current
        node."""
        try:
            current_node = self.context["view"].kwargs["node"]
        except KeyError:
            current_node = None
        if not current_node:
            return False

        if current_node in instance.managers.all():
            return True
        return False

    def get_cards(self, instance):
        """Function for filter latest active card details of farmer."""
        query_set = instance.cards.filter(status=101).order_by("-updated_on")[
            :1
        ]
        data = query_set.values("card_id", "fairid")
        return data

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

    def create(self, validated_data):
        """Overriding the create method.

        - Update Creator
        - Update Updator
        """
        if "admin" not in validated_data:
            try:
                current_user = self.context["request"].user
            except Exception:
                current_user = self.context["user"]
            validated_data["admin"] = current_user
        return super(FarmerSerializer, self).serializer_create(
            validated_data, Farmer
        )


class CompanySerializer(NodeSerializer):
    """Serializer for Company."""

    user = custom_fields.KWArgsObjectField(
        related_model=FairfoodUser, write_only=True, required=False
    )
    incharge = user_serializers.PersonSerializer(required=False)

    class Meta(NodeSerializer.Meta):
        """Meta data."""

        model = Company

    def create(self, validated_data):
        """Overriding the create method.

        - Add incharge
        - Update Creator
        - Update Updator
        """
        validated_data["updater"] = validated_data.pop("user")
        if "incharge" not in validated_data.keys():
            current_user = self.context["request"].user
            validated_data["incharge"] = {
                "first_name": current_user.first_name,
                "last_name": current_user.last_name,
                "email": current_user.email,
                "phone": current_user.phone,
                "dob": current_user.dob,
            }

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
        validated_data["admin"] = incharge.get_or_create_user()
        return super(CompanySerializer, self).serializer_create(
            validated_data, Company
        )

    @staticmethod
    def has_changed(instance, field_name, value):
        """To perform function has_changed."""
        return not getattr(instance, field_name) == value

    def get_changed_fields(self, instance, validated_data):
        """To perform function get_changed_fields."""
        field_titles = {
            "name": "Name",
            "identification_no": "registration number",
            "description_basic": "description",
            "description_full": "description",
            "house_name": "address",
            "street": "address",
            "city": "address",
            "province": "address",
            "country": "address",
            "latitude": "address",
            "longitude": "address",
            "zipcode": "address",
            "image": "image",
        }
        changed_fields = []
        for field_name, value in validated_data.items():
            if self.has_changed(instance, field_name, value):
                changed_fields.append(field_titles.get(field_name, ""))
        return list(set(changed_fields))

    @transaction.atomic
    def update(self, instance, validated_data):
        """Overriding the update method.

        - Change Incharge if updation exists
        - Update Updator
        """
        current_node = self.context["view"].kwargs["node"]
        incharge_changed_fields = []
        validated_data["updater"] = validated_data.pop("user")
        resend_invite = False
        try:
            supply_chain = comm_lib._decode(
                self.context["request"].query_params["supply_chain"]
            )
            nsc, created = NodeSupplyChain.objects.get_or_create(
                node=instance, supply_chain_id=supply_chain
            )
            nsc.primary_operation = validated_data["primary_operation"]
            nsc.save()
        except Exception:
            pass
        if "incharge" in validated_data.keys():
            if instance.incharge:
                incharge_changed_fields = (
                    user_serializers.PersonSerializer.get_changed_fields(
                        instance.incharge, validated_data["incharge"]
                    )
                )
            incharge_serializer = user_serializers.PersonSerializer(
                instance.incharge,
                data=validated_data["incharge"],
                context={"request": self.context["request"]},
                partial=True,
            )
            if not incharge_serializer.is_valid():
                raise BadRequest(incharge_serializer.errors)
            instance.incharge = incharge_serializer.save()
            instance.save()
            if "email" in validated_data["incharge"]:
                if not instance.date_joined:
                    nodemembers = instance.nodemembers.all()
                    if nodemembers.count() == 1:
                        nodemember = nodemembers.first()
                        if not nodemember.user.email_verified:
                            if nodemember.user.nodes.count() != 1:
                                user = nodemember.user
                                user.id = None
                                user.save()
                                nodemember.user = user
                                nodemember.save()
                            nodemember.user.update_email(
                                validated_data["incharge"]["email"]
                            )
                            resend_invite = True
            validated_data.pop("incharge")
        changed_fields = (
            self.get_changed_fields(instance, validated_data)
            + incharge_changed_fields
        )
        changed_fields = [i.strip() for i in changed_fields if i.strip()]
        company = super(CompanySerializer, self).update(
            instance, validated_data
        )
        if changed_fields:
            changed_fields_text = comm_lib._list_to_sentence(changed_fields)
            Activity.log(
                event=instance,
                activity_type=act_constants.UPDATED_NODE_DETAILS,
                object_id=instance.id,
                object_type=act_constants.OBJECT_TYPE_NODE,
                user=instance.updater,
                node=instance,
                prevent_duplication=False,
                context={"updated_fields": changed_fields_text},
            )
        if resend_invite:
            for invite in company.invitations_received.filter(
                inviter=current_node, email_sent=True
            ):
                invite.send_invite()
        return company

    def to_representation(self, instance):
        """Convert the object instance to a dictionary representation.

        This method overrides the superclass`s to_representation method and
        adds additional data to the serialized representation. It includes the
        'is_admin' key in the returned dictionary, indicating whether the
        current user is an admin for the company.

        Parameters:
        - instance: The object instance to serialize.

        Returns:
        - dict: The dictionary representation of the serialized object.
        """
        data = super(CompanySerializer, self).to_representation(instance)

        # initialize is_admin key
        data["is_admin"] = False

        # Get current user from request
        current_user = self.context["request"].user

        # Update field with member type or user typr.
        if current_user.is_fairtrace_admin:
            data["is_admin"] = True
        member = instance.nodemembers.filter(user=current_user).last()
        if member and member.type == NODE_MEMBER_TYPE_ADMIN:
            data["is_admin"] = True

        return data


class NodeListSerializer(DynamicModelSerializer):
    """Serializer for node to be used in drop-downs. Returns minimal details,

    - Name
    - ID
    - Type
    """

    id = custom_fields.IdencodeField(read_only=True)
    name = serializers.CharField(source="full_name")

    class Meta:
        model = Node
        fields = ("id", "name", "type", "image")


class CompanyListSerializer(serializers.ModelSerializer):
    """Serializer to list company details."""

    id = custom_fields.IdencodeField(read_only=True)
    connected = serializers.SerializerMethodField("is_connected")
    connectable = serializers.SerializerMethodField("is_connectable")

    class Meta:
        """Meta data."""

        model = Company
        fields = (
            "id",
            "name",
            "image",
            "connected",
            "connectable",
            "email_sent",
        )

    def is_connected(self, instance):
        """Check whether the node_ptr of the company instance is connected with
        the current node through the buyer chain.

        Args:
            instance (Company()):
        Returns:
            Boolean (True/False)
        """
        node = self.context["view"].kwargs["node"]
        sc_id = self.context["request"].query_params.get("supply_chain", None)
        try:
            supply_chain = SupplyChain.objects.get(id=comm_lib._decode(sc_id))
        except ObjectDoesNotExist:
            supply_chain = None
        buyer_chain_nodes = node.get_buyer_chain(supply_chain=supply_chain)[0]
        if instance.node_ptr in buyer_chain_nodes:
            return True
        return False

    def is_connectable(self, instance):
        """To perform function is_connectable."""
        node = self.context["view"].kwargs["node"]
        if instance.node_ptr == node:
            return False
        sc_id = self.context["request"].query_params.get("supply_chain", None)
        if sc_id:
            supply_chain = SupplyChain.objects.get(id=comm_lib._decode(sc_id))
        else:
            supply_chain = None
        if instance.node_ptr in node.get_suppliers(supply_chain=supply_chain):
            return False
        return True


class FarmerListSerializer(serializers.ModelSerializer):
    """Serializer to list company details."""

    id = custom_fields.IdencodeField(read_only=True)
    connected = serializers.SerializerMethodField("is_connected")

    class Meta:
        """Meta data."""

        model = Farmer
        fields = ("id", "first_name", "last_name", "image", "connected")

    def is_connected(self, instance):
        """To perform function is_connected."""
        connected = False

        node = self.context["view"].kwargs["node"]
        sc_id = self.context["request"].query_params.get("supply_chain", None)
        if sc_id:
            supply_chain = SupplyChain.objects.get(id=comm_lib._decode(sc_id))
        else:
            supply_chain = None
        if instance.node_ptr in node.get_suppliers(supply_chain=supply_chain):
            connected = True
        return connected


class FarmerExportSerializer(serializers.ModelSerializer):
    """Serializer to convert farmer data into human readable json to be
    exported as an excel."""

    id = custom_fields.IdencodeField()
    phone = custom_fields.PhoneNumberField(required=False, allow_blank=True)

    class Meta:
        model = Farmer
        fields = "__all__"

    def to_representation(self, instance):
        """To perform function to_representation."""
        supply_chain = self.context.get("supply_chain", None)

        data = super(FarmerExportSerializer, self).to_representation(instance)
        phone_data = data["phone"]
        if supply_chain:
            nsc = instance.nodesupplychain_set.get(supply_chain=supply_chain)
            data["primary_operation"] = nsc.primary_operation.name
        else:
            data["primary_operation"] = ""
        data["dial_code"] = DIAL_CODE_NAME_MAP.get(phone_data["dial_code"], "")
        data["phone"] = phone_data["phone"]
        return data


class NodeWalletSerializer(serializers.ModelSerializer):
    """Serializer for blockchain wallet."""

    id = custom_fields.IdencodeField()

    class Meta:
        model = BlockchainWallet
        fields = (
            "id",
            "account_id",
            "public",
            "wallet_type",
            "default",
            "explorer_url",
        )


class ValidateFarmerIDSerializer(serializers.Serializer):
    """Serializer to check the farmer id validity."""

    id = serializers.CharField()
    node = serializers.CharField()
    supply_chain = serializers.CharField()

    def _validate_farmer_id(self, obj):
        """To perform function _validate_farmer_id."""
        response = {"valid": True, "name": "", "message": "", "id": ""}
        try:
            farmer = Farmer.objects.filter(
                identification_no=obj["id"],
                managers=comm_lib._decode(obj["node"]),
                nodesupplychain__supply_chain=comm_lib._decode(
                    obj["supply_chain"]
                ),
            ).first()
            response["name"] = farmer.name
            response["id"] = farmer.idencode
        except Exception:
            response["valid"] = False
            try:
                Farmer.objects.get(identification_no=obj["id"])
            except Exception:
                response["message"] = "Invalid farmer Id"
            response[
                "message"
            ] = "Farmer not connected to this company/supply chain"
        return response

    def to_representation(self, obj):
        """Overriding the value returned when returning the serializer."""
        response = self._validate_farmer_id(obj)
        return response
