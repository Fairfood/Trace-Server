from common.admin import BaseAdmin
from django.contrib import admin

from .models import AttachedBatchClaim
from .models import AttachedBatchCriterion
from .models import AttachedClaim
from .models import AttachedCompanyClaim
from .models import AttachedCompanyCriterion
from .models import AttachedCriterion
from .models import Claim
from .models import Criterion
from .models import CriterionField
from .models import FieldResponse
from .models import TransactionClaim


# Register your models here.


def create_new_version(modeladmin, request, queryset):
    """To perform function create_new_version."""
    for item in queryset:
        item.create_new_version()


create_new_version.short_description = "Create new version of the claim"


class CriterionInline(admin.TabularInline):
    """In-line view function for Sub-element model."""

    model = Criterion
    extra = 0
    fields = (
        "name",
        "description",
        "is_mandatory",
        "verification_type",
        "verifier",
    )


class CriterionFieldInline(admin.TabularInline):
    """In-line view function for Sub-element model."""

    model = CriterionField
    extra = 0
    fields = ("title", "description", "options", "multiple_options", "type")


class BatchCriterionInline(admin.TabularInline):
    """In-line view function for Sub-element model."""

    model = AttachedBatchCriterion
    extra = 0
    fields = (
        "criterion",
        "attached_from",
        "status",
        "blockchain_address",
        "verification_info",
    )


class CompanyCriterionInline(admin.TabularInline):
    """In-line view function for Sub-element model."""

    model = AttachedCompanyCriterion
    extra = 0
    fields = (
        "criterion",
        "attached_from",
        "status",
        "blockchain_address",
        "verification_info",
    )


class AttachedCriterionAdmin(BaseAdmin):
    """Class to handle AttachedCriterionAdmin and functions."""

    readonly_fields = BaseAdmin.readonly_fields + ("criterion",)


class BatchCriterionAdmin(BaseAdmin):
    """Class to handle BatchCriterionAdmin and functions."""

    readonly_fields = BaseAdmin.readonly_fields + (
        "batch_claim",
        "criterion",
    )
    list_select_related = ("batch_claim__claim", "batch_claim__batch")


class CompanyCriterionAdmin(BaseAdmin):
    """Class to handle CompanyCriterionAdmin and functions."""

    readonly_fields = BaseAdmin.readonly_fields + (
        "company_claim",
        "criterion",
    )
    list_select_related = (
        "company_claim__claim",
        "company_claim__node",
        "company_claim__node__company",
    )


class ClaimsAdmin(BaseAdmin):
    """Class to handle ClaimsAdmin and functions."""

    readonly_fields = BaseAdmin.readonly_fields + ("reference", "owners")
    list_display = ("name", "type", "scope", "idencode")
    list_filter = (
        "type",
        "scope",
    )
    inlines = [
        CriterionInline,
    ]
    actions = [create_new_version]


class CriterionAdmin(BaseAdmin):
    """Class to handle CriterionAdmin and functions."""

    readonly_fields = BaseAdmin.readonly_fields + ("reference",)
    inlines = [CriterionFieldInline]


class AttachedClaimAdmin(BaseAdmin):
    """Class to handle AttachedClaimAdmin and functions."""

    list_display = ("claim", "idencode")
    readonly_fields = BaseAdmin.readonly_fields + (
        "claim",
        "verifier",
        "attached_by",
    )
    list_select_related = ("claim",)


class BatchClaimAdmin(BaseAdmin):
    """Class to handle BatchClaimAdmin and functions."""

    list_display = ("batch", "claim", "idencode")
    readonly_fields = BaseAdmin.readonly_fields + (
        "batch",
        "claim",
        "verifier",
        "attached_by",
    )
    inlines = [
        BatchCriterionInline,
    ]
    list_select_related = ("claim", "batch", "batch__product")


class CompanyClaimAdmin(BaseAdmin):
    """Class to handle CompanyClaimAdmin and functions."""

    list_display = ("node", "claim", "idencode")
    readonly_fields = BaseAdmin.readonly_fields + (
        "node",
        "claim",
        "verifier",
        "attached_by",
    )
    inlines = [
        CompanyCriterionInline,
    ]
    list_select_related = ("claim", "node", "node__company")


class TransactionClaimAdmin(BaseAdmin):
    """Class to handle TransactionClaimAdmin and functions."""

    readonly_fields = BaseAdmin.readonly_fields + ("transaction", "claim")


class FieldResponseAdmin(BaseAdmin):
    """Class to handle FieldResponseAdmin and functions."""

    readonly_fields = BaseAdmin.readonly_fields + (
        "criterion",
        "field",
        "added_by",
    )
    list_select_related = ("field",)


admin.site.register(Claim, ClaimsAdmin)
admin.site.register(Criterion, CriterionAdmin)
admin.site.register(TransactionClaim, TransactionClaimAdmin)

admin.site.register(AttachedClaim, AttachedClaimAdmin)
admin.site.register(AttachedBatchClaim, BatchClaimAdmin)
admin.site.register(AttachedCompanyClaim, CompanyClaimAdmin)

admin.site.register(AttachedCriterion, AttachedCriterionAdmin)
admin.site.register(AttachedBatchCriterion, BatchCriterionAdmin)
admin.site.register(AttachedCompanyCriterion, CompanyCriterionAdmin)

admin.site.register(CriterionField, BaseAdmin)
admin.site.register(FieldResponse, FieldResponseAdmin)
