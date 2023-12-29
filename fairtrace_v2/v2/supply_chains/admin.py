from common.admin import BaseAdmin
from django.contrib import admin
from modeltranslation.admin import TranslationAdmin
from v2.supply_chains.cache_handlers import clear_connection_cache
from v2.supply_chains.models import BlockchainWallet
from v2.supply_chains.models import BulkExcelUploads
from v2.supply_chains.models import Company
from v2.supply_chains.models import Connection
from v2.supply_chains.models import ConnectionTag
from v2.supply_chains.models import Farmer
from v2.supply_chains.models import Invitation
from v2.supply_chains.models import Label
from v2.supply_chains.models import Node
from v2.supply_chains.models import NodeDocument
from v2.supply_chains.models import NodeFeatures
from v2.supply_chains.models import NodeManager
from v2.supply_chains.models import NodeMember
from v2.supply_chains.models import NodeSupplyChain
from v2.supply_chains.models import Operation
from v2.supply_chains.models import OperationSupplyChain
from v2.supply_chains.models import SupplyChain
from v2.supply_chains.models import Verifier
from v2.supply_chains.models import WalletTokenAssociation
from v2.supply_chains.models.profile import FarmerAttachment
from v2.supply_chains.models.profile import FarmerPlot
from v2.supply_chains.models.profile import FarmerReference
from v2.supply_chains.models.profile import Reference
from v2.supply_chains.models.supply_chain import UploadFarmerMapping


# Register your models here.


def clear_filesystem_caching(modeladmin, request, queryset):
    """To perform function clear_filesystem_caching."""
    if queryset.count() > 10:
        raise Exception("Select less than 10 items")
    for cmp in queryset:
        clear_connection_cache(cmp.id)


def add_to_all_supplychains(modeladmin, request, queryset):
    """To perform function add_to_all_supplychains."""
    for comp in queryset:
        for sc in SupplyChain.objects.all():
            nsc = NodeSupplyChain(node=comp, supply_chain=sc)
            nsc.save()


class NodeMemberInline(admin.TabularInline):
    """In-line view function for Sub-element model."""

    model = NodeMember
    extra = 0
    list_select_related = ("user__name", "user__id")
    readonly_fields = ("vtoken",)


class UploadFarmerMappingInline(admin.TabularInline):
    """In-line view function for Sub-element model."""

    model = UploadFarmerMapping
    extra = 0
    fk_name = "upload"
    fields = ("farmer",)
    can_delete = False
    readonly_fields = ("farmer",)


class OperationSupplyChainInline(admin.TabularInline):
    """In-line view function for Sub-element model."""

    model = OperationSupplyChain
    extra = 0
    fields = ("supply_chain", "operation", "active")


class OperationsAdmin(TranslationAdmin):
    """Class to handle OperationsAdmin and functions."""

    list_display = ("name", "node_type", "idencode")
    inlines = [
        OperationSupplyChainInline,
    ]


class CompanyAdmin(BaseAdmin):
    """Class to handle CompanyAdmin and functions."""

    list_display = ("name", "idencode")
    search_fields = ["name"]
    inlines = [
        NodeMemberInline,
    ]
    actions = [add_to_all_supplychains, clear_filesystem_caching]


class NodeAdmin(BaseAdmin):
    """Class to handle NodeAdmin and functions."""

    search_fields = ("description_basic", "email", "pk")


class FarmerAdmin(BaseAdmin):
    """Class to handle FarmerAdmin and functions."""

    list_display = ("first_name", "last_name", "idencode")
    inlines = [
        NodeMemberInline,
    ]
    search_fields = [
        "first_name",
        "last_name",
        "creator__first_name",
        "creator__last_name",
    ]
    list_filter = ("creator",)


class NodeMemberAdmin(BaseAdmin):
    """Class to customize EntityAdmin table."""

    list_display = ("id", "node", "user", "idencode")


class NodeDocumentAdmin(BaseAdmin):
    """Customize Node documents admin."""

    list_display = ("id", "name", "node", "idencode")


class SupplyChainAdmin(BaseAdmin):
    """Customize SupplyChain Model."""

    list_display = ("id", "name", "active", "idencode")
    inlines = [
        OperationSupplyChainInline,
    ]


class InvitationAdmin(BaseAdmin):
    """Customize Invitation model."""

    list_display = ("id", "inviter", "connection", "type")


class ConnectionTagAdmin(BaseAdmin):
    """Customize ConnectionTag model."""

    def buyer(self, object):
        """To perform function buyer."""
        return object.buyer_connection.buyer

    def through(self, object):
        """To perform function through."""
        return object.buyer_connection.supplier

    def supplier(self, object):
        """To perform function supplier."""
        return object.supplier_connection.supplier

    list_display = ("id", "supplier", "through", "buyer")


class ConnectionAdmin(BaseAdmin):
    """Customize Connection model."""

    list_display = ("id", "buyer", "supplier", "supply_chain")
    list_select_related = (
        "buyer",
        "buyer__farmer",
        "buyer__company",
        "supplier",
        "supplier__farmer",
        "supplier__company",
        "supply_chain",
    )


class NodeSupplyChainAdmin(BaseAdmin):
    """Customize Connection model."""

    list_display = (
        "idencode",
        "node",
        "supply_chain",
    )


class BlockchainWalletAdmin(BaseAdmin):
    """Customize BlockchainWallet admin."""

    list_display = ("id", "public")
    search_fields = ["public"]
    readonly_fields = ("node", "block_chain_request")


class NodeFeaturesAdmin(BaseAdmin):
    """Class to handle NodeFeaturesAdmin and functions."""

    readonly_fields = BaseAdmin.readonly_fields + ("node",)


class LabelAdmin(BaseAdmin):
    """Class to handle LabelAdmin and functions."""

    readonly_fields = BaseAdmin.readonly_fields + ("added_by",)


class WalletTokenAssociationAdmin(BaseAdmin):
    """Class to handle WalletTokenAssociationAdmin and functions."""

    readonly_fields: tuple = BaseAdmin.readonly_fields + (
        "block_chain_request",
        "node_wallet",
    )


class BulkExcelUploadsAdmin(BaseAdmin):
    """Class to handle BulkExcelUploadsAdmin and functions."""

    readonly_fields = BaseAdmin.readonly_fields
    autocomplete_fields = ("node",)
    inlines = [UploadFarmerMappingInline]


class FarmerPlotAdmin(BaseAdmin):
    """Class to handle FarmerPlotAdmin and functions."""

    autocomplete_fields = ("farmer",)


class FarmerAttachmentAdmin(BaseAdmin):
    """Class to handle FarmerAttachmentAdmin and functions."""

    autocomplete_fields = ("farmer", "node")


admin.site.register(Operation, OperationsAdmin)
admin.site.register(OperationSupplyChain, BaseAdmin)
admin.site.register(Company, CompanyAdmin)
admin.site.register(Farmer, FarmerAdmin)
admin.site.register(NodeManager, BaseAdmin)
admin.site.register(NodeMember, NodeMemberAdmin)
admin.site.register(NodeDocument, NodeDocumentAdmin)
admin.site.register(SupplyChain, SupplyChainAdmin)
admin.site.register(Connection, ConnectionAdmin)
admin.site.register(Invitation, InvitationAdmin)
admin.site.register(ConnectionTag, ConnectionTagAdmin)
admin.site.register(NodeSupplyChain, NodeSupplyChainAdmin)
admin.site.register(BlockchainWallet, BlockchainWalletAdmin)
admin.site.register(Verifier, BaseAdmin)
admin.site.register(NodeFeatures, NodeFeaturesAdmin)
admin.site.register(Label, LabelAdmin)
admin.site.register(WalletTokenAssociation, WalletTokenAssociationAdmin)
admin.site.register(BulkExcelUploads, BulkExcelUploadsAdmin)
admin.site.register(Node, NodeAdmin)
admin.site.register(Reference, BaseAdmin)
admin.site.register(FarmerReference, BaseAdmin)
admin.site.register(FarmerPlot, FarmerPlotAdmin)
admin.site.register(FarmerAttachment, FarmerAttachmentAdmin)
