"""Serializers for admin dashboard related APIs."""
from common import library as comm_lib
from common.drf_custom import fields as custom_fields
from common.exceptions import BadRequest
from django.db import transaction as django_transaction
from rest_framework import serializers
from v2.accounts.constants import USER_STATUS_COMPANY_ADDED
from v2.accounts.models import FairfoodUser
from v2.accounts.serializers import user as user_serializers
from v2.activity import constants as act_constants
from v2.activity.models import Activity
from v2.dashboard.models import CITheme
from v2.dashboard.models import DashboardTheme
from v2.products import constants as prod_constants
from v2.products.models import Product
from v2.products.serializers.product import ProductSerializer
from v2.supply_chains import constants
from v2.supply_chains.constants import NODE_INVITED_BY_FFADMIN
from v2.supply_chains.models import AdminInvitation
from v2.supply_chains.models import Company
from v2.supply_chains.models import Node
from v2.supply_chains.models import NodeFeatures
from v2.supply_chains.models import NodeMember
from v2.supply_chains.models import NodeSupplyChain
from v2.supply_chains.models import SupplyChain
from v2.supply_chains.models import Verifier
from v2.supply_chains.serializers import node as node_serializers
from v2.supply_chains.serializers import (
    supply_chain as supply_chain_serializers,
)
from v2.supply_chains.serializers.supply_chain import SupplyChainSerializer


class FFAdminCompanyInviteSerializer(node_serializers.NodeSerializer):
    """Serializer for Company."""

    incharge = user_serializers.PersonSerializer(required=False)
    name = serializers.CharField(required=False)
    company = custom_fields.IdencodeField(
        required=False,
        serializer=node_serializers.CompanySerializer,
        related_model=Company,
    )
    # primary_operation = custom_fields.IdencodeField(
    # serializer=OperationSerializer)
    # supply_chains = custom_fields.ManyToManyIdencodeField(
    # related_model=SupplyChain)
    supply_chains = supply_chain_serializers.NodeSupplyChainSerializer(
        many=True
    )

    class Meta:
        """Meta data."""

        model = Company
        fields = (
            "id",
            "name",
            "identification_no",
            "street",
            "country",
            "province",
            "city",
            "zipcode",
            "supply_chains",
            "incharge",
            "company",
        )

    def validate(self, attrs):
        """To perform function validate."""
        if "incharge" in attrs:
            if "email" in attrs["incharge"]:
                attrs["incharge"]["email"] = attrs["incharge"]["email"].lower()
        return attrs

    @django_transaction.atomic
    def create(self, validated_data):
        """Overriding the create method.

        - Add incharge
        - Update Creator
        - Update Updator
        """
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
            validated_data["admin"] = incharge.get_or_create_user()
            validated_data["plan"] = constants.NODE_PLAN_PREMIUM
        else:
            validated_data["node_object"] = validated_data["company"]

        supply_chains = validated_data.pop("supply_chains")

        node = super(FFAdminCompanyInviteSerializer, self).serializer_create(
            validated_data, Company
        )

        admin_invitation = AdminInvitation.objects.create(invitee=node)
        for data in supply_chains:
            nsc, created = NodeSupplyChain.objects.get_or_create(
                node=node, supply_chain=data["supply_chain"]
            )
            nsc.primary_operation = data["primary_operation"]
            nsc.save()
            if data["verifier"]:
                verifier, created = Verifier.objects.get_or_create(
                    node=node, supply_chain=data["supply_chain"]
                )
            admin_invitation.node_supply_chains.add(nsc)
        if created:
            nsc.invited_by = constants.NODE_INVITED_BY_FFADMIN
            nsc.save()
            admin_invitation.send_invite()
            admin_invitation.log_activity()
        else:
            raise BadRequest("Node already exists")
        django_transaction.on_commit(lambda: node.stats.update_values())
        return node

    def to_representation(self, instance):
        """Representation."""
        data = {"status": "Success", "id": instance.idencode}
        return data


class FFAdminCompanyListSerializer(serializers.ModelSerializer):
    """Serializer to list company details."""

    id = custom_fields.IdencodeField(read_only=True)
    supply_chain_count = serializers.IntegerField(read_only=True)

    # primary_operation = custom_fields.IdencodeField(
    #    serializer=OperationSerializer)

    class Meta:
        """Meta data."""

        model = Company
        fields = (
            "id",
            "name",
            "image",
            "status",
            "country",
            "supply_chain_count",
        )


class FFAdminCompanySerializer(node_serializers.NodeSerializer):
    """Serializer for Company."""

    user = custom_fields.KWArgsObjectField(
        related_model=FairfoodUser, write_only=True
    )
    incharge = user_serializers.PersonSerializer(required=False)

    class Meta(node_serializers.NodeSerializer.Meta):
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
        # validated_data['admin'] = incharge.get_or_create_user()
        return super(FFAdminCompanySerializer, self).serializer_create(
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
            "primary_operation": "type",
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

    @django_transaction.atomic
    def update(self, instance, validated_data):
        """Overriding the update method.

        - Change Incharge if updation exists
        - Update Updator
        """
        resend_invite = False
        incharge_changed_fields = []
        validated_data["updater"] = validated_data.pop("user")
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
        company = super(FFAdminCompanySerializer, self).update(
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
            for invite in company.invitations_received.filter(email_sent=True):
                invite.send_invite()
        return company


class FFAdminSupplyChainViewSerializer(serializers.ModelSerializer):
    """Serialize node stats."""

    id = custom_fields.IdencodeField(read_only=True)
    products = custom_fields.ManyToManyIdencodeField(
        serializer=ProductSerializer, required=False
    )
    active_actor_count = serializers.IntegerField(read_only=True)
    farmer_count = serializers.IntegerField(read_only=True)

    class Meta:
        """Meta Data."""

        model = SupplyChain
        fields = (
            "id",
            "name",
            "products",
            "active_actor_count",
            "farmer_count",
        )


class FFAdminNodeMemberSerializer(serializers.ModelSerializer):
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
    email = serializers.CharField(write_only=True, required=False)
    dob = serializers.DateField(required=False)
    phone = custom_fields.PhoneNumberField(required=False, allow_blank=True)
    address = serializers.CharField(required=False)
    image = serializers.ImageField(required=False)
    type = serializers.IntegerField(required=False)

    terms_accepted = serializers.BooleanField(required=False)
    privacy_accepted = serializers.BooleanField(required=False)
    email_verified = serializers.BooleanField(required=False)

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
        node_id = self.context["view"].kwargs["pk"]
        node = Node.objects.get(id=node_id)

        current_user = self.context["request"].user
        validated_data["creator"] = current_user
        validated_data["updater"] = current_user
        validated_data["status"] = USER_STATUS_COMPANY_ADDED
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
            node=node, user=validated_data["user"]
        )

        if created:
            member.type = validated_data["type"]
            member.creator = current_user
            member.updater = current_user
            member.save()
            member.send_invite()
            member.log_added_activity()
            member.unhide_notifications()
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


class FFAdminSupplyChainSerializer(serializers.ModelSerializer):
    """Class to handle FFAdminSupplyChainSerializer and functions."""

    id = custom_fields.IdencodeField()

    class Meta:
        """Meta Data."""

        model = NodeSupplyChain
        fields = ("id", "name", "farmer_count", "image")


class FFAdminResendInviteSerializer(serializers.Serializer):
    """Serializer for resend companies which is not joined."""

    def create(self, validated_data):
        """Overriding the create method."""
        invitee = self.context["view"].kwargs["pk"]
        self.context["view"].kwargs["user"]

        invitee = Node.objects.get(id=invitee)

        nsc = (
            NodeSupplyChain.objects.filter(
                node=invitee, invited_by=NODE_INVITED_BY_FFADMIN
            )
            .order_by("created_on")
            .first()
        )
        supply_chain = nsc.supply_chain
        invites = AdminInvitation.objects.get(
            node_supply_chains__supply_chain=supply_chain, invitee=invitee
        )

        if invites:
            invites.send_invite()
        return {"status": True, "message": "Invite sent"}

    def to_representation(self, instance):
        """To perform function to_representation."""
        return instance


class FFAdminProductSerializer(serializers.ModelSerializer):
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
            product = super(FFAdminProductSerializer, self).create(
                validated_data
            )
            product.create_token()
        return product

    def update(self, instance, validated_data):
        """To perform function update."""
        if "image" in validated_data:
            validated_data["image_name"] = validated_data["image"]
        product = super(FFAdminProductSerializer, self).update(
            instance, validated_data
        )
        return product


class FFAdminNodeThemeViewSerializer(serializers.ModelSerializer):
    """Theme serializer."""

    id = custom_fields.IdencodeField(read_only=True)
    dashboard_theming = serializers.BooleanField(required=False)
    consumer_interface_theming = serializers.BooleanField(required=False)
    node = custom_fields.IdencodeField(read_only=True)

    class Meta:
        model = NodeFeatures
        fields = (
            "id",
            "node",
            "dashboard_theming",
            "consumer_interface_theming",
        )

    @django_transaction.atomic
    def create(self, validated_data):
        """To perform function create."""
        node_id = self.context["view"].kwargs["pk"]
        node = Node.objects.get(id=node_id)
        validated_data["node"] = node

        nodefeature = getattr(node, "features", None)

        if nodefeature is None:
            nodefeature = super(FFAdminNodeThemeViewSerializer, self).create(
                validated_data
            )
        else:
            nodefeature = super(FFAdminNodeThemeViewSerializer, self).update(
                nodefeature, validated_data
            )
        if (
            "consumer_interface_theming" in validated_data
            and validated_data["consumer_interface_theming"] is True
        ):
            if not node.themes.exists():
                default_theme = CITheme.objects.filter(is_public=True).first()
                default_theme.id = None
                default_theme.node = node
                default_theme.name = f"theme{node.idencode}"
                default_theme.is_public = False
                default_theme.save()
        if (
            "dashboard_theming" in validated_data
            and validated_data["dashboard_theming"] is True
        ):
            if not getattr(node, "dashboard_theme", None):
                default_theme = DashboardTheme.objects.get(default=True)
                default_theme.id = None
                default_theme.node = node
                default_theme.default = False
                default_theme.save()

        return nodefeature


class FFAdminNodeVerifierSerializer(serializers.ModelSerializer):
    """Verifier serializer."""

    id = custom_fields.IdencodeField(read_only=True)
    node = custom_fields.IdencodeField(read_only=True)
    supply_chain = custom_fields.ManyToManyIdencodeField(
        related_model=SupplyChain
    )

    class Meta:
        model = Verifier
        fields = ("id", "node", "supply_chain")

    def create(self, validated_data):
        """To perform function create."""
        supply_chains = validated_data.pop("supply_chain")
        node_id = self.context["view"].kwargs["pk"]
        node = Node.objects.get(id=node_id)

        for supply_chain in supply_chains:
            verifier, created = Verifier.objects.get_or_create(
                node=node, supply_chain=supply_chain
            )
            if not created:
                raise BadRequest("SupplyChain already exists")

        return verifier

    def to_representation(self, instance):
        """Representation."""

        data = {
            "id": instance.idencode,
            "supply_chain": {
                "id": instance.supply_chain.idencode,
                "name": instance.supply_chain.name,
            },
            "node": instance.node.idencode,
        }
        return data
